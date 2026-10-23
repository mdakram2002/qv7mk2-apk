# WindLens

WindLens compares UK national wind generation forecasts with actual wind generation for January 2026. It is a dashboard for analysis, not a trading system. Its measurements come from Elexon's BMRS Insights API. When a value is unavailable, WindLens leaves it blank instead of estimating it.

## Data status

The January dataset contains 1,488 actual half-hour records and 26,280 WINDFOR source rows. After limiting forecast versions to January delivery times, 18,080 versions remain across 744 hourly delivery starts. Since the forecasts are hourly and actuals are half-hourly, only 744 of the 1,488 intervals have both values (50% coverage). WindLens does not copy or interpolate forecasts into the gaps. This retrieval had no missing actuals, conflicting duplicates, or invalid source rows.

FUELHH returned 48 actual records for January 1 when queried through its dataset endpoint. Its stream endpoint ignored the requested filters and returned current data, so the ingestion process uses the dataset endpoint for history. WINDFOR history must be fetched in publication-time windows of at most seven days; a month-long request returns HTTP 400. For January, ingestion starts publication searches 14 days before the delivery period. That two-week horizon is an assumption documented in [the architecture notes](docs/architecture.md) and [known limitations](docs/known-limitations.md).

## Run locally

With Docker:

```powershell
docker compose up --build
```

The frontend is at http://localhost:8080, the API at http://localhost:8000, and the health endpoint at http://localhost:8000/api/v1/health.

To run without Docker, use Python 3.12 and Node 20 or later. Create a Python virtual environment, install `backend/requirements.lock`, then run `python -m uvicorn app.main:app --app-dir backend --reload`. In a second terminal, run `npm ci --prefix frontend` and `npm run dev --prefix frontend`. During development, Vite sends `/api` requests to the local backend.

## Refresh the data

Install the backend dependencies, then run `python scripts/ingest_january.py`. The script needs live API access. It retries bounded requests, divides publication dates into supported windows, and saves the source responses alongside processed files. The dashboard reads the processed files. See [data/README.md](data/README.md) for details.

## Forecast selection and metrics

WindLens defaults to a decision cutoff of **10:00 Europe/London on the day before delivery**. This is an analytical assumption, not a confirmed procurement deadline. For each delivery interval, it selects the latest forecast published at or before the cutoff.

Exact duplicates are collapsed. If rows for the same interval and publication time disagree, WindLens picks one deterministically by sorting the source-row JSON and flags the conflict. Times are stored in UTC and shown in Europe/London in the interface.

Forecast error is forecast minus actual, so positive bias means over-forecasting. MAE, RMSE, and bias are measured in MW. WAPE is the total absolute error divided by total actual generation, expressed as a percentage; it is unavailable when total actual generation is zero. Monthly scores are calculated from interval records rather than by averaging daily scores.

## API and data

The versioned API is documented at `/docs`. It includes health and metadata, summaries, time series, daily and monthly accuracy, paginated intervals, forecast versions, data-quality statistics, and CSV or JSON exports.

The data comes from [Elexon's FUELHH endpoint](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream) and [WINDFOR endpoint](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream). The [Elexon developer portal](https://developer.data.elexon.co.uk/) documents the wider API. The API base URL is `https://data.elexon.co.uk/bmrs/api/v1`.

Generation values are in MW. `startTime` is the start of a delivery interval; `publishTime` is when a forecast version was published. Exported timestamps use ISO 8601 UTC. Missing values remain null, and actual generation is filtered to `fuelType=WIND`.

## Configuration and deployment

Copy `.env.example` to `.env`. Set `VITE_API_URL` when building the frontend and `CORS_ORIGINS` for the backend. Deployment settings are in `render.yaml`, `vercel.json`, and the GitHub Actions workflow.

There is no public WindLens repository or deployment yet. The project is inside an existing checkout, and no service credentials or public URLs were provided.

To publish it, create a public GitHub repository for this project and push this directory, not its parent checkout. In Render, create a Docker web service using `backend/Dockerfile` from the repository root. Set `CORS_ORIGINS` to the Vercel site origin and keep `DATA_DIR=/app/data/processed`. The current January files are copied into the image. If the service uses ephemeral storage and you re-ingest data, run ingestion after each fresh deployment; alternatively, attach persistent storage and point `DATA_DIR` to it.

In Vercel, import the same repository with its root as the project root. The included `vercel.json` builds `frontend/`; set `VITE_API_URL` to the Render service URL. After deploying, add the assigned Vercel origin to Render's `CORS_ORIGINS` and redeploy. Then check the health and summary endpoints, charts, CSV exports, and logged-out access. Add the resulting public URLs here after verifying them.

## Project checks

Run backend checks with `pytest backend/tests`. Frontend checks are `npm test --prefix frontend`, `npm run lint --prefix frontend`, `npm run typecheck --prefix frontend`, and `npm run build --prefix frontend`. CI runs these checks. Synthetic records are used only in tests.
