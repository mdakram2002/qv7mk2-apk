"""Fetch January 2026 production measurements and build auditable CSVs."""
import asyncio
import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.core import DEFAULT_CUTOFF, LONDON, aggregate_actuals_hourly, cutoff_for, deduplicate_records, metrics, select_versions, validate_measurement  # noqa: E402

API = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
RAW = ROOT / "data/raw"
OUT = ROOT / "data/processed"
META = ROOT / "data/metadata"


async def fetch(client: httpx.AsyncClient, dataset: str, params: dict) -> list[dict]:
    url = f"{API}/{dataset}/stream"
    for attempt in range(5):
        try:
            response = await client.get(url, params=params, headers={"Accept": "application/json"})
            if response.is_error:
                excerpt = response.text[:400].replace("\n", " ")
                print(f"Elexon request failed: url={response.url} status={response.status_code} content_type={response.headers.get('content-type')} body={excerpt}", file=sys.stderr)
                if response.status_code != 429 and response.status_code < 500:
                    response.raise_for_status()
                if attempt == 4:
                    response.raise_for_status()
                retry_after = response.headers.get("Retry-After")
                await asyncio.sleep(float(retry_after) if retry_after and retry_after.isdigit() else 0.5 * 2**attempt)
                continue
            try:
                payload = response.json()
            except ValueError:
                excerpt = response.text[:400].replace("\n", " ")
                raise ValueError(f"Malformed JSON from {response.url}; status={response.status_code}; content_type={response.headers.get('content-type')}; body={excerpt}") from None
            rows = payload.get("data", payload) if isinstance(payload, dict) else payload
            if not isinstance(rows, list):
                raise ValueError(f"Unexpected {dataset} response shape at {response.url}: {type(rows).__name__}")
            if isinstance(payload, dict) and any(key in payload for key in ("next", "nextPage", "nextPageToken", "continuationToken")):
                raise ValueError(f"{dataset} response indicates pagination that this ingester does not implement: {response.url}")
            return rows
        except httpx.RequestError as error:
            print(f"Elexon transport error: url={url} error={error}", file=sys.stderr)
            if attempt == 4:
                raise
            await asyncio.sleep(0.5 * 2**attempt)


async def run(from_cache: bool = False):
    for folder in (RAW, OUT, META):
        folder.mkdir(parents=True, exist_ok=True)
    actual, forecasts = [], []
    prior_report_path = META / "ingestion_report.json"
    prior_report = json.loads(prior_report_path.read_text(encoding="utf-8")) if prior_report_path.exists() else {}
    counts = []
    if from_cache:
        actual = json.loads((RAW / "fuelhh_wind_january_2026.json").read_text(encoding="utf-8"))
        forecasts = json.loads((RAW / "windfor_january_2026.json").read_text(encoding="utf-8"))
        if not isinstance(actual, list) or not isinstance(forecasts, list) or not actual or not forecasts:
            raise ValueError("Cached raw source files must be non-empty JSON arrays")
        counts = prior_report.get("request_counts", [])
        print(f"Rebuilding from cached raw responses: FUELHH={len(actual)}, WINDFOR={len(forecasts)}; no API request made.")
    else:
        async with httpx.AsyncClient(timeout=60, limits=httpx.Limits(max_connections=2)) as client:
            cursor = date(2026, 1, 1)
            while cursor < date(2026, 2, 1):
                end = min(cursor + timedelta(days=6), date(2026, 1, 31))
                rows = await fetch(client, "FUELHH", {"settlementDateFrom": cursor.isoformat(), "settlementDateTo": end.isoformat(), "fuelType": "WIND"})
                actual.extend(rows)
                counts.append({"dataset": "FUELHH", "from": cursor.isoformat(), "to": end.isoformat(), "count": len(rows)})
                cursor = end + timedelta(days=1)
            # Publication range is partitioned into <=7-day requests.
            cursor_dt = datetime(2025, 12, 18, tzinfo=timezone.utc)
            finish = datetime(2026, 2, 1, tzinfo=timezone.utc)
            while cursor_dt < finish:
                end_dt = min(cursor_dt + timedelta(days=6, hours=23, minutes=59, seconds=59), finish)
                rows = await fetch(client, "WINDFOR", {"publishDateTimeFrom": cursor_dt.isoformat().replace("+00:00", "Z"), "publishDateTimeTo": end_dt.isoformat().replace("+00:00", "Z")})
                forecasts.extend(rows)
                counts.append({"dataset": "WINDFOR", "from": cursor_dt.isoformat(), "to": end_dt.isoformat(), "count": len(rows)})
                cursor_dt = end_dt + timedelta(seconds=1)
    (RAW / "fuelhh_wind_january_2026.json").write_text(json.dumps(actual, indent=2), encoding="utf-8")
    (RAW / "windfor_january_2026.json").write_text(json.dumps(forecasts, indent=2), encoding="utf-8")

    actual_rows, quality = [], {"actual_exact_duplicates": 0, "actual_conflicts": 0, "forecast_exact_duplicates": 0, "forecast_conflicts": 0, "invalid_records": 0, "invalid_record_reasons": {}, "forecast_records_outside_delivery_period": 0}
    for r in actual:
        if r.get("fuelType") != "WIND":
            continue
        try:
            invalid = validate_measurement(r)
            if invalid:
                quality["invalid_records"] += 1
                quality["invalid_record_reasons"][invalid] = quality["invalid_record_reasons"].get(invalid, 0) + 1
                continue
            stamp, value = pd.Timestamp(r["startTime"]), float(r["generation"])
            actual_rows.append({"startTime": stamp.tz_convert("UTC").isoformat(), "settlementDate": r.get("settlementDate"), "settlementPeriod": r.get("settlementPeriod"), "generation_mw": value, "source_dataset": "FUELHH"})
        except (KeyError, ValueError, TypeError):
            quality["invalid_records"] += 1
            quality["invalid_record_reasons"]["invalid_record"] = quality["invalid_record_reasons"].get("invalid_record", 0) + 1
    unique_actuals, quality["actual_exact_duplicates"], quality["actual_conflicts"] = deduplicate_records(actual_rows, ("startTime",))
    quality["actual_duplicates"] = quality["actual_exact_duplicates"] + quality["actual_conflicts"]
    actual_df = pd.DataFrame(unique_actuals, columns=["startTime", "settlementDate", "settlementPeriod", "generation_mw", "source_dataset"]).sort_values("startTime")
    actual_df.to_csv(OUT / "actual_wind_january_2026.csv", index=False)

    forecast_candidates = []
    for r in forecasts:
        try:
            invalid = validate_measurement(r, forecast=True)
            if invalid:
                quality["invalid_records"] += 1
                quality["invalid_record_reasons"][invalid] = quality["invalid_record_reasons"].get(invalid, 0) + 1
                continue
            start, pub, value = pd.Timestamp(r["startTime"]), pd.Timestamp(r["publishTime"]), float(r["generation"])
            if start < pd.Timestamp("2026-01-01", tz="UTC") or start >= pd.Timestamp("2026-02-01", tz="UTC"):
                quality["forecast_records_outside_delivery_period"] += 1
                continue
            row = {"startTime": start.tz_convert("UTC").isoformat(), "publishTime": pub.tz_convert("UTC").isoformat(), "generation_mw": value, "source_dataset": "WINDFOR"}
            forecast_candidates.append(row)
        except (KeyError, ValueError, TypeError):
            quality["invalid_records"] += 1
            quality["invalid_record_reasons"]["invalid_record"] = quality["invalid_record_reasons"].get("invalid_record", 0) + 1
    forecast_rows, quality["forecast_exact_duplicates"], quality["forecast_conflicts"] = deduplicate_records(forecast_candidates, ("startTime", "publishTime"))
    forecast_df = pd.DataFrame(forecast_rows, columns=["startTime", "publishTime", "generation_mw", "source_dataset"]).sort_values(["startTime", "publishTime"])
    forecast_df.to_csv(OUT / "wind_forecast_versions_january_2026.csv", index=False)

    # Canonical scores use hourly forecasts and means of the matching half-hour actuals.
    slots = pd.date_range("2026-01-01T00:00:00Z", periods=744, freq="h")
    actual_by_hour = aggregate_actuals_hourly(actual_df, slots)
    forecast_df["_start"] = pd.to_datetime(forecast_df.startTime, utc=True) if not forecast_df.empty else pd.Series(dtype="datetime64[ns, UTC]")
    matched = []
    for start in slots:
        actual_val = actual_by_hour.at[start, "actual_generation_mw"]
        actual_count = int(actual_by_hour.at[start, "actual_half_hour_count"])
        cutoff = cutoff_for(start.tz_convert(LONDON).date(), DEFAULT_CUTOFF)
        group = forecast_df[forecast_df._start == start] if not forecast_df.empty else pd.DataFrame()
        chosen, eligible = select_versions(group.to_dict("records"), cutoff)
        fval = float(chosen["generation_mw"]) if chosen is not None else None
        pub = chosen["publishTime"] if chosen is not None else None
        err = fval - float(actual_val) if fval is not None and pd.notna(actual_val) else None
        matched.append({"startTime": start.isoformat(), "decision_cutoff": cutoff.isoformat(), "actual_half_hour_count": actual_count, "eligible_forecast_versions": len(eligible), "selection_status": "selected_latest_eligible" if chosen is not None else "missing_eligible_forecast", "selection_reason": "latest retrieved version published by the decision cutoff" if chosen is not None else "no retrieved forecast was published by the decision cutoff", "selected_publishTime": pub, "forecast_generation_mw": fval, "actual_generation_mw": float(actual_val) if pd.notna(actual_val) else None, "signed_error_mw": err, "absolute_error_mw": abs(err) if err is not None else None, "squared_error_mw": err**2 if err is not None else None, "percentage_error": err / float(actual_val) * 100 if err is not None and actual_val else None, "forecast_available_at_cutoff": chosen is not None, "data_quality_status": "matched" if err is not None else "missing_forecast" if pd.notna(actual_val) else "missing_actual"})
    matched_df = pd.DataFrame(matched)
    matched_df.to_csv(OUT / "matched_wind_january_2026.csv", index=False)
    daily = []
    matched_df["delivery_date"] = pd.to_datetime(matched_df.startTime, utc=True).dt.tz_convert(LONDON).dt.date.astype(str)
    for day, group in matched_df.groupby("delivery_date"):
        daily.append({"delivery_date": day, "expected_interval_count": len(group), "matched_interval_count": int(group.data_quality_status.eq("matched").sum()), "coverage_percent": float(group.data_quality_status.eq("matched").mean() * 100), **metrics(group)})
    pd.DataFrame(daily).to_csv(OUT / "daily_wind_accuracy_january_2026.csv", index=False)
    pd.DataFrame([{ "month": "2026-01", "expected_interval_count": len(matched_df), "matched_interval_count": int(matched_df.data_quality_status.eq("matched").sum()), "coverage_percent": float(matched_df.data_quality_status.eq("matched").mean() * 100), **metrics(matched_df)}]).to_csv(OUT / "monthly_wind_accuracy_january_2026.csv", index=False)
    actual_steps = pd.to_datetime(actual_df.startTime, utc=True).drop_duplicates().sort_values().diff().dropna().dt.total_seconds().div(60) if not actual_df.empty else pd.Series(dtype=float)
    forecast_steps = pd.to_datetime(forecast_df.startTime, utc=True).drop_duplicates().sort_values().diff().dropna().dt.total_seconds().div(60) if not forecast_df.empty else pd.Series(dtype=float)
    if not forecast_df.empty:
        forecast_df["_start"] = pd.to_datetime(forecast_df.startTime, utc=True)
        forecast_df["_publish"] = pd.to_datetime(forecast_df.publishTime, utc=True)
        positive_leads = (forecast_df._start - forecast_df._publish).dt.total_seconds().div(3600)
        earliest_january_publish = forecast_df._publish.min().isoformat()
        max_observed_forecast_lead_hours = float(positive_leads[positive_leads >= 0].max()) if positive_leads.ge(0).any() else None
    else:
        earliest_january_publish = None
        max_observed_forecast_lead_hours = None
    warnings = ["Forecast publication search began 2025-12-18; the earliest returned January-delivery version was published 2025-12-30, and the maximum observed lead was 66.5 hours. Older source-history completeness before the search boundary is not independently established."]
    if len(actual_df) != len(slots) * 2:
        warnings.append("Retrieved actual record count differs from the expected half-hour interval count.")
    if matched_df.actual_generation_mw.notna().sum() != len(slots):
        warnings.append("Some hourly actuals could not be formed from both half-hour FUELHH records.")
    if matched_df.forecast_generation_mw.notna().sum() != len(slots):
        warnings.append("Some hourly delivery starts have no eligible WINDFOR version at the cutoff.")
    report = {
        "status": "success",
        "retrieved_at": prior_report.get("retrieved_at") if from_cache else datetime.now(timezone.utc).isoformat(),
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "retrieval_mode": "validated_committed_raw_cache" if from_cache else "live_elexon_api",
        "period": ["2026-01-01", "2026-02-01"],
        "sources": {
            "actuals": {"endpoint": f"{API}/FUELHH" if from_cache else f"{API}/FUELHH/stream", "filters": {"fuelType": "WIND", "settlementDateFrom": "2026-01-01", "settlementDateTo": "2026-01-31"}},
            "forecasts": {"endpoint": f"{API}/WINDFOR" if from_cache else f"{API}/WINDFOR/stream", "filters": {"publishDateTimeFrom": "2025-12-18T00:00:00Z", "publishDateTimeTo": "2026-02-01T00:00:00Z"}},
        },
        "cutoff_default": DEFAULT_CUTOFF,
        "cutoff_timezone": "Europe/London",
        "forecast_publish_search_start": "2025-12-18T00:00:00Z",
        "forecast_search_start_assumption": "Search began 14 days before the delivery month and extends beyond the longest observed 66.5-hour forecast lead; it does not prove older archive completeness.",
        "earliest_retrieved_january_delivery_publish_time": earliest_january_publish,
        "max_observed_january_forecast_lead_hours": max_observed_forecast_lead_hours,
        "request_counts": counts,
        "raw_actual_records": len(actual),
        "raw_forecast_records": len(forecasts),
        "actual_records": len(actual_df),
        "forecast_versions": len(forecast_df),
        "forecast_unique_delivery_starts": int(forecast_df.startTime.nunique()),
        "actual_resolution_minutes_observed": int(actual_steps.mode().iloc[0]) if not actual_steps.empty else None,
        "forecast_resolution_minutes_observed": int(forecast_steps.mode().iloc[0]) if not forecast_steps.empty else None,
        "expected_actual_intervals": len(slots) * 2,
        "expected_hourly_intervals": len(slots),
        "quality": quality,
        "actual_records_observed": int(actual_df.startTime.nunique()),
        "actual_coverage_percent": float(actual_df.startTime.nunique() / (len(slots) * 2) * 100),
        "hourly_actuals_available": int(matched_df.actual_generation_mw.notna().sum()),
        "missing_actuals": int(len(slots) * 2 - actual_df.startTime.nunique()),
        "missing_hourly_actuals": int(matched_df.actual_generation_mw.isna().sum()),
        "missing_forecasts": int(matched_df.forecast_generation_mw.isna().sum()),
        "matched_intervals": int(matched_df.data_quality_status.eq("matched").sum()),
        "coverage_percent": float(matched_df.data_quality_status.eq("matched").mean() * 100),
        "eligible_forecast_delivery_starts": int(matched_df.forecast_available_at_cutoff.sum()),
        "forecast_availability_percent": float(matched_df.forecast_available_at_cutoff.mean() * 100),
        "matched_coverage_denominator": "expected hourly delivery starts",
        "actual_aggregation": "Mean MW from the two FUELHH half-hour intervals starting in each hour; incomplete hours remain missing.",
        "forecast_resolution_note": "Observed WINDFOR delivery starts are hourly; metrics compare them with hourly actual MW averaged from both corresponding half-hour FUELHH records.",
        "warnings": warnings,
    }
    (META / "ingestion_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-cache", action="store_true", help="Revalidate committed raw JSON and rebuild processed files without network requests")
    asyncio.run(run(from_cache=parser.parse_args().from_cache))
