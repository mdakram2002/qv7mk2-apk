"""Fetch January 2026 production measurements and build auditable CSVs."""
import asyncio
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.core import DEFAULT_CUTOFF, LONDON, cutoff_for, deduplicate_records, metrics, validate_measurement  # noqa: E402

API = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
RAW = ROOT / "data/raw"
OUT = ROOT / "data/processed"
META = ROOT / "data/metadata"


async def fetch(client: httpx.AsyncClient, dataset: str, params: dict) -> list[dict]:
    url = f"{API}/{dataset}"
    for attempt in range(5):
        try:
            response = await client.get(url, params=params, headers={"Accept": "application/json"})
            response.raise_for_status()
            payload = response.json()
            return payload.get("data", payload) if isinstance(payload, dict) else payload
        except (httpx.HTTPError, ValueError):
            if attempt == 4:
                raise
            await asyncio.sleep(0.5 * 2**attempt)


async def run():
    for folder in (RAW, OUT, META):
        folder.mkdir(parents=True, exist_ok=True)
    actual, forecasts = [], []
    counts = []
    async with httpx.AsyncClient(timeout=60, limits=httpx.Limits(max_connections=2)) as client:
        cursor = date(2026, 1, 1)
        while cursor < date(2026, 2, 1):
            end = min(cursor + timedelta(days=6), date(2026, 1, 31))
            rows = await fetch(client, "FUELHH", {"settlementDateFrom": cursor.isoformat(), "settlementDateTo": end.isoformat(), "fuelType": "WIND"})
            actual.extend(rows)
            counts.append({"dataset": "FUELHH", "from": cursor.isoformat(), "to": end.isoformat(), "count": len(rows)})
            cursor = end + timedelta(days=1)
        # WINDFOR supports publication-time filtering, with a documented 7-day maximum.
        # Start 14 days before delivery to include the full advertised day-ahead forecast horizon.
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

    # Use analytical default, preserving a row for every expected slot.
    slots = pd.date_range("2026-01-01", "2026-02-01", freq="30min", inclusive="left", tz="UTC")
    forecast_df["_start"] = pd.to_datetime(forecast_df.startTime, utc=True) if not forecast_df.empty else pd.Series(dtype="datetime64[ns, UTC]")
    matched = []
    for start in slots:
        actual_match = actual_df[pd.to_datetime(actual_df.startTime, utc=True) == start] if not actual_df.empty else pd.DataFrame()
        actual_val = actual_match.iloc[0].generation_mw if len(actual_match) else None
        local_date = start.tz_convert(LONDON).date()
        cutoff = cutoff_for(local_date, DEFAULT_CUTOFF)
        group = forecast_df[(forecast_df._start == start) & (pd.to_datetime(forecast_df.publishTime, utc=True) <= cutoff)] if not forecast_df.empty else pd.DataFrame()
        chosen = group.sort_values(["publishTime", "generation_mw"], kind="stable").iloc[-1] if not group.empty else None
        fval = float(chosen.generation_mw) if chosen is not None else None
        err = fval - float(actual_val) if fval is not None and actual_val is not None else None
        matched.append({"startTime": start.isoformat(), "decision_cutoff": cutoff.isoformat(), "selected_publishTime": chosen.publishTime if chosen is not None else None, "forecast_generation_mw": fval, "actual_generation_mw": float(actual_val) if actual_val is not None else None, "signed_error_mw": err, "absolute_error_mw": abs(err) if err is not None else None, "squared_error_mw": err**2 if err is not None else None, "percentage_error": err / float(actual_val) * 100 if err is not None and actual_val else None, "forecast_available_at_cutoff": chosen is not None, "data_quality_status": "matched" if err is not None else "missing_forecast" if actual_val is not None else "missing_actual"})
    matched_df = pd.DataFrame(matched)
    matched_df.to_csv(OUT / "matched_wind_january_2026.csv", index=False)
    daily = []
    matched_df["delivery_date"] = pd.to_datetime(matched_df.startTime, utc=True).dt.tz_convert(LONDON).dt.date.astype(str)
    for day, group in matched_df.groupby("delivery_date"):
        daily.append({"delivery_date": day, "expected_interval_count": len(group), "matched_interval_count": int(group.data_quality_status.eq("matched").sum()), "coverage_percent": float(group.data_quality_status.eq("matched").mean() * 100), **metrics(group)})
    pd.DataFrame(daily).to_csv(OUT / "daily_wind_accuracy_january_2026.csv", index=False)
    pd.DataFrame([{ "month": "2026-01", "expected_interval_count": len(matched_df), "matched_interval_count": int(matched_df.data_quality_status.eq("matched").sum()), "coverage_percent": float(matched_df.data_quality_status.eq("matched").mean() * 100), **metrics(matched_df)}]).to_csv(OUT / "monthly_wind_accuracy_january_2026.csv", index=False)
    report = {"status": "success", "retrieved_at": datetime.now(timezone.utc).isoformat(), "period": ["2026-01-01", "2026-02-01"], "cutoff_default": DEFAULT_CUTOFF, "cutoff_timezone": "Europe/London", "forecast_publish_search_start": "2025-12-18T00:00:00Z", "forecast_search_start_assumption": "14 days before delivery; includes available pre-delivery issue history", "request_counts": counts, "raw_actual_records": len(actual), "raw_forecast_records": len(forecasts), "actual_records": len(actual_df), "forecast_versions": len(forecast_df), "forecast_unique_delivery_starts": int(forecast_df.startTime.nunique()), "expected_intervals": len(matched_df), "quality": quality, "missing_actuals": int(matched_df.actual_generation_mw.isna().sum()), "missing_forecasts": int(matched_df.forecast_generation_mw.isna().sum()), "matched_intervals": int(matched_df.data_quality_status.eq("matched").sum()), "coverage_percent": float(matched_df.data_quality_status.eq("matched").mean() * 100), "forecast_resolution_note": "Retrieved WINDFOR records cover hourly delivery starts; alternate half-hour starts have no forecast row and are left missing."}
    (META / "ingestion_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(run())
