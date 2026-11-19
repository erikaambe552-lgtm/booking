"""Runs N truly simultaneous PostgreSQL sessions (N separate server processes)
against one exclusive slot and records what happens under three designs.

Each session is a separate `psql` process -> separate PostgreSQL backend
process. All sessions wait with pg_sleep_until() for the same start instant,
then call try_book(). Requires only `psql` on PATH.

    python run_db_concurrency_test.py --host /var/run/postgresql --user postgres --db postgres
"""
import argparse
import json
import statistics
import subprocess
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).parent


def psql(a, sql, timeout=120):
    cmd = ["psql", "-h", a.host, "-U", a.user, "-d", a.db, "-qAtX", "-v", "ON_ERROR_STOP=1", "-c", sql]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=True).stdout.strip()


def reset(a, kind, n_slots=1):
    psql(a, "SET search_path=cb; TRUNCATE bookings_beachreservation, bookings_guidereservation, "
            "naive_beachreservation; DELETE FROM bookings_venueslot; DELETE FROM bookings_guideschedule;")
    ids = []
    for i in range(n_slots):
        table, owner = ("bookings_venueslot", "venue_id") if kind == "beach" else ("bookings_guideschedule", "guide_id")
        ids.append(int(psql(a, f"SET search_path=cb; INSERT INTO {table} ({owner}, start_at, end_at) VALUES "
                               f"({i + 1}, now() + interval '3 days', now() + interval '3 days 12 hours') "
                               f"RETURNING id;").splitlines()[-1]))
    return ids


def race(a, kind, mode, n, delay_ms, slot_ids):
    """Start n psql processes; all begin try_book() at the same instant."""
    start_at = datetime.now(timezone.utc) + timedelta(seconds=1.5)
    ts = start_at.isoformat()
    procs = []
    for i in range(n):
        slot = slot_ids[i % len(slot_ids)]
        sql = (f"SET search_path=cb; SELECT pg_sleep_until('{ts}'); "
               f"SELECT try_book('{kind}', {slot}, {i + 1}, {delay_ms}, '{mode}');")
        procs.append(subprocess.Popen(["psql", "-h", a.host, "-U", a.user, "-d", a.db, "-qAtX", "-c", sql],
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
    t0 = time.perf_counter()
    outs = [p.communicate(timeout=120) for p in procs]
    rows = []
    for out, err in outs:
        line = [l for l in out.strip().splitlines() if "|" in l]
        if not line:
            rows.append(dict(outcome="error", pid=None, wait_ms=0.0, total_ms=0.0, err=err.strip()[:120]))
            continue
        o, pid, wait, total = line[-1].split("|")
        rows.append(dict(outcome=o, pid=int(pid), wait_ms=float(wait), total_ms=float(total)))
    table = "naive_beachreservation" if mode == "none" else (
        "bookings_beachreservation" if kind == "beach" else "bookings_guidereservation")
    col = "schedule_id" if kind == "mountain" else "slot_id"
    stored = psql(a, f"SET search_path=cb; SELECT count(*), count(DISTINCT {col}) FROM {table} "
                     f"WHERE status IN ('PENDING','APPROVED');").splitlines()[-1].split("|")
    # Wall time of the booking work itself = latest finish (approx) — use max total_ms.
    return rows, int(stored[0]), int(stored[1])


def summarize(label, kind, mode, n, delay, rows, stored, distinct_slots, n_slots):
    c = Counter(r["outcome"] for r in rows)
    totals = [r["total_ms"] for r in rows if r["pid"]]
    waits = [r["wait_ms"] for r in rows if r["pid"]]
    expected_active = n_slots  # one booking per slot at most
    return dict(scenario=label, kind=kind, mode=mode, sessions=n, slots=n_slots, delay_ms=delay,
                success=c.get("success", 0), conflict_after_lock=c.get("conflict", 0),
                conflict_by_constraint=c.get("conflict_by_constraint", 0), errors=c.get("error", 0),
                distinct_backend_pids=len({r["pid"] for r in rows if r["pid"]}),
                active_rows_stored=stored, expected_max_active=expected_active,
                consistent=stored <= expected_active and distinct_slots == stored,
                avg_ms=round(statistics.mean(totals), 2), max_ms=round(max(totals), 2),
                avg_lock_wait_ms=round(statistics.mean(waits), 2), max_lock_wait_ms=round(max(waits), 2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="/var/run/postgresql")
    ap.add_argument("--user", default="postgres")
    ap.add_argument("--db", default="postgres")
    ap.add_argument("--delay", type=int, default=50, help="simulated processing ms inside critical section")
    a = ap.parse_args()

    psql(a, (HERE / "schema.sql").read_text())
    results = []

    # 1) Same exclusive slot, three designs, increasing concurrency
    for n in (5, 10, 20):
        for mode in ("none", "constraint_only", "locked"):
            ids = reset(a, "beach")
            rows, stored, distinct = race(a, "beach", mode, n, a.delay, ids)
            results.append(summarize(f"same-slot/{mode}", "beach", mode, n, a.delay, rows, stored, distinct, 1))
        ids = reset(a, "mountain")
        rows, stored, distinct = race(a, "mountain", "locked", n, a.delay, ids)
        results.append(summarize("same-schedule/locked", "mountain", "locked", n, a.delay, rows, stored, distinct, 1))

    # 2) No contention: N users each booking a DIFFERENT slot (locks don't block each other)
    for n in (1, 5, 10, 20):
        ids = reset(a, "beach", n_slots=n)
        t0 = time.perf_counter()
        rows, stored, distinct = race(a, "beach", "locked", n, a.delay, ids)
        results.append(summarize("distinct-slots/locked", "beach", "locked", n, a.delay, rows, stored, distinct, n))

    out = HERE / "results"
    out.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    (out / f"db_concurrency_{stamp}.json").write_text(json.dumps(results, indent=2))

    hdr = ("| Scenario | Sessions | Success | Conflict (after lock) | Conflict (constraint) | Active rows stored "
           "| Consistent | Backend PIDs | Avg ms | Max ms | Max lock wait ms |")
    md = [f"# PostgreSQL concurrency test — measured {datetime.now():%Y-%m-%d %H:%M}\n",
          f"Simulated processing inside critical section: {a.delay} ms. Each session = separate PostgreSQL "
          f"backend process.\n", hdr, "|" + "---|" * 11]
    for r in results:
        md.append(f"| {r['scenario']} | {r['sessions']} | {r['success']} | {r['conflict_after_lock']} | "
                  f"{r['conflict_by_constraint']} | {r['active_rows_stored']} (max {r['expected_max_active']}) | "
                  f"{'YES' if r['consistent'] else 'NO'} | {r['distinct_backend_pids']} | {r['avg_ms']} | "
                  f"{r['max_ms']} | {r['max_lock_wait_ms']} |")
    (out / f"db_concurrency_{stamp}.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
