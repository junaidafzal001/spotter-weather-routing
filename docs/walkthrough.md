# 5–10 Minute Walkthrough Script

A practical Loom plan for demonstrating the assessment. Timings assume one continuous recording; total ≈ 9 minutes.

**Before recording**

1. `cd backend && source .venv/bin/activate && python manage.py runserver 8000`
2. `cd frontend && npm run dev`
3. Open <http://localhost:5173> and confirm the header shows **API online**.
4. Have a second terminal ready for `pytest` and `npm test`.
5. Optional: set `ORS_API_KEY` and restart to show the **Truck routing (ORS hgv)** badge and up to 3 alternatives.

---

## 0:00–0:45 — What this is

> "This is a weather-aware truck routing planner. The key idea: ordinary weather apps show conditions now, but a truck crossing 280 miles will meet different weather at different times. This app samples the forecast at each checkpoint's projected arrival time, scores the risk with the assessment's exact rules, and recommends the safest of up to three distinct routes."

Show the empty dashboard: planner on the left, map area with the empty state, and the header status chips.

---

## 0:45–2:00 — Plan a trip

1. Set **Origin** to `Chicago, IL` — pause to show the debounced autocomplete suggestions.
2. Set **Destination** to `Detroit, MI`.
3. Point out **Departure** (timezone-aware) and **Load weight** with presets (Empty / 20k / 35k / 44k).
4. Toggle the **checkpoint interval** (10 / 25 / 50 mi) and explain: "The interval changes sampling density, not the route miles — exposure totals stay stable."
5. Click **Analyze routes** and narrate the loading state.

---

## 2:00–3:30 — Routes, recommendation, and map

While results render:

> "The backend geocoded both cities, requested alternatives, sampled checkpoints, and fetched one batched forecast for every checkpoint ETA."

Point at:

- **Recommendation banner** — read the reason aloud; note the ranking order (fewest Severe → fewest High → lowest average risk → shortest time).
- **Route cards** — distance, duration, arrival, stacked risk bar, average risk, max risk, checkpoint count.
- **Map** — all alternatives, recommended highlighted, selected route emphasized; risk-colored segments; green dots are checkpoints.
- Click a **checkpoint** to open the popup: ETA, condition, wind/gusts/rain/snow/temperature, risk level, and the forecast hour used (with "interpolated to ETA" when applicable).

---

## 3:30–4:30 — Weight changes the outcome (the load rule)

1. Set **Load weight** to `45000` (or click **44k**).
2. Re-run Analyze.
3. If the corridor has 45–54 mph winds anywhere, that route now shows **No-Travel** miles — the rule *wind 45–54 mph + load > 30,000 lb → No-Travel* — and it drops out of the safe ranking.

> "This is the assessment's load-dependent rule in action: the same weather is safe for an empty truck and No-Travel for a heavy load. If every route is unsafe, the app refuses to recommend one and shows a least-exposure comparison instead."

**If live weather is calm** (common), say so honestly and show the deterministic proof instead:

- Open `backend/tests/test_risk.py` and run `pytest tests/test_risk.py -q` — show the boundary/load-rule tests passing.
- Point out the severity chips on a checkpoint (e.g., Wind LOW / Rain MODERATE / Snow LOW) and explain that the highest wins.

---

## 4:30–5:45 — Corridor heatmap and slider

1. Toggle **Corridor weather** on if hidden.
2. Drag the **0–48 h slider** to +12 h, +24 h, +36 h.
3. Point out:
   - the timestamp label and the viewer's timezone,
   - severity counts per hour (Low/Moderate/High/Severe/No-Travel),
   - the map heatmap updating for that hour.

> "Each slider position uses the forecast for its own timestamp — it is not one timestamp reused. The intensity is a kernel-density interpolation between about 75 corridor samples, and the panel says so. This is a time-slice view of the corridor; the checkpoint risk above uses the forecast at each checkpoint's ETA, which is a different thing."

Toggle the heatmap off and on to show it doesn't disturb route rendering.

---

## 5:45–6:45 — Exposure details and data quality

1. Open the **Route details** panel: **Checkpoints** tab (mile, ETA, conditions, wind/rain/snow/temp, risk).
2. Switch to **Exposure**: stacked bar, average risk, max risk, total miles, unassessed %.
3. Explain interval attribution: "Miles between checkpoints are assigned to the worse endpoint, so totals stay conserved."
4. Switch to **Notes & warnings** and read a data-quality warning:
   - "No ORS key configured → OSRM fallback (car profile, not truck-legal)."
   - "Only 2 genuinely distinct routes — no duplicates were fabricated."

> "The app never invents alternatives and never claims truck legality without a truck-capable provider."

---

## 6:45–7:45 — API demo (optional but recommended)

In a terminal:

```bash
curl -s -X POST http://localhost:8000/api/routes/analyze/ \
  -H 'Content-Type: application/json' \
  -d '{"origin":"Denver, CO","destination":"Kansas City, MO",
       "departure_time":"'$(date -u -v+6H +%Y-%m-%dT%H:%M:%SZ)'",
       "load_weight_lbs":35000,"checkpoint_interval_miles":25}' \
  | python -m json.tool | head -60
```

Point out the envelope (`data`, `warnings`, `meta`), per-checkpoint weather + risk, `segments`, `exposure`, and `recommendation`.

Also show `GET /api/health/` and the structured error for an invalid request:

```bash
curl -s -X POST http://localhost:8000/api/routes/analyze/ \
  -H 'Content-Type: application/json' -d '{"origin":"Chicago"}' | python -m json.tool
```

---

## 7:45–8:45 — Tests and engineering signals

```bash
cd backend && pytest -q          # 130 passed
cd ../frontend && npm test       # 31 passed
npm run lint && npx tsc --noEmit && npm run build
```

Narrate:

> "The risk engine is a single deterministic module. Tests cover every boundary value, all three load rules, checkpoint interpolation, ETA from provider timings, unit conversions, forecast matching, distance-weighted exposure invariants, No-Travel exclusion, ranking ties, provider failures, and the API contracts. Fixtures are only used in tests — the UI always labels live data."

Show `docs/architecture.md` briefly: the boundary table, exposure algorithm, and heatmap time semantics.

---

## 8:45–9:30 — Wrap-up and honesty

Summarize:

- Real routing alternatives (with graceful, disclosed fallbacks)
- ETA-aware forecasts, not "current weather"
- Deterministic risk + distance-weighted exposure
- Safety exclusion for No-Travel; UNKNOWN ≠ LOW
- Interactive map + corridor heatmap
- Tests, Docker, and deployment configs included

State clearly:

> "GitHub publishing and hosting are manual steps I have prepared for but not performed; the README includes the exact Render and Vercel configuration, including CORS and environment variables."

---

## Demo trips that usually produce interesting weather

Weather changes daily — check the heatmap first and pick a departure where the slider shows orange/red cells:

| Trip | Notes |
|---|---|
| Chicago, IL → Detroit, MI | Reliable 2–3 alternatives; good baseline demo |
| Denver, CO → Kansas City, MO | Plains wind corridor; good for wind/load rules |
| Dallas, TX → Atlanta, GA | Long corridor; good for heatmap variety |
| Minneapolis, MN → Chicago, IL | Winter snow scenarios in season |
| Any route with a departing forecast of thunderstorms | Set load to 44k to demonstrate load overrides |

**Tip:** for deterministic severe scenarios in a demo, show the test suite's boundary tests — live weather cannot be scripted, but the rule engine can be proven.

---

## Reset between takes

- Reload the page to clear the analysis.
- Backend caches are in-memory and reset on restart (`Ctrl+C`, re-run `runserver`).
- If the OSRM demo rate-limits, wait a minute or add an ORS key.
