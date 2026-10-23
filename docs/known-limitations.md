# Known limitations

- Historical delivery metrics depend on successful retrieval of historical WINDFOR publication versions. No values should be implied if ingestion failed.
- The WINDFOR query is partitioned into seven-day publication windows. A 14-day pre-delivery start is used as an analytical coverage assumption; verify against Elexon's current horizon documentation when requirements change.
- The retrieved WINDFOR versions have hourly delivery starts while FUELHH actuals are half-hourly. No interpolation or duplication is applied; the alternate half-hour slots are missing forecast records, leaving 50% matched coverage for this January retrieval.
- Official live API checks confirmed FUELHH history and that a multi-week WINDFOR request fails with HTTP 400 due to its seven-day maximum. The filtered FUELHH stream request returned current data, confirming stream is unsuitable for backfill.
- Default 10:00 D-1 is not a verified procurement gate or contractual cutoff.
- The API loads January CSVs into memory and is intended for a small analytical dataset, not high-concurrency operational use.
- No public frontend/backend deployment, credentials, or public URLs were available in this environment. Deployment templates are prepared but must be configured and published by an account owner.
- A Vercel frontend build embeds its backend URL at build time. Configure `VITE_API_URL`, then set backend CORS to the deployed origin.
