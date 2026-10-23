# API reference

All routes use the `/api/v1` prefix. The interactive API documentation is available at `/docs`.

| Method and path | What it returns |
|---|---|
| `GET /health` | Service status and readiness |
| `GET /metadata` | Analysis scope, data sources, cutoff, and ingestion report |
| `GET /summary` | Aggregate metrics and coverage; accepts `start_date`, `end_date`, and `cutoff_time` |
| `GET /timeseries` | Interval time series; accepts the same date and cutoff parameters |
| `GET /accuracy/daily`, `GET /accuracy/monthly` | Daily or monthly accuracy scores |
| `GET /intervals` | Paginated interval records with quality filters |
| `GET /forecast-versions?start_time=...` | Forecast publications for one delivery interval and their cutoff eligibility |
| `GET /data-quality` | Ingestion quality report |
| `GET /export/{actuals,forecasts,matched,daily-accuracy}.csv` | CSV download with an attachment filename |
| `GET /export/ingestion-report.json` | Ingestion report download |

The API accepts date ranges within January 2026. Page sizes are limited to 500 records. The forecast cutoff defaults to 10:00 Europe/London on the day before delivery.
