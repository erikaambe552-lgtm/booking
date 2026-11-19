import { useState } from "react";
import { FiCpu, FiDatabase, FiGlobe, FiLock, FiServer, FiZap } from "react-icons/fi";
import { api, type ApiMeta } from "../lib/api";

interface Hit { n: number; pid?: string; serverMs?: string; clientMs: number }

/** Live demo for the panel: fire N requests at once from the browser and see
 *  which server worker process answered each one. */
function ParallelPing() {
  const [n, setN] = useState(10);
  const [hits, setHits] = useState<Hit[]>([]);
  const [wall, setWall] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const fire = async () => {
    setBusy(true); setHits([]);
    const t0 = performance.now();
    const res = await Promise.all(Array.from({ length: n }, (_, i) => {
      let m: ApiMeta | undefined;
      return api("/system/info/", {}, (x) => { m = x; }).then(() => ({ n: i + 1, pid: m?.workerPid, serverMs: m?.serverMs, clientMs: m?.clientMs ?? 0 }))
        .catch(() => ({ n: i + 1, pid: "error", clientMs: 0 }));
    }));
    setWall(Math.round(performance.now() - t0));
    setHits(res); setBusy(false);
  };
  const pids = [...new Set(hits.map((h) => h.pid))];
  const palette = ["#ff7a3d", "#22b8cf", "#8b7cf6", "#ffb347", "#f472b6", "#60a5fa", "#e2e8f0", "#fb923c"];
  return (
    <div className="ping">
      <div className="ping-ctrl">
        <label>Parallel requests<input type="number" min={1} max={50} value={n} onChange={(e) => setN(Number(e.target.value))} /></label>
        <button className="pill pill-solid" onClick={fire} disabled={busy}><FiZap /> {busy ? "Sending…" : "Send simultaneously"}</button>
      </div>
      {hits.length > 0 && (
        <>
          <div className="ping-grid">
            {hits.map((h) => (
              <div key={h.n} className="ping-cell" style={{ borderColor: palette[pids.indexOf(h.pid) % palette.length] }}>
                <small>#{h.n}</small><b>PID {h.pid}</b><span>{h.clientMs} ms</span>
              </div>
            ))}
          </div>
          <p className="small"><b>{pids.length}</b> distinct server worker process{pids.length === 1 ? "" : "es"} handled {hits.length} requests · total wall time {wall} ms. (Browsers cap ~6 parallel connections per host; use <code>scripts/concurrency_test.py</code> for larger tests.)</p>
        </>
      )}
    </div>
  );
}

export default function HowItWorks() {
  return (
    <div className="page">
      <section className="page-hero">
        <div className="container">
          <span className="eyebrow">How it works</span>
          <h1>Discovery to reservation — and what happens on the server</h1>
          <p>CampBlazer is a client–server system: your browser talks to a Django REST API over HTTP, the API runs as several worker processes, and PostgreSQL is the single source of truth for availability.</p>
        </div>
      </section>
      <div className="container">
        <section className="panel">
          <h3>Two separate booking workflows</h3>
          <div className="flows">
            <div className="flow flow-sea"><h4>Beaches → Venue booking</h4><ol><li>Choose a beach</li><li>Pick a venue / camping area</li><li>Pick a date slot (venue availability records)</li><li>Guests, contact details, special requests</li><li>Price breakdown → submit → server locks the venue slot</li></ol></div>
            <div className="flow flow-violet"><h4>Mountains → Tour-guide booking</h4><ol><li>Choose a mountain</li><li>Pick a preferred tour date</li><li>Pick an available guide and tour schedule (guide availability records)</li><li>Participants, contact details, special requests</li><li>Price breakdown → submit → server locks the guide schedule</li></ol></div>
          </div>
        </section>

        <section className="panel">
          <h3>Architecture</h3>
          <div className="arch">
            <div className="arch-col"><FiGlobe size={28} /><b>Many users</b><span>Browsers (React + TypeScript)</span></div>
            <div className="arch-arrow">HTTP / JSON<br />REST API</div>
            <div className="arch-col arch-server"><FiServer size={28} /><b>Django + DRF</b>
              <div className="workers">{[1, 2, 3, 4].map((w) => <span key={w}><FiCpu /> worker {w}</span>)}</div>
              <span>gunicorn processes (or waitress threads)</span></div>
            <div className="arch-arrow">SQL over TCP<br />1 connection / worker</div>
            <div className="arch-col"><FiDatabase size={28} /><b>PostgreSQL</b><span><FiLock /> row locks · unique &amp; exclusion constraints</span></div>
          </div>
          <ol className="seq">
            <li>User submits a reservation in the browser.</li>
            <li>Frontend sends <code>POST /api/bookings/beach/</code> (or <code>/mountain/</code>).</li>
            <li>One of the Django workers receives it.</li>
            <li>It opens <code>transaction.atomic()</code> and locks the slot row with <code>select_for_update()</code>.</li>
            <li>While holding the lock it re-checks availability in PostgreSQL and inserts the reservation.</li>
            <li>Commit releases the lock; other workers waiting on that row now see it taken.</li>
            <li>Winner gets <code>201 Created</code>; the others get <code>409 Conflict</code>.</li>
            <li>The frontend shows the confirmation or refreshes availability.</li>
          </ol>
        </section>

        <section className="panel">
          <h3>Live: parallel requests to the server</h3>
          <p className="muted">Each response carries an <code>X-Worker-PID</code> header showing which server process handled it.</p>
          <ParallelPing />
        </section>
      </div>
    </div>
  );
}
