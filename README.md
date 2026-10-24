# WindLens

WindLens helps a day-ahead electricity procurement team compare UK wind forecasts with actual generation. It replays the forecast versions available at a chosen decision cutoff and shows how those forecasts performed.

WindLens is a decision-support tool. It does not calculate how much electricity to buy or make trading decisions. Demand, prices, and other generation sources are outside this project.

## Try the app

- Frontend: [windlens.vercel.app](https://windlens.vercel.app/)
- Backend health: [Render API health](https://qv7mk2-apk.onrender.com/api/v1/health)
- Interactive API docs: [Render API docs](https://qv7mk2-apk.onrender.com/docs)

The last public check was on 24 October 2026. The Vercel home page and Render health endpoint returned HTTP 200, and Render reported `ready: true`. The deployed Render summary still used the older calculation, and direct access to the Vercel `/about` page returned 404. A Vercel rewrite and updated analysis are in this repository, but production needs to be redeployed before those fixes can be confirmed. Incognito access has not been checked.

The repository is named `qv7mk2-apk`, but its GitHub owner is `mdakram2002`. The name looks random; the owner is identifiable, so the repository is not anonymous.

## What WindLens shows

- Forecasts from Elexon's WINDFOR dataset compared with actuals from FUELHH, filtered to `fuelType=WIND`.
- A configurable historical cutoff. The default is 10:00 Europe/London on the day before delivery. This is an analytical assumption, not a confirmed market deadline.
- Summary and daily accuracy, hourly interval details, forecast publication history, data-quality information, and CSV/JSON downloads.
- Missing source values stay missing. WindLens does not copy hourly forecasts into half-hour slots or fill gaps by interpolation.

The forecast data has hourly delivery starts; FUELHH actuals have half-hour starts. For each forecast hour, WindLens averages the two half-hour actual MW values. If either actual value is missing, the hourly comparison is unavailable. The actuals download still contains the original half-hour rows. Screenshots are not included in the repository.

## Data and current results

WindLens uses the official Elexon BMRS Insights API:

- [FUELHH stream](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream) for actual generation, with `fuelType=WIND`.
- [WINDFOR stream](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream) for forecast versions. The raw records retain `startTime`, `publishTime`, and `generation`.
- [Elexon developer portal](https://developer.data.elexon.co.uk/) for API documentation and conventions.

The committed raw cache has 1,488 FUELHH records and 26,280 WINDFOR records. Of the forecast records, 18,080 have delivery starts in January, covering 744 hourly starts. At the default cutoff, the cache contains all 1,488 expected half-hour actual records, an eligible forecast for all 744 expected hourly starts, and 744 matched hourly pairs.

The forecast publication search began on 18 December 2025. The earliest retrieved version for January delivery was published on 30 December, and the longest observed forecast lead was about 66.5 hours. These observations do not prove that the source archive is complete before the search boundary.

Recalculating the committed raw cache at the default cutoff gives these results for 744 hourly pairs:

| Metric | Result |
|---|---:|
| MAE | 2,122.81 MW |
| RMSE | 2,616.69 MW |
| Signed bias | +1,840.30 MW |
| WAPE | 18.33% |

Positive bias means the forecast was higher than actual generation on average. Forecast availability and matched coverage use the 744 expected hourly starts. Actual coverage is reported separately against 1,488 expected half-hour records. These results describe the committed cache and the stated cutoff assumption; they are not a complete historical archive guarantee.

## How the analysis works

For each delivery hour, WindLens creates a cutoff at the configured time on the preceding day in `Europe/London`. It converts that cutoff to UTC and selects the latest forecast whose `publishTime` is at or before the cutoff. It matches the forecast to actuals using the UTC delivery `startTime`.

The error is `forecast_mw - actual_mw`. The dashboard reports:

- **MAE:** average absolute error, in MW.
- **RMSE:** square root of average squared error, in MW.
- **Signed bias:** average signed error, in MW. Positive means overforecast.
- **WAPE:** total absolute error divided by total actual generation, multiplied by 100.

All four scores use the same rows with valid actual and forecast values. WAPE is unavailable when total actual generation is zero.

## Project layout

```text
backend/app/       FastAPI routes and analysis code
backend/tests/     Backend and API tests
frontend/src/      React app and UI tests
scripts/           Data ingestion and API inspection tools
data/raw/          Retrieved Elexon source rows
data/processed/    Normalized CSV files and matched results
data/metadata/     Ingestion counts, request windows, and warnings
docs/              API, architecture, methodology, and submission notes
```

## Clone and run WindLens locally

The January raw and processed data files are included in the repository, so you can explore the dashboard without an Elexon account or API key. You will need Git, Python 3.12, and Node.js 20 or later.

### 1. Clone the repository

```shell
git clone https://github.com/mdakram2002/qv7mk2-apk.git
cd qv7mk2-apk
```

### 2. Install the backend and start the API

On Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
```

On macOS or Linux:

```shell
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.lock
.venv/bin/python -m uvicorn app.main:app --app-dir backend --reload
```

Leave this terminal running. The API should be available at `http://localhost:8000`. You can check its status at [the health endpoint](http://localhost:8000/api/v1/health) or browse its routes at [the interactive API docs](http://localhost:8000/docs).

### 3. Install and start the frontend

Open a second terminal in the project folder:

```shell
npm ci --prefix frontend
npm run dev --prefix frontend
```

Open the local dashboard at [http://localhost:5173](http://localhost:5173). Vite forwards API requests to the backend at `http://127.0.0.1:8000`. Keep both terminals running while you use the app. Press `Ctrl+C` in each terminal to stop the services.

### 4. Explore the features

- **Overview:** compare hourly forecasts and actuals, review MAE, RMSE, bias, WAPE, and daily errors. Change the cutoff to see how the selected forecast versions and scores respond.
- **Intervals:** choose a January delivery date, filter and sort hourly records, and download the displayed selection as a CSV.
- **Forecast history:** inspect the forecast versions for a delivery hour. The page marks the selected version, eligible versions that were superseded, and versions published after the cutoff.
- **Data quality:** review actual and forecast coverage, record counts, ingestion details, and missing-data warnings. Download the JSON report here.
- **About this analysis:** read how the data is matched, how the cutoff works, and how each metric is calculated.

The app uses the committed dataset by default. If you want to fetch the data again, follow the instructions in [Refresh the data](#refresh-the-data).

### Run with Docker Compose

```powershell
docker compose up --build
```

Open the dashboard at `http://localhost:8080`. The API is at `http://localhost:8000`; its health endpoint is `http://localhost:8000/api/v1/health`.

## Refresh the data

To request the source datasets again and rebuild the processed files:

```powershell
python scripts/ingest_january.py
```

To rebuild from the committed raw JSON without making network requests:

```powershell
python scripts/ingest_january.py --from-cache
```

Cached processing preserves the source retrieval time and records when processing took place. The script uses public Elexon endpoints; no API key is needed or stored here. See [data notes](data/README.md) and [known limitations](docs/known-limitations.md) before treating the replay as a complete forecast archive.

## Configuration and deployment

Copy `.env.example` to `.env` for local settings. `DATA_DIR` selects the processed CSV directory, `DEFAULT_CUTOFF` sets the default cutoff time, `CORS_ORIGINS` lists permitted browser origins, and `VITE_API_URL` sets the backend origin used when building the frontend.

This project uses two deployed services:

1. **Render** runs the FastAPI backend in `backend/Dockerfile`. The root `render.yaml` sets the health path, data directory, and allowed Vercel origin. The data files are copied into the Docker image, so updated files require a new deployment unless persistent storage is configured.
2. **Vercel** serves the Vite frontend from the `frontend` project root. Use `npm ci` for installation, `npm run build` for the build command, and `dist` for the output directory. Set `VITE_API_URL` to the Render service origin without an `/api/v1` suffix. `frontend/vercel.json` contains the SPA rewrite for direct route loads.

For a manually configured native Python service on Render, leave the root directory blank. Use `pip install -r backend/requirements.lock` as the build command and `python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port $PORT` as the start command. The Docker Blueprint in `render.yaml` is the intended setup. Set `CORS_ORIGINS` to the exact deployed frontend origin.

## Checks

Run the backend checks from the repository root:

```powershell
python -m pytest backend/tests
.\.venv\Scripts\python.exe -m ruff check backend scripts
```

Run the frontend checks:

```powershell
npm test --prefix frontend
npm run lint --prefix frontend
npm run typecheck --prefix frontend
npm run build --prefix frontend
```

To check Docker configuration and start both services:

```powershell
docker compose config
docker compose up --build
```

The latest local backend run passed **31 tests**. The latest frontend run passed **4 tests**. Ruff and `git diff --check` also passed. GitHub Actions runs backend lint and tests plus frontend tests, lint, type checking, and a production build. Public deployments still need to be updated and checked after the latest changes.

## More detail

- [API reference](docs/api-reference.md)
- [Architecture](docs/architecture.md)
- [Data dictionary](docs/data-dictionary.md)
- [Known limitations](docs/known-limitations.md)
- [Requirements and evidence](docs/requirements-evidence.md)
