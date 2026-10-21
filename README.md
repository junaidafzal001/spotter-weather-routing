# Spotter Route Weather — Weather-Aware Truck Routing

A full-stack trip planner that helps truck drivers choose the safest route based on **forecast weather at the time they will actually be driving**, cargo weight, departure time, and route duration.

Given an origin, destination, departure time, load weight, and a 10/25/50-mile checkpoint interval, the backend:

1. geocodes both ends,
2. retrieves up to **three genuinely distinct** route alternatives,
3. places weather checkpoints along each route at exact cumulative-mile intervals,
4. computes each checkpoint's ETA from the router's own segment timings,
5. fetches the forecast **for that ETA** (not "now"),
6. applies the assessment's deterministic wind / rain / snow / load risk rules,
7. aggregates **distance-weighted exposure** per route, and
8. recommends a route using the required priority order — with No-Travel routes excluded from the safe ranking.

---

## Feature highlights

**Trip planning & routing**
- Origin/destination autocomplete (debounced Nominatim, cached server-side)
- Departure date-time (timezone-aware), load weight (0–80,000 lb), checkpoint interval 10/25/50 mi
- Up to 3 distinct alternatives via ORS `driving-hgv` (`alternative_routes`), with GraphHopper and a keyless OSRM fallback
- Near-duplicate geometries are collapsed; the API never fabricates "alternatives"
- Per-step provider timings (ORS steps / OSRM annotations) drive checkpoint ETAs — constant speed only as a documented last resort
- Explicit data-quality warnings when fewer than 3 genuinely distinct routes exist

**Weather**
- Open-Meteo hourly forecasts, batched across all checkpoints in one call
- Rain and snowfall kept separate (never mislabeled mixed precipitation)
- Units normalized (`mph`, `in/hr`, `°F`), snowfall converted defensively from provider units
- Forecast selected/interpolated at each checkpoint ETA; outside the horizon → **UNKNOWN**, never LOW

**Risk & recommendation**
- Exact PDF rules with documented boundary conventions, centralized in one engine
- All three load-dependent wind overrides (including 55 mph No-Travel for every load)
- Highest severity across wind/rain/snow/load wins; No-Travel is a distinct level (4)
- Interval-based, distance-weighted exposure (miles conserved when interval changes)
- Ranking: fewest Severe miles → fewest High miles → lowest average risk → shortest travel time
- Safety exclusion for No-Travel; if every route is unsafe, no route is declared safe and a least-exposure comparison is shown

**Map & heatmap**
- All alternatives drawn, recommended highlighted, selected route emphasized
- Risk-colored segments, checkpoint markers, click popups with ETA weather
- Auto fit bounds, map legend, zoom/scale controls
- 0–48 h corridor heatmap with per-hour forecast slices (each hour uses its own timestamp)
- Spatial interpolation is explicitly labeled as an estimate in the UI
- Lazy-loaded map chunk; memoized GeoJSON; MapLibre source updates without layer churn

**Engineering**
- 130 backend tests (risk boundaries, load rules, interpolation, ETA, units, failures, ranking, API contracts)
- 31 frontend tests (form validation, route cards, recommendation states, heatmap slider behavior)
- Typed provider adapters, structured API envelope, cached/rate-limited outbound calls
- Docker Compose, Render + Vercel deployment configuration, environment templates

---

## Quick start

**Prerequisites:** Python 3.12+ (3.13/3.14 tested), Node 20.19+ (22/23 tested), npm.

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt   # runtime + test tooling
cp ../.env.example .env          # optional: add ORS_API_KEY
python manage.py migrate         # applies Django's built-in migrations (no app models)
python manage.py check
python manage.py runserver 8000
```

The API is now at `http://localhost:8000` (health: `/api/health/`).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` to `http://localhost:8000`, so no CORS setup is needed in development.

> **No API key is strictly required.** Without `ORS_API_KEY` the app uses the keyless OSRM demo server (car profile) and shows a clear warning that routes are not truck-legal. With a free ORS key it uses the truck-aware `driving-hgv` profile and requests 3 alternatives.

### Getting an ORS key (recommended, free)

1. Sign up at <https://openrouteservice.org/dev/#/signup>.
2. Create a token, then set `ORS_API_KEY=...` in `backend/.env`.
3. Restart the backend. `/api/health/` will report `openrouteservice: true` and the UI badge changes to **Truck routing (ORS hgv)**.

---

## Key design decisions

**Boundary convention.** The PDF's bands share endpoints. Every band is treated as lower-inclusive, so a value exactly on a boundary maps to the more severe band (wind 25 → Moderate, 35 → High, 45 → Severe, 55 → No-Travel; rain 0.10 → Moderate, 0.25 → High, 0.50 → Severe; snow 0.50 → Moderate, 1.00 → High, 2.00 → Severe). Rain 1.00 and snow 3.00 remain Severe because the PDF says **>**1.00 / **>**3.00 for No-Travel. Every endpoint is tested.

**Exposure is interval-based, not checkpoint-count-based.** The miles between consecutive checkpoints are attributed to the higher endpoint severity. Per-level miles plus unassessed miles always sum to the route distance, regardless of 10/25/50-mile sampling.

**UNKNOWN is never LOW.** Missing/out-of-horizon forecasts produce `available: false` and unassessed miles; they are excluded from risk averages and flagged, so an incompletely assessed route is never presented as confidently safe.

**No-Travel is a safety exclusion.** Routes with No-Travel exposure cannot be recommended. If all routes are unsafe, the response returns no recommendation, explains the conflict, and provides a clearly marked least-exposure comparison instead.

**Alternatives must be genuine.** Providers may return fewer than three distinct routes (documented ORS/OSRM behavior, especially on long corridors). The API deduplicates by geometry similarity and warns instead of duplicating a route.

**Heatmap time semantics.** The slider is anchored at "now" (0–48 h lead time). Each position uses the forecast for its own timestamp — never one fixed timestamp reused. This is deliberately separate from checkpoint ETA weather, which drives route risk.

---

## Assumptions & limitations

- **Truck legality:** routes are truck-aware only when configured with ORS `driving-hgv` (or a comparable truck profile). Bridge clearance, axle limits, and posted road-weight restrictions must still be verified by dispatch. Without an ORS key the app uses OSRM's car profile and says so.
- **Routing alternatives:** ORS does not guarantee 3 alternatives for every corridor; OSRM's demo server is best-effort and rate-limited. The UI shows only genuinely distinct routes and warns when fewer are available.
- **Public services:** Nominatim (1 req/s), Open-Meteo, OSRM demo, and OpenFreeMap are free public services without SLA. Caching, batching, and a single throttled geocoder protect them; production deployments should use commercial endpoints/keys.
- **Forecast horizon:** weather is available up to 16 days; trips beyond that are marked UNKNOWN. The heatmap covers the next 48 hours.
- **Interpolation:** values between forecast hours and between corridor sample points are estimates; the UI labels the heatmap as a spatial interpolation.
- **No authentication or persistence:** the assessment focuses on routing/weather analysis. Analyses are cached briefly; there are no user accounts or saved trips.
- **Fixture data:** static provider fixtures exist only under `backend/tests/` and are never served by the API or shown in the UI.

---

## Data attribution

Weather: [Open-Meteo](https://open-meteo.com/) · Geocoding: [OpenStreetMap Nominatim](https://nominatim.org/) · Routing: [OpenRouteService](https://openrouteservice.org/) / [GraphHopper](https://www.graphhopper.com/) / [OSRM](http://project-osrm.org/) · Tiles: [OpenFreeMap](https://openfreemap.org/) © OpenMapTiles, data © OpenStreetMap contributors.
