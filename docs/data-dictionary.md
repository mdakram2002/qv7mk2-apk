# Data dictionary

All timestamps are ISO-8601 UTC in exported files; the user interface renders Europe/London. All generation values are MW.

| Field | Meaning |
|---|---|
| `startTime` | Start of delivery interval |
| `publishTime` | WINDFOR version publication time |
| `settlementDate`, `settlementPeriod` | Elexon delivery date and half-hour period |
| `generation_mw` | FUELHH actual or WINDFOR forecast generation |
| `decision_cutoff` | D-1 configured cutoff, normalized to UTC |
| `selected_publishTime` | Chosen version publication; null when none eligible |
| `signed_error_mw` | Forecast minus actual |
| `absolute_error_mw`, `squared_error_mw` | Absolute and squared signed error |
| `percentage_error` | Signed error / actual × 100; null when actual is zero |
| `forecast_available_at_cutoff` | Whether any eligible version exists |
| `data_quality_status` | matched, missing_forecast, or missing_actual |

Null means unavailable or not meaningful. Zero is a valid generation value. Raw API payloads are preserved independently from processed rows.
