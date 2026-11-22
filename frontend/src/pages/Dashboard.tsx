import { useEffect, useState, type FormEvent } from "react";
import { FiCalendar, FiCheckCircle, FiClock, FiUser } from "react-icons/fi";
import { Spinner } from "../components/Cards";
import { countByStatus, ReservationList, StatusTabs } from "../components/Reservations";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { roleLabel } from "../lib/format";
import { useLiveEvent, useLivePolling } from "../lib/realtime";
import { useApi } from "../lib/useApi";
import type { Reservation } from "../lib/types";

export default function Dashboard() {
  const { user, refresh } = useAuth();
  const { data, loading, reload, setData } = useApi<Reservation[]>("/bookings/mine/");
  const [tab, setTab] = useState("ALL");
  const [saved, setSaved] = useState("");
  const [profile, setProfile] = useState({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    hometown: "",
  });

  useLiveEvent(["reservation.status"], (event) => {
    setData((current) => current?.map((reservation) =>
      reservation.id === event.id
        ? { ...reservation, status: event.status as Reservation["status"] }
        : reservation
    ) ?? null);
    reload();
  });
  useLivePolling(reload, 5000);

  useEffect(() => {
    if (user) {
      setProfile({
        first_name: user.first_name,
        last_name: user.last_name,
        email: user.email,
        phone: user.phone ?? "",
        hometown: user.hometown ?? "",
      });
    }
  }, [user]);

  const saveProfile = async (event: FormEvent) => {
    event.preventDefault();
    setSaved("");
    try {
      await api("/auth/me/", { method: "PATCH", body: profile });
      await refresh();
      setSaved("Profile updated.");
    } catch (error) {
      setSaved((error as Error).message);
    }
  };

  const list = data ?? [];
  const upcoming = list.filter((r) =>
    ["PENDING", "APPROVED"].includes(r.status) &&
    new Date(r.start_at) > new Date()
  ).length;
  const approved = list.filter((r) => r.status === "APPROVED").length;
  const pending = list.filter((r) => r.status === "PENDING").length;
  const completed = list.filter((r) => r.status === "COMPLETED").length;
  const shown = tab === "ALL" ? list : list.filter((r) => r.status === tab);

  return (
    <div className="profile-dashboard">
      <header className="profile-dashboard-header">
        <div>
          <span className="eyebrow">My account</span>
          <h1>{user?.first_name || user?.username}</h1>
          <p>{roleLabel[user?.role ?? "CAMPER"]} profile and reservation history</p>
        </div>
        <div className="profile-role-badge"><FiUser /> Active account</div>
      </header>

      <section className="profile-summary" aria-label="Reservation summary">
        <article><span><FiCalendar /> Upcoming</span><b>{upcoming}</b></article>
        <article><span><FiClock /> Pending</span><b>{pending}</b></article>
        <article><span><FiCheckCircle /> Approved</span><b>{approved}</b></article>
        <article><span><FiUser /> Completed</span><b>{completed}</b></article>
      </section>

      <div className="profile-dashboard-layout">
        <aside className="panel profile-details">
          <div className="profile-panel-title"><div><span>Personal information</span><h3>Profile</h3></div></div>
          <form onSubmit={saveProfile} className="stack">
            <div className="grid-2">
              <label>First name<input value={profile.first_name} onChange={(e) => setProfile({ ...profile, first_name: e.target.value })} /></label>
              <label>Last name<input value={profile.last_name} onChange={(e) => setProfile({ ...profile, last_name: e.target.value })} /></label>
            </div>
            <label>Email<input type="email" value={profile.email} onChange={(e) => setProfile({ ...profile, email: e.target.value })} /></label>
            <label>Mobile<input value={profile.phone} onChange={(e) => setProfile({ ...profile, phone: e.target.value })} /></label>
            <label>Hometown<input value={profile.hometown} onChange={(e) => setProfile({ ...profile, hometown: e.target.value })} /></label>
            <button className="pill pill-solid">Save profile</button>
            {saved && <small className={saved === "Profile updated." ? "profile-success" : "result result-err"}>{saved}</small>}
          </form>
        </aside>

        <section className="panel profile-reservations">
          <div className="profile-panel-title"><div><span>My bookings</span><h3>Reservations</h3></div></div>
          <StatusTabs value={tab} onChange={setTab} counts={countByStatus(list)} />
          {loading && !data ? <Spinner /> : <ReservationList items={shown} mode="camper" onChanged={reload} />}
        </section>
      </div>
    </div>
  );
}
