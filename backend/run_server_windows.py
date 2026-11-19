"""Single-process ASGI server for native Windows (gunicorn does not run there).

Use WSL for multiple worker processes. Native Windows Uvicorn workers can fail
while sharing the listening socket.

    python run_server_windows.py
"""
import argparse
import os

import uvicorn

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--workers", type=int, default=1)
    a = p.parse_args()
    if a.workers != 1:
        p.error("Native Windows supports one worker; use WSL for multiple workers.")
    print(f"CampBlazer on http://{a.host}:{a.port} with {a.workers} worker processes")
    uvicorn.run("config.asgi:application", host=a.host, port=a.port)
