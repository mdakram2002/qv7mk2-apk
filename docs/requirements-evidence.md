# Requirements and evidence

This page records what has been checked in the current working copy and what still needs an external check. Local results do not prove that the public services are running the same code.

## Findings and changes

| Priority | What was wrong | What changed | How it was checked |
|---|---|---|---|
| High | The analysis compared hourly WINDFOR forecasts with individual half-hour FUELHH values and used a half-hour denominator for forecast coverage. | The analysis now averages the two actual MW values in each hour. Forecast and match coverage use 744 expected hours; actual coverage uses 1,488 expected half-hours. | Independent reconstruction from raw JSON, API/export comparisons, and backend tests. |
| High | The previous monthly scores came from the mismatched resolutions. | Summary, daily and monthly results, charts, interval records, and matched exports now use the same hourly pairs. | Independent recalculation and API checks against the checked-in raw data. |
| Medium | Some ingestion failures were hard to diagnose. | Failed requests log the URL, status, content type, and a bounded response excerpt. Transient errors are retried; other client errors fail clearly. | Mock request tests cover HTTP 400/503, malformed JSON, empty responses, and pagination metadata. |
| Medium | Coverage wording did not make the different resolutions clear. | The API and dashboard report hourly forecast/match coverage separately from half-hour actual coverage. | API tests and frontend coverage test. |
| Medium | A rounded actual and rounded error could appear inconsistent in the interval table. | Actual and error values now display to one decimal place when half-MW values occur. | Frontend regression test for the first interval's 13,814.5 MW actual and 5,651.5 MW signed error. |
| Medium | CI could not import the top-level ingestion script from backend tests. | Test setup now adds both the repository and backend directories to Python's import path. | `python -m pytest backend/tests` passes from the repository root. |

## Requirements and evidence

| Requirement | Evidence and current status |
|---|---|
| Use only Elexon FUELHH wind actuals and WINDFOR forecasts. | The ingestion script uses FUELHH with `fuelType=WIND` and WINDFOR. Raw JSON and the ingestion report are checked in. Live sample requests to each official stream route returned HTTP 200 during the 24 October 2026 check. The full month was reprocessed from the committed cache, not freshly downloaded. [FUELHH docs](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream) · [WINDFOR docs](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream) |
| Analyze January 1–31, 2026 using the right resolutions. | The cache contains 1,488 half-hour actual records and 744 hourly forecast starts. At the default cutoff it has 744 eligible forecasts and 744 matched hourly pairs. Verified locally from raw data. |
| Select forecasts available by the preceding-day cutoff. | `cutoff_for` and `select_versions` construct a timezone-aware London cutoff and compare publication instants in UTC. Tests cover exact-cutoff eligibility, timezone offsets, preceding-day selection, and daylight-saving changes. Completeness before 18 December 2025 is unknown. |
| Calculate metrics from one valid sample. | Independent raw-data calculation at 10:00 gives n=744, MAE 2,122.8112 MW, RMSE 2,616.6887 MW, signed bias +1,840.2964 MW, and WAPE 18.3305%. API summary and CSV exports reconcile with these values. |
| Keep missing data visible and coverage denominators separate. | The cache has 1,488/1,488 actual records, 744/744 eligible forecasts, and 744/744 hourly matches. No values are filled or interpolated. |
| Provide API endpoints and exports. | FastAPI provides summary, timeseries, daily/monthly accuracy, intervals, forecast history, quality, and CSV/JSON exports. **31 backend tests pass locally.** |
| Provide a React frontend. | The app includes overview, interval, forecast-history, data-quality, and analysis-methodology views. **4 frontend tests pass locally.** Lint, type checking, and production build passed in the earlier local verification. |
| Support Docker, CI, and deployment. | Dockerfiles, Compose, GitHub Actions, Render, and Vercel configuration are present. The backend test import issue is fixed locally. The latest CI result has not been rerun from a pushed commit. |
| Provide public links and anonymous repository identity. | The public URLs are listed in the README. The owner account is visible as `mdakram2002`, so only the repository name is random-looking; ownership is not anonymous. |
| Provide a short unlisted demo and verify links in private browsing. | The video is not recorded or uploaded, and incognito access has not been verified. |

## Data and deployment limits

- The raw cache has 26,280 WINDFOR rows, including 18,080 January delivery versions. The publication search starts on 18 December 2025. The earliest retrieved January-delivery version is dated 30 December, and the maximum observed lead is 66.5 hours. Older archive completeness is not established.
- The 10:00 Europe/London cutoff is a configurable analytical assumption, not a verified procurement deadline.
- On 24 October 2026, public checks reached the Vercel home page and Render health and summary endpoints. Render returned the old summary calculation, and Vercel `/about` returned 404. Local changes need redeployment before public routes, metrics, or exports can be rechecked.
- The full-month data was rebuilt with `python scripts/ingest_january.py --from-cache`; the report keeps the original retrieval time and records the processing time separately.
- No private browsing check was available. The public endpoints, direct routes, and exports must be checked again after deployment.
