# Architecture

```mermaid
flowchart LR
 E[Elexon BMRS API<br/>FUELHH + WINDFOR] --> I[Bounded ingestion script]
 I --> R[Raw JSON archive]
 I --> P[Validated processed CSVs]
 P --> S[FastAPI analytics and export API]
 S --> Q[TanStack Query]
 Q --> U[React + Recharts WindLens]
```

WindLens is a modular monolith with a separate data-ingestion pipeline. The dashboard does not fetch the full Elexon history every time someone opens a page. The ingestion script retrieves and validates the source data, keeps raw JSON for auditing, and writes processed CSVs. Data selection and metric calculations are separate from the FastAPI routes.

The API loads processed CSVs into a small in-process cache keyed by file modification time. Re-ingestion invalidates the cache. Changing the forecast cutoff recalculates selection from the cached versions. On hosts with ephemeral storage, set `DATA_DIR` to durable storage if files need to survive a fresh deployment.

FUELHH requests use settlement dates and the WIND fuel type. WINDFOR requests use publication-time windows no longer than seven days, and the returned raw records are retained. The analysis creates each expected half-hour UTC interval, calculates a cutoff in Europe/London for each delivery date, and selects the latest forecast published on or before that cutoff. It joins the selected forecast to actual generation by normalized UTC `startTime`.

The default 10:00 day-ahead cutoff is an assumption. Publication timestamps are parsed as timezone-aware instants and converted to UTC before comparison; source spellings remain in raw JSON. When conflicting rows share an interval and publication time, a stable sorted-JSON rule selects one; quality counts preserve evidence of the conflict. Metric functions return null when there are no samples or WAPE's denominator is zero.

The checked-in retrieval shows 30-minute actual records and 60-minute forecast delivery starts. The canonical accuracy sample contains the independently expected 744 hourly starts. It averages the two half-hour FUELHH MW values within each hour, and leaves an hourly actual missing if either source interval is absent. At the default cutoff, the cache has 1,488/1,488 actual records, 744/744 eligible hourly forecast starts, and 744/744 matched hourly pairs. The interval explorer uses hourly pairs; the actuals CSV preserves the half-hour records. The publication search begins 14 days before delivery; this boundary is not proof of complete historical publication history.
