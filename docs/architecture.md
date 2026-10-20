# Architecture & Algorithms

This document explains how the weather-aware routing pipeline works, the conventions it follows, and why. It reflects the implementation in `backend/services/` and `frontend/src/`.

---

## 1. Request lifecycle

```
POST /api/routes/analyze/
  │
  ├─ 1. Validate request (DRF serializer) ......... api/serializers.py
  ├─ 2. Geocode origin + destination .............. services/geocoding/nominatim.py
  ├─ 3. Fetch up to 3 distinct routes ............. services/routing/service.py
  ├─ 4. Build checkpoints + ETAs .................. services/analysis/checkpoints.py
  ├─ 5. Plan forecast window ...................... services/analysis/pipeline.py
  ├─ 6. Batch-fetch forecast at all checkpoints ... services/weather/open_meteo.py
  ├─ 7. Select/interpolate forecast at each ETA ... services/weather/selection.py
  ├─ 8. Apply risk rules per checkpoint ........... services/risk/engine.py
  ├─ 9. Aggregate distance-weighted exposure ...... services/recommendation/exposure.py
  ├─ 10. Rank + explain recommendation ............ services/recommendation/ranker.py
  ├─ 11. Cache route geometry for heatmap ......... Django cache (analysis:<id>)
  └─ 12. Return envelope {data, warnings, meta}
```

The response is fully computed server-side; the frontend renders it and fetches the corridor heatmap separately from cached geometry.

---

## 2. Routing strategy

### Providers

| Priority | Provider | Profile | Alternatives | Credentials |
|---|---|---|---|---|
| 1 | OpenRouteService | `driving-hgv` (truck-aware) | `alternative_routes: {target_count: 3, share_factor: 0.6, weight_factor: 1.6}` | `ORS_API_KEY` |
| 2 | OpenRouteService | `driving-hgv` | single route (used when alternatives are rejected/unavailable for a corridor) | `ORS_API_KEY` |
| 3 | GraphHopper | `car` | `alternative_route.max_paths: 3` | `GRAPHHOPPER_API_KEY` |
| 4 | OSRM public server | `driving` (car) | `alternatives=3` | none |

### Fallback chain

`services/routing/service.py` tries providers in order and appends a **data-quality warning** for each failure, so the UI can explain degradations. Key behaviors:

- ORS alternatives are not guaranteed for long corridors; a rejection falls back to a single ORS route, then to other providers.
- OSRM is always available as a keyless last resort, but its demo server is rate-limited and car-profile only.
- If no provider can route, the API returns `422 no_route_found` with a clear message.
- The chosen provider/profile is shown per route (`provider`, `profile`, `timing_source`).

### Genuine alternatives (deduplication)

Every candidate geometry is resampled to 64 points equally spaced **by distance fraction**. Two routes are considered duplicates when the mean point-to-point distance is below **400 m**. Duplicates are dropped; the remaining routes are capped at 3. If fewer than 3 remain, the API adds:

> "Routing providers returned only N genuinely distinct route(s) of 3 requested for this corridor; no duplicates were fabricated."

This prevents the common anti-pattern of duplicating one route under multiple labels.

### Truck-legality disclaimer

The `driving-hgv` profile accounts for OSM truck restrictions, but OpenStreetMap data can be incomplete. The UI and documentation state that bridge clearance, axle limits, and posted road-weight restrictions must still be verified. Without an ORS key, routes are explicitly labeled as car-profile/OSRM fallback.

---

## 3. Geocoding

- Nominatim `/search?format=jsonv2&limit=1`.
- **Throttled** to ≥1.05 s between outbound calls (policy: max 1 req/s), with a process-level lock.
- Results cached by SHA-1 of the normalized query for 24 h.
- Empty results raise `422 geocode_not_found` with the offending field.
- Autocomplete uses the same adapter with `limit=5`, a 350 ms client debounce, and server-side caching.

---

## 4. Checkpoint sampling

For each route we have:

- `coordinates[]` — (lon, lat) vertices,
- `cumdist_m[]` — cumulative great-circle distance at every vertex,
- `cumdur_s[]` — cumulative provider timing at every vertex.

Checkpoints are placed at:

```
0, I, 2I, 3I, …, and the route's exact final distance
```

where `I` is the interval (10/25/50 miles). The destination is always included; an intermediate checkpoint within 1 m of the destination is omitted to avoid duplication.

Coordinates are linearly interpolated **along the geometry**, and the ETA is interpolated along the timing array (see §5). Checkpoint `mile` values are exact cumulative-distance fractions, not index × interval.

Example for a 100-mile route at 25 miles: `[0, 25, 50, 75, 100]`; at 60 miles: `[0, 60, 100]`.

---

## 5. ETA calculation

Provider timing is used wherever it exists:

**ORS (GeoJSON response).** Each feature has `properties.segments[].steps[]`, where each step carries `distance`, `duration`, and `way_points` indices into the geometry. The adapter converts these into a per-vertex cumulative duration array:

```
for each step (a, b, duration D):
    total_distance = cumdist[b] - cumdist[a]
    for vertex v in (a, b]:
        cumdur[v] = t_prev + D * (cumdist[v] - cumdist[a]) / total_distance
    t_prev += D
```

Within a step, duration accrues proportionally to distance (much finer than step granularity); across the route, real per-step timing is preserved. Degenerate zero-distance steps (arrival instructions) are handled explicitly.

**OSRM.** Requested with `overview=full&annotations=duration,distance`. Each leg's annotation arrays provide per-segment durations; cumulative time is the running sum. Geometry and annotations are aligned because full overview geometry is requested.

**Last-resort fallback.** GraphHopper (and any provider without per-vertex timing) uses constant-speed accumulation from the total duration. The response marks this with `timing_source: "constant_speed_fallback"` so the UI can disclose it.

Checkpoint ETA:

```
eta(checkpoint at distance d) = departure_utc + interpolate(cumdur_s, d)
```

The endpoint arrival time uses the provider's total duration.

---

## 6. Weather integration

### Provider and batching

Open-Meteo `/v1/forecast` with **multi-location** coordinates:

```
latitude=41.88,42.33,…&longitude=-87.63,-83.05,…
hourly=temperature_2m,precipitation,rain,snowfall,wind_speed_10m,wind_gusts_10m,weather_code
wind_speed_unit=mph&precipitation_unit=inch&timezone=GMT&forecast_days=N
```

- One HTTP call covers every checkpoint on every route (Open-Meteo returns a JSON list in request order; the adapter validates the count).
- The forecast window is planned from `departure + max route duration + 6 h`, clamped to 2–16 days. Trips beyond 16 days skip the fetch and mark every checkpoint UNKNOWN with a warning.
- Response arrays are normalized into `HourlyForecast` (times as UTC, wind mph, rain in/hr, snow in/hr, °C internally).

### Units and semantics

| Quantity | Provider units used | Handling |
|---|---|---|
| Wind | mph (`wind_speed_unit=mph`) | used directly |
| Rain | inch (`precipitation_unit=inch`) | hourly value = **preceding-hour sum**, treated as average intensity in **in/hr** |
| Snow | **cm** by default, even with inch precipitation | read `hourly_units.snowfall`; convert cm → inches by ÷2.54; recorded in `warnings` |
| Temperature | °C | converted to °F for display |
| Condition | WMO code | mapped to text (e.g., 75 → "Heavy snowfall") |

**Rain vs snow separation.** The adapter requests `rain` and `snowfall` separately. The generic `precipitation` (rain + showers + snow water equivalent) is fetched only for cross-checking and is **never** used as rainfall. This avoids treating mixed precipitation as rain.

**Hourly sum → intensity.** Open-Meteo documents precipitation as the sum over the preceding hour; the assessment asks for an intensity in in/hr. The hourly sum over a one-hour window is exactly an average hourly rate, so it is used directly. This conversion is stated in code comments and here.

### Forecast selection at ETA

Given an hourly series and a checkpoint ETA:

- If ETA < first hour → `available=false`, reason "before the forecast window start".
- If ETA > last hour → `available=false`, reason "beyond the forecast horizon".
- Otherwise find bracketing hours `t0 ≤ ETA < t1` and linearly interpolate wind, gusts, rain, snow, and temperature by `f = (ETA − t0)/(t1 − t0)`.
- The weather condition and code come from the nearest hour.
- `None` values remain `None` (a provider gap is not filled by invention).

### Failure handling

- Weather provider errors degrade gracefully: the analyze response still returns routes, all checkpoint risks are `UNKNOWN`, and a warning explains why.
- The weather fetch retries once on server errors.
- Weather responses are cached for 30 minutes keyed by rounded coordinates + window.

---

## 7. Risk engine

`services/risk/engine.py` is the single source of truth. Severity scores: **LOW 0, MODERATE 1, HIGH 2, SEVERE 3, NO_TRAVEL 4**.

### Boundary convention

The PDF's bands share endpoints. Every band is **lower-inclusive**, so a value exactly on a shared boundary maps to the **more severe** band:

| Class | LOW | MODERATE | HIGH | SEVERE | NO_TRAVEL |
|---|---|---|---|---|---|
| Wind (mph) | `< 25` | `[25, 35)` | `[35, 45)` | `[45, 55)` | `≥ 55` |
| Rain (in/hr) | `< 0.10` | `[0.10, 0.25)` | `[0.25, 0.50)` | `[0.50, 1.00]` | `> 1.00` |
| Snow (in/hr) | `< 0.50` | `[0.50, 1.00)` | `[1.00, 2.00)` | `[2.00, 3.00]` | `> 3.00` |

Rain 1.00 and snow 3.00 stay SEVERE because the assessment explicitly says **>**1.00 / **>**3.00 for No-Travel. All endpoints are covered by parametrized tests.

### Load-dependent wind overrides

Applied after the base classification, taking the maximum:

1. `wind ≥ 55 mph` → **NO_TRAVEL** for every load.
2. `45 ≤ wind < 55 mph` and `load > 30,000 lb` → **NO_TRAVEL**.
3. `35 ≤ wind < 45 mph` and `load > 40,000 lb` → **at least SEVERE**.

`load > 30,000` is strict: exactly 30,000 lb does not trigger. The same applies to 40,000 lb. Both boundaries are tested.

### Combination and UNKNOWN

- Final severity = max(wind, rain, snow, load override).
- No-Travel is never downgraded to Severe and is not averaged away.
- If wind/rain/snow are all missing, the checkpoint is `available=false` (UNKNOWN). Partial data is assessed but marked `complete=false`.
- UNKNOWN is never treated as LOW.

---

## 8. Distance-weighted exposure

For each route, checkpoints define intervals:

```
[0, 25] [25, 50] … [last, destination]
```

Each interval's miles are attributed to the **higher severity of its two endpoints** (conservative). This is interval-based, not a count of checkpoints.

```
for each consecutive pair (miles_i, sev_i) → (miles_{i+1}, sev_{i+1}):
    segment_miles = miles_{i+1} - miles_i
    if either endpoint is UNKNOWN:
        unassessed_miles += segment_miles
    else:
        bucket[max(sev_i, sev_{i+1})] += segment_miles
```

Properties (unit-tested):

- `low + moderate + high + severe + no_travel + unassessed = total_miles`
- Changing 10 → 25 → 50 miles changes granularity but **never** multiplies or discards route miles.
- `average_risk = Σ(miles × score) / assessed_miles`; `None` when nothing was assessed.
- `max_risk` is the worst assessed level.

---

## 9. Recommendation ranking

1. **Safety exclusion:** routes with any No-Travel miles are ineligible.
2. Eligible routes are sorted by:
   1. fewest Severe miles,
   2. fewest High miles,
   3. lowest distance-weighted average risk,
   4. shortest travel time.
3. The reason string is generated from the winning comparison, e.g.:
   - "Recommended because this route avoids severe weather."
   - "…it also has fewer High-risk miles (12.0 vs 38.0)."
   - "…its distance-weighted average risk is lower (0.84 vs 1.12)."
   - "…routes are otherwise equivalent; this one is faster (318 vs 344 min)."
4. If a route has unassessed miles, a caveat is appended ("Weather could not be assessed for X% of this route…"), and >50% unassessed triggers a cautionary note. The strict rule order is preserved; incompleteness is surfaced rather than hidden.
5. If **every** route is ineligible, no route is recommended. The response explains that no safe route is available and returns a clearly marked least-exposure route (fewest No-Travel → Severe → High → average risk → duration) for comparison.
6. If there are no routes at all, the recommendation explains that nothing was available.

---

## 10. Weather heatmap (0–48 h corridor)

### Lattice generation

`services/geo/corridor.py` samples the route corridor:

- Along-route anchors every **20 miles**, always including origin and destination.
- Each anchor is fanned perpendicular to the local bearing at offsets **0, ±15, ±30 miles**.
- Capped at **120 points** so the corridor remains one batched weather call.

The result is a lattice of ~55–120 locations with `mile` and `offset_miles` metadata.

### Time semantics

- `hours` starts at **the current GMT hour** (the forecast arrays start at 00:00 GMT today; the service slices from the current hour) and spans **49 entries** (0…48 h).
- Each slider hour maps to **its own forecast timestamp**. No timestamp is reused across slider positions.
- Severity per point per hour is computed with the same risk engine, including the trip's load weight.
- The response is cached for 30 minutes per analysis + route.

### Spatial interpolation

MapLibre's `heatmap` layer renders kernel-density interpolation over the lattice. Weight mapping: LOW 0.12, MODERATE 0.38, HIGH 0.62, SEVERE 0.85, NO_TRAVEL 1.0; UNKNOWN is omitted. The panel states that intensity is an estimate between sample locations, not point observations.

### Separation from checkpoint weather

Checkpoint risk uses forecast data at the checkpoint's **ETA** (possibly many hours after departure), while the heatmap is a **time-slice situational view** of the corridor for the next 48 hours. The UI labels both explicitly; the API returns them from different endpoints and never mixes the data.

### Client synchronization

- Corridor data is fetched once per selected route (TanStack Query, 30 min stale time).
- Hour changes update a memoized GeoJSON FeatureCollection; the MapLibre source is updated with `setData` (no layer re-creation).
- The severity summary chips and the map consume the same selected hour, and the slider label shows the actual local timestamp plus the viewer's timezone.

---

## 11. API contract

- Envelope: `{data, warnings, meta}` on success; `{error: {code, detail, fields}}` on failure.
- Validation errors: `400 invalid_request` with per-field messages.
- Unresolvable locations: `422 geocode_not_found`.
- Routing impossible: `422 no_route_found`.
- Provider outages: `502` codes (`geocoding_failed`, `weather_provider_failed`, `routing_failed`); weather outages degrade to UNKNOWN instead of failing the whole request.
- Expired analysis: `404 analysis_not_found`.
- DRF serializers validate all inputs; service errors are mapped centrally in `api/exceptions.py`.

---

## 12. Caching and rate limits

| Data | Key | TTL | Notes |
|---|---|---|---|
| Geocode | SHA-1 of normalized query | 24 h | Nominatim 1 req/s throttle |
| Autocomplete | SHA-1 of query | 24 h | 350 ms client debounce |
| Routes | rounded coordinates | 1 h | provider fallback result cached |
| Weather | rounded coordinates + window | 30 min | batched multi-location |
| Analysis geometry | analysis UUID | 6 h | enables corridor requests |
| Corridor lattice | analysis + route | 30 min | derived from cached geometry |

Cache backend: LocMem by default; Redis when `REDIS_URL` is set (`django-redis`). Outbound calls use a bounded timeout, one retry for weather 5xx/timeouts, and no aggressive parallel fan-out (Nominatim is serialized; weather is one batch).

---

## 13. Frontend performance

- Route/checkpoint/heatmap GeoJSON is computed in memoized pure functions (`lib/mapData.ts`).
- MapLibre is lazy-loaded as a separate chunk (initial JS ≈ 435 KB / 133 KB gzip; map chunk ≈ 1.07 MB / 292 KB gzip).
- Sources are updated with `setData`; layers are created once. Selection changes only rebuild small FeatureCollections.
- The heatmap slider uses the precomputed severity matrix; changing hours does not refetch or recreate layers.
- Fit bounds runs only on a new analysis (all routes) or route selection (selected route); no re-fit on every render.
- TanStack Query caches analysis-independent provider data (health, suggestions, corridor) and avoids duplicate requests.

---

## 14. Security & operational notes

- No secrets in the repo; all keys come from environment variables.
- CORS is an explicit origin allow-list; credentials are disabled.
- The API is read-only apart from analysis computation; no user data is stored.
- Request validation rejects past departures (>5 min), weights outside 0–80,000 lb, and unsupported intervals.
- Health endpoint exposes provider configuration booleans, not keys.
- Production settings require `DJANGO_SECRET_KEY` and enable HTTPS redirect/HSTS.

---

## 15. Known limitations

- Public providers have no SLA and rate limits; heavy production use needs commercial keys/self-hosted routers.
- OSM truck attributes are incomplete; routing is not a legal compliance guarantee.
- Forecasts are model output; interpolation between hours and corridor samples is an estimate.
- The public OSRM demo may return fewer than 3 alternatives and is not truck-aware.
- Analyses are ephemeral (cache TTL), so corridor requests require a recent analyze call.
