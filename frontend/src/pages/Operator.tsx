import { useState } from "react";
import { Spinner } from "../components/Cards";
import { countByStatus, ReservationList, StatusTabs } from "../components/Reservations";
import { SlotManager } from "../components/SlotManager";
import { useAuth } from "../lib/auth";
import { roleLabel } from "../lib/format";
import { useApi } from "../lib/useApi";
import { useLiveEvent } from "../lib/realtime";
import type { Reservation } from "../lib/types";

export default function Operator() {
  const { user } = useAuth();
  const { data, loading, reload } = useApi<Reservation[]>("/operator/reservations/");
  const [tab, setTab] = useState("PENDING");
  useLiveEvent(["reservation.new", "reservation.status"], reload);
  const list = data ?? [];
  const shown = tab === "ALL" ? list : list.filter((r) => r.status === tab);
  return (
    <div className="page container dash">
      <div className="dash-head">
        <div><span className="eyebrow">{roleLabel[user?.role ?? "VENUE_OPERATOR"]}</span><h1>Service dashboard</h1></div>
        <div className="mini-stats"><div><b>{countByStatus(list).PENDING ?? 0}</b><span>Awaiting approval</span></div></div>
      </div>
      <section className="panel">
        <h3>{user?.role === "GUIDE" ? "Tour schedules" : "Venue availability"}</h3>
        <SlotManager />
      </section>
      <section className="panel">
        <h3>Reservations for my services</h3>
        <StatusTabs value={tab} onChange={setTab} counts={countByStatus(list)} />
        {loading && !data ? <Spinner /> : <ReservationList items={shown} mode="provider" onChanged={reload} />}
      </section>
    </div>
  );
}
