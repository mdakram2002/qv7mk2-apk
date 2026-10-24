# API reference

All routes use the `/api/v1` prefix. The interactive API documentation is available at `/docs`. Date filters accept the January 2026 delivery period, with `end_date` exclusive. Cutoffs use `HH:MM` in Europe/London. Invalid values return HTTP 422.

| Method and path | What it returns |
|---|---|
| `GET /health` | Service status and readiness |
| `GET /metadata` | Analysis scope, data sources, cutoff, and ingestion report |
| `GET /summary` | Hourly matched-pair metrics plus separate half-hour actual coverage; accepts `start_date`, `end_date`, and `cutoff_time` |
| `GET /timeseries` | Hourly comparison series with actuals averaged from both half-hour FUELHH records |
| `GET /accuracy/daily`, `GET /accuracy/monthly` | Hourly daily or monthly scores; expected denominator is 24 hourly starts per January day |
| `GET /intervals` | Paginated interval records with quality filters |
| `GET /forecast-versions?start_time=...` | Forecast versions for one timezone-aware delivery start, the cutoff, eligible count, selected version, and selection reasons |
| `GET /data-quality` | Ingestion report plus distinct half-hour actual and hourly forecast availability/match counts |
| `GET /export/{actuals,forecasts,matched,daily-accuracy,hourly-matched}.csv` | CSV download with an attachment filename; actuals retain half-hourly source rows, while both matched exports use the canonical hourly sample |
| `GET /export/ingestion-report.json` | Ingestion report plus cutoff-specific quality counts; accepts `cutoff_time` |

The API accepts date ranges within January 2026. Page sizes are limited to 500 records. The forecast cutoff defaults to 10:00 Europe/London on the day before delivery. This is an analytical assumption. Hourly forecast availability and match coverage use the 744 expected hourly starts; actual coverage uses the 1,488 expected half-hour FUELHH records. The matched CSV accepts `start_date`, `end_date`, `cutoff_time`, and optional `quality_status` filters so it matches the interval explorer. `/export/hourly-matched.csv` is an explicit alias for the same hourly comparison sample.
