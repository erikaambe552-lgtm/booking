import { useEffect, useMemo, useState, type FormEvent } from "react";
import { FiCheckCircle, FiAlertTriangle, FiCpu, FiLock } from "react-icons/fi";
import { api, ApiError, type ApiMeta } from "../lib/api";
import { useAuth } from "../lib/auth";
import { dateOnly, peso, timeRange } from "../lib/format";
import type { Availability, DestinationDetail, Guide, Reservation, Slot, Venue } from "../lib/types";

interface Props { dest: DestinationDetail; availability: Availability | null; reload: () => void }

const localDay = (iso: string) => new Date(iso).toLocaleDateString("en-CA");

function groupByDate(slots: Slot[]) {
  const map = new Map<string, Slot[]>();
  for (const s of slots) {
    const k = new Date(s.start_at).toDateString();
    map.set(k, [...(map.get(k) ?? []), s]);
  }
  return [...map.entries()];
}

function CustomerFields({ v, set }: { v: Record<string, string>; set: (k: string, val: string) => void }) {
  return (
    <>
      <div className="grid-2">
        <label>Full name<input required value={v.customer_name} onChange={(e) => set("customer_name", e.target.value)} /></label>
        <label>Mobile number<input required pattern="[0-9+\- ]{7,20}" value={v.contact_phone} onChange={(e) => set("contact_phone", e.target.value)} placeholder="09XX XXX XXXX" /></label>
      </div>
      <label>Email<input required type="email" value={v.contact_email} onChange={(e) => set("contact_email", e.target.value)} /></label>
      <label>Special requests <span className="muted">(optional)</span>
        <textarea maxLength={1000} rows={3} value={v.special_requests} onChange={(e) => set("special_requests", e.target.value)} />
      </label>
    </>
  );
}

function Result({ ok, meta, onReset }: { ok: Reservation | null; meta: ApiMeta | null; onReset: () => void }) {
  if (!ok) return null;
  return (
    <div className="result result-ok">
      <FiCheckCircle size={28} />
      <div>
        <h4>Reservation submitted — {ok.reference}</h4>
        <p>Status: <b>Pending</b> operator confirmation. Total {peso(ok.total_amount)}. Track it in <a href="#/dashboard">My reservations</a>.</p>
        {meta && <p className="tech-note"><FiCpu /> Processed by server worker PID {meta.workerPid} · server {meta.serverMs} ms · round-trip {meta.clientMs} ms</p>}
        <button className="link-btn" onClick={onReset}>Make another reservation</button>
      </div>
    </div>
  );
}

function useCustomer() {
  const { user } = useAuth();
  const [v, setV] = useState<Record<string, string>>({ customer_name: "", contact_phone: "", contact_email: "", special_requests: "" });
  useEffect(() => {
    if (user) setV((o) => ({ ...o, customer_name: o.customer_name || `${user.first_name} ${user.last_name}`.trim(),
      contact_email: o.contact_email || user.email, contact_phone: o.contact_phone || user.phone || "" }));
  }, [user]);
  return [v, (k: string, val: string) => setV((o) => ({ ...o, [k]: val }))] as const;
}

function LoginGate({ slug }: { slug: string }) {
  return (
    <div className="gate">
      <FiLock size={22} />
      <p>Log in to check out. Availability below is live from the server.</p>
      <a className="pill pill-solid" href={`#/login?next=/destinations/${slug}`}>Log in to reserve</a>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* BEACHES — Venue booking                                             */
/* ------------------------------------------------------------------ */
export function BeachVenueBooking({ dest, availability, reload }: Props) {
  const { user } = useAuth();
  const venues = dest.services.type === "VENUE" ? dest.services.items : [];
  const [venueId, setVenueId] = useState<number | null>(venues[0]?.id ?? null);
  const [slotId, setSlotId] = useState<number | null>(null);
  const [guests, setGuests] = useState(2);
  const [cust, setCust] = useCustomer();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<{ msg: string; conflict: boolean } | null>(null);
  const [ok, setOk] = useState<Reservation | null>(null);
  const [meta, setMeta] = useState<ApiMeta | null>(null);

  const venue: Venue | undefined = venues.find((v) => v.id === venueId);
  const slots = availability?.services.find((s) => s.id === venueId)?.slots ?? [];
  const slot = slots.find((s) => s.id === slotId);
  const price = useMemo(() => {
    if (!venue) return null;
    const extraGuests = Math.max(0, guests - venue.included_guests);
    const extra = extraGuests * Number(venue.price_per_extra_guest);
    return { base: Number(venue.base_price), extraGuests, extra, total: Number(venue.base_price) + extra };
  }, [venue, guests]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!slotId) return setErr({ msg: "Choose an available date and slot first.", conflict: false });
    setBusy(true); setErr(null);
    try {
      const r = await api<Reservation>("/bookings/beach/", { method: "POST", body: { slot_id: slotId, guests, ...cust } }, setMeta);
      setOk(r); reload();
    } catch (x) {
      const conflict = x instanceof ApiError && x.status === 409;
      setErr({ msg: (x as Error).message, conflict });
      if (conflict) { setSlotId(null); reload(); }
    } finally { setBusy(false); }
  };

  if (ok) return <Result ok={ok} meta={meta} onReset={() => { setOk(null); setSlotId(null); }} />;
  return (
    <form className="booking" onSubmit={submit}>
      <div className="booking-head"><span className="tag tag-sea">Beach · Venue booking</span><h3>Reserve a venue at {dest.name}</h3></div>
      {!user && <LoginGate slug={dest.slug} />}
      <label>Venue / camping area
        <select value={venueId ?? ""} onChange={(e) => { setVenueId(Number(e.target.value)); setSlotId(null); }}>
          {venues.map((v) => <option key={v.id} value={v.id}>{v.name} — up to {v.max_guests} guests</option>)}
        </select>
      </label>
      {venue?.is_demo && <p className="demo-note">Simulated demo listing — prices and slots are not real offers.</p>}
      <div className="field-label">Reservation date &amp; slot</div>
      {slots.length === 0 ? <p className="muted">No upcoming slots configured for this venue.</p> : (
        <div className="slot-days">
          {groupByDate(slots).map(([day, list]) => (
            <div key={day} className="slot-day">
              <div className="slot-date">{dateOnly(list[0].start_at)}</div>
              <div className="slot-chips">
                {list.map((s) => (
                  <button type="button" key={s.id} disabled={!s.available}
                    className={`chip ${slotId === s.id ? "chip-on" : ""}`} onClick={() => setSlotId(s.id)}>
                    {timeRange(s.start_at, s.end_at)}{!s.available && " · booked"}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
      <label>Number of guests
        <input type="number" min={1} max={venue?.max_guests ?? 1} value={guests} onChange={(e) => setGuests(Number(e.target.value))} />
      </label>
      <CustomerFields v={cust} set={setCust} />
      {price && (
        <div className="breakdown">
          <div><span>Venue slot (includes {venue!.included_guests} guests)</span><span>{peso(price.base)}</span></div>
          <div><span>Extra guests × {price.extraGuests} @ {peso(venue!.price_per_extra_guest)}</span><span>{peso(price.extra)}</span></div>
          <div className="total"><span>Total</span><span>{peso(price.total)}</span></div>
          {slot && <small className="muted">{dateOnly(slot.start_at)} · {timeRange(slot.start_at, slot.end_at)}</small>}
        </div>
      )}
      {err && <div className={`result ${err.conflict ? "result-conflict" : "result-err"}`}><FiAlertTriangle /> <span>{err.msg}{err.conflict && " Availability has been refreshed — please pick another slot."}</span></div>}
      <button className="pill pill-solid pill-lg" disabled={busy || !user}>{busy ? "Checking availability…" : "Reserve venue"}</button>
      <p className="muted small">The server re-checks availability inside a locked database transaction before confirming.</p>
    </form>
  );
}

/* ------------------------------------------------------------------ */
/* MOUNTAINS — Tour-guide booking                                      */
/* ------------------------------------------------------------------ */
export function MountainGuideBooking({ dest, availability, reload }: Props) {
  const { user } = useAuth();
  const guides = dest.services.type === "GUIDE" ? dest.services.items : [];
  const [date, setDate] = useState("");
  const [guideId, setGuideId] = useState<number | null>(null);
  const [scheduleId, setScheduleId] = useState<number | null>(null);
  const [participants, setParticipants] = useState(2);
  const [cust, setCust] = useCustomer();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<{ msg: string; conflict: boolean } | null>(null);
  const [ok, setOk] = useState<Reservation | null>(null);
  const [meta, setMeta] = useState<ApiMeta | null>(null);

  const all = (availability?.services ?? []).flatMap((g) => g.slots.map((s) => ({ ...s, guideId: g.id, guideName: g.name })));
  const dates = [...new Set(all.map((s) => localDay(s.start_at)))];
  const onDate = all.filter((s) => !date || localDay(s.start_at) === date);
  const guidesOnDate = guides.filter((g) => onDate.some((s) => s.guideId === g.id && s.available));
  const guide: Guide | undefined = guides.find((g) => g.id === guideId);
  const schedules = onDate.filter((s) => s.guideId === guideId);
  const price = guide ? { base: Number(guide.price_per_group), per: Number(guide.price_per_participant),
    total: Number(guide.price_per_group) + participants * Number(guide.price_per_participant) } : null;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!scheduleId) return setErr({ msg: "Choose a date, an available guide and a tour schedule.", conflict: false });
    setBusy(true); setErr(null);
    try {
      const r = await api<Reservation>("/bookings/mountain/", { method: "POST", body: { schedule_id: scheduleId, participants, ...cust } }, setMeta);
      setOk(r); reload();
    } catch (x) {
      const conflict = x instanceof ApiError && x.status === 409;
      setErr({ msg: (x as Error).message, conflict });
      if (conflict) { setScheduleId(null); reload(); }
    } finally { setBusy(false); }
  };

  if (ok) return <Result ok={ok} meta={meta} onReset={() => { setOk(null); setScheduleId(null); }} />;
  return (
    <form className="booking" onSubmit={submit}>
      <div className="booking-head"><span className="tag tag-violet">Mountain · Tour-guide booking</span><h3>Book a guide for {dest.name}</h3></div>
      {!user && <LoginGate slug={dest.slug} />}
      <label>Preferred tour date
        <select value={date} onChange={(e) => { setDate(e.target.value); setGuideId(null); setScheduleId(null); }}>
          <option value="">Select a date…</option>
          {dates.map((d) => <option key={d} value={d}>{dateOnly(d + "T08:00:00")}</option>)}
        </select>
      </label>
      <div className="field-label">Available guide</div>
      {!date ? <p className="muted">Pick a date to see guides with open schedules.</p> : guidesOnDate.length === 0 ? <p className="muted">No guide is free on this date.</p> : (
        <div className="guide-list">
          {guidesOnDate.map((g) => (
            <button type="button" key={g.id} className={`guide-opt ${guideId === g.id ? "on" : ""}`} onClick={() => { setGuideId(g.id); setScheduleId(null); }}>
              <b>{g.display_name}</b>
              <span>Up to {g.max_participants} hikers · {peso(g.price_per_group)} guide fee</span>
              {g.is_demo && <em>Simulated demo guide</em>}
            </button>
          ))}
        </div>
      )}
      {guide && (
        <>
          <div className="field-label">Tour schedule</div>
          <div className="slot-chips">
            {schedules.map((s) => (
              <button type="button" key={s.id} disabled={!s.available} className={`chip ${scheduleId === s.id ? "chip-on" : ""}`} onClick={() => setScheduleId(s.id)}>
                {timeRange(s.start_at, s.end_at)}{s.meeting_point ? ` · ${s.meeting_point}` : ""}{!s.available && " · booked"}
              </button>
            ))}
          </div>
        </>
      )}
      <label>Number of participants
        <input type="number" min={1} max={guide?.max_participants ?? 20} value={participants} onChange={(e) => setParticipants(Number(e.target.value))} />
      </label>
      <CustomerFields v={cust} set={setCust} />
      {price && (
        <div className="breakdown">
          <div><span>Guide fee (per group)</span><span>{peso(price.base)}</span></div>
          <div><span>Participants × {participants} @ {peso(price.per)}</span><span>{peso(participants * price.per)}</span></div>
          <div className="total"><span>Total</span><span>{peso(price.total)}</span></div>
        </div>
      )}
      {err && <div className={`result ${err.conflict ? "result-conflict" : "result-err"}`}><FiAlertTriangle /> <span>{err.msg}{err.conflict && " Schedules refreshed — choose another."}</span></div>}
      <button className="pill pill-solid pill-lg" disabled={busy || !user}>{busy ? "Checking guide availability…" : "Book tour guide"}</button>
      <p className="muted small">Guide schedules are locked row-by-row on the server, so a guide can never be double-booked.</p>
    </form>
  );
}
