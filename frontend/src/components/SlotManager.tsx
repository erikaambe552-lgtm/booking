import { useState, type FormEvent } from "react";
import { FiTrash2 } from "react-icons/fi";
import { api } from "../lib/api";
import { dateOnly, timeRange } from "../lib/format";
import { useApi } from "../lib/useApi";
import type { Slot } from "../lib/types";

interface Services { venues: { id: number; name: string; destination: string }[]; guides: { id: number; name: string; destination: string }[] }

/** Operators/guides (own services) and admins (all services) configure availability here. */
export function SlotManager() {
  const svc = useApi<Services>("/operator/services/");
  const venueSlots = useApi<Slot[]>("/operator/venue-slots/");
  const guideScheds = useApi<Slot[]>("/operator/guide-schedules/");
  const [f, setF] = useState({ target: "", date: "", start: "08:00", end: "20:00", meeting_point: "", note: "" });
  const [msg, setMsg] = useState("");

  const options = [
    ...(svc.data?.venues ?? []).map((v) => ({ key: `v-${v.id}`, label: `Venue · ${v.name} (${v.destination})` })),
    ...(svc.data?.guides ?? []).map((g) => ({ key: `g-${g.id}`, label: `Guide · ${g.name} (${g.destination})` })),
  ];
  const isGuide = f.target.startsWith("g-");

  const add = async (e: FormEvent) => {
    e.preventDefault(); setMsg("");
    if (!f.target || !f.date) return setMsg("Choose a service and date.");
    const start = new Date(`${f.date}T${f.start}:00`);
    let end = new Date(`${f.date}T${f.end}:00`);
    if (end <= start) end = new Date(end.getTime() + 86400000); // overnight slot ends next day
    const id = Number(f.target.slice(2));
    try {
      if (isGuide) await api("/operator/guide-schedules/", { method: "POST", body: { guide: id, start_at: start.toISOString(), end_at: end.toISOString(), meeting_point: f.meeting_point, note: f.note } });
      else await api("/operator/venue-slots/", { method: "POST", body: { venue: id, start_at: start.toISOString(), end_at: end.toISOString(), note: f.note } });
      setMsg("Availability added."); venueSlots.reload(); guideScheds.reload();
    } catch (x) { setMsg((x as Error).message); }
  };

  const toggle = async (kind: "venue-slots" | "guide-schedules", s: Slot) => {
    try { await api(`/operator/${kind}/${s.id}/`, { method: "PATCH", body: { is_open: !s.is_open } }); venueSlots.reload(); guideScheds.reload(); }
    catch (x) { setMsg((x as Error).message); }
  };
  const del = async (kind: "venue-slots" | "guide-schedules", s: Slot) => {
    try { await api(`/operator/${kind}/${s.id}/`, { method: "DELETE" }); venueSlots.reload(); guideScheds.reload(); }
    catch (x) { setMsg((x as Error).message); }
  };

  const rows = [
    ...(venueSlots.data ?? []).map((s) => ({ s, kind: "venue-slots" as const, name: s.venue_name })),
    ...(guideScheds.data ?? []).map((s) => ({ s, kind: "guide-schedules" as const, name: s.guide_name })),
  ].filter((r) => new Date(r.s.end_at) > new Date()).sort((a, b) => a.s.start_at.localeCompare(b.s.start_at));

  return (
    <div className="slot-mgr">
      {options.length === 0 ? <p className="muted">No services are assigned to your account yet. An administrator links venues/guides to operator accounts.</p> : (
        <form className="slot-form" onSubmit={add}>
          <label>Service<select value={f.target} onChange={(e) => setF({ ...f, target: e.target.value })}><option value="">Select…</option>{options.map((o) => <option key={o.key} value={o.key}>{o.label}</option>)}</select></label>
          <label>Date<input type="date" value={f.date} min={new Date().toLocaleDateString("en-CA")} onChange={(e) => setF({ ...f, date: e.target.value })} /></label>
          <label>Start<input type="time" value={f.start} onChange={(e) => setF({ ...f, start: e.target.value })} /></label>
          <label>End<input type="time" value={f.end} onChange={(e) => setF({ ...f, end: e.target.value })} /></label>
          {isGuide && <label>Meeting point<input value={f.meeting_point} onChange={(e) => setF({ ...f, meeting_point: e.target.value })} /></label>}
          <label>Note<input value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} /></label>
          <button className="pill pill-solid">Add availability</button>
        </form>
      )}
      {msg && <p className="small muted">{msg}</p>}
      <table className="table">
        <thead><tr><th>Service</th><th>Date</th><th>Time</th><th>State</th><th></th></tr></thead>
        <tbody>
          {rows.map(({ s, kind, name }) => (
            <tr key={`${kind}-${s.id}`}>
              <td>{name}</td><td>{dateOnly(s.start_at)}</td><td>{timeRange(s.start_at, s.end_at)}</td>
              <td>{!s.available && s.is_open ? <span className="status status-approved">Reserved</span> : s.is_open ? <span className="status status-pending">Open</span> : <span className="status status-cancelled">Closed</span>}</td>
              <td className="row-actions">
                <button className="link-btn" onClick={() => toggle(kind, s)}>{s.is_open ? "Close" : "Reopen"}</button>
                <button className="icon-btn" title="Delete" onClick={() => del(kind, s)}><FiTrash2 /></button>
              </td>
            </tr>
          ))}
          {rows.length === 0 && <tr><td colSpan={5} className="muted">No upcoming availability.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
