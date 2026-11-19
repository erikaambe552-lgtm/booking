import { useState } from "react";
import { FiChevronDown, FiChevronUp } from "react-icons/fi";
import { api } from "../lib/api";
import { dateOnly, dateTime, peso, timeRange } from "../lib/format";
import type { Reservation, Status } from "../lib/types";
import { Empty, StatusBadge } from "./Cards";

export const STATUS_TABS: (Status | "ALL")[] = ["ALL", "PENDING", "APPROVED", "REJECTED", "CANCELLED", "COMPLETED"];

export function StatusTabs({ value, onChange, counts }: { value: string; onChange: (s: string) => void; counts: Record<string, number> }) {
  return (
    <div className="seg seg-wrap">
      {STATUS_TABS.map((s) => (
        <button key={s} className={value === s ? "on" : ""} onClick={() => onChange(s)}>
          {s === "ALL" ? "All" : s.charAt(0) + s.slice(1).toLowerCase()} <span className="count">{counts[s] ?? 0}</span>
        </button>
      ))}
    </div>
  );
}

export function countByStatus(list: Reservation[]) {
  const c: Record<string, number> = { ALL: list.length };
  list.forEach((r) => { c[r.status] = (c[r.status] ?? 0) + 1; });
  return c;
}

type Mode = "camper" | "provider" | "admin";

export function ReservationList({ items, mode, onChanged }: { items: Reservation[]; mode: Mode; onChanged: () => void }) {
  const [open, setOpen] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState("");
  if (!items.length) return <Empty title="No reservations here yet" />;

  const kind = (r: Reservation) => (r.type === "BEACH" ? "beach" : "mountain");
  const act = async (r: Reservation, status: string) => {
    const key = `${r.type}-${r.id}`;
    setBusy(key); setErr("");
    try {
      if (mode === "camper") await api(`/bookings/${kind(r)}/${r.id}/cancel/`, { method: "POST" });
      else await api(`/${mode === "admin" ? "admin" : "operator"}/reservations/${kind(r)}/${r.id}/status/`, { method: "POST", body: { status } });
      onChanged();
    } catch (x) { setErr((x as Error).message); } finally { setBusy(null); }
  };

  return (
    <div className="res-list">
      {err && <div className="result result-err">{err}</div>}
      {items.map((r) => {
        const key = `${r.type}-${r.id}`;
        return (
          <div className="res" key={key}>
            <div className="res-main">
              <div className="res-when">
                <b>{new Date(r.start_at).getDate()}</b>
                <span>{new Date(r.start_at).toLocaleDateString("en-PH", { month: "short" })}</span>
              </div>
              <div className="res-info">
                <div className="res-top">
                  <span className={`tag ${r.type === "BEACH" ? "tag-sea" : "tag-violet"}`}>{r.type === "BEACH" ? "Venue" : "Guide"}</span>
                  <StatusBadge s={r.status} />
                  <code>{r.reference}</code>
                </div>
                <h4><a href={`#/destinations/${r.destination_slug}`}>{r.destination}</a> · {r.service}</h4>
                <p className="muted small">{dateOnly(r.start_at)} · {timeRange(r.start_at, r.end_at)} · {r.party_size} {r.type === "BEACH" ? "guests" : "participants"}{mode !== "camper" && ` · ${r.customer_name} (${r.username})`}</p>
              </div>
              <div className="res-amt">{peso(r.total_amount)}</div>
              <div className="res-actions">
                {mode === "camper" && r.can_cancel && <button className="pill pill-ghost pill-sm" disabled={busy === key} onClick={() => confirm("Cancel this reservation?") && act(r, "CANCELLED")}>Cancel</button>}
                {mode !== "camper" && r.status === "PENDING" && (
                  <>
                    <button className="pill pill-solid pill-sm" disabled={busy === key} onClick={() => act(r, "APPROVED")}>Approve</button>
                    <button className="pill pill-ghost pill-sm" disabled={busy === key} onClick={() => act(r, "REJECTED")}>Reject</button>
                  </>
                )}
                {mode !== "camper" && r.status === "APPROVED" && (
                  <>
                    <button className="pill pill-ghost pill-sm" disabled={busy === key} onClick={() => act(r, "COMPLETED")}>Mark completed</button>
                    <button className="pill pill-ghost pill-sm" disabled={busy === key} onClick={() => act(r, "CANCELLED")}>Cancel</button>
                  </>
                )}
                <button className="icon-btn" aria-label="Details" onClick={() => setOpen(open === key ? null : key)}>{open === key ? <FiChevronUp /> : <FiChevronDown />}</button>
              </div>
            </div>
            {open === key && (
              <div className="res-more">
                <div>
                  <h5>Price breakdown</h5>
                  <p className="small">Base {peso(r.base_amount)} + extras {peso(r.extra_amount)} = <b>{peso(r.total_amount)}</b></p>
                  <h5>Contact</h5>
                  <p className="small">{r.customer_name} · {r.contact_phone} · {r.contact_email}</p>
                  {r.meeting_point && <><h5>Meeting point</h5><p className="small">{r.meeting_point}</p></>}
                  {r.special_requests && <><h5>Special requests</h5><p className="small">{r.special_requests}</p></>}
                </div>
                <div>
                  <h5>Booking history</h5>
                  <ol className="timeline">
                    {r.history.map((h, i) => (
                      <li key={i}><b>{h.to_status}</b> <span className="muted small">{dateTime(h.created_at)} · {h.changed_by ?? "system"}{h.note && ` — ${h.note}`}</span></li>
                    ))}
                  </ol>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
