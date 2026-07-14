# Plotline Backend

The backend lives in `plotline_api.py` and runs with Python 3.11 only. It serves both the existing website and JSON API from the same localhost server.

## Run

```bash
cd /Users/shaluagarwal/Documents/Codex/2026-07-14/itinerary-design-studio-plotline-a-bespoke/outputs/plotline-site
python3 plotline_api.py --port 8088
```

Open the site:

```text
http://127.0.0.1:8088/
```

Check the API:

```bash
curl http://127.0.0.1:8088/health
curl http://127.0.0.1:8088/api/services/pricing
```

## Admin Token

Admin endpoints use:

```text
Authorization: Bearer dev-admin-token
```

Override for real use:

```bash
PLOTLINE_ADMIN_TOKEN=your-secret-token python3 plotline_api.py --port 8088
```

## Main Endpoints

- `POST /api/briefs`: create a client trip brief
- `GET /api/briefs`: list briefs, admin only
- `GET /api/briefs/{id}`: get a brief with itinerary drafts and concierge requests
- `PATCH /api/briefs/{id}/status`: move a brief through `new`, `qualified`, `designing`, `delivered`, `archived`
- `POST /api/itineraries`: create an itinerary draft, admin only
- `GET /api/itineraries/{id}`: fetch an itinerary draft
- `POST /api/concierge/requests`: create a concierge support request
- `GET /api/concierge/requests`: list concierge requests, admin only

## Why This Is More Scalable

The first version was just a static demo. This adds durable backend entities:

- `trip_briefs` for inbound demand and qualification
- `itinerary_drafts` for planner-created trip versions
- `concierge_requests` for live support workflow
- service pricing tiers for fee anchors

SQLite is fine for local demos and early internal usage. The production upgrade path is Postgres, FastAPI or Django, role-based auth, Stripe, PDF generation workers, email notifications, affiliate attribution tables, and object storage for designed itinerary PDFs.
