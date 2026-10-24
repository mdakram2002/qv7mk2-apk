# Requirements-to-evidence audit

Audit date: 23 October 2026. “Verified locally” means checked against this checkout, its committed data, or commands run in this environment. It does not mean the public deployment was reachable.

## Findings and changes

| Severity | Finding and evidence | Change | Verification |
|---|---|---|---|
| High | `select_versions` sorted publication timestamps as strings, which can misorder different UTC offsets (`backend/app/core.py`). | Compare timezone-aware UTC instants; keep deterministic tie ordering. | Added regression test with offset-spelled times; backend suite passes. |
| High | The matched CSV route exported the whole month and ignored the interval explorer's selected date/status (`backend/app/main.py`, `frontend/src/App.tsx`). | Added validated date/status filters and passes the explorer's active filters into the download link. | API test confirms a one-day matched-only export has 24 rows. |
| High | Forecast history accepted malformed/naive starts with potential server errors and did not return the delivery start or eligible count. The UI queried a fixed noon interval without identifying it as the delivery interval. | Validate timezone-aware January start, return provenance and missing-selection status, add delivery-hour selection, and distinguish delivery start from publication time in the table. | API tests cover invalid starts; frontend typecheck/build pass. |
| Medium | Health readiness only checked file existence, and data quality displayed absent values as zeros. | Health checks populated actual/forecast CSVs and a successful ingestion report; quality counts are cutoff-aware and loading/errors do not masquerade as zero. | Backend API suite passes; frontend typecheck/build pass. |
| Medium | Overview chart labels showed time-of-day only across a full month and called the joined series half-hourly despite hourly forecasts. | Show date and time, sample hourly actual points against hourly forecasts, and state the sampling cadence. | Frontend lint/typecheck/build pass; visual public check remains blocked. |
| Medium | README deployment statements were stale; the Render Blueprint used a placeholder CORS origin, and Vercel commands conflicted with the selected `frontend` root. | Updated deployment docs/config, set the production Vercel origin in `render.yaml`, and aligned Vercel commands with the `frontend` root. | Configuration inspected locally; deployed services need an external redeploy and live check. |

## Requirement status

| Requirement | Evidence in this repository | Status |
|---|---|---|
| Official sources only; FUELHH actuals filtered to WIND and WINDFOR forecasts retained with `startTime`, `publishTime`, and `generation` | `scripts/ingest_january.py`, `data/raw/`, `data/processed/`, report source filters. Official references: [FUELHH](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream), [WINDFOR](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream). | Implemented; source files and mappings verified locally. Fresh API retrieval not rerun. |
| January 1–31, 2026 delivery period | Raw and processed files, ingestion report, API date-range validation. | Verified locally: 1,488 expected half-hour intervals. |
| Timestamp mapping and UTC normalization | Ingestion maps source timestamps; raw rows preserve original spellings; API uses UTC and UI renders Europe/London. | Verified locally; selection ordering bug fixed and tested. |
| Latest forecast published by configurable D-1 cutoff; no look-ahead | `cutoff_for`, `select_versions`, `load_matched`, `/forecast-versions`; tests cover exact cutoff and offset times. | Implemented and unit-tested. Completeness of versions before the retrieval boundary is unverified. |
| Forecast resolution and missing coverage handled honestly | Raw file has 744 January delivery starts, each 60 minutes apart; actual CSV has 1,488 30-minute starts. Matched file/report shows 744 matched (50%). | Verified from committed records; no interpolation or duplication. |
| Independent MAE, RMSE, bias, WAPE checks | `backend/app/core.py`; hand-calculated fixture in `backend/tests/test_core.py`; committed monthly CSV independently recalculated. | Verified locally. Current sample results: MAE 2,107.18 MW; RMSE 2,611.24 MW; bias +1,839.92 MW; WAPE 18.19%. |
| API endpoints, input validation, exports | FastAPI routes in `backend/app/main.py`; API tests in `backend/tests/test_api.py`; `/docs` configured. | Local tests pass; public endpoint response not verified. |
| Dashboard pages and API-derived data | React queries in `frontend/src/App.tsx`; interval and history screens; cutoff-aware overview. | Implemented and built locally. No screenshot or external browser audit available. |
| Docker, Compose, health, CI | `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml`, Render/Vercel config. | Both Docker images built; Compose API and frontend reported healthy; local health and summary endpoints responded. CI-equivalent commands pass locally. |
| Public deployment and CORS | Owner-provided URLs: [frontend](https://windlens.vercel.app/), [health](https://qv7mk2-apk.onrender.com/api/v1/health), [API docs](https://qv7mk2-apk.onrender.com/docs). | URLs supplied but live requests failed from this environment; availability, CORS, exports, and direct-route refresh are unverified. |
| README, method, limitations, and AI disclosure | `README.md`, `docs/architecture.md`, `docs/data-dictionary.md`, `docs/known-limitations.md`; OpenAI Codex disclosure. | Updated. |
| Random/anonymous repository requirement | Git remote: `mdakram2002/qv7mk2-apk`. | Name is random-looking; owner is identifiable. Anonymity is not met if it applies to ownership. No ownership change made. |
| Unlisted video <=10 minutes and submission links | `docs/video-script.md`; README records no upload. | Outstanding; video must be recorded, uploaded, and checked by owner. |

## Current verification gaps

- Official Elexon endpoint documentation pages render through a JavaScript application in the available browser tool. The API/developer portal and endpoint-index search results were reviewed, and the committed raw responses were inspected, but a fresh live ingestion and full pagination/history audit were not completed.
- Outbound requests to the supplied Vercel and Render URLs were refused from this environment. Their actual public state cannot be claimed.
- Docker image builds, Compose startup, and actual browser/incognito accessibility still need verification in an environment with Docker daemon and external network access.
- The public YouTube video and anonymous repository ownership remain account-owner tasks.
