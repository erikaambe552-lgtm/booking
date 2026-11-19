import { useEffect, useState, type FormEvent } from "react";
import { Spinner } from "../components/Cards";
import { countByStatus, ReservationList, StatusTabs } from "../components/Reservations";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { roleLabel } from "../lib/format";
import { useApi } from "../lib/useApi";
import { useLiveEvent } from "../lib/realtime";
import type { Reservation } from "../lib/types";

export default function Dashboard() {
  const { user, refresh } = useAuth();
  const { data, loading, reload } = useApi<Reservation[]>("/bookings/mine/");
  const [tab, setTab] = useState("ALL");
  // Operator approves -> server pushes -> list refreshes instantly (no polling).
  useLiveEvent(["reservation.status"], reload);
  const [p, setP] = useState({ first_name: "", last_name: "", email: "", phone: "", hometown: "" });
  const [saved, setSaved] = useState("");
  useEffect(() => { if (user) setP({ first_name: user.first_name, last_name: user.last_name, email: user.email, phone: user.phone ?? "", hometown: user.hometown ?? "" }); }, [user]);

  const save = async (e: FormEvent) => {
    e.preventDefault(); setSaved("");
    try { await api("/auth/me/", { method: "PATCH", body: p }); await refresh(); setSaved("Profile saved."); }
    catch (x) { setSaved((x as Error).message); }
  };
  const list = data ?? [];
  const shown = tab === "ALL" ? list : list.filter((r) => r.status === tab);
  const upcoming = list.filter((r) => ["PENDING", "APPROVED"].includes(r.status) && new Date(r.start_at) > new Date()).length;

  return (
    <div className="page container dash">
      <div className="dash-head">
        <div><span className="eyebrow">{roleLabel[user?.role ?? "CAMPER"]}</span><h1>Hi, {user?.first_name || user?.username}</h1></div>
        <div className="mini-stats"><div><b>{upcoming}</b><span>Upcoming</span></div><div><b>{list.length}</b><span>All bookings</span></div></div>
      </div>
      <div className="dash-grid">
        <section className="panel">
          <h3>My reservations</h3>
          <StatusTabs value={tab} onChange={setTab} counts={countByStatus(list)} />
          {loading && !data ? <Spinner /> : <ReservationList items={shown} mode="camper" onChanged={reload} />}
        </section>
        <aside className="panel">
          <h3>Profile</h3>
          <form onSubmit={save} className="stack">
            <div className="grid-2">
              <label>First name<input value={p.first_name} onChange={(e) => setP({ ...p, first_name: e.target.value })} /></label>
              <label>Last name<input value={p.last_name} onChange={(e) => setP({ ...p, last_name: e.target.value })} /></label>
            </div>
            <label>Email<input type="email" value={p.email} onChange={(e) => setP({ ...p, email: e.target.value })} /></label>
            <label>Mobile<input value={p.phone} onChange={(e) => setP({ ...p, phone: e.target.value })} /></label>
            <label>Hometown<input value={p.hometown} onChange={(e) => setP({ ...p, hometown: e.target.value })} /></label>
            <button className="pill pill-solid">Save profile</button>
            {saved && <small className="muted">{saved}</small>}
          </form>
        </aside>
      </div>
    </div>
  );
}
