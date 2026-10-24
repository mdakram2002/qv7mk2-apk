# WindLens demo video plan

Target length: 8–9 minutes total. Keep the customer walkthrough under five minutes and the technical review under five minutes. No video has been recorded or uploaded yet. The script describes the checked-in January dataset; first confirm the live app and current metrics before recording.

## Part 1: customer walkthrough (about 4 minutes)

| Time | Screen | Narration |
|---|---|---|
| 0:00–0:35 | WindLens Overview | “WindLens helps a day-ahead procurement team review national wind forecasts against actual wind generation. It supports forecast review; it does not calculate a purchase requirement or replace a procurement decision.” |
| 0:35–1:05 | Cutoff control and assumption note | “The cutoff is configurable. This example uses 10:00 Europe/London on the preceding delivery date as an analytical assumption. It is not represented as an official market deadline.” |
| 1:05–1:55 | Overview metrics and chart | “The dashboard reports mean absolute error, root mean squared error, signed bias, and WAPE for intervals with both an eligible forecast and an actual. In the committed sample at this cutoff, MAE is 2,107.18 MW, RMSE 2,611.24 MW, bias plus 1,839.92 MW, and WAPE 18.19%, over 744 matched intervals. Positive bias means forecasts were higher than actual generation on average. The chart compares the observed hourly forecast cadence with actuals.” |
| 1:55–2:30 | Coverage and daily chart | “The committed January retrieval has 1,488 half-hour actual intervals and 744 hourly forecast delivery starts. At the selected cutoff, 744 intervals match, so coverage is 50 percent. WindLens leaves the other half-hours missing instead of filling them.” |
| 2:30–3:15 | Interval explorer | “Here I can choose a delivery date, filter matched or missing records, sort the rows, and export the same selected date and status to CSV. Each row shows actual, eligible forecast, error, publication time, cutoff, and data status.” |
| 3:15–3:45 | Forecast history | “This view separates the interval's delivery start from each version's publication time. It marks versions as selected, eligible but superseded, or published after the cutoff. A forecast after the cutoff is excluded from the historical score.” |
| 3:45–4:10 | Data quality | “The data-quality view provides record counts, forecast coverage at the cutoff, missing data, ingestion details, and a downloadable report. Publication searches began 14 days before delivery, so completeness before that boundary has not been established.” |
| 4:10–4:25 | Close | “This analysis can help compare wind forecast performance. A complete procurement decision also needs demand, other generation, prices, and additional market information outside WindLens.” |

## Part 2: technical review (about 4 minutes)

| Time | Screen | Narration |
|---|---|---|
| 0:00–0:35 | Repository tree | “The React interface is in `frontend/`; the FastAPI service and analytical functions are in `backend/app/`; tests are in `backend/tests/`; and controlled ingestion is in `scripts/`.” |
| 0:35–1:10 | Data folders and report | “The source rows are from Elexon BMRS FUELHH filtered to WIND and WINDFOR. Raw records are kept separately from normalized CSVs. The report records request windows, record counts, and retrieval time.” |
| 1:10–1:55 | `core.py` and tests | “For each delivery start, the service constructs a timezone-aware 10:00 Europe/London day-ahead cutoff, compares exact publication instants in UTC, then selects the latest eligible version. A test covers timestamp strings with different UTC offsets.” |
| 1:55–2:35 | Metrics and metric tests | “Metrics use only finite matched actual/forecast pairs. Error is forecast minus actual. The tests use a hand-calculable fixture for MAE, RMSE, bias, and WAPE, and cover empty and zero-denominator cases.” |
| 2:35–3:10 | API docs and exports | “The API exposes summary, time series, daily accuracy, intervals, forecast versions, quality, and exports under `/api/v1`. Date and cutoff values are validated, and the matched CSV accepts the explorer's date and quality filters.” |
| 3:10–3:40 | Docker and CI files | “Docker Compose runs the API and frontend together. GitHub Actions runs backend lint/tests and frontend tests, lint, typechecking, and build. The checked local frontend build and test results are listed in the README.” |
| 3:40–4:15 | Deployment status and limitations | “The intended deployment is Vercel for the frontend and Render for the Docker API. The owner provided public URLs, but they could not be reached from the audit environment, so this recording must show live results only after the owner confirms both services, CORS, exports, and direct routes.” |
| 4:15–4:30 | Close | “The main remaining evidence gaps are a complete publication-history boundary check, public deployment verification, repository-owner anonymity, and the video upload itself.” |

## Recording checklist

- Confirm the deployed frontend, API health, summary, interval/history routes, CORS, and exports in a logged-out/private browser session.
- Compare the displayed cutoff, match count, coverage, and scores against the API and current CSVs before quoting values.
- Use the production URLs only after those checks succeed; otherwise label the screen as local and avoid implying a live deployment.
- Show the actual test/build output if discussing it. Do not show credentials, personal browser data, or environment files.
- Record customer and technical sections separately if that makes editing easier; keep the combined final video below ten minutes.
- Review audio, labels, timestamps, and all claims. Upload to YouTube as **Unlisted** only from the account owner's session, then verify playback and privacy settings.
- Add the final video URL to the submission form and README only after the upload is complete.
