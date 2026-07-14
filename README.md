# Plotline — Itinerary Design Studio

Plotline is a bespoke trip-planning service for travelers who hate generic packages but do not have time to plan every detail themselves. It is positioned like a creative agency for vacations, not a booking engine.

The project includes a polished brand website, an interactive itinerary preview, and a lightweight backend API for trip briefs, itinerary drafts, concierge requests, and service pricing.

## Features

- Editorial landing page for the Plotline brand
- Interactive sample itinerary selector
- Client brief form connected to a backend API
- Automatic first-pass itinerary generation from a submitted brief
- Printable designed itinerary export that can be saved as PDF
- Mock Stripe-style checkout flow for planning fees
- Planner dashboard with briefs, generated itineraries, concierge requests, and pipeline metrics
- SQLite-backed persistence for trip briefs
- Admin-protected endpoints for planner workflows
- Concierge request endpoint for live support use cases
- Static site and API served from one local Python server

## Tech Stack

### Frontend

- HTML
- CSS
- Vanilla JavaScript
- Generated PNG hero image

### Backend

- Python 3.11
- Python standard-library `http.server`
- SQLite with WAL mode
- JSON REST API
- Simple bearer-token admin auth

No React, Node, Express, FastAPI, Django, or external packages are required.

## Project Structure

```text
.
├── README.md
├── .gitignore
└── outputs/
    └── plotline-site/
        ├── index.html
        ├── checkout.html
        ├── styles.css
        ├── script.js
        ├── plotline_api.py
        ├── BACKEND.md
        └── assets/
            └── plotline-hero.png
```

## Run Locally

```bash
cd outputs/plotline-site
PYTHONDONTWRITEBYTECODE=1 python3 plotline_api.py --port 8088
```

Open:

```text
http://127.0.0.1:8088/
```

Health check:

```bash
curl http://127.0.0.1:8088/health
```

## API Examples

Create a trip brief:

```bash
curl -X POST http://127.0.0.1:8088/api/briefs \
  -H 'Content-Type: application/json' \
  -d '{
    "mood": "literary Lisbon",
    "travel_window": "December, 6 nights",
    "tier": "essentials",
    "traveler_email": "traveler@example.com"
  }'
```

Create a brief and receive a generated itinerary plus mock checkout:

```bash
curl -X POST http://127.0.0.1:8088/api/briefs \
  -H 'Content-Type: application/json' \
  -d '{
    "mood": "market-led Seoul",
    "travel_window": "November, 5 nights",
    "tier": "full_plot",
    "traveler_email": "traveler@example.com"
  }'
```

List briefs as admin:

```bash
curl http://127.0.0.1:8088/api/briefs \
  -H 'Authorization: Bearer dev-admin-token'
```

Load planner dashboard:

```bash
curl http://127.0.0.1:8088/api/admin/dashboard \
  -H 'Authorization: Bearer dev-admin-token'
```

Open a generated itinerary export:

```text
http://127.0.0.1:8088/api/itineraries/YOUR_ITINERARY_ID/export
```

## Backend Notes

The backend creates its SQLite database automatically on first run. Local database files are intentionally ignored by Git.

Default admin token:

```text
dev-admin-token
```

Override it:

```bash
PLOTLINE_ADMIN_TOKEN=your-secret-token python3 plotline_api.py --port 8088
```

## Scalability Path

This is a local, dependency-light implementation designed to run reliably on the current machine. To productionize it:

- Move SQLite to Postgres
- Replace the standard-library server with FastAPI or Django
- Add role-based auth for planners and admins
- Replace mock checkout with Stripe for planning fees and subscriptions
- Add object storage for designed itinerary PDFs
- Add a worker queue for PDF generation and email delivery
- Add affiliate booking attribution tables
- Add planner audit logs and itinerary versioning
