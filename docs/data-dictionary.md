# Data dictionary

Exports use ISO 8601 UTC timestamps. The interface displays times in Europe/London. Generation values are measured in MW.

| Field | Meaning |
|---|---|
| `startTime` | Start of the delivery interval |
| `publishTime` | Time when the WINDFOR forecast version was published |
| `settlementDate`, `settlementPeriod` | Elexon's delivery date and half-hour period |
| `generation_mw` | Actual FUELHH or forecast WINDFOR generation |
| `actual_generation_mw` in hourly analysis | Arithmetic mean of the two FUELHH half-hour MW values starting within the hour; null unless both exist |
| `actual_half_hour_count` | Number of source FUELHH records available for the hourly aggregate; a complete hour has 2 |
| `decision_cutoff` | Configured day-ahead cutoff, normalized to UTC |
| `selected_publishTime` | Publication time of the selected forecast; null if none is eligible |
| `signed_error_mw` | Forecast minus actual generation |
| `absolute_error_mw`, `squared_error_mw` | Absolute and squared signed error |
| `percentage_error` | Signed error divided by actual generation, multiplied by 100; null when actual generation is zero |
| `forecast_available_at_cutoff` | Whether an eligible forecast version exists |
| `eligible_forecast_versions` | Number of retrieved versions published at or before the selected cutoff |
| `selection_status` | `selected_latest_eligible` or `missing_eligible_forecast` |
| `selection_reason` | Short explanation of why a version was selected or why none was eligible |
| `data_quality_status` | `matched`, `missing_forecast`, or `missing_actual` |

`matched_wind_january_2026.csv`, summary metrics, daily/monthly accuracy, overview charts, the interval explorer, `/export/matched.csv`, and `/export/hourly-matched.csv` use one row per expected hourly delivery start (744 for January 2026). `/export/actuals.csv` retains the 1,488 half-hour FUELHH source rows. Coverage denominators are named in each API response; these two resolutions must not be compared as if they had the same denominator.

Null means a value is unavailable or does not apply. Zero is a valid generation value. Raw API responses are stored separately from the processed rows.
