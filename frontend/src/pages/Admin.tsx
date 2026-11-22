import { useState, type FormEvent } from "react";
import {
  FiActivity, FiCalendar, FiGrid, FiInbox, FiLogOut, FiMapPin,
  FiPlus, FiTrash2, FiEdit2, FiUsers, FiX, FiBriefcase, FiShield,
} from "react-icons/fi";
import { Spinner } from "../components/Cards";
import { countByStatus, ReservationList, StatusTabs } from "../components/Reservations";
import { SlotManager } from "../components/SlotManager";
import { api, upload, mediaUrl } from "../lib/api";
import { peso, roleLabel } from "../lib/format";
import { useApi } from "../lib/useApi";
import { useLiveEvent, useLivePolling } from "../lib/realtime";
import { useAuth } from "../lib/auth";
import { navigate } from "../lib/router";
import type { Reservation, User } from "../lib/types";

type AdminDest = {
  id: number; name: string; slug: string; category: "BEACH" | "MOUNTAIN"; municipality: string; barangay: string;
  location_verified: boolean; location_note: string; short_description: string; description: string;
  amenities: string[]; activities: string[]; reservation_instructions: string; source_notes: string;
  is_published: boolean; is_verified: boolean; booking_enabled: boolean; is_featured: boolean; is_bookable: boolean;
};
type AdminUser = User & { is_active: boolean };
type Svc = Record<string, unknown> & { id: number; destination: number; destination_name: string; is_verified: boolean; is_active: boolean; is_demo: boolean };

const TABS = ["Overview", "Destinations", "Services", "Availability", "Reservations", "Users"] as const;
const MUNIS = ["Almeria", "Biliran", "Cabucgayan", "Caibiran", "Culaba", "Kawayan", "Maripipi", "Naval"];

export default function Admin() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("Overview");
  const { user, logout } = useAuth();
  const tabIcons = {
    Overview: FiGrid,
    Destinations: FiMapPin,
    Services: FiBriefcase,
    Availability: FiCalendar,
    Reservations: FiInbox,
    Users: FiUsers,
  };
  const signOut = async () => {
    await logout();
    navigate("/");
  };
  return (
    <div className="admin-workspace">
      <aside className="admin-sidebar">
        <div className="admin-brand"><span className="admin-brand-mark"><FiShield /></span><div><b>CampBlazer</b><small>Admin workspace</small></div></div>
        <nav className="admin-nav" aria-label="Admin sections">
          {TABS.map((item) => {
            const Icon = tabIcons[item];
            return <button key={item} className={tab === item ? "active" : ""} onClick={() => setTab(item)}><Icon /><span>{item}</span></button>;
          })}
        </nav>
        <div className="admin-profile">
          <span className="admin-avatar">{(user?.first_name || user?.username || "A").charAt(0).toUpperCase()}</span>
          <div><b>{user?.first_name || user?.username}</b><small>Administrator</small></div>
          <button className="icon-btn" title="Log out" onClick={signOut}><FiLogOut /></button>
        </div>
      </aside>
      <main className="admin-main">
        <header className="admin-topbar">
          <div><span>Administration</span><h1>{tab}</h1></div>
          <div className="admin-live"><span /><FiActivity /> Live system</div>
        </header>
        <div className="admin-content">
          {tab === "Overview" && <Overview />}
          {tab === "Destinations" && <Destinations />}
          {tab === "Services" && <Services />}
          {tab === "Availability" && <section className="panel admin-panel"><div className="admin-section-title"><div><span>Operations</span><h3>Availability &amp; schedules</h3></div></div><SlotManager /></section>}
          {tab === "Reservations" && <AllReservations />}
          {tab === "Users" && <Users />}
        </div>
      </main>
    </div>
  );
}

function Overview() {
  const { data, reload } = useApi<Record<string, any>>("/admin/stats/"); // eslint-disable-line @typescript-eslint/no-explicit-any
  useLiveEvent(["reservation.new", "reservation.status"], reload);
  useLiveEvent(["admin.data.changed"], reload);
  useLivePolling(reload);
  if (!data) return <Spinner />;
  const sum = (o: Record<string, number>) => Object.values(o).reduce((a, b) => a + b, 0);
  const beachReservations = sum(data.beach_reservations);
  const guideReservations = sum(data.guide_reservations);
  const pending = (data.beach_reservations.PENDING ?? 0) + (data.guide_reservations.PENDING ?? 0);
  const approved = (data.beach_reservations.APPROVED ?? 0) + (data.guide_reservations.APPROVED ?? 0);
  const cards = [
    { label: "Registered users", value: data.users, detail: "All account roles", icon: FiUsers, tone: "violet" },
    { label: "Destinations", value: data.destinations.total, detail: `${data.destinations.beaches} beach · ${data.destinations.mountains} mountain`, icon: FiMapPin, tone: "sea" },
    { label: "Verified", value: data.destinations.verified, detail: "Checked destinations", icon: FiShield, tone: "amber" },
    { label: "Bookings enabled", value: data.destinations.bookable, detail: "Ready for reservations", icon: FiCalendar, tone: "orange" },
  ];
  return (
    <div className="overview-grid">
      <section className="overview-stats">
        {cards.map((card) => {
          const Icon = card.icon;
          return <article className="overview-card" key={card.label}>
            <div className={`overview-card-icon ${card.tone}`}><Icon /></div>
            <div><span>{card.label}</span><b>{card.value}</b><small>{card.detail}</small></div>
          </article>;
        })}
      </section>
      <section className="overview-primary">
        <div className="admin-section-title"><div><span>Reservations</span><h3>Booking activity</h3></div><b className="overview-total">{beachReservations + guideReservations}</b></div>
        <div className="overview-metrics">
          <article><span>Pending</span><b>{pending}</b><small>Needs review</small></article>
          <article><span>Approved</span><b>{approved}</b><small>Confirmed trips</small></article>
          <article><span>Beach</span><b>{beachReservations}</b><small>Venue bookings</small></article>
          <article><span>Mountain</span><b>{guideReservations}</b><small>Guide bookings</small></article>
        </div>
        <div className="overview-status">
          <div><span>Booking value</span><b>{peso(data.simulated_booking_value_php)}</b></div>
          <div><span>Open venues</span><b>{data.open_venue_slots}</b></div>
          <div><span>Open guides</span><b>{data.open_guide_schedules}</b></div>
          <div><span>Services</span><b>{data.venues + data.guides}</b></div>
        </div>
      </section>
      <section className="overview-breakdown">
        <div className="admin-section-title"><div><span>Status breakdown</span><h3>Reservations by status</h3></div></div>
        <div className="status-breakdown-grid">
          {["PENDING", "APPROVED", "REJECTED", "CANCELLED", "COMPLETED"].map((status) => {
            const value = (data.beach_reservations[status] ?? 0) + (data.guide_reservations[status] ?? 0);
            return <div className="status-breakdown" key={status}><span className={`status status-${status.toLowerCase()}`}>{status}</span><b>{value}</b></div>;
          })}
        </div>
      </section>
      <section className="overview-breakdown">
        <div className="admin-section-title"><div><span>Inventory</span><h3>Services &amp; availability</h3></div></div>
        <div className="inventory-grid">
          <div><FiBriefcase /><span>Beach venues</span><b>{data.venues}</b></div>
          <div><FiActivity /><span>Mountain guides</span><b>{data.guides}</b></div>
          <div><FiCalendar /><span>Open venue slots</span><b>{data.open_venue_slots}</b></div>
          <div><FiCalendar /><span>Open guide schedules</span><b>{data.open_guide_schedules}</b></div>
        </div>
      </section>
    </div>
  );
}

function Destinations() {
  const { data, reload } = useApi<AdminDest[]>("/admin/destinations/");
  useLiveEvent(["admin.data.changed", "reservation.status", "reservation.new"], (e) => {
    if (e.type !== "admin.data.changed" || e.entity === "destinations") reload();
  });
  useLivePolling(reload);
  const [edit, setEdit] = useState<Partial<AdminDest> | null>(null);
  const [msg, setMsg] = useState("");
  const patch = async (d: AdminDest, body: Partial<AdminDest>) => {
    setMsg("");
    try { await api(`/admin/destinations/${d.id}/`, { method: "PATCH", body }); reload(); }
    catch (x) { setMsg(`${d.name}: ${(x as Error).message}`); }
  };
  const remove = async (d: AdminDest) => {
    if (!confirm(`Delete ${d.name}? This cannot be undone.`)) return;
    try { await api(`/admin/destinations/${d.id}/`, { method: "DELETE" }); reload(); } catch (x) { setMsg((x as Error).message); }
  };
  return (
    <section className="panel">
      <div className="panel-head"><h3>Destinations (Biliran only)</h3><button className="pill pill-solid pill-sm" onClick={() => setEdit({ category: "BEACH", amenities: [], activities: [], is_published: true })}><FiPlus /> Add destination</button></div>
      {msg && <div className="result result-err">{msg}</div>}
      {!data ? <Spinner /> : (
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Name</th><th>Type</th><th>Municipality</th><th>Location ✓</th><th>Verified</th><th>Bookings</th><th>Featured</th><th></th></tr></thead>
            <tbody>
              {data.map((d) => (
                <tr key={d.id}>
                  <td><a href={`#/destinations/${d.slug}`}>{d.name}</a></td>
                  <td>{d.category === "BEACH" ? "Beach" : "Mountain"}</td>
                  <td>{d.municipality || <span className="muted">pending</span>}</td>
                  <td><Toggle on={d.location_verified} set={(v) => patch(d, { location_verified: v })} /></td>
                  <td><Toggle on={d.is_verified} set={(v) => patch(d, v ? { is_verified: true } : { is_verified: false, booking_enabled: false })} /></td>
                  <td><Toggle on={d.booking_enabled} set={(v) => patch(d, { booking_enabled: v })} /></td>
                  <td><Toggle on={d.is_featured} set={(v) => patch(d, { is_featured: v })} /></td>
                  <td className="row-actions"><button className="icon-btn" onClick={() => setEdit(d)}><FiEdit2 /></button><button className="icon-btn" onClick={() => remove(d)}><FiTrash2 /></button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {edit && <DestinationEditor d={edit} close={() => setEdit(null)} saved={() => { setEdit(null); reload(); }} />}
    </section>
  );
}

function Toggle({ on, set }: { on: boolean; set: (v: boolean) => void }) {
  return <button className={`toggle ${on ? "on" : ""}`} onClick={() => set(!on)} aria-pressed={on}><span /></button>;
}

function DestinationEditor({ d, close, saved }: { d: Partial<AdminDest>; close: () => void; saved: () => void }) {
  const [v, setV] = useState<Partial<AdminDest>>(d);
  const [currentDestination, setCurrentDestination] = useState<Partial<AdminDest>>(d);
  const [err, setErr] = useState("");
  const photos = useApi<{ id: number; src: string; credit_line: string; caption: string; is_cover: boolean }[]>(
    currentDestination.id ? `/admin/images/?destination=${currentDestination.id}` : null,
  );
  const [ph, setPh] = useState({ image_url: "", credit: "", license: "", caption: "", is_cover: !d.id });
  const [file, setFile] = useState<File | null>(null);
  const s = (k: keyof AdminDest) => (e: { target: { value: string } }) => setV({ ...v, [k]: e.target.value });
  const list = (k: "amenities" | "activities") => (e: { target: { value: string } }) => setV({ ...v, [k]: e.target.value.split(",").map((x) => x.trim()).filter(Boolean) });

  const uploadPhoto = async (destinationId: number) => {
    const form = new FormData();
    form.append("destination", String(destinationId));
    Object.entries(ph).forEach(([k, val]) => { if (k !== "is_cover") form.append(k, String(val)); });
    form.append("is_cover", ph.is_cover ? "true" : "false");
    if (file) form.append("image_file", file);
    await upload("/admin/images/", form);
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault(); setErr("");
    const isNew = !currentDestination.id;
    const addPhotoWithDestination = isNew && (!!file || !!ph.image_url.trim());
    if (addPhotoWithDestination && !ph.credit.trim()) {
      setErr("A photo credit is required.");
      return;
    }
    const body = { name: v.name, category: v.category, municipality: v.municipality ?? "", barangay: v.barangay ?? "", location_note: v.location_note ?? "",
      short_description: v.short_description, description: v.description ?? "", amenities: v.amenities ?? [], activities: v.activities ?? [],
      reservation_instructions: v.reservation_instructions ?? "", source_notes: v.source_notes ?? "" };
    try {
      const destination = await api<AdminDest>(
        currentDestination.id ? `/admin/destinations/${currentDestination.id}/` : "/admin/destinations/",
        { method: currentDestination.id ? "PATCH" : "POST", body },
      );
      setCurrentDestination(destination);
      setV(destination);
      if (addPhotoWithDestination) {
        try {
          await uploadPhoto(destination.id);
          setPh({ image_url: "", credit: "", license: "", caption: "", is_cover: false });
          setFile(null);
        } catch (x) {
          setErr(`Destination saved, but the photo could not be uploaded: ${(x as Error).message}`);
          return;
        }
      }
      saved();
    }
    catch (x) { setErr((x as Error).message); }
  };
  const addPhoto = async (e: FormEvent) => {
    e.preventDefault(); setErr("");
    if (!currentDestination.id) return;
    if (!file && !ph.image_url.trim()) {
      setErr("Choose an image file or enter an image URL.");
      return;
    }
    if (!ph.credit.trim()) {
      setErr("A photo credit is required.");
      return;
    }
    try {
      await uploadPhoto(currentDestination.id);
      setPh({ image_url: "", credit: "", license: "", caption: "", is_cover: false });
      setFile(null);
      photos.reload();
    }
    catch (x) { setErr((x as Error).message); }
  };
  const removePhoto = async (id: number) => {
    if (!confirm("Delete this destination photo?")) return;
    setErr("");
    try {
      await api(`/admin/images/${id}/`, { method: "DELETE" });
      photos.reload();
    } catch (x) { setErr((x as Error).message); }
  };

  return (
    <div className="drawer" role="dialog">
      <div className="drawer-card">
        <div className="panel-head"><h3>{currentDestination.id ? `Edit ${currentDestination.name}` : "New destination"}</h3><button className="icon-btn" onClick={close}><FiX /></button></div>
        <form onSubmit={submit} className="stack">
          <div className="grid-2">
            <label>Name<input required value={v.name ?? ""} onChange={s("name")} /></label>
            <label>Category<select value={v.category} onChange={s("category")} disabled={!!d.id}><option value="BEACH">Beach (venue booking)</option><option value="MOUNTAIN">Mountain (tour guides)</option></select></label>
          </div>
          <div className="grid-2">
            <label>Municipality (Biliran)<select value={v.municipality ?? ""} onChange={s("municipality")}><option value="">— not yet verified —</option>{MUNIS.map((m) => <option key={m}>{m}</option>)}</select></label>
            <label>Barangay<input value={v.barangay ?? ""} onChange={s("barangay")} /></label>
          </div>
          <label>Location note<input value={v.location_note ?? ""} onChange={s("location_note")} /></label>
          <label>Short description<input required maxLength={280} value={v.short_description ?? ""} onChange={s("short_description")} /></label>
          <label>Description<textarea rows={3} value={v.description ?? ""} onChange={s("description")} /></label>
          <label>Amenities (comma-separated, verified only)<input value={(v.amenities ?? []).join(", ")} onChange={list("amenities")} /></label>
          <label>Activities (comma-separated)<input value={(v.activities ?? []).join(", ")} onChange={list("activities")} /></label>
          <label>Reservation instructions<textarea rows={2} value={v.reservation_instructions ?? ""} onChange={s("reservation_instructions")} /></label>
          <label>Source notes (admin only)<textarea rows={2} value={v.source_notes ?? ""} onChange={s("source_notes")} /></label>
          {!currentDestination.id && (
            <>
              <h4>Cover photo (optional)</h4>
              <label>Upload photo (JPG/PNG/WEBP, max 8 MB)
                <input key={file?.name ?? "no-file"} type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
              </label>
              <label>…or image URL<input type="url" value={ph.image_url} onChange={(e) => setPh({ ...ph, image_url: e.target.value })} /></label>
              <label>Photo credit<input required={!!file || !!ph.image_url.trim()} value={ph.credit} onChange={(e) => setPh({ ...ph, credit: e.target.value })} /></label>
              <label>Licence / permission<input value={ph.license} onChange={(e) => setPh({ ...ph, license: e.target.value })} /></label>
              <label>Photo caption<input value={ph.caption} onChange={(e) => setPh({ ...ph, caption: e.target.value })} /></label>
            </>
          )}
          {err && <div className="result result-err">{err}</div>}
          <button className="pill pill-solid">{currentDestination.id ? "Save destination" : "Create destination"}</button>
        </form>
        {currentDestination.id && (
          <>
            <h4 className="mt">Photos <span className="muted small">— authentic, licensed photos only, with credit</span></h4>
            <div className="thumbs">
              {photos.data?.map((p) => (
                <figure key={p.id}><img src={mediaUrl(p.src)} alt={p.caption} /><figcaption>{p.is_cover && "★ "}{p.credit_line}</figcaption>
                  <button className="icon-btn" onClick={() => removePhoto(p.id)}><FiTrash2 /></button></figure>
              ))}
            </div>
            <form onSubmit={addPhoto} className="stack">
              <label>Upload photo (JPG/PNG/WEBP, max 8 MB)<input key={file?.name ?? "no-file"} type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => setFile(e.target.files?.[0] ?? null)} /></label>
              <label>…or image URL (e.g. Wikimedia Commons)<input type="url" value={ph.image_url} onChange={(e) => setPh({ ...ph, image_url: e.target.value })} /></label>
              <div className="grid-2">
                <label>Credit (required)<input required={!!file || !!ph.image_url.trim()} value={ph.credit} onChange={(e) => setPh({ ...ph, credit: e.target.value })} placeholder="e.g. Photo by J. Cruz (BiPSU)" /></label>
                <label>Licence / permission<input value={ph.license} onChange={(e) => setPh({ ...ph, license: e.target.value })} placeholder="Own photo · CC BY-SA 4.0 · Used with permission" /></label>
              </div>
              <div className="grid-2">
                <label>Caption<input value={ph.caption} onChange={(e) => setPh({ ...ph, caption: e.target.value })} /></label>
              </div>
              <label className="check"><input type="checkbox" checked={ph.is_cover} onChange={(e) => setPh({ ...ph, is_cover: e.target.checked })} /> Use as cover photo</label>
              <button className="pill pill-ghost" disabled={!file && !ph.image_url.trim()}>Add photo</button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}

function Services() {
  const venues = useApi<Svc[]>("/admin/venues/");
  const guides = useApi<Svc[]>("/admin/guides/");
  const dests = useApi<AdminDest[]>("/admin/destinations/");
  const users = useApi<AdminUser[]>("/admin/users/");
  useLiveEvent(["admin.data.changed"], (e) => {
    if (e.entity === "services" || e.entity === "destinations" || e.entity === "users") {
      venues.reload(); guides.reload(); dests.reload(); users.reload();
    }
  });
  useLivePolling(() => { venues.reload(); guides.reload(); dests.reload(); users.reload(); });
  const [kind, setKind] = useState<"venue" | "guide">("venue");
  const [f, setF] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState("");
  const set = (k: string) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });

  const create = async (e: FormEvent) => {
    e.preventDefault(); setMsg("");
    const owner = f.owner ? Number(f.owner) : null;
    const body = kind === "venue"
      ? { destination: Number(f.destination), name: f.name, description: f.description ?? "", operator: owner, max_guests: Number(f.max || 10), base_price: f.price, included_guests: Number(f.included || 1), price_per_extra_guest: f.extra || "0", is_verified: false }
      : { destination: Number(f.destination), display_name: f.name, bio: f.description ?? "", user: owner, max_participants: Number(f.max || 8), price_per_group: f.price, price_per_participant: f.extra || "0", accreditation: f.accreditation ?? "", is_verified: false };
    try { await api(`/admin/${kind === "venue" ? "venues" : "guides"}/`, { method: "POST", body }); setF({}); setMsg("Created — verify it below once the operator/guide details are confirmed."); venues.reload(); guides.reload(); }
    catch (x) { setMsg((x as Error).message); }
  };
  const patch = async (path: string, id: number, body: Record<string, unknown>) => {
    try { await api(`/admin/${path}/${id}/`, { method: "PATCH", body }); venues.reload(); guides.reload(); } catch (x) { setMsg((x as Error).message); }
  };
  const del = async (path: string, id: number) => {
    if (!confirm("Delete this service? Services with reservations cannot be deleted.")) return;
    try { await api(`/admin/${path}/${id}/`, { method: "DELETE" }); venues.reload(); guides.reload(); } catch (x) { setMsg((x as Error).message); }
  };
  const destOpts = (dests.data ?? []).filter((d) => d.category === (kind === "venue" ? "BEACH" : "MOUNTAIN"));
  const ownerOpts = (users.data ?? []).filter((u) => u.role === (kind === "venue" ? "VENUE_OPERATOR" : "GUIDE"));

  const table = (title: string, path: string, rows: Svc[] | null, nameKey: string, priceKey: string) => (
    <>
      <h4 className="mt">{title}</h4>
      <div className="table-wrap"><table className="table">
        <thead><tr><th>Name</th><th>Destination</th><th>Price</th><th>Verified</th><th>Active</th><th></th></tr></thead>
        <tbody>
          {(rows ?? []).map((r) => (
            <tr key={r.id}>
              <td>{String(r[nameKey])}{r.is_demo && <span className="demo-pill">Demo</span>}</td><td>{r.destination_name}</td><td>{peso(String(r[priceKey]))}</td>
              <td><Toggle on={r.is_verified} set={(v) => patch(path, r.id, { is_verified: v })} /></td>
              <td><Toggle on={r.is_active} set={(v) => patch(path, r.id, { is_active: v })} /></td>
              <td><button className="icon-btn" onClick={() => del(path, r.id)}><FiTrash2 /></button></td>
            </tr>
          ))}
          {rows?.length === 0 && <tr><td colSpan={6} className="muted">None configured.</td></tr>}
        </tbody>
      </table></div>
    </>
  );

  return (
    <section className="panel">
      <h3>Beach venues &amp; mountain guides</h3>
      <p className="muted small">Only add services with confirmed operator/guide details and prices. Nothing becomes bookable until both the service and its destination are verified and bookings are enabled.</p>
      <form className="slot-form" onSubmit={create}>
        <label>Type<select value={kind} onChange={(e) => { setKind(e.target.value as "venue" | "guide"); setF({}); }}><option value="venue">Beach venue</option><option value="guide">Mountain guide</option></select></label>
        <label>Destination<select required value={f.destination ?? ""} onChange={set("destination")}><option value="">Select…</option>{destOpts.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}</select></label>
        <label>{kind === "venue" ? "Venue name" : "Guide / team name"}<input required value={f.name ?? ""} onChange={set("name")} /></label>
        <label>{kind === "venue" ? "Operator account" : "Guide account"}<select value={f.owner ?? ""} onChange={set("owner")}><option value="">(none)</option>{ownerOpts.map((u) => <option key={u.id} value={u.id}>{u.username}</option>)}</select></label>
        <label>{kind === "venue" ? "Base price / slot (₱)" : "Guide fee / group (₱)"}<input required type="number" min="0" step="0.01" value={f.price ?? ""} onChange={set("price")} /></label>
        <label>{kind === "venue" ? "Extra guest fee (₱)" : "Per participant (₱)"}<input type="number" min="0" step="0.01" value={f.extra ?? ""} onChange={set("extra")} /></label>
        <label>{kind === "venue" ? "Max guests" : "Max participants"}<input type="number" min="1" value={f.max ?? ""} onChange={set("max")} /></label>
        {kind === "venue" ? <label>Guests included<input type="number" min="1" value={f.included ?? ""} onChange={set("included")} /></label>
          : <label>Accreditation<input value={f.accreditation ?? ""} onChange={set("accreditation")} /></label>}
        <button className="pill pill-solid">Create</button>
      </form>
      {msg && <p className="small muted">{msg}</p>}
      {table("Beach venues", "venues", venues.data, "name", "base_price")}
      {table("Mountain guides", "guides", guides.data, "display_name", "price_per_group")}
    </section>
  );
}

function AllReservations() {
  const { data, loading, reload } = useApi<Reservation[]>("/admin/reservations/");
  const [tab, setTab] = useState("ALL");
  useLiveEvent(["reservation.new", "reservation.status"], reload);
  useLiveEvent(["admin.data.changed"], reload);
  useLivePolling(reload);
  const list = data ?? [];
  return (
    <section className="panel">
      <h3>All reservations</h3>
      <StatusTabs value={tab} onChange={setTab} counts={countByStatus(list)} />
      {loading && !data ? <Spinner /> : <ReservationList items={tab === "ALL" ? list : list.filter((r) => r.status === tab)} mode="admin" onChanged={reload} />}
    </section>
  );
}

function Users() {
  const { data, reload } = useApi<AdminUser[]>("/admin/users/");
  useLiveEvent(["admin.data.changed"], (e) => {
    if (e.entity === "users") reload();
  });
  useLivePolling(reload);
  const [msg, setMsg] = useState("");
  const patch = async (u: AdminUser, body: Record<string, unknown>) => {
    try { await api(`/admin/users/${u.id}/`, { method: "PATCH", body }); reload(); } catch (x) { setMsg((x as Error).message); }
  };
  return (
    <section className="panel">
      <h3>Users &amp; roles</h3>
      {msg && <div className="result result-err">{msg}</div>}
      {!data ? <Spinner /> : (
        <div className="table-wrap"><table className="table">
          <thead><tr><th>Username</th><th>Name</th><th>Email</th><th>Role</th><th>Active</th></tr></thead>
          <tbody>{data.map((u) => (
            <tr key={u.id}>
              <td>{u.username}</td><td>{u.first_name} {u.last_name}</td><td>{u.email}</td>
              <td><select value={u.role} onChange={(e) => patch(u, { role: e.target.value })}>{Object.entries(roleLabel).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></td>
              <td><Toggle on={u.is_active} set={(v) => patch(u, { is_active: v })} /></td>
            </tr>
          ))}</tbody>
        </table></div>
      )}
    </section>
  );
}
