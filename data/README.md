# Data files

This folder contains the Elexon source records used by WindLens, the processed files built from those records, and a report of the ingestion run.

## Sources

- **FUELHH** provides actual generation. The ingestion script requests records with `fuelType=WIND`.
- **WINDFOR** provides wind forecast versions. Raw rows retain their delivery time (`startTime`), publication time (`publishTime`), and generation value.

The [ingestion script](../scripts/ingest_january.py) records the source endpoints, request windows, record counts, retrieval time, and data-quality warnings in `metadata/ingestion_report.json`.

## Files and formats

- `raw/fuelhh_wind_january_2026.json` and `raw/windfor_january_2026.json` contain the source rows returned by Elexon.
- `processed/actual_wind_january_2026.csv` contains normalized half-hour actual records.
- `processed/wind_forecast_versions_january_2026.csv` contains the retrieved forecast versions.
- `processed/matched_wind_january_2026.csv` contains the cutoff-selected hourly forecast and actual rows.
- `processed/daily_wind_accuracy_january_2026.csv` and `processed/monthly_wind_accuracy_january_2026.csv` contain grouped accuracy results.

CSV timestamps use ISO 8601 UTC, and generation is measured in MW. Empty values mean unavailable or invalid; zero is a valid reading. Raw and processed files are kept separate so the source can be checked against the analysis.

## Rebuild the processed files

Fetch source data and rebuild the files:

```powershell
python scripts/ingest_january.py
```

Rebuild from the checked-in raw JSON without network access:

```powershell
python scripts/ingest_january.py --from-cache
```

The cache command preserves the original source retrieval time and records the processing time separately. It does not contact Elexon.

## Current cache and matching method

The committed cache contains 1,488 half-hour FUELHH actual records and 26,280 WINDFOR records. Of those forecast records, 18,080 have January delivery starts, covering 744 hourly starts. At the default 10:00 Europe/London cutoff, all 744 hourly starts have an eligible forecast and a matched actual.

For each hour, WindLens averages the two half-hour actual MW values that start within that hour. If either record is missing, the hourly actual remains unavailable. Forecast and matched coverage use 744 expected hourly starts. Actual coverage uses 1,488 expected half-hour records. The actuals export retains all half-hour source rows.

The publication search began 14 days before January. The earliest retrieved forecast for January delivery was published on 30 December 2025, and the longest observed forecast lead was about 66.5 hours. The search window includes the observed publication times, but it does not prove that Elexon's older publication history is complete before 18 December.

Invalid and out-of-period source rows are counted in the report. Exact duplicates are removed. If rows have the same key but conflicting values, the ingestion code selects one deterministically and records the conflict; see the report for the counts.
