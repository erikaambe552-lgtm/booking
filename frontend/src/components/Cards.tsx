import type { ReactNode } from "react";
import { FiMapPin, FiArrowRight, FiLock } from "react-icons/fi";
import type { DestinationSummary, Status } from "../lib/types";
import { PhotoFrame } from "./Brand";

export function DestinationCard({ d, i = 0, tall = false }: { d: DestinationSummary; i?: number; tall?: boolean }) {
  return (
    <article className={`dcard ${tall ? "dcard-tall" : ""}`} style={{ animationDelay: `${Math.min(i, 10) * 60}ms` }}>
      <a href={`#/destinations/${d.slug}`} className="dcard-media">
        <PhotoFrame photo={d.cover_image} category={d.category} seed={d.id} alt={d.name} />
        <span className={`tag ${d.category === "BEACH" ? "tag-sea" : "tag-violet"}`}>
          {d.category === "BEACH" ? "Beach · Venue" : "Mountain · Guide"}
        </span>
        <div className="dcard-overlay">
          <h3>{d.name}</h3>
          <p><FiMapPin /> {d.municipality ? `${d.municipality}, Biliran` : "Biliran · location pending"}</p>
        </div>
      </a>
      <div className="dcard-body">
        <p>{d.short_description}</p>
        <div className="dcard-actions">
          <a className="link-arrow" href={`#/destinations/${d.slug}`}>View Details <FiArrowRight /></a>
          {d.is_bookable ? (
            <a className="pill pill-solid pill-sm" href={`#/destinations/${d.slug}?book=1`}>
              {d.category === "BEACH" ? "Book Venue" : "Book Tour Guide"}
            </a>
          ) : (
            <span className="book-locked" title={d.category === "BEACH" ? "Opens once a venue/camping area is verified by an admin" : "Opens once a tour guide and schedule are verified by an admin"}>
              <button className="pill pill-muted pill-sm" disabled aria-disabled="true">
                <FiLock /> {d.category === "BEACH" ? "Book Venue" : "Book Tour Guide"}
              </button>
              <small>Awaiting verified {d.category === "BEACH" ? "venue" : "guide"}</small>
            </span>
          )}
        </div>
      </div>
    </article>
  );
}

export function StatusBadge({ s }: { s: Status }) {
  return <span className={`status status-${s.toLowerCase()}`}>{s.charAt(0) + s.slice(1).toLowerCase()}</span>;
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return <div className="empty"><h4>{title}</h4>{children}</div>;
}

export function Spinner() {
  return <div className="spinner" role="status" aria-label="Loading" />;
}
