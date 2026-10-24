# WindLens

WindLens helps a day-ahead electricity procurement team review UK wind-generation forecasts against actual generation. It shows which forecast version was available by a selected decision cutoff and how that forecast performed. It is decision support, not a procurement optimizer or trading system: demand, non-wind generation, prices, and other inputs needed to calculate a purchase requirement are outside this analysis.

## Live links

- Frontend: [windlens.vercel.app](https://windlens.vercel.app/)
- Backend health: [qv7mk2-apk.onrender.com/api/v1/health](https://qv7mk2-apk.onrender.com/api/v1/health)
- Interactive API docs: [qv7mk2-apk.onrender.com/docs](https://qv7mk2-apk.onrender.com/docs)

These URLs were supplied for the project. Public checks from the current development environment could not connect to the hosts, so their present availability and the frontend-to-backend integration are not independently verified here. The Git remote is `mdakram2002/qv7mk2-apk`; its repository name is random-looking, but the owner name is identifiable. Do not describe the repository ownership as anonymous.

## What it does

- Compares January 2026 FUELHH actual generation with WINDFOR forecast versions.
- Replays forecast availability using a configurable cutoff, defaulting to 10:00 Europe/London on the preceding delivery date. This is an analytical assumption, not a verified market deadline.
- Shows summary and daily accuracy, interval records, forecast publication history, data-quality counts, and CSV/JSON exports.
- Leaves forecasts and metrics unavailable when the source has no eligible value. It does not duplicate hourly forecasts into half-hour slots or interpolate them.

There are no screenshots checked into this repository yet. The UI's main chart samples every other half-hour actual record, giving hourly chart points to match the observed hourly forecast cadence. Interval exports and the explorer retain the half-hour records.

## Data and current results

The analysis uses the official Elexon BMRS Insights datasets only:

- [FUELHH](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream) for actual generation, requested with `fuelType=WIND`.
- [WINDFOR](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream) for forecast versions, retaining each `startTime`, `publishTime`, and `generation` in the raw records.
- [Elexon developer portal](https://developer.data.elexon.co.uk/) for API conventions and endpoint documentation.

The committed retrieval contains 1,488 FUELHH half-hour records and 26,280 raw WINDFOR rows. Of the WINDFOR rows, 18,080 have January delivery starts, across 744 unique hourly starts. The matched dataset contains 744 of 1,488 expected half-hours (50% coverage); the intervening half-hours have no forecast record and remain missing. These interval counts and resolution were checked from the committed raw and processed files. The retrieval used a publication search beginning 14 days before January; the files alone do not prove that every potentially relevant version before that boundary was available or retrieved.

Recalculation from the committed matched CSV at the default 10:00 cutoff produces MAE **2,107.18 MW**, RMSE **2,611.24 MW**, mean bias **+1,839.92 MW**, and WAPE **18.19%** over 744 matched intervals. Positive bias means forecasts were higher than actual generation on average. Coverage uses all 1,488 expected half-hour slots as its denominator. These values describe this retrieved sample and its assumed publication-history boundary.

## Method

For each delivery interval, WindLens calculates 10:00 Europe/London on the preceding calendar day, converts that cutoff to UTC, and selects the latest forecast with `publishTime <= cutoff`. It matches using the normalized UTC delivery `startTime`. Publication timestamps are compared as timezone-aware instants; the source timestamp text remains in raw JSON.

Error is `forecast_mw - actual_mw`. MAE is the mean absolute error, RMSE is the square root of mean squared error, bias is mean signed error, and WAPE is total absolute error divided by total actual generation times 100. These scores use the same records with both finite actual and forecast values. WAPE is null if its denominator is zero. Coverage is matched intervals divided by expected half-hour intervals times 100.

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

No API key is stored in this repository. The current script partitions WINDFOR publication-time requests and records request windows. Its 14-day lookback is an assumption. It does not establish completeness of publication history before its search boundary. See [data/README.md](data/README.md) and [known limitations](docs/known-limitations.md) before interpreting a replay as a complete historical archive.

## Configuration and deployment

Copy `.env.example` to `.env` for local configuration. `DATA_DIR` points to processed CSVs, `DEFAULT_CUTOFF` sets the default clock time, `CORS_ORIGINS` lists allowed browser origins, and `VITE_API_URL` is compiled into the frontend.

The deployment setup is split across two services:

1. Render hosts the FastAPI backend as a Docker web service from `backend/Dockerfile`. The root `render.yaml` Blueprint sets the Dockerfile, health route, data path, and the Vercel CORS origin. The dataset is copied into the image, so re-ingested files need a new image deployment unless persistent storage is configured.
2. Vercel hosts the Vite frontend with project root `frontend`. `vercel.json` uses `npm ci`, `npm run build`, and `dist`, which are commands relative to that root. Set `VITE_API_URL` to the Render service origin, with no `/api/v1` suffix.

For a manually created native Python service on Render, use build command `pip install -r backend/requirements.lock`, root directory blank, and start command `python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port $PORT`. The Docker Blueprint is the recommended path. After creating the Vercel deployment, configure Render's `CORS_ORIGINS` to the exact Vercel origin.

## Checks

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
npm test --prefix frontend
npm run lint --prefix frontend
npm run typecheck --prefix frontend
npm run build --prefix frontend
docker compose config
docker compose up --build
```

GitHub Actions runs backend lint/tests and frontend tests, lint, type checking, and build. Both Docker images were built locally, Compose services became healthy, and the local API returned the expected January summary. The public deployment checks are still outstanding.

## AI disclosure and submission status

OpenAI Codex assisted with implementation, documentation, and test updates. The project maintainer is responsible for reviewing the changes and submitted results.

No YouTube video has been recorded or uploaded. A time-coded walkthrough plan and checklist are in [docs/video-script.md](docs/video-script.md). Repository ownership anonymity is also unresolved because the public GitHub owner handle is personal; changing ownership requires the account owner's action.

## Further documentation

- [API reference](docs/api-reference.md)
- [Architecture](docs/architecture.md)
- [Data dictionary](docs/data-dictionary.md)
- [Known limitations](docs/known-limitations.md)
- [Requirements-to-evidence audit](docs/requirements-evidence.md)
