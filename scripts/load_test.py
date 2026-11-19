"""Performance & scalability test: 1, 5, 10, 20 concurrent users.

For each concurrency level C, C client threads each send R requests as fast as
possible to a realistic API mix (catalog list, destination detail,
availability check). Records:
  * average / median / p95 response time
  * throughput (requests per second)
  * error rate
  * which server worker PIDs answered

It also compares the SAME workload against two server set-ups so you can
compute speedup and efficiency from YOUR OWN measurements:
  1) start the server with 1 worker   -> run:  --label workers1
  2) start the server with 4 workers  -> run:  --label workers4
  3) python scripts/load_test.py --report   (builds tables + charts from both)

Speedup  S(p) = T(1 worker) / T(p workers)     (T = wall time for the workload)
Efficiency E(p) = S(p) / p

Usage:
  python scripts/load_test.py --label workers4 --levels 1 5 10 20 --requests 30
  python scripts/load_test.py --report
"""
import argparse
import csv
import json
import statistics
import threading
import time
from collections import Counter
from pathlib import Path

import requests

RESULTS = Path(__file__).parent / "results"


def percentile(values, p):
    v = sorted(values)
    k = max(0, min(len(v) - 1, round(p / 100 * (len(v) - 1))))
    return v[k]


def run_level(base, users, per_user, slugs):
    barrier = threading.Barrier(users)
    samples, lock = [], threading.Lock()
    paths = ["/api/destinations/", "/api/destinations/?category=BEACH"]
    for s in slugs:
        paths += [f"/api/destinations/{s}/", f"/api/destinations/{s}/availability/"]

    def client(cid):
        sess = requests.Session()
        barrier.wait()
        for n in range(per_user):
            path = paths[(cid + n) % len(paths)]
            t0 = time.perf_counter()
            try:
                r = sess.get(base + path, timeout=30)
                code, pid = r.status_code, r.headers.get("X-Worker-PID")
                srv = float(r.headers.get("X-Processing-Time-ms", "nan"))
            except requests.RequestException:
                code, pid, srv = 0, None, float("nan")
            with lock:
                samples.append(((time.perf_counter() - t0) * 1000, code, pid, srv))

    threads = [threading.Thread(target=client, args=(i,)) for i in range(users)]
    t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wall = time.perf_counter() - t0
    rts = [s[0] for s in samples]
    errors = sum(1 for s in samples if not (200 <= s[1] < 300))
    srv = [s[3] for s in samples if s[3] == s[3]]
    return dict(users=users, requests=len(samples), wall_s=round(wall, 3),
                throughput_rps=round(len(samples) / wall, 2), avg_ms=round(statistics.mean(rts), 2),
                median_ms=round(statistics.median(rts), 2), p95_ms=round(percentile(rts, 95), 2),
                max_ms=round(max(rts), 2), avg_server_ms=round(statistics.mean(srv), 2) if srv else None,
                error_rate_pct=round(100 * errors / len(samples), 2),
                distinct_pids=len({s[2] for s in samples if s[2]}),
                status_codes=dict(Counter(s[1] for s in samples)))


def measure(a):
    slugs = [d["slug"] for d in requests.get(f"{a.base}/api/destinations/", timeout=10).json()[:6]]
    requests.get(f"{a.base}/api/destinations/", timeout=10)  # warm-up
    rows = []
    for lv in a.levels:
        res = run_level(a.base, lv, a.requests, slugs)
        res["label"] = a.label
        rows.append(res)
        print(f"[{a.label}] users={lv:>3}  req={res['requests']:>4}  thr={res['throughput_rps']:>7.1f} rps  "
              f"avg={res['avg_ms']:>7.1f} ms  p95={res['p95_ms']:>7.1f} ms  err={res['error_rate_pct']}%  "
              f"pids={res['distinct_pids']}")
    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / f"load_{a.label}.json"
    out.write_text(json.dumps(rows, indent=2))
    print(f"Saved -> {out}")


def report():
    files = sorted(RESULTS.glob("load_*.json"))
    if not files:
        raise SystemExit("No results yet. Run with --label first.")
    data = {f.stem.replace("load_", ""): json.loads(f.read_text()) for f in files}
    lines = ["# CampBlazer load-test results (measured)\n"]
    for label, rows in data.items():
        lines += [f"\n## {label}\n", "| Users | Requests | Wall (s) | Throughput (req/s) | Avg (ms) | Median (ms) "
                  "| p95 (ms) | Avg server (ms) | Error rate | Worker PIDs |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            lines.append(f"| {r['users']} | {r['requests']} | {r['wall_s']} | {r['throughput_rps']} | {r['avg_ms']} | "
                         f"{r['median_ms']} | {r['p95_ms']} | {r['avg_server_ms']} | {r['error_rate_pct']}% | "
                         f"{r['distinct_pids']} |")

    # Speedup / efficiency only when a 1-worker baseline exists.
    if "workers1" in data:
        base = {r["users"]: r for r in data["workers1"]}
        for label, rows in data.items():
            if label == "workers1" or not label.startswith("workers"):
                continue
            p = int(label.replace("workers", "") or 1)
            lines += [f"\n## Speedup: workers1 vs {label} (p = {p})\n",
                      "| Users | T(1) s | T(p) s | Speedup S=T1/Tp | Efficiency E=S/p |", "|---|---|---|---|---|"]
            for r in rows:
                if r["users"] in base and r["requests"] == base[r["users"]]["requests"]:
                    s = base[r["users"]]["wall_s"] / r["wall_s"]
                    lines.append(f"| {r['users']} | {base[r['users']]['wall_s']} | {r['wall_s']} | {s:.2f} | {s / p:.2f} |")
    md = RESULTS / "load_report.md"
    md.write_text("\n".join(lines) + "\n")
    print(md.read_text())

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 2, figsize=(11, 4))
        for label, rows in data.items():
            u = [r["users"] for r in rows]
            ax[0].plot(u, [r["throughput_rps"] for r in rows], marker="o", label=label)
            ax[1].plot(u, [r["avg_ms"] for r in rows], marker="o", label=label)
        ax[0].set(title="Throughput vs concurrent users", xlabel="Concurrent users", ylabel="requests / s")
        ax[1].set(title="Average response time", xlabel="Concurrent users", ylabel="ms")
        for x in ax:
            x.grid(alpha=.3)
            x.legend()
        fig.tight_layout()
        fig.savefig(RESULTS / "load_charts.png", dpi=150)
        print(f"Chart -> {RESULTS / 'load_charts.png'}")
    except ImportError:
        print("matplotlib not installed — skipped charts.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--label", default="run")
    ap.add_argument("--levels", type=int, nargs="+", default=[1, 5, 10, 20])
    ap.add_argument("--requests", type=int, default=30, help="requests per user")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    report() if a.report else measure(a)


if __name__ == "__main__":
    main()
