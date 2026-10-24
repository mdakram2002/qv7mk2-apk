# API reference

All endpoints start with `/api/v1`. FastAPI's interactive documentation is available at `/docs`. The API supports delivery dates in January 2026; `end_date` is exclusive. Cutoff values use `HH:MM` in Europe/London. Invalid query parameters return HTTP 422.

| Method and path | Response |
|---|---|
| `GET /health` | Service status and whether the required dataset is ready. |
| `GET /metadata` | Analysis period, timezone, sources, default cutoff, and ingestion report. |
| `GET /summary` | Accuracy metrics and separate hourly forecast and half-hour actual coverage. Accepts `start_date`, `end_date`, and `cutoff_time`. |
| `GET /timeseries` | Hourly forecast and actual values. Each actual is the average of its two half-hour FUELHH records. |
| `GET /accuracy/daily` | Daily scores, sample counts, and coverage. Each January day has 24 expected hourly starts. |
| `GET /accuracy/monthly` | Monthly scores, sample count, and coverage. |
| `GET /intervals` | Paginated hourly records. Supports date range, cutoff, sorting, and quality-status filters. |
| `GET /forecast-versions?start_time=...` | Versions for one timezone-aware delivery start, including publication time, eligibility, selection, and reason. |
| `GET /data-quality` | Ingestion report and separate actual, forecast, and matched counts. |
| `GET /export/{actuals,forecasts,matched,daily-accuracy,hourly-matched}.csv` | CSV downloads. The actuals file keeps half-hour records; matched files use the hourly comparison. |
| `GET /export/ingestion-report.json` | Ingestion report with counts for the requested cutoff. Accepts `cutoff_time`. |

## Parameters and coverage

Date filters must fall within January 2026. The cutoff defaults to 10:00 Europe/London on the preceding delivery day. This is an analytical assumption, not a verified market deadline. Interval page sizes are limited to 500.

Forecast availability and matched coverage use the 744 expected hourly delivery starts. Actual coverage uses the 1,488 expected half-hour FUELHH records. `/export/matched.csv` accepts `start_date`, `end_date`, `cutoff_time`, and `quality_status`, matching the interval explorer's filters. `/export/hourly-matched.csv` is an alias for the same hourly sample.
