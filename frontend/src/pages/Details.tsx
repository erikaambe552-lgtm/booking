import { useEffect, useRef, useState } from "react";
import { FiMapPin, FiInfo, FiCheck, FiAlertCircle } from "react-icons/fi";
import { PhotoFrame } from "../components/Brand";
import { BeachVenueBooking, MountainGuideBooking } from "../components/Booking";
import { Empty, Spinner } from "../components/Cards";
import { locationText, peso } from "../lib/format";
import type { Route } from "../lib/router";
import { useApi } from "../lib/useApi";
import { useLiveEvent, useRealtime } from "../lib/realtime";
import type { Availability, DestinationDetail } from "../lib/types";
import { mediaUrl } from "../lib/api";

export default function Details({ slug, route }: { slug: string; route: Route }) {
  const { data: d, error, loading } = useApi<DestinationDetail>(`/destinations/${slug}/`);
  const av = useApi<Availability>(d?.is_bookable ? `/destinations/${slug}/availability/` : null);
  const [img, setImg] = useState(0);
  // Live availability: when anyone books/cancels here, the server pushes the change.
  const { watch } = useRealtime();
  useEffect(() => { watch(slug); return () => watch(null); }, [slug, watch]);
  useLiveEvent(["availability.changed"], (e) => { if (e.destination === slug) av.reload(); });
  const bookRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (d && route.query.get("book") === "1") setTimeout(() => bookRef.current?.scrollIntoView({ behavior: "smooth" }), 300);
  }, [d, route]);

  if (loading) return <div className="page container"><Spinner /></div>;
  if (error || !d) return <div className="page container"><Empty title="Destination not found">{error}</Empty></div>;

  const photos = d.images.map((i) => ({ url: i.src, credit: i.credit_line, caption: i.caption }));
  const main = photos[img] ?? null;
  const isBeach = d.category === "BEACH";
  const items = d.services.items;

  return (
    <div className="page">
      <section className="detail-hero">
        <PhotoFrame photo={main} category={d.category} seed={d.id} alt={d.name} className="detail-hero-img" />
        <div className="detail-hero-shade" />
        <div className="container detail-hero-copy">
          <span className={`tag ${isBeach ? "tag-sea" : "tag-violet"}`}>{isBeach ? "Beach · Venue booking" : "Mountain · Tour-guide booking"}</span>
          <h1>{d.name}</h1>
          <p><FiMapPin /> {d.municipality ? locationText(d) : "Biliran Province · municipality being verified"}</p>
        </div>
      </section>

      {photos.length > 1 && (
        <div className="container gallery">
          {photos.map((p, i) => (
            <button key={i} className={i === img ? "on" : ""} onClick={() => setImg(i)}><img src={mediaUrl(p.url)} alt={p.caption || d.name} /></button>
          ))}
        </div>
      )}

      <div className="container detail-grid">
        <div className="detail-main">
          {!d.location_verified && (
            <div className="notice"><FiAlertCircle /> <span><b>Location under verification.</b> {d.location_note}</span></div>
          )}
          <h2>About</h2>
          <p className="lead">{d.short_description}</p>
          {d.description && <p>{d.description}</p>}

          <div className="info-cols">
            <div>
              <h3>Amenities</h3>
              {d.amenities.length ? <ul className="ticks">{d.amenities.map((a) => <li key={a}><FiCheck /> {a}</li>)}</ul>
                : <p className="muted">Not yet verified — confirm with the operator.</p>}
            </div>
            <div>
              <h3>Activities</h3>
              {d.activities.length ? <ul className="ticks">{d.activities.map((a) => <li key={a}><FiCheck /> {a}</li>)}</ul>
                : <p className="muted">Not yet listed.</p>}
            </div>
          </div>

          <h3>{isBeach ? "Venues & prices" : "Tour guides & prices"}</h3>
          {items.length === 0 ? <p className="muted">No verified {isBeach ? "venue" : "guide"} has been configured yet, so prices aren't shown.</p> : (
            <div className="svc-list">
              {d.services.type === "VENUE" ? d.services.items.map((v) => (
                <div className="svc" key={v.id}>
                  <div><b>{v.name}</b>{v.is_demo && <span className="demo-pill">Simulated</span>}<p className="muted small">{v.description}</p></div>
                  <div className="svc-price">{peso(v.base_price)}<small>per slot · {v.included_guests} guests incl. · +{peso(v.price_per_extra_guest)}/extra</small></div>
                </div>
              )) : d.services.items.map((g) => (
                <div className="svc" key={g.id}>
                  <div><b>{g.display_name}</b>{g.is_demo && <span className="demo-pill">Simulated</span>}<p className="muted small">{g.bio}</p></div>
                  <div className="svc-price">{peso(g.price_per_group)}<small>guide fee · +{peso(g.price_per_participant)}/hiker · max {g.max_participants}</small></div>
                </div>
              ))}
            </div>
          )}

          <h3>Reservation instructions</h3>
          <p>{d.reservation_instructions || "—"}</p>
          {d.images.length > 0 && <p className="muted small">Photo credits: {d.images.map((i) => i.credit_line).join(" · ")}</p>}
        </div>

        <aside className="detail-side" ref={bookRef}>
          {d.is_bookable ? (
            av.loading && !av.data ? <Spinner /> : isBeach
              ? <BeachVenueBooking dest={d} availability={av.data} reload={av.reload} />
              : <MountainGuideBooking dest={d} availability={av.data} reload={av.reload} />
          ) : (
            <div className="booking booking-off">
              <FiInfo size={24} />
              <h3>Explore only — not yet bookable</h3>
              <p>CampBlazer only accepts reservations for services an administrator has verified. {isBeach ? "Venue" : "Guided-tour"} booking for {d.name} will open once a verified {isBeach ? "operator" : "local guide"} is added.</p>
              <a className="pill pill-ghost" href={`#/explore?category=${d.category}`}>See other {isBeach ? "beaches" : "mountains"}</a>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
