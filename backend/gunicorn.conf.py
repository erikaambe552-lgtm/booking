"""Gunicorn config: several independent worker PROCESSES, each running the
ASGI app (HTTP + WebSockets) under uvicorn. Linux/macOS/WSL:

    gunicorn -c gunicorn.conf.py config.asgi:application

Workers don't share memory; they coordinate through PostgreSQL (bookings) and
Redis (WebSocket events). Set REDIS_URL in .env when workers > 1.
On Windows use run_server_windows.py instead."""
import multiprocessing
import os

bind = os.getenv("GUNICORN_BIND", "127.0.0.1:8000")
workers = int(os.getenv("GUNICORN_WORKERS", min(4, multiprocessing.cpu_count() * 2 + 1)))
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "uvicorn_worker.UvicornWorker")
timeout = 30
accesslog = "-"


def post_fork(server, worker):
    server.log.info("CampBlazer worker spawned (pid: %s)", worker.pid)
