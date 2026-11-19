import { useEffect, useState } from "react";
import { FiSearch } from "react-icons/fi";
import { DestinationCard, Empty, Spinner } from "../components/Cards";
import { navigate, type Route } from "../lib/router";
import { useApi } from "../lib/useApi";
import type { DestinationSummary } from "../lib/types";

export default function Explore({ route }: { route: Route }) {
  const category = route.query.get("category") ?? "";
  const municipality = route.query.get("municipality") ?? "";
  const q = route.query.get("q") ?? "";
  const [text, setText] = useState(q);
  const { data: munis } = useApi<{ value: string; label: string }[]>("/municipalities/");

  const qs = new URLSearchParams();
  if (category) qs.set("category", category);
  if (municipality) qs.set("municipality", municipality);
  if (q) qs.set("q", q);
  const { data, loading, error } = useApi<DestinationSummary[]>(`/destinations/?${qs}`);

  const setParam = (k: string, v: string) => {
    const p = new URLSearchParams(qs);
    v ? p.set(k, v) : p.delete(k);
    navigate(`/explore?${p}`);
  };
  useEffect(() => {
    const t = setTimeout(() => { if (text !== q) setParam("q", text.trim()); }, 350);
    return () => clearTimeout(t);
  }, [text]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="page">
      <section className="page-hero">
        <div className="container">
          <span className="eyebrow">Explore Biliran</span>
          <h1>{category === "BEACH" ? "Beaches" : category === "MOUNTAIN" ? "Mountains" : "All destinations"}</h1>
          <p>Beaches are reserved by <b>venue</b>; mountains are reserved through a <b>tour guide</b>. Destinations marked "Explore only" don't accept bookings until a verified service is added.</p>
        </div>
      </section>
      <div className="container">
        <div className="filters">
          <div className="seg">
            {[["", "All"], ["BEACH", "Beaches"], ["MOUNTAIN", "Mountains"]].map(([v, l]) => (
              <button key={v} className={category === v ? "on" : ""} onClick={() => setParam("category", v)}>{l}</button>
            ))}
          </div>
          <label className="search"><FiSearch />
            <input placeholder="Search destinations, barangays…" value={text} onChange={(e) => setText(e.target.value)} />
          </label>
          <select value={municipality} onChange={(e) => setParam("municipality", e.target.value)} aria-label="Municipality">
            <option value="">All municipalities</option>
            {munis?.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
          </select>
        </div>
        {loading && !data ? <Spinner /> : error ? <Empty title="Couldn't reach the server">{error}</Empty> :
          data && data.length === 0 ? <Empty title="No destinations match">Try another municipality or clear the search.</Empty> : (
          <>
            <p className="muted small results-count">{data?.length} destination{data?.length === 1 ? "" : "s"} in Biliran Province</p>
            <div className="grid-cards">{data?.map((d, i) => <DestinationCard key={d.id} d={d} i={i} />)}</div>
          </>
        )}
      </div>
    </div>
  );
}
