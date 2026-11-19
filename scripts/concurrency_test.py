"""End-to-end CONCURRENT booking test against a running CampBlazer server.

Real HTTP requests from N client threads (one per demo camper account) are
released at the same instant with a threading.Barrier and all target the SAME
exclusive slot. The server must accept exactly one and answer 409 to the rest.

Prerequisites (see README):
  1. python manage.py seed_destinations && python manage.py seed_demo
  2. Start a multi-worker server, e.g.  gunicorn -c gunicorn.conf.py config.wsgi
     (Windows: python run_server_windows.py --threads 8)
  3. LOGIN_THROTTLE=1000/min in .env so 20 logins are not throttled

Usage:
  python scripts/concurrency_test.py --kind beach --users 10
  python scripts/concurrency_test.py --kind mountain --users 20 --base http://127.0.0.1:8000

Results are printed and appended to scripts/results/concurrency_results.csv
"""
import argparse
import csv
import statistics
import threading
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import requests

PASSWORD_DEFAULT = "CampDemo#2026"
RESULTS = Path(__file__).parent / "results"


def login(base, username, password):
    r = requests.post(f"{base}/api/auth/login/", json={"username": username, "password": password}, timeout=10)
    r.raise_for_status()
    return r.json()["token"]


DEFAULT_SLUG = {"beach": "agta-beach-resort", "mountain": "mount-tres-marias"}


def find_free_slot(base, kind, slug):
    data = requests.get(f"{base}/api/destinations/{slug}/availability/", timeout=10).json()
    for svc in data["services"]:
        for s in svc["slots"]:
            if s["available"]:
                return s["id"], svc["name"]
    raise SystemExit("No free slot left — run `python manage.py seed_demo` again or cancel bookings.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--kind", choices=["beach", "mountain"], default="beach")
    ap.add_argument("--users", type=int, default=10)
    ap.add_argument("--password", default=PASSWORD_DEFAULT)
    ap.add_argument("--destination", help="slug of an approved destination (default: agta-beach-resort / "
                                           "mount-tres-marias)")
    a = ap.parse_args()

    tokens = [login(a.base, f"camper{i:02d}_demo", a.password) for i in range(1, a.users + 1)]
    slug = a.destination or DEFAULT_SLUG[a.kind]
    slot_id, svc_name = find_free_slot(a.base, a.kind, slug)
    print(f"Target: {a.kind} slot #{slot_id} ({svc_name}) — {a.users} simultaneous clients")

    url = f"{a.base}/api/bookings/{a.kind}/"
    payload_key = ("slot_id", "guests") if a.kind == "beach" else ("schedule_id", "participants")
    barrier = threading.Barrier(a.users)
    results, lock = [], threading.Lock()

    def client(i):
        body = {payload_key[0]: slot_id, payload_key[1]: 2, "customer_name": f"Demo Camper {i + 1}",
                "contact_phone": "09170000000", "contact_email": f"camper{i + 1:02d}@demo.campblazer.test"}
        session = requests.Session()
        barrier.wait()  # everyone fires at the same moment
        sent = time.time()
        t0 = time.perf_counter()
        r = session.post(url, json=body, headers={"Authorization": f"Token {tokens[i]}"}, timeout=30)
        rt = (time.perf_counter() - t0) * 1000
        with lock:
            results.append(dict(client=i + 1, status=r.status_code, response_ms=round(rt, 2),
                                server_ms=float(r.headers.get("X-Processing-Time-ms", "nan")),
                                worker_pid=r.headers.get("X-Worker-PID"), sent_at=sent,
                                detail=(r.json().get("reference") or r.json().get("detail", ""))[:60]))

    threads = [threading.Thread(target=client, args=(i,)) for i in range(a.users)]
    wall0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wall = (time.perf_counter() - wall0) * 1000

    results.sort(key=lambda r: r["response_ms"])
    print(f"\n{'client':>6} {'status':>6} {'resp ms':>9} {'server ms':>9} {'worker pid':>10}  detail")
    for r in results:
        print(f"{r['client']:>6} {r['status']:>6} {r['response_ms']:>9.1f} {r['server_ms']:>9.1f} "
              f"{str(r['worker_pid']):>10}  {r['detail']}")

    codes = Counter(r["status"] for r in results)
    send_spread = (max(r["sent_at"] for r in results) - min(r["sent_at"] for r in results)) * 1000
    pids = sorted({r["worker_pid"] for r in results})
    ok, conflict = codes.get(201, 0), codes.get(409, 0)
    rts = [r["response_ms"] for r in results]
    consistent = ok == 1 and conflict == a.users - 1
    print(f"\nSimultaneous requests : {a.users} (send times within {send_spread:.1f} ms)")
    print(f"Successful (201)      : {ok}")
    print(f"Conflicts (409)       : {conflict}")
    print(f"Other                 : {a.users - ok - conflict}  {dict(codes)}")
    print(f"Distinct server PIDs  : {len(pids)} -> {pids}")
    print(f"Response time ms      : min {min(rts):.1f} / avg {statistics.mean(rts):.1f} / max {max(rts):.1f}")
    print(f"Wall-clock total      : {wall:.1f} ms")

    # Verify the database: exactly one ACTIVE reservation for this slot.
    mine = requests.get(f"{a.base}/api/destinations/{slug}/availability/", timeout=10).json()
    still_free = any(s["id"] == slot_id and s["available"] for svc in mine["services"] for s in svc["slots"])
    print(f"Slot still free after : {still_free} (expected False)")
    print("DATA CONSISTENT ✔" if consistent and not still_free else "INCONSISTENT ✘ — investigate")

    RESULTS.mkdir(exist_ok=True)
    f = RESULTS / "concurrency_results.csv"
    new = not f.exists()
    with f.open("a", newline="") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["timestamp", "kind", "simultaneous", "success", "conflict", "other", "distinct_pids",
                        "avg_ms", "min_ms", "max_ms", "wall_ms", "consistent"])
        w.writerow([datetime.now().isoformat(timespec="seconds"), a.kind, a.users, ok, conflict,
                    a.users - ok - conflict, len(pids), round(statistics.mean(rts), 2), round(min(rts), 2),
                    round(max(rts), 2), round(wall, 2), consistent and not still_free])
    print(f"Saved -> {f}")


if __name__ == "__main__":
    main()
