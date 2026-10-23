# Data provenance and file formats

Production measurements in this directory come from Elexon's BMRS Insights API: FUELHH provides actual generation for `fuelType=WIND`, and WINDFOR provides forecast versions. Raw JSON files preserve the source responses. Processed CSVs use UTF-8, stable headers, UTC ISO timestamps, and MW values. Null represents unavailable or invalid data; zero is a valid measurement.

Run `python scripts/ingest_january.py` to retrieve the data again and rebuild the processed files. The expected raw files are `raw/fuelhh_wind_january_2026.json` and `raw/windfor_january_2026.json`. Processed outputs include actuals, forecast versions, matched intervals, daily and monthly accuracy, and `metadata/ingestion_report.json`.

Actual records include `startTime`, `settlementDate`, `settlementPeriod`, `generation_mw`, and `source_dataset`. Forecast records include `startTime`, `publishTime`, `generation_mw`, and `source_dataset`. Matched rows include the decision cutoff, selected publication, errors, forecast availability, and quality status. Summary rows include expected and matched counts, coverage, MAE, RMSE, bias, and WAPE.

The current retrieval contains 1,488 actual half-hour intervals and 18,080 January-delivery forecast versions across 744 hourly delivery starts. Forecasts are not interpolated into the intervening half-hours, leaving 744 intervals without a forecast and matched coverage at 50%. Invalid and out-of-period records remain in raw files and are counted separately. Exact duplicates are collapsed; conflicting rows at the same key are resolved using a stable sorted-JSON rule and counted in the quality report.
