# Requirements-to-evidence audit

Audit date: 24 October 2026. This records evidence from the current checkout and runs performed during the audit. Local verification does not establish public deployment availability.

## Findings and fixes

| Severity | Evidence-based finding | Fix | Verification |
|---|---|---|---|
| High | Accuracy and interval error rows paired hourly WINDFOR forecasts with a single half-hour FUELHH reading and divided 744 matches by 1,488 half-hours. | Compare hourly forecasts with the mean MW of both half-hour actual records. Use 744 expected hourly starts for forecast/matched coverage and 1,488 expected records for actual coverage. Keep the explorer hourly and export the complete half-hour actual source separately. | Aggregation fixture; API/export reconciliation; 744 matched hourly pairs and 1,488 actual records. |
| High | The committed monthly scores came from the incorrect hourly/half-hour pairing. | Recalculate all scores from the canonical hourly matched sample and make summary, daily/monthly endpoints, charts, and hourly CSV export share the same function. | Independently calculate summary values from `/export/hourly-matched.csv` in API tests. |
| Medium | Ingestion errors did not report a safe response excerpt and classified some HTTP failures only as generic retries. | Log failed request URL, status, content type, and a bounded response excerpt; retry transient 429/5xx and transport errors; fail on other 4xx responses. | Live one-day probes plus MockTransport tests for HTTP 400/503, malformed JSON, empty arrays, and pagination metadata. |
| Medium | Existing quality copy conflated forecast availability with half-hour actual coverage. | Add distinct denominators and resolution labels to the summary and data-quality API and dashboard. | API assertions and frontend coverage test. |
| Medium | Conflicting or stale documentation described 50% coverage and old scores. | Update README, data notes, methodology/API docs, known limitations, and audit evidence to describe hourly aggregation and the retrieval boundary. | Cross-checked against regenerated report and API tests. |

## Requirements-to-evidence matrix

| Requirement | Evidence | Status |
|---|---|---|
| Official FUELHH actuals filtered to `WIND`, and WINDFOR versions with `startTime`, `publishTime`, `generation` | `scripts/ingest_january.py`, raw JSON, report. Official docs: [FUELHH](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream), [WINDFOR](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream). Read-only sample API requests returned HTTP 200 with JSON and expected fields. | Sample routes validated live; full month was reprocessed from cached raw data, not freshly downloaded. |
| January 1–31, 2026, expected intervals and resolutions | Cached source data: 1,488 actual starts at 30-minute cadence; 744 forecast starts at 60-minute cadence. | Verified locally. January has 1,488 expected half-hour actuals and 744 expected hourly starts. |
| Timezone-aware D-1 cutoff and latest eligible version, without future leakage | `cutoff_for`, `select_versions`, hourly/interval loaders, forecast history. Times compare in UTC and cutoff is configured in Europe/London. | Tests cover exact cutoff, offset-aware ordering, D-1, and DST boundary. Publication history before 18 December 2025 remains unverified. |
| Resolution-aware comparisons and missing data | Hourly actual is mean MW of both corresponding FUELHH half-hours. The explorer uses hourly rows; the actuals export retains half-hour source records. | At cached default cutoff: actuals 1,488/1,488; eligible forecasts 744/744; matched hourly pairs 744/744. |
| Independently validated metrics | Hand-calculated metric fixtures and API tests compare summary scores with hourly CSV records. | Cached sample at 10:00: n=744; MAE 2,122.81 MW; RMSE 2,616.69 MW; bias +1,840.30 MW; WAPE 18.33%. |
| API, filtering, and exports | FastAPI routes under `/api/v1`; `/export/matched.csv` and `/export/hourly-matched.csv` both export the hourly analysis; actuals CSV retains half-hour data. | 31 backend tests pass. Public `/summary` responded HTTP 200 but still serves the prior code and metrics. |
| React UI, route behavior, and accessibility | `frontend/src/App.tsx`, About page, Vercel rewrite, and React tests. | 3 frontend tests, lint, typecheck, and production build pass locally. Local Docker serves `/about`; public Vercel returned 404 before this rewrite was deployed. Incognito browser review remains outstanding. |
| Docker, CI, secrets, deployment configuration | Dockerfiles, Compose, GitHub Actions, Render and Vercel config. | Latest images rebuilt; Compose API/frontend started healthy; API summary/export and frontend About route were verified, then services stopped. No secrets added. Public app/API require redeployment. |
| README and product disclosures | README and docs state data scope, methods, cache boundaries, AI disclosure, and deployment/video status. | Updated locally. |
| Random repository name and anonymity | Remote is `mdakram2002/qv7mk2-apk`. | Repository name is random-looking; ownership remains personally identifiable and was not changed. |
| Unlisted video <=10 minutes and incognito URL checks | `docs/video-script.md`; public app/API URLs listed in README. | Video not recorded or uploaded; public links/incognito access need owner verification. |

## Data and source limitations

- The raw cache includes 26,280 WINDFOR rows, of which 18,080 have January delivery starts. Its publication-time search begins on 18 December 2025; the earliest returned January-delivery publication is 30 December, and the longest observed forecast lead is 66.5 hours. That supports the retrieval window for the observed data, but does not prove the source archive is complete before the search boundary.
- The live API probe checked one day for each dataset only. A full-month live refresh, complete pagination audit, and retrieval-boundary completeness check remain outstanding.
- Public Vercel root, Render health, summary, and CORS preflight were checked over HTTP. Vercel `/about` returned 404, while Render `/summary` returned the old 50% half-hour calculation. Local fixes are in this checkout, but both services need redeployment before the deployed behavior can be revalidated. No incognito browser session was available.
- Cached reprocessing used `python scripts/ingest_january.py --from-cache`. It retained the source retrieval timestamp and records the processing timestamp separately.
- The 10:00 Europe/London cutoff is an analytical assumption, not a verified procurement deadline.
- Logged-out incognito access, deployed exports, and direct routes must be retested after redeployment. Repository anonymity and YouTube upload also require account-owner action.
