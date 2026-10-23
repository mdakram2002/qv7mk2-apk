# Known limitations

- Historical analysis depends on retrieving the relevant WINDFOR publication versions. If ingestion fails, affected values remain unavailable.
- WINDFOR history is requested in publication-time windows of no more than seven days. The January retrieval starts 14 days before delivery as a coverage assumption; check Elexon's current horizon documentation if requirements change.
- Retrieved forecasts have hourly delivery starts, while FUELHH actuals are half-hourly. WindLens does not interpolate or duplicate forecasts, so January has forecasts for 744 of 1,488 intervals (50% coverage).
- Live API checks confirmed that FUELHH history is available through its dataset endpoint, while its filtered stream returned current data. A multi-week WINDFOR request failed with HTTP 400, so neither stream nor long date ranges are used for historical backfill.
- The default 10:00 Europe/London day-ahead cutoff is an analytical choice, not a confirmed procurement gate or contractual deadline.
- The API loads January CSVs into memory. It is suitable for this small analysis, but has not been designed for heavy concurrent use.
- There was no public deployment, service credentials, or public URL available when this was written. The deployment templates still need to be configured and published by an account owner.
- Vercel embeds the backend URL when it builds the frontend. Set `VITE_API_URL` before building and configure backend CORS to allow the deployed frontend origin.
