# Technical review script (under five minutes)

1. Trace the bounded ingestion script from FUELHH and WINDFOR into auditable raw JSON and stable processed CSVs.
2. Explain the official filter contract, including the seven-day limit on WINDFOR publication windows and why stream endpoints are not used for historical backfill.
3. Show timezone-aware cutoff construction, latest eligible `publishTime` selection, tie handling, and UTC `startTime` join.
4. Review metrics: MAE, RMSE, signed bias, and ratio-of-sums WAPE, with nulls for empty data or zero denominator.
5. Show the FastAPI versioned endpoints and CSV exports, then the React dashboard's query caching and chart/table views.
6. Review automated unit tests, Docker Compose, CI, CORS configuration, and Render/Vercel templates. Explain persistence requirements for ephemeral hosting.

Checklist: show actual test output; note whether real January history was ingested; show health endpoint and production build; confirm the backend origin is configured in CORS and frontend build; do not claim a deployment or video upload until verified.
