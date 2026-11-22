import { useState } from "react";
import { FiMapPin, FiSearch } from "react-icons/fi";
import { DestinationCard, Empty, Spinner } from "../components/Cards";
import { useAuth } from "../lib/auth";
import { useApi } from "../lib/useApi";
import type { DestinationSummary } from "../lib/types";

export default function UserHome() {
  const { user } = useAuth();
  const [category, setCategory] = useState("");
  const [municipality, setMunicipality] = useState("");
  const [text, setText] = useState("");
  const { data: munis } = useApi<{ value: string; label: string }[]>("/municipalities/");

  const qs = new URLSearchParams();
  if (category) qs.set("category", category);
  if (municipality) qs.set("municipality", municipality);
  if (text.trim()) qs.set("q", text.trim());
  const { data, loading, error } = useApi<DestinationSummary[]>(`/destinations/?${qs}`);

  return (
    <div className="user-home">
      <header className="user-home-header">
        <div>
          <h1>Welcome, {user?.first_name || user?.username}</h1>
          <p>Search verified beaches and mountain destinations, then choose a bookable venue or tour guide.</p>
        </div>
      </header>

      <section className="user-home-toolbar" aria-label="Destination search filters">
        <div className="seg" aria-label="Destination category">
          {[["", "All"], ["BEACH", "Beaches"], ["MOUNTAIN", "Mountains"]].map(([value, label]) => (
            <button key={value} className={category === value ? "on" : ""} onClick={() => setCategory(value)}>{label}</button>
          ))}
        </div>
        <label className="search"><FiSearch />
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Search name, barangay or municipality..."
          />
        </label>
        <label className="user-home-municipality">
          <span>Municipality</span>
          <select value={municipality} onChange={(e) => setMunicipality(e.target.value)}>
            <option value="">All municipalities</option>
            {(munis ?? []).map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
          </select>
        </label>
      </section>

      {loading && !data ? <Spinner /> : error ? <Empty title="Couldn't reach the server">{error}</Empty> :
        data && data.length === 0 ? (
          <Empty title="No destinations match"><p className="muted">Try clearing a filter or choosing another municipality.</p></Empty>
        ) : (
          <section className="user-home-results">
            <div className="user-home-results-head">
              <div><span className="eyebrow">Biliran destinations</span><h2>{category === "BEACH" ? "Beach destinations" : category === "MOUNTAIN" ? "Mountain destinations" : "All destinations"}</h2></div>
              <span className="muted small"><FiMapPin /> Biliran Province</span>
            </div>
            <div className="grid-cards">{(data ?? []).map((d, i) => <DestinationCard key={d.id} d={d} i={i} />)}</div>
          </section>
        )}
    </div>
  );
}
