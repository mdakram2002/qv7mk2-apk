# WindLens

WindLens helps a day-ahead electricity procurement team review UK wind-generation forecasts against actual generation. It shows which forecast version was available by a selected decision cutoff and how that forecast performed. It is decision support, not a procurement optimizer or trading system: demand, non-wind generation, prices, and other inputs needed to calculate a purchase requirement are outside this analysis.

## Live links

- Frontend: [windlens.vercel.app](https://windlens.vercel.app/)
- Backend health: [qv7mk2-apk.onrender.com/api/v1/health](https://qv7mk2-apk.onrender.com/api/v1/health)
- Interactive API docs: [qv7mk2-apk.onrender.com/docs](https://qv7mk2-apk.onrender.com/docs)

Public HTTP checks on 24 October 2026 reached the Vercel home page and Render health endpoint (HTTP 200); Render returned `ready: true`, and its CORS preflight allowed the Vercel origin. The deployed Render summary still returns the old sample (MAE 2,107.18 MW and a 50% half-hour denominator), so production is behind this working copy. A direct Vercel `/about` request returned 404; `frontend/vercel.json` now adds the SPA fallback for the configured `frontend` root, but this fix needs a Vercel redeploy before that route can be retested. Incognito browser access has not been checked. The Git remote is `mdakram2002/qv7mk2`; its repository name is random-looking, but the owner name is identifiable. Do not describe the repository ownership as anonymous.

## What it does

- Compares January 2026 FUELHH actual generation with WINDFOR forecast versions.
- Replays forecast availability using a configurable cutoff, defaulting to 10:00 Europe/London on the preceding delivery date. This is an analytical assumption, not a verified market deadline.
- Shows summary and daily accuracy, interval records, forecast publication history, data-quality counts, and CSV/JSON exports.
- Leaves forecasts and metrics unavailable when the source has no eligible value. It does not duplicate hourly forecasts into half-hour slots or interpolate them.

There are no screenshots checked into this repository yet. The main chart and interval explorer use hourly actual MW averages to match WINDFOR's observed hourly delivery cadence. The actuals export retains all half-hour FUELHH records.

## Data and current results

The analysis uses the official Elexon BMRS Insights datasets only:

- [FUELHH](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream) for actual generation, requested with `fuelType=WIND`.
- [WINDFOR](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream) for forecast versions, retaining each `startTime`, `publishTime`, and `generation` in the raw records.
- [Elexon developer portal](https://developer.data.elexon.co.uk/) for API conventions and endpoint documentation.

The committed raw cache contains 1,488 FUELHH half-hour records and 26,280 WINDFOR rows. Of the WINDFOR rows, 18,080 have January delivery starts, across 744 unique hourly starts. The observed resolution is 30 minutes for actuals and 60 minutes for forecasts. The canonical accuracy sample has 744 expected hourly starts. It compares each hourly forecast with the mean MW of the two half-hour actual records starting in that hour; an hourly actual stays missing unless both source records exist. In the current cache, 1,488 of 1,488 half-hour actuals are present, 744 of 744 hourly forecast starts have an eligible version at the default cutoff, and all 744 hourly pairs match. The publication search began on 18 December; the earliest returned January-delivery version was published on 30 December, and the longest observed forecast lead was about 66.5 hours. This is a useful margin in the retrieved data, but it does not prove that older publication history is complete.

Recalculation from the committed raw cache at the default 10:00 cutoff produces MAE **2,122.81 MW**, RMSE **2,616.69 MW**, mean bias **+1,840.30 MW**, and WAPE **18.33%** over 744 matched hourly pairs. Positive bias means forecasts were higher than actual generation on average. Hourly matched coverage uses 744 expected hourly starts; actual coverage is reported separately against 1,488 half-hour records. These values describe this retrieved sample and its assumed publication-history boundary.

## Method

For each hourly delivery start, WindLens calculates 10:00 Europe/London on the preceding calendar day, converts that cutoff to UTC, and selects the latest forecast with `publishTime <= cutoff`. It matches using the normalized UTC delivery `startTime`. Publication timestamps are compared as timezone-aware instants; the source timestamp text remains in raw JSON. Actual MW is the arithmetic mean of the two half-hour FUELHH records for that hour, and incomplete hours remain unavailable.

Error is `forecast_mw - actual_mw`. MAE is the mean absolute error, RMSE is the square root of mean squared error, bias is mean signed error, and WAPE is total absolute error divided by total actual generation times 100. These scores use the same records with both finite actual and forecast values. WAPE is null if its denominator is zero. Matched and forecast availability use expected hourly starts; FUELHH coverage separately uses expected half-hour records.

## Data layout

- `data/raw/`: retrieved FUELHH and WINDFOR source rows.
- `data/processed/`: normalized actuals, forecast versions, cutoff-matched intervals, and daily/monthly accuracy CSVs.
- `data/metadata/ingestion_report.json`: request windows, counts, retrieval time, and quality summary.
- `backend/app/`: FastAPI endpoints and analysis functions.
- `backend/tests/`: metric, cutoff, quality, and API tests.
- `frontend/src/`: React application and UI tests.
- `scripts/`: controlled ingestion and API inspection scripts.
- `docs/`: API, architecture, field definitions, limitations, and submission evidence.
- `render.yaml`, `vercel.json`, `docker-compose.yml`: deployment and local container configuration.

## Run locally

Use Python 3.12 and Node 20 or later.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.lock
python -m uvicorn app.main:app --app-dir backend --reload
```

In a second terminal:

```powershell
npm ci --prefix frontend
npm run dev --prefix frontend
```

The Vite development server proxies `/api` to `http://127.0.0.1:8000`.

### Docker Compose

```powershell
docker compose up --build
```

The dashboard is at `http://localhost:8080`; the API is at `http://localhost:8000`; health is at `http://localhost:8000/api/v1/health`.

## Refresh the data

The controlled ingestion script makes public Elexon API requests and writes raw and processed files:

```powershell
python scripts/ingest_january.py
```

To revalidate the committed raw JSON and rebuild processed outputs without network requests, run `python scripts/ingest_january.py --from-cache`. The report labels this as cached-data processing and retains the original source retrieval timestamp.

No API key is stored in this repository. The script partitions WINDFOR publication-time requests and records request windows. In the cached data, the earliest January-delivery publication was 30 December and the largest observed forecast lead was 66.5 hours; the 18 December search boundary covers those observations, but does not prove completeness before that boundary. See [data/README.md](data/README.md) and [known limitations](docs/known-limitations.md) before interpreting the replay as a complete historical archive.

## Configuration and deployment

Copy `.env.example` to `.env` for local configuration. `DATA_DIR` points to processed CSVs, `DEFAULT_CUTOFF` sets the default clock time, `CORS_ORIGINS` lists allowed browser origins, and `VITE_API_URL` is compiled into the frontend.

The deployment setup is split across two services. The public services have not yet been redeployed with the changes in this working copy; the Render summary returned the previous calculation during the audit:

1. Render hosts the FastAPI backend as a Docker web service from `backend/Dockerfile`. The root `render.yaml` Blueprint sets the Dockerfile, health route, data path, and the Vercel CORS origin. The dataset is copied into the image, so re-ingested files need a new image deployment unless persistent storage is configured.
2. Vercel hosts the Vite frontend with project root `frontend`. `frontend/vercel.json` provides the SPA rewrite required for direct route loads. Set install/build/output to `npm ci`, `npm run build`, and `dist`, relative to that root. Set `VITE_API_URL` to the Render service origin, with no `/api/v1` suffix.

For a manually created native Python service on Render, use build command `pip install -r backend/requirements.lock`, root directory blank, and start command `python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port $PORT`. The Docker Blueprint is the recommended path. After creating the Vercel deployment, configure Render's `CORS_ORIGINS` to the exact Vercel origin.

## Checks

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
.\.venv\Scripts\python.exe -m ruff check backend scripts
npm test --prefix frontend
npm run lint --prefix frontend
npm run typecheck --prefix frontend
npm run build --prefix frontend
docker compose config
docker compose up --build
```

GitHub Actions runs backend lint/tests and frontend tests, lint, type checking, and build. The updated Docker images and Compose services were rebuilt and checked locally. Public checks reached the current deployments, but Render still serves the previous summary and Vercel direct app routes returned 404; push and redeploy this working copy, then repeat the endpoint and incognito checks.

## AI disclosure and submission status

OpenAI Codex assisted with implementation, documentation, and test updates. The project maintainer is responsible for reviewing the changes and submitted results.

No YouTube video has been recorded or uploaded. A time-coded walkthrough plan and checklist are in [docs/video-script.md](docs/video-script.md). Repository ownership anonymity is also unresolved because the public GitHub owner handle is personal; changing ownership requires the account owner's action.

## Further documentation

- [API reference](docs/api-reference.md)
- [Architecture](docs/architecture.md)
- [Data dictionary](docs/data-dictionary.md)
- [Known limitations](docs/known-limitations.md)
- [Requirements-to-evidence audit](docs/requirements-evidence.md)
