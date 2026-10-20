# Requirements Checklist

Requirement-by-requirement mapping against the Spotter Full Stack Developer Assessment. "Verified" means demonstrated locally during development (tests and/or live run); deployment and recording are manual submission steps that have **not** been performed.

Legend: ✅ implemented & verified · 🟦 implemented, manual step pending · ⚠️ limitation documented

---

## 1. Primary objective

| Requirement | Status | Where / how verified |
|---|---|---|
| React + Django weather-aware truck routing app | ✅ | `frontend/`, `backend/`; live run Chicago→Detroit returned 2 real OSRM routes with Open-Meteo forecasts |
| Routing/weather/risk/recommendation (40%) | ✅ | Pipeline in `services/analysis/pipeline.py`; 130 backend tests |
| UI/map/heatmap/performance (40%) | ✅ | MapLibre map, corridor heatmap, lazy map chunk; 31 UI tests; live browser run |
| Clean architecture (15%) | ✅ | Typed adapters, pure risk engine, centralized recommendation, no provider logic in views |
| Docs & walkthrough readiness (5%) | ✅ | `README.md`, `docs/architecture.md`, `docs/walkthrough.md`, this checklist |

---

## 2. Technology stack

| Requirement | Status | Where |
|---|---|---|
| React + TypeScript + Vite | ✅ | React 19.3, TS 5.9, Vite 8 |
| Tailwind CSS | ✅ | Tailwind 4 via `@tailwindcss/vite` |
| Interactive mapping library | ✅ | MapLibre GL JS 6 + OpenFreeMap tiles |
| TanStack Query | ✅ | Queries for health/suggest/corridor; mutation for analyze |
| React Hook Form + Zod | ✅ | `features/trip-planner` |
| Lucide icons | ✅ | Used throughout |
| Python + Django + DRF | ✅ | Django 6.1, DRF 3.18 |
| django-cors-headers | ✅ | `config/settings/base.py` |
| HTTPX for third-party APIs | ✅ | `services/http.py` + all adapters |
| pytest / pytest-django | ✅ | 130 passing tests + respx fixtures |
| Real routing/weather APIs | ✅ | ORS/OSRM, Nominatim, Open-Meteo verified live |
| Environment variables for keys | ✅ | `.env.example`, settings from env |
| No unnecessary paid infrastructure | ✅ | All providers have free tiers; app runs keyless |

---

## 3. User inputs

| Requirement | Status | Where |
|---|---|---|
| Origin with suggestions | ✅ | Debounced Nominatim autocomplete (`LocationField`) |
| Destination | ✅ | Same component |
| Departure date & time + timezone handling | ✅ | `datetime-local` → ISO instant; UTC pipeline; local display + timezone label |
| Load weight in pounds | ✅ | Number input 0–80,000 with presets and validation |
| Checkpoint interval 10/25/50 | ✅ | Segmented control |
| Input validation with useful messages | ✅ | Zod schema + server field errors surfaced inline |
| Loading / success / empty / error states | ✅ | Spinner/overlay, results, empty hero, structured error banner |

---

## 4. Routing engine

| Requirement | Status | Where / how |
|---|---|---|
| Geocode origin & destination | ✅ | Nominatim adapter, cached, 1 req/s throttle |
| Up to 3 distinct alternatives | ✅ | ORS `alternative_routes`; OSRM `alternatives=3`; dedup + honest warning when fewer |
| Decode route geometry | ✅ | GeoJSON consumers + encoded-polyline decoder (tested) |
| Total distance & duration | ✅ | Provider summary; shown per route |
| Departure & arrival timestamps | ✅ | Departure + provider duration; per-checkpoint ETAs |
| Precise cumulative-distance checkpoints | ✅ | `build_checkpoints`; origin + destination always included |
| Interpolated coordinates | ✅ | Linear interpolation between geometry vertices |
| ETA from provider segment timing | ✅ | ORS step `way_points`/durations; OSRM annotations; constant-speed only as marked fallback |
| Forecast at projected arrival time | ✅ | `selection.sample_at` per checkpoint ETA |
| Try documented alternatives/fallback when <3 routes | ✅ | ORS single → GraphHopper → OSRM; warnings recorded |
| Never silently duplicate routes | ✅ | 400 m mean-distance dedup + explicit warning |
| Truck-legality documented | ✅ | UI warning, README, architecture doc; `driving-hgv` when ORS configured |

---

## 5. Weather integration

| Requirement | Status | Where / how |
|---|---|---|
| Forecast timestamp per checkpoint | ✅ | `forecast_time` + ETA in response |
| Wind speed mph | ✅ | `wind_speed_unit=mph` |
| Rainfall intensity in/hr | ✅ | `rain` variable, inches; hourly sum documented as in/hr |
| Snowfall intensity in/hr | ✅ | `snowfall`, defensive cm→in conversion via `hourly_units` |
| Temperature | ✅ | °C→°F for display |
| Weather condition | ✅ | WMO code mapping |
| Forecast source | ✅ | `source: "open-meteo"` |
| Select/interpolate by ETA | ✅ | Linear interpolation between bracketing hours |
| Document hourly totals → intensity | ✅ | architecture.md §6 + code comments |
| Don't treat mixed precipitation as rain | ✅ | `rain` vs `snowfall` kept separate; `precipitation` never used as rain |
| Concurrency limits, caching, batching | ✅ | One batched multi-location call; TTL caches; serialized Nominatim |
| No invented weather data | ✅ | Missing values stay missing; UNKNOWN propagation |
| Out-of-range forecast → unavailable | ✅ | Explicit reasons before/after window; tests |

---

## 6. Exact risk rules

| Requirement | Status | Verification |
|---|---|---|
| Wind bands (LOW/MOD/HIGH/SEV/NO_TRAVEL) | ✅ | `test_risk.py::test_wind_boundaries` (13 cases) |
| Rain bands | ✅ | `test_rain_boundaries` (11 cases) |
| Snow bands | ✅ | `test_snow_boundaries` (10 cases) |
| Load: ≥55 mph → No-Travel any load | ✅ | `test_rule_1_wind_55_any_load` |
| Load: 45–54 mph + >30,000 lb → No-Travel | ✅ | `test_rule_2…` (incl. exact 30,000 boundary) |
| Load: 35–44 mph + >40,000 lb → ≥ Severe | ✅ | `test_rule_3…` (incl. exact 40,000 boundary) |
| Highest severity across dimensions | ✅ | `test_highest_severity_wins` |
| Scores 0–4 | ✅ | `test_scores_match_assessment` |
| No-Travel ≠ Severe | ✅ | `test_no_travel_is_distinct_from_severe` |
| Shared endpoints documented & tested | ✅ | Boundary convention in `engine.py` docstring, architecture §7, parametrized tests |

---

## 7. Route risk & recommendation

| Requirement | Status | Verification |
|---|---|---|
| Distance, duration, arrival, checkpoint count | ✅ | Per-route payload + UI cards |
| Miles per risk level | ✅ | `exposure.to_dict()` |
| Distance-weighted average risk | ✅ | `compute_exposure` + tests |
| Maximum risk | ✅ | `max_risk` |
| Interval-based aggregation | ✅ | Segment attribution in `exposure.py` |
| Interval changes don't distort totals | ✅ | `test_total_miles_conserved_across_intervals` |
| Ranking order (4 tiers) | ✅ | `test_rule_1..4` |
| No-Travel excluded before ranking | ✅ | `test_no_travel_route_excluded_even_if_best` |
| All routes No-Travel → no safe route + least exposure | ✅ | `test_all_no_travel_no_safe_route` |
| Human-readable explanation | ✅ | Ranker reason templates + UI banner |
| UNKNOWN ≠ LOW | ✅ | `test_unknown_endpoints_become_unassessed_not_low`, weather unavailability tests |
| Incomplete route not confidently safe | ✅ | Caveat appended; >50% unassessed caution; `test_heavily_unassessed_route_still_ranked_but_flagged` |

---

## 8. Interactive map

| Requirement | Status | Where |
|---|---|---|
| All alternatives displayed | ✅ | Risk-colored segment source |
| Recommended highlighted | ✅ | Badge + wider casing/line; recommendation banner |
| Select any route | ✅ | Cards update selection; map fitBounds to selection |
| Checkpoints rendered | ✅ | Circle layer for selected route |
| Segments colored by risk | ✅ | `match` expression on segment level |
| Checkpoint weather + ETA on click | ✅ | Popup with ETA, condition, wind/rain/snow/temp, risk, source |
| Auto fit bounds | ✅ | All routes on new analysis; selected route on selection |
| Legend | ✅ | Bottom-left overlay, all six colors |
| Differentiated colors | ✅ | Green / yellow / orange / red / dark red / gray |
| Route statistics & reasons | ✅ | Cards + details panel + recommendation banner |
| Responsive layout | ✅ | Sidebar + map on desktop; stacked on mobile |

---

## 9. Heatmap & slider

| Requirement | Status | Verification |
|---|---|---|
| 0–48 h forecast slider | ✅ | Range 0–48, 49 slices |
| Forecast time labels | ✅ | Timestamp + local timezone, "Now" at 0 |
| Corridor-based samples | ✅ | Along route + lateral offsets, ≤120 points |
| Heatmap/spatial intensity | ✅ | MapLibre heatmap layer |
| Selected time updates visualization | ✅ | Source data rebuilt per hour |
| Severity legend | ✅ | Panel chips + map legend gradient |
| Synchronized without needless rerenders | ✅ | Memoized FeatureCollections; `setData` only |
| Distinguish time-slice vs checkpoint ETA weather | ✅ | Separate payloads, labels, notes |
| No timestamp reuse across slider positions | ✅ | Hour-sliced matrix; test `test_slider_hours_use_their_own_timestamps…` |
| No fictional values | ✅ | All values from Open-Meteo; UNKNOWN preserved |
| Spatial interpolation explained | ✅ | Panel note + docs |
| Debouncing/memoization/request caching | ✅ | Debounced autocomplete/slider value; memoized data; server + client caches |

---

## 10. Backend API

| Requirement | Status | Where |
|---|---|---|
| `POST /api/routes/analyze/` with documented request | ✅ | `api/views.py`, README |
| Normalized locations | ✅ | `request.origin/destination.resolved` |
| Alternatives + GeoJSON geometry | ✅ | `routes[].segments[].coordinates` |
| Route metrics | ✅ | distance/duration/arrival/checkpoints |
| Checkpoint coordinates + ETAs + weather + risk | ✅ | `checkpoints[]` |
| Segment risk | ✅ | `segments[]` with mile ranges + levels |
| Recommendation | ✅ | `recommendation` object |
| Data-quality warnings | ✅ | `warnings[]` global + per route |
| Corridor weather API | ✅ | `GET /api/weather/corridor/` |
| Health check | ✅ | `GET /api/health/` |
| DRF serializers | ✅ | `AnalyzeTripSerializer` |
| Consistent response/error envelope | ✅ | `api/responses.py`, `api/exceptions.py` |
| External comms in services/adapters | ✅ | `services/http.py` + adapters |

---

## 11. Project structure

| Requirement | Status |
|---|---|
| Monorepo `frontend/`, `backend/`, `docs/`, `README.md`, `.env.example`, `docker-compose.yml` | ✅ |
| Backend layers: api / services/{routing,weather,risk,recommendation} / tests | ✅ (plus geo, geocoding, analysis) |
| Frontend organization: components / features / hooks / services / types / utils | ✅ (`lib/` acts as services/utils; feature folders mirror requirements) |

---

## 12. Tests & validation

| # | Required test | Status | Evidence |
|---|---|---|---|
| 1 | Every weather risk boundary | ✅ | `test_risk.py` parametrized (34 boundary cases) |
| 2 | All three load wind rules | ✅ | `test_rule_1/2/3` |
| 3 | Conditions with different severities | ✅ | `test_highest_severity_wins` |
| 4 | Checkpoint geospatial interpolation | ✅ | `test_checkpoints.py` + `test_geometry.py` |
| 5 | Checkpoint distance calculation | ✅ | Interval tests incl. destination handling |
| 6 | ETA calculations | ✅ | Warped-timing test proves provider timing used |
| 7 | Weather unit conversion | ✅ | cm→in, °C→°F, hourly sum→intensity |
| 8 | Forecast timestamp matching | ✅ | Exact hour, interpolation, nearest condition |
| 9 | Missing/expired forecasts | ✅ | Before/after window; empty series; provider gap |
| 10 | No-Travel exclusion | ✅ | Ranker tests |
| 11 | Recommendation priority | ✅ | Four ordering tests + tie breaks |
| 12 | Distance-weighted risk | ✅ | Conservation + weighted average tests |
| 13 | Routing API failures | ✅ | ORS 500 → OSRM fallback; all fail → 422 |
| 14 | Weather API failures | ✅ | Degrade to UNKNOWN + warning (API test) |
| 15 | Less than three routes | ✅ | Warning + no fabrication assertions |
| 16 | Route & heatmap UI behavior | ✅ | RouteList, RecommendationBanner, HeatmapPanel, TripPlanner tests |
| Fixtures | Realistic offline fixtures | ✅ | `tests/fixtures/*.json` + generator |
| Fixtures never in production UI | ✅ | Tests only; UI labels live source |
| Backend tests run | ✅ | **130 passed** |
| Frontend tests run | ✅ | **31 passed** |
| Lint / TS / production build | ✅ | ESLint 0 errors, `tsc --noEmit` clean, `vite build` succeeds |

---

## 13. Documentation

| Requirement | Status | File |
|---|---|---|
| README overview, architecture, stack, setup, keys, dev, Docker, deploy, testing, limitations | ✅ | `README.md` |
| architecture.md: routing, checkpoints, ETA, weather, risk, ranking, heatmap, caching | ✅ | `docs/architecture.md` |
| walkthrough.md: 5–10 min Loom script, demo trip, risk scenarios | ✅ | `docs/walkthrough.md` |

---

## 14. Deployment preparation

| Requirement | Status | Notes |
|---|---|---|
| Deployment-ready configuration | ✅ | `backend/Dockerfile`, `frontend/Dockerfile` + nginx, `docker-compose.yml`, `render.yaml`, `vercel.json` |
| CORS configuration | ✅ | `CORS_ALLOWED_ORIGINS` env; documented |
| Environment variables | ✅ | `.env.example`, settings |
| Production settings | ✅ | `config.settings.prod` (secret required, HTTPS redirect, HSTS) |
| Health checks | ✅ | `/api/health/` + Docker/Render health checks |
| Static assets | ✅ | WhiteNoise + nginx |
| No secrets committed | ✅ | `.gitignore`, env-only |
| GitHub publishing / live deployment / Loom recording | 🟦 **Not performed** | Manual steps documented; no claims made |

---

## 15. Known limitations (explicitly disclosed)

- ⚠️ Truck routing is only as good as OSM's truck attributes; not a legal compliance guarantee.
- ⚠️ Public providers (OSRM demo, Nominatim, Open-Meteo, OpenFreeMap) are best-effort without SLA.
- ⚠️ ORS may return fewer than 3 alternatives for a corridor; the app warns instead of fabricating.
- ⚠️ Heatmap and intra-hour weather are interpolated estimates, labeled as such.
- ⚠️ No authentication or saved trips (out of scope).
