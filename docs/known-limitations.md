# Known limitations

- Forecast publication searches in the committed retrieval begin on 18 December 2025, 14 days before the delivery month. The available files do not prove that every forecast version published earlier was retrieved. Historical scores are therefore bounded by that retrieval assumption.
- The retrieved January WINDFOR rows have 744 unique hourly delivery starts. FUELHH has 1,488 half-hour actual intervals. At the default cutoff, only the hourly starts match; WindLens does not interpolate or copy forecasts into the intervening intervals. Coverage is 744/1,488, or 50%.
- The 10:00 Europe/London day-ahead cutoff is configurable and clearly treated as an analytical assumption. It has not been verified as a procurement gate or contractual deadline.
- The ingestion script partitions WINDFOR publication-time requests and preserves the raw returned records. The current checked-in report records request windows and retrieval counts, but a new live ingestion was not possible during this audit. Recheck current endpoint behavior and history boundaries when refreshing the dataset.
- The API loads processed CSVs into memory. It is designed for this small January analysis, not high-concurrency operational use.
- The dataset is copied into the backend Docker image. Files written to Render's default ephemeral filesystem do not survive a redeploy; use a supported persistent disk if ingestion writes need to persist.
- The public URLs were provided by the project owner, but outbound network access from this environment refused the connection. Current frontend availability, backend health, CORS behavior, exports, and logged-out access remain unverified.
- The repository is publicly named `qv7mk2-apk`, but its GitHub owner handle is personal and visible. The repository name looks random; ownership is not anonymous.
- No unlisted demo video has been recorded or uploaded. See [video script and recording checklist](video-script.md).
