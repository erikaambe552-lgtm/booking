# CampBlazer

Camping destination discovery and reservation platform for **Biliran Province, Philippines**.
Capstone for Parallel and Distributed Computing at BiPSU.

- **Beaches → venue booking** (VenueSlot → BeachReservation)
- **Mountains → tour-guide booking** (GuideSchedule → GuideReservation)
- **Stack:** React + TypeScript (Vite) · Django 5 + DRF · **Django Channels + Redis (WebSockets)** · PostgreSQL · ASGI workers (gunicorn+uvicorn / uvicorn on Windows)
- **Catalog:** 18 approved destinations: 12 beaches and 6 mountains (Agta Beach Resort appeared twice in the approved list, so it is stored once). Every one has a photo and booking.

```
campblazer/
├── backend/                 Django project (config, accounts, destinations, bookings)
│   ├── bookings/services.py ← concurrency core: transaction.atomic + select_for_update
│   ├── bookings/tests.py    ← functional, security and threaded concurrency tests
│   ├── bookings/realtime.py ← publishes WebSocket events after COMMIT
│   ├── bookings/consumers.py← WebSocket endpoint ws://…/ws/live/
│   ├── seed_photos/         ← destination photos + photos.json mapping
│   ├── gunicorn.conf.py     ← 4 ASGI worker processes (Linux/macOS/WSL)
│   └── run_server_windows.py← single uvicorn worker (native Windows)
├── frontend/                React + TypeScript UI
├── scripts/                 concurrency_test.py, load_test.py (HTTP, against the running server)
├── db_concurrency_test/     PostgreSQL-only race test (already run, results included)
└── docs/                    technical documentation, screenshots, logo
```

**Deploying (GitHub, laptop public link, Render):** see [DEPLOY.md](DEPLOY.md).

---

## 1. Requirements

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+ (16 recommended)
- **Redis 6+** (WebSocket channel layer for multiple workers). The easiest way to get PostgreSQL and Redis is `docker compose up -d` in the project root. A single worker can use the in-memory channel layer if `REDIS_URL` is empty.

## 2. Database

```sql
-- in psql as the postgres superuser
CREATE USER campblazer WITH PASSWORD 'campblazer_dev_pw';
CREATE DATABASE campblazer OWNER campblazer;
ALTER USER campblazer CREATEDB;   -- lets `manage.py test` create a test database
```

`btree_gist` is enabled by the first migration. It's a trusted extension, so the database owner can create it.

## 3. Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate     macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # then edit DJANGO_SECRET_KEY and DB password
python manage.py migrate
python manage.py seed_destinations   # syncs to the 18 approved destinations and DELETES any others (photos, services, bookings)
python manage.py seed_photos --reset # REPLACES all photos with backend/seed_photos/photos.json (1 per destination + Agta Commons photo)
python manage.py seed_demo           # test accounts + one [DEMO] venue/guide with 14 days of slots for EVERY approved destination
python manage.py createsuperuser     # optional — your own admin
```

Database migrations are committed in each app. Run `makemigrations` only when you change models and intend to create a new migration.

**Run with several workers.** This runs parallel request handling and WebSockets together. Make sure Redis is running and `REDIS_URL` is set in `.env`. Use WSL for multiple workers on Windows; the native Windows launcher is single-process.

```bash
# Linux / macOS / WSL — 4 ASGI worker processes
gunicorn -c gunicorn.conf.py config.asgi:application
# Native Windows — one ASGI worker
python run_server_windows.py
```

`python manage.py runserver` runs daphne in a single process and is fine for development. If `REDIS_URL` is empty, Channels falls back to an in-memory layer, which only works with one process.

**Real-time updates:** when an operator approves a booking, the server pushes the change to the camper's open browser over WebSocket. The camper doesn't need to refresh, and there is no polling. The **LIVE** dot in the navbar shows the connection status.

## 4. Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (proxies /api to :8000)
```

## 5. Demo accounts (made by `seed_demo`)

Every demo account uses the password `CampDemo#2026`. You can change it with the `DEMO_PASSWORD` env var.

| Username | Role |
|---|---|
| admin_demo | Administrator |
| operator_demo | Beach venue operator (owns the demo venue) |
| guide_demo | Mountain tour guide (owns the demo guide) |
| camper01_demo … camper20_demo | Campers |

`seed_demo` gives all 18 approved destinations one clearly labelled **[DEMO]** venue (beaches) or guide team (mountains), so every **Book Venue / Book Tour Guide** button works during the panel demo. It adds no destinations. The services are simulated (₱500 venue slot / ₱1,500 guide fee are placeholders, shown with a "Simulated" badge). Replace them with real services in the Admin dashboard, then remove the demo with `python manage.py seed_demo --remove`.

**Enabling real bookings for any destination (Admin dashboard):** Services → add the verified venue or guide with real prices → Availability → add dates → Destinations → switch Verified and Bookings on. The Book Venue / Book Tour Guide button then becomes active.

## 6. Tests

```bash
cd backend
python manage.py test -v 2          # functional + security + threaded concurrency tests
```

### Concurrency over real HTTP (server must be running with multiple workers)

Put these in `.env` before starting the server so the test logins aren't throttled:

```
LOGIN_THROTTLE=1000/min
ANON_THROTTLE=100000/min
```

```bash
python scripts/concurrency_test.py --kind beach --users 10                 # default: agta-beach-resort
python scripts/concurrency_test.py --kind mountain --users 20
```

Each run should show exactly one 201, the rest as 409, and several distinct worker PIDs. Results are appended to `scripts/results/concurrency_results.csv`.

To make the lock waiting easier to see during a live demo, set `BOOKING_DEMO_DELAY_MS=300` in `.env`. This adds a fake 300 ms of work while the lock is held. Leave it at 0 when you take performance measurements.

### Performance and speedup

```bash
GUNICORN_WORKERS=1 gunicorn -c gunicorn.conf.py config.asgi:application   # terminal A
python scripts/load_test.py --label workers1                     # terminal B
# stop the server, restart with 4 workers
GUNICORN_WORKERS=4 gunicorn -c gunicorn.conf.py config.asgi:application
python scripts/load_test.py --label workers4
python scripts/load_test.py --report     # -> scripts/results/load_report.md + load_charts.png
```

For Windows multi-worker comparisons, run both tests inside WSL with the Gunicorn commands above.

### PostgreSQL-only race test (no Django needed)

```bash
python db_concurrency_test/run_db_concurrency_test.py --host localhost --user postgres --db postgres
```

## 7. Main API endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | /api/auth/register/ · /login/ · /logout/ | Authentication (token) |
| GET/PATCH | /api/auth/me/ | Profile |
| GET | /api/destinations/?category=&municipality=&q= | Catalog with filters |
| GET | /api/destinations/{slug}/ | Destination details |
| GET | /api/destinations/{slug}/availability/ | Venue slots (beach) or guide schedules (mountain) |
| POST | /api/bookings/beach/ | Create a beach venue reservation |
| POST | /api/bookings/mountain/ | Create a mountain guide reservation |
| GET | /api/bookings/mine/?status= | Booking history |
| POST | /api/bookings/{beach\|mountain}/{id}/cancel/ | Cancel own reservation |
| GET/POST | /api/operator/reservations/ … /status/ | Operator or guide approves/rejects |
| CRUD | /api/operator/venue-slots/ · /guide-schedules/ | Availability management |
| CRUD | /api/admin/users · destinations · images · venues · guides | Admin |
| GET | /api/admin/reservations/ · /api/admin/stats/ | Admin monitoring |
| GET | /api/system/info/ | Returns the worker PID (for the parallelism demo) |
| WS | /ws/live/ | Real-time events: `reservation.status`, `reservation.new`, `availability.changed` |

## 8. Data honesty rules built into the system

- The catalog only accepts Biliran's 8 municipalities, and this is enforced by a database constraint.
- When a municipality hasn't been verified, the field stays blank and the record has `location_verified=False`.
- `seed_destinations` contains no prices, operators, guides or schedules. Those come from the Admin dashboard (real) or `seed_demo` (simulated, labelled [DEMO]).
- The database won't let a destination take bookings until it is verified (`booking_requires_verification`). All 18 approved destinations are seeded as verified with bookings enabled.
- Photos: every approved destination has a photo from `backend/seed_photos/`. The credit comes from the watermark, and all are marked "permission pending" until the owner agrees. See `docs/PHOTO_SOURCES.md`.
- Only the 18 approved destinations appear. Anything else is deleted by `seed_destinations`. A **Book** button is active whenever the destination has a verified venue/guide with open slots.
