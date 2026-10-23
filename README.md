# WindLens

WindLens is a decision-support dashboard for checking UK national wind generation forecasts against FUELHH wind outturn during January 2026. It is not a trading system. All measurements are sourced from the official Elexon BMRS Insights API; if data is absent, metrics remain unavailable rather than being fabricated.

## Status

The official API has been checked live. `GET /datasets/FUELHH?settlementDateFrom=2026-01-01&settlementDateTo=2026-01-01&fuelType=WIND` returns 48 real half-hourly records. The FUELHH stream endpoint ignores those filters and returns current records, so ingestion uses the non-stream dataset endpoint. That endpoint returns `data` arrays and supports JSON, CSV and XML.

The ingested January window contains 1,488/1,488 actual intervals and 26,280 WINDFOR source rows. After restricting forecast versions to January delivery starts, 18,080 versions cover 744 hourly delivery starts. Consequently only 744 of 1,488 half-hour intervals have both an eligible forecast and actual (50% coverage); the alternating half-hours without WINDFOR values are explicitly missing and excluded from accuracy scores. There are no missing actuals, duplicate conflicts, or invalid source rows in this retrieval.

WINDFOR historical data is queried by `publishDateTimeFrom`/`publishDateTimeTo`, with a maximum inclusive range of seven days per request. A full month request receives HTTP 400. The stream endpoint is unsuitable for version reconstruction. The ingestion process partitions publication time windows and preserves all returned versions. January's assumed retrieval start is 14 days before the delivery period, consistent with a two-week forecast horizon; this is documented as a boundary assumption. See [docs/architecture.md](docs/architecture.md) and [docs/known-limitations.md](docs/known-limitations.md).

## Run locally

```powershell
docker compose up --build
```

Frontend: http://localhost:8080 · API: http://localhost:8000 · Health: http://localhost:8000/api/v1/health

Without Docker, use Python 3.12 and Node 20+: `python -m venv .venv`, install `backend/requirements.lock`, then run `python -m uvicorn app.main:app --app-dir backend --reload`; in another terminal run `npm ci --prefix frontend` and `npm run dev --prefix frontend`. Vite proxies `/api` to the local backend for development.

## Regenerate data

Install backend dependencies and run `python scripts/ingest_january.py`. Live API access is required. The script uses bounded retries, date partitions and preserves raw source responses. The dashboard serves only processed data. See [data/README.md](data/README.md).

## Forecast selection and metrics

The default cutoff is **10:00 Europe/London on the preceding delivery date**, an analytical assumption, not a confirmed procurement gate. Eligible versions have `publishTime <= cutoff`; the latest eligible publish time is selected. Exact duplicates are collapsed; conflicting rows at the same interval and publication timestamp are deterministically selected by sorted source-row JSON and flagged. Times are UTC internally and Europe/London in the interface. Forecast error is forecast minus actual; positive bias means over-forecasting. MAE, RMSE and bias are in MW; WAPE is total absolute error divided by total actual generation, in percent, and is null when its denominator is zero. Monthly metrics are calculated from interval samples, not averaged daily metrics.

## API and data

The versioned API is documented at `/docs`. It provides health, metadata, summary, time series, daily/monthly accuracy, paginated intervals, forecast versions, quality statistics, and CSV/JSON exports. Sources: [FUELHH](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream), [WINDFOR](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream), [Elexon developer portal](https://developer.data.elexon.co.uk/). API base: `https://data.elexon.co.uk/bmrs/api/v1`.

Generation values are MW. `startTime` denotes interval start and `publishTime` the forecast publication time. CSV timestamps are ISO 8601 UTC. Missing values stay null. Actuals are filtered to `fuelType=WIND`.

## Configuration and deployment

Copy `.env.example` to `.env`; configure `VITE_API_URL` at frontend build time and `CORS_ORIGINS` for the backend. See `render.yaml`, `vercel.json`, and GitHub Actions workflow. No standalone public WindLens repository or public deployment has been created; this workspace is nested under a separate existing checkout, and no service credentials or public URLs were supplied.

### Deployment steps

1. Create a new **public** GitHub repository for WindLens, then push the contents of this project directory (not its parent checkout).
2. In Render, create a Docker web service for that repository using `backend/Dockerfile` from the repository root. Set `CORS_ORIGINS` to the eventual Vercel origin and keep `DATA_DIR=/app/data/processed`. The current genuine January files are copied into the image; if re-ingesting on an ephemeral instance, run the ingestion script again after each fresh deployment or attach persistent storage and point `DATA_DIR` to its mounted processed-data directory.
3. In Vercel, import the same repository with repository root as project root. The included `vercel.json` builds `frontend/`; set `VITE_API_URL` to the deployed Render origin and deploy.
4. Update Render's `CORS_ORIGINS` with the assigned Vercel origin and redeploy. Verify `/api/v1/health`, `/api/v1/summary`, frontend interval charts, CSV exports, and access while logged out. Add actual resulting URLs here after successful verification.

## Checks

Backend: `pytest backend/tests`; frontend: `npm test --prefix frontend`, `npm run lint --prefix frontend`, `npm run typecheck --prefix frontend`, `npm run build --prefix frontend`. CI runs these checks. Synthetic records exist only in tests.

## AI disclosure

OpenAI Codex was used to author this application and documentation. Data is not AI-generated.

