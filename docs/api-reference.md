# API reference

All routes use the `/api/v1` prefix. The interactive API documentation is available at `/docs`. Date filters accept the January 2026 delivery period, with `end_date` exclusive. Cutoffs use `HH:MM` in Europe/London. Invalid values return HTTP 422.

| Method and path | What it returns |
|---|---|
| `GET /health` | Service status and readiness |
| `GET /metadata` | Analysis scope, data sources, cutoff, and ingestion report |
| `GET /summary` | Aggregate metrics and coverage; accepts `start_date`, `end_date`, and `cutoff_time` |
| `GET /timeseries` | Interval time series; accepts the same date and cutoff parameters |
| `GET /accuracy/daily`, `GET /accuracy/monthly` | Daily or monthly accuracy scores |
| `GET /intervals` | Paginated interval records with quality filters |
| `GET /forecast-versions?start_time=...` | Forecast versions for one timezone-aware delivery start, the cutoff, eligible count, selected version, and selection reasons |
| `GET /data-quality` | Ingestion report plus cutoff-specific eligible coverage, matched and missing counts |
| `GET /export/{actuals,forecasts,matched,daily-accuracy}.csv` | CSV download with an attachment filename |
| `GET /export/ingestion-report.json` | Ingestion report plus cutoff-specific quality counts; accepts `cutoff_time` |

The API accepts date ranges within January 2026. Page sizes are limited to 500 records. The forecast cutoff defaults to 10:00 Europe/London on the day before delivery. The matched CSV export accepts `start_date`, `end_date`, `cutoff_time`, and optional `quality_status` filters so it can match the interval explorer selection.
