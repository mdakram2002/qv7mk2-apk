# API reference

Prefix: `/api/v1`; interactive OpenAPI UI: `/docs`.

| Method/path | Purpose |
|---|---|
| `GET /health` | Service status and readiness |
| `GET /metadata` | Scope, sources, cutoff and ingestion report |
| `GET /summary` | Aggregate metrics and coverage; accepts `start_date`, `end_date`, `cutoff_time` |
| `GET /timeseries` | Interval series; accepts same date and cutoff parameters |
| `GET /accuracy/daily`, `/accuracy/monthly` | Daily/monthly scores |
| `GET /intervals` | Paginated interval observations and quality filtering |
| `GET /forecast-versions?start_time=...` | All publications for one delivery interval and cutoff eligibility |
| `GET /data-quality` | Ingestion quality report |
| `GET /export/{actuals,forecasts,matched,daily-accuracy}.csv` | Download CSV (`Content-Disposition: attachment`) |
| `GET /export/ingestion-report.json` | Ingestion report download |

Only January 2026 ranges are accepted. Page size is limited to 500. Cutoff defaults to 10:00 Europe/London.
