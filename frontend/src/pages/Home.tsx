import { FiArrowRight, FiShield, FiMap, FiUsers, FiZap } from "react-icons/fi";
import { PhotoFrame } from "../components/Brand";
import WireTerrain from "../components/WireTerrain";
import { DestinationCard } from "../components/Cards";
import { useApi } from "../lib/useApi";
import type { DestinationSummary } from "../lib/types";

export default function Home() {
  const { data } = useApi<DestinationSummary[]>("/destinations/");
  const all = data ?? [];
  const beaches = all.filter((d) => d.category === "BEACH");
  const mountains = all.filter((d) => d.category === "MOUNTAIN");
  const bandPhoto = all.find((d) => d.slug === "napo-beach-resort" && d.cover_image) ?? all.find((d) => d.cover_image);

  return (
    <>
      <section className="hero-wire">
        <WireTerrain />
        <div className="hero-inner container">
          <div className="hero-copy">
            <span className="eyebrow">CampBlazer · Biliran Province</span>
            <h1>Plan your trip. <em>We&rsquo;ll handle</em> the rest.</h1>
            <div className="hero-sub">
              <p>Plan your next trip with ease. Check essential details, compare amenities, and message local hosts or tour guides before you book.</p>
              <div className="hero-cta">
                <a href="#/explore" className="btn-rect btn-accent">Explore Destinations</a>
                <a href="#mountains" className="btn-rect btn-line">Discover Mountains</a>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="stats container">
        <div><b>8</b><span>Municipalities covered</span></div>
        <div><b>{beaches.length || 12}</b><span>Beach destinations</span></div>
        <div><b>{mountains.length || 6}</b><span>Mountains &amp; peaks</span></div>
        <div><b>2</b><span>Separate booking flows</span></div>
      </section>

      <section className="showcase" id="beaches">
        <div className="bigword" aria-hidden="true">BEACHES</div>
        <div className="container">
          <div className="section-head">
            <span className="eyebrow">Beaches · Venue &amp; camping-area booking</span>
            <h2>Explore Biliran Beaches</h2>
            <p>{beaches.length || 12} approved beach destinations in Biliran. Tap <b>Book Venue</b> to pick a venue or camping area and an open date — the operator's approval reaches you live.</p>
          </div>
          <div className="grid-cards">
            {beaches.map((d, i) => <DestinationCard key={d.id} d={d} i={i} />)}
          </div>
          <a className="link-arrow center" href="#/explore?category=BEACH">Filter beaches by municipality <FiArrowRight /></a>
        </div>
      </section>

      <section className="showcase showcase-alt" id="mountains">
        <div className="bigword" aria-hidden="true">MOUNTAINS</div>
        <div className="container">
          <div className="section-head">
            <span className="eyebrow eyebrow-violet">Mountains · Tour-guide booking</span>
            <h2>Explore Biliran Mountains</h2>
            <p>Discover Biliran's mountain destinations and camping spots. Explore hiking and camping opportunities, find available tour guides, and book your next mountain adventure.</p>
          </div>
          <div className="grid-cards">
            {mountains.map((d, i) => <DestinationCard key={d.id} d={d} i={i} />)}
          </div>
          <a className="link-arrow center" href="#/explore?category=MOUNTAIN">Filter mountains <FiArrowRight /></a>
        </div>
      </section>

      <section className="brandband">
        <div className="brandband-word" aria-hidden="true">CampBlazer</div>
        <div className="container brandband-grid">
          <div className="brandband-copy">
            <span className="eyebrow">Made for Biliran explorers</span>
            <h2>From &ldquo;planning lang&rdquo; to actually going.</h2>
            <p>The only surprises you want are scenic views, not hidden fees. Check prices, amenities, and open dates across Biliran&rsquo;s best beaches and mountain trails, and book on CampBlazer without the guesswork.</p>
            <a href="#/explore" className="btn-rect btn-accent">Browse all destinations</a>
          </div>
          <div className="brandband-photo">
            <PhotoFrame photo={bandPhoto?.cover_image ?? null} category={bandPhoto?.category ?? "BEACH"} seed={3} alt={bandPhoto?.name ?? "Biliran"} />
          </div>
        </div>
      </section>

      <section className="why">
        <div className="container why-grid">
          <div>
            <span className="eyebrow">Why CampBlazer</span>
            <h2>Explore More, <em className="accent">Camp Better,</em> Book Easier.</h2>
            <p>CampBlazer brings Biliran's beaches, mountains, and camping destinations together in one platform. It makes exploring locations, checking availability, and booking outdoor experiences easier, faster, and more convenient.</p>
          </div>
          <div className="why-cards">
            <div><FiMap /><h4>Biliran-only catalog</h4><p>No out-of-province spots. Locations are verified before they're shown as fact.</p></div>
            <div><FiUsers /><h4>Supports local operators</h4><p>Beach operators and mountain guides manage their own schedules.</p></div>
            <div><FiZap /><h4>Concurrent &amp; consistent</h4><p>Multiple server workers, row-level locks and DB constraints keep data correct.</p></div>
            <div><FiShield /><h4>Secure accounts</h4><p>Hashed passwords, role-based access, validated inputs.</p></div>
          </div>
        </div>
      </section>

      <section className="cta container">
        <div className="cta-card">
          <div>
            <h2>Ready to blaze a trail in Biliran?</h2>
            <p>Create a free account and reserve your beach venue or mountain guide.</p>
          </div>
          <div className="cta-actions">
            <a className="pill pill-solid pill-lg" href="#/register">Create account</a>
            <a className="pill pill-ghost pill-lg" href="#/explore">Browse first</a>
          </div>
        </div>
      </section>
    </>
  );
}
