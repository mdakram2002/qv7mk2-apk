# Data dictionary

CSV exports use ISO 8601 timestamps in UTC. The dashboard displays times in Europe/London. Generation values are in MW.

| Field | Meaning |
|---|---|
| `startTime` | Start of the delivery interval. For WINDFOR, this is the forecast target time. |
| `publishTime` | Time when Elexon published a WINDFOR forecast version. |
| `settlementDate`, `settlementPeriod` | FUELHH delivery date and half-hour settlement period. |
| `generation_mw` | Generation value in MW from FUELHH or WINDFOR. |
| `actual_generation_mw` | In the hourly analysis, the average of the two half-hour FUELHH readings that start in that hour. Null if either reading is missing. |
| `actual_half_hour_count` | Number of FUELHH records used for the hourly actual. A complete hour has two. |
| `decision_cutoff` | Configured day-ahead cutoff, stored as a UTC timestamp. |
| `selected_publishTime` | Publication time of the chosen forecast version, or null if none met the cutoff. |
| `signed_error_mw` | Forecast generation minus actual generation. Positive means overforecast. |
| `absolute_error_mw`, `squared_error_mw` | Absolute or squared signed error. |
| `percentage_error` | Signed error divided by actual generation, times 100. Null when actual generation is zero. |
| `forecast_available_at_cutoff` | Whether a forecast version met the selected cutoff. |
| `eligible_forecast_versions` | Number of retrieved versions published at or before the cutoff for that delivery start. |
| `selection_status` | Whether the latest eligible forecast was selected or no eligible forecast was found. |
| `selection_reason` | Short explanation of the selection or why no forecast was available. |
| `data_quality_status` | `matched`, `missing_forecast`, or `missing_actual`. |

The matched CSV, summary metrics, daily and monthly results, charts, interval explorer, and matched exports use the same hourly sample: one row per expected January delivery hour, or 744 rows. The actuals export keeps all 1,488 half-hour FUELHH records. Coverage denominators differ by resolution and are reported separately.

Null means a value is unavailable or does not apply. Zero is a valid generation value. The original Elexon records are stored separately in `data/raw/`.
