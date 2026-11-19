# Deploying CampBlazer for free

| Option | What it gives you | Cost | Best for |
|---|---|---|---|
| A. GitHub | Your code online, version history, shareable repo link | Free | Submitting / sharing the source |
| B. Laptop + Cloudflare Quick Tunnel | A public `https://….trycloudflare.com` link to the app running on YOUR laptop: PostgreSQL and live WebSockets (one native Windows worker; multi-worker via WSL) | Free, no account | The panel demo |
| D. GitHub Codespaces | The whole app (backend + frontend + PostgreSQL + Redis) runs in GitHub's cloud; a public `…app.github.dev` link | Free monthly hours on a personal account | Deploying from GitHub without your laptop running it |
| C. Render + Neon | Always-reachable website, no laptop needed | Free tiers (sleeps when idle; can hit account limits) | Leaving it online after the defense |

---

## A. Put the code on GitHub

1. Create an empty repository on github.com (New → name it `campblazer` → **don't** add a README).
2. In the VS Code terminal, inside the `campblazer` folder:

```bash
git init
git add .
git commit -m "CampBlazer capstone"
git branch -M main
git remote add origin https://github.com/<your-username>/campblazer.git
git push -u origin main
```

`.gitignore` keeps out `.env` (secrets), Python environments, `node_modules`, build output, and uploaded media.
Check with `git status` before committing: **`.env` must never appear**. If it does, stop and run `git rm --cached backend/.env`.

GitHub stores the code only; it doesn't run Django. Use B or C to run it.

---

## B. Laptop as the server + Cloudflare Quick Tunnel (recommended for the demo)

Everything runs on your laptop exactly as in the setup guide; Cloudflare gives it a temporary public HTTPS link.

1. Install `cloudflared`. On Windows: `winget install --id Cloudflare.cloudflared`, then reopen VS Code.
2. In `backend/.env` set:

```
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,.trycloudflare.com
SERVE_MEDIA=1
```

   (DEBUG off so visitors never see error pages with your settings; `SERVE_MEDIA=1` keeps the photos working.)
3. Start PostgreSQL and the backend. On native Windows use one worker; use WSL for a multi-worker demo:

```powershell
docker compose up -d
cd backend
.\venv\Scripts\Activate.ps1   # or .\.venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py collectstatic --noinput
python run_server_windows.py
```

4. Build and serve the frontend (new terminal):

```powershell
cd frontend
npm run build
npm run preview          # http://localhost:4173 — proxies /api, /media and /ws to Django
```

**Shortcut:** after the one-time setup, `powershell -ExecutionPolicy Bypass -File .\start-public.ps1` (in the `campblazer` folder) does steps 3–5 for you in separate windows.

5. Open the tunnel (new terminal):

```powershell
cloudflared tunnel --url http://localhost:4173
```

   It prints a link like `https://random-words.trycloudflare.com`. Anyone can open it on their phone or laptop. Bookings, approvals and live updates all work through it.

Notes:
- The link changes every time you restart `cloudflared`, and it stops when you press Ctrl + C or the laptop sleeps.
- Keep the laptop plugged in and set sleep to "Never" during the demo.
- Quick Tunnels are meant for testing and demos, not permanent hosting.

---

## C. Deploy to Render (frontend + API + Key Value) with Neon PostgreSQL

The Blueprint in `render.yaml` creates a Render API web service, a static frontend, and a Redis-compatible Key Value service. The frontend build runs from the repository root so it can copy photos from `backend/seed_photos`; changes to either frontend files or those photos trigger a rebuild. PostgreSQL is hosted separately on Neon so its free database does not expire with Render's 30-day free Postgres limit.

### 1. Push the project to GitHub

Render deploys from a Git repository. The repository root must contain `render.yaml`, `backend/`, and `frontend/` (push the contents of the `campblazer` folder, not an outer folder containing it). The root `.gitignore` excludes `.env`, Python environments, `node_modules`, and build output. Check `git status` before pushing; never commit `backend/.env`.

### 2. Create the production database

1. Create a Neon project in the Singapore region (or a region near your Render services).
2. Copy the **direct** PostgreSQL connection string, not a pooled connection string. It should start with `postgresql://` and use SSL; the project uses row locks and needs a direct database connection.

### 3. Apply the Render Blueprint

1. In Render, choose **New → Blueprint** and connect the GitHub repository.
2. Confirm that Render finds `render.yaml` at the repository root, then apply it. The API and Key Value services are configured for Singapore; the frontend is served from Render's CDN.
3. When prompted for values marked `sync: false`, enter the following. The default service names usually map to `campblazer-api.onrender.com` and `campblazer.onrender.com`; use the actual hostnames Render assigns. If a hostname differs, update these values in the service's **Environment** page and redeploy:

| Service | Variable | Value |
|---|---|---|
| `campblazer-api` | `DATABASE_URL` | Neon direct connection string |
| `campblazer-api` | `CORS_ALLOWED_ORIGINS` | `https://<frontend-domain>.onrender.com` |
| `campblazer-api` | `CSRF_TRUSTED_ORIGINS` | `https://<api-domain>.onrender.com,https://<frontend-domain>.onrender.com` |
| `campblazer-api` | `PHOTO_BASE_URL` | `https://<frontend-domain>.onrender.com` |
| `campblazer` | `VITE_API_URL` | `https://<api-domain>.onrender.com` |

Render generates `DJANGO_SECRET_KEY` and `DEMO_PASSWORD`; the API's `REDIS_URL` is linked to the Key Value service automatically. If you change any of these values after the initial deploy, redeploy the affected service. In particular, changing `VITE_API_URL` requires a frontend rebuild because Vite embeds it at build time.

The API build collects Django static files and WhiteNoise serves them, including the Django admin CSS. The API start command applies committed migrations before starting Gunicorn. It does **not** create migrations or reset/seed the database on each restart.

### 4. Seed the database and create an admin login once

Render's free web services don't provide Shell access, so run these one-time management commands from your local PowerShell using the Neon URL. From the project root:

```powershell
cd backend
.\venv\Scripts\Activate.ps1   # or .\.venv\Scripts\Activate.ps1
$env:DATABASE_URL = Read-Host "Paste the Neon direct connection string"
$env:PHOTO_BASE_URL = "https://<frontend-domain>.onrender.com"
python manage.py seed_destinations --keep-unapproved
python manage.py seed_photos
```

`--keep-unapproved` avoids deleting any destinations already in the database; `seed_photos` (without `--reset`) adds missing photos without removing existing ones. To include the simulated booking accounts and services, copy `DEMO_PASSWORD` from the API service's **Environment** page into the local PowerShell environment, then run:

```powershell
$env:DEMO_PASSWORD = Read-Host "Paste DEMO_PASSWORD from Render"
python manage.py seed_demo
```

Create your own Django admin superuser against the same Neon database:

```powershell
python manage.py createsuperuser
```

The management commands connect to the hosted database through `DATABASE_URL`; keep the connection string and demo password private. When finished, clear the temporary environment variables:

```powershell
Remove-Item Env:DATABASE_URL, Env:PHOTO_BASE_URL, Env:DEMO_PASSWORD -ErrorAction SilentlyContinue
```

The frontend is at `https://<frontend-domain>.onrender.com`; the Django admin is at `https://<api-domain>.onrender.com/django-admin/`.

### Render free-tier limitations

- Free web services spin down after 15 minutes without traffic and can take about a minute to wake.
- Free services have limited CPU and memory; use your laptop or WSL for the project's worker-speedup/load tests.
- The web service's filesystem is ephemeral. Destination photos are served from the frontend static site; uploaded files should not be treated as persistent.
- Render Key Value is Redis-compatible and used for cross-worker WebSocket events. Free-tier services are intended for demos and testing, not production workloads.

---

## D. Run it on GitHub Codespaces (from your GitHub repo, no laptop needed while it runs)

GitHub Pages can't run Django (static files only), but **Codespaces** gives you a free Linux machine in GitHub's cloud that can run everything.

1. Do **A** first (code on GitHub).
2. On the repo page: **Code → Codespaces → Create codespace on main** (2-core machine). VS Code opens in the browser.
3. In its terminal:

```bash
docker compose up -d                       # PostgreSQL + Redis inside the codespace
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

4. Edit `backend/.env`: paste a secret key, and set
   `DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,.app.github.dev` and `SERVE_MEDIA=1`, `DJANGO_DEBUG=False`.
5. Apply migrations, load demo data, and start 4 workers:

```bash
python manage.py migrate
python manage.py seed_destinations --keep-unapproved && python manage.py seed_photos && python manage.py seed_demo
gunicorn -c gunicorn.conf.py config.asgi:application
```

6. New terminal: `cd frontend && npm install && npm run build && npm run preview`
7. Open the **Ports** tab → port **4173** → right-click → **Port Visibility → Public**. Copy its `https://…-4173.app.github.dev` link and share it.

Notes:
- Free personal accounts get a monthly allowance of Codespaces core-hours. A 2-core codespace uses 2 core-hours per hour, so **stop the codespace when you're done** (Codespaces page → ⋯ → Stop).
- A codespace stops itself after a period of inactivity, and the link stops working then. Restart it and re-run steps 5–7 (the database is kept).
