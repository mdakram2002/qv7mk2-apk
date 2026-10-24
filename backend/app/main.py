from datetime import date, datetime
import io
import json
import os
from typing import Literal

import pandas as pd
from fastapi import FastAPI, Query
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.core import DATA, DEFAULT_CUTOFF, LONDON, cutoff_for, load_csv, load_hourly_matched, metrics, select_versions

app = FastAPI(title="WindLens API", version="1.0.0", description="UK wind forecast accuracy analytics")
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:8080").split(",")]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET"], allow_headers=["*"])
PREFIX = "/api/v1"


class HealthResponse(BaseModel):
    status: str
    version: str
    ready: bool


class SummaryResponse(BaseModel):
    sample_count: int
    mae_mw: float | None
    rmse_mw: float | None
    bias_mw: float | None
    wape_percent: float | None
    expected_intervals: int
    matched_intervals: int
    coverage_percent: float | None
    expected_hourly_intervals: int
    eligible_forecast_intervals: int
    forecast_availability_percent: float | None
    hourly_actual_coverage_percent: float | None
    expected_actual_intervals: int
    actual_records_observed: int
    actual_coverage_percent: float | None
    missing_forecasts: int
    missing_hourly_actuals: int
    quality_counts: dict[str, int]


def validate_range(start_date: date, end_date: date):
    if start_date < date(2026, 1, 1) or end_date > date(2026, 2, 1) or start_date >= end_date:
        from fastapi import HTTPException
        raise HTTPException(422, "Date range must be within January 2026 and end_date must be later than start_date")


def in_date_range(df: pd.DataFrame, start_date: date, end_date: date):
    if df.empty:
        return df
    stamps = pd.to_datetime(df.startTime, utc=True).dt.tz_convert(LONDON).dt.date
    return df[(stamps >= start_date) & (stamps < end_date)].copy()


def selected(start_date: date, end_date: date, cutoff_time: str):
    validate_range(start_date, end_date)
    return in_date_range(load_hourly_matched(cutoff_time), start_date, end_date)


@app.get(PREFIX + "/health", response_model=HealthResponse)
def health():
    try:
        actual = load_csv("actual_wind_january_2026.csv")
        forecasts = load_csv("wind_forecast_versions_january_2026.csv")
        matched = load_csv("matched_wind_january_2026.csv")
        report_path = DATA.parent / "metadata" / "ingestion_report.json"
        report_ok = json.loads(report_path.read_text(encoding="utf-8")).get("status") == "success"
    except (OSError, ValueError, pd.errors.ParserError):
        report_ok = False
        actual = forecasts = matched = pd.DataFrame()
    ready = not actual.empty and not forecasts.empty and not matched.empty and report_ok
    return {"status": "ok", "version": app.version, "ready": ready}


@app.get(PREFIX + "/metadata")
def metadata():
    report = DATA.parent / "metadata" / "ingestion_report.json"
    return {"period": {"start": "2026-01-01", "end_exclusive": "2026-02-01"}, "timezone": "Europe/London", "cutoff_default": DEFAULT_CUTOFF, "sources": ["FUELHH", "WINDFOR"], "schema": {"time_fields": ["startTime", "publishTime"], "generation_field": "generation_mw", "generation_unit": "MW"}, "ingestion": json.loads(report.read_text()) if report.exists() else {"status": "not_ingested"}}


@app.get(PREFIX + "/summary", response_model=SummaryResponse)
def summary(start_date: date = date(2026, 1, 1), end_date: date = date(2026, 2, 1), cutoff_time: str = Query(DEFAULT_CUTOFF, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")):
    df = selected(start_date, end_date, cutoff_time)
    result = metrics(df)
    expected_hours = len(df)
    expected_actuals = (end_date - start_date).days * 48
    all_actuals = load_csv("actual_wind_january_2026.csv")
    actual_count = 0
    if not all_actuals.empty:
        all_actuals["startTime"] = pd.to_datetime(all_actuals.startTime, utc=True)
        stamps = all_actuals.startTime.dt.tz_convert(LONDON).dt.date
        actual_count = int(((stamps >= start_date) & (stamps < end_date)).sum())
    eligible = int(df.eligible_forecast_versions.gt(0).sum()) if not df.empty else 0
    hourly_actuals = int(df.actual_generation_mw.notna().sum()) if not df.empty else 0
    matched = result["sample_count"]
    return {
        **result,
        "expected_intervals": expected_hours,
        "matched_intervals": matched,
        "coverage_percent": matched / expected_hours * 100 if expected_hours else None,
        "expected_hourly_intervals": expected_hours,
        "eligible_forecast_intervals": eligible,
        "forecast_availability_percent": eligible / expected_hours * 100 if expected_hours else None,
        "hourly_actual_coverage_percent": hourly_actuals / expected_hours * 100 if expected_hours else None,
        "expected_actual_intervals": expected_actuals,
        "actual_records_observed": actual_count,
        "actual_coverage_percent": actual_count / expected_actuals * 100 if expected_actuals else None,
        "missing_forecasts": int(df.forecast_generation_mw.isna().sum()) if not df.empty else expected_hours,
        "missing_hourly_actuals": expected_hours - hourly_actuals,
        "quality_counts": df.data_quality_status.value_counts().to_dict() if not df.empty else {},
    }


@app.get(PREFIX + "/timeseries")
def timeseries(start_date: date = date(2026, 1, 1), end_date: date = date(2026, 2, 1), cutoff_time: str = Query(DEFAULT_CUTOFF, pattern=r"^([01]\d|2[0-3]):[0-5]\d$"), delivery_date: date | None = None):
    if delivery_date:
        start_date, end_date = delivery_date, date.fromordinal(delivery_date.toordinal() + 1)
    df = selected(start_date, end_date, cutoff_time)
    return df.astype(object).where(pd.notna(df), None).to_dict("records")


@app.get(PREFIX + "/accuracy/daily")
def daily(cutoff_time: str = Query(DEFAULT_CUTOFF, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")):
    df = load_hourly_matched(cutoff_time)
    if df.empty:
        return []
    df["delivery_date"] = pd.to_datetime(df.startTime, utc=True).dt.tz_convert(LONDON).dt.date.astype(str)
    rows = []
    for day, group in df.groupby("delivery_date"):
        result = metrics(group)
        rows.append({"delivery_date": day, "expected_interval_count": len(group), "matched_interval_count": result["sample_count"], "coverage_percent": result["sample_count"] / len(group) * 100 if len(group) else None, **result})
    return rows


@app.get(PREFIX + "/accuracy/monthly")
def monthly(cutoff_time: str = Query(DEFAULT_CUTOFF, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")):
    df = load_hourly_matched(cutoff_time)
    result = metrics(df)
    return {"month": "2026-01", "expected_interval_count": len(df), "matched_interval_count": result["sample_count"], "coverage_percent": result["sample_count"] / len(df) * 100 if len(df) else None, **result}


@app.get(PREFIX + "/intervals")
def intervals(start_date: date = date(2026, 1, 1), end_date: date = date(2026, 2, 1), cutoff_time: str = Query(DEFAULT_CUTOFF, pattern=r"^([01]\d|2[0-3]):[0-5]\d$"), page: int = Query(1, ge=1), page_size: int = Query(48, ge=1, le=500), quality_status: Literal["matched", "missing_forecast", "missing_actual"] | None = None, sort_by: Literal["startTime", "forecast_generation_mw", "actual_generation_mw", "signed_error_mw", "absolute_error_mw", "selected_publishTime"] = "startTime", sort_order: Literal["asc", "desc"] = "asc"):
    df = selected(start_date, end_date, cutoff_time)
    if quality_status:
        df = df[df.data_quality_status == quality_status]
    df = df.sort_values(sort_by, ascending=sort_order == "asc", na_position="last")
    items = df.iloc[(page-1)*page_size:page*page_size].astype(object).where(pd.notna(df.iloc[(page-1)*page_size:page*page_size]), None)
    return {"page": page, "page_size": page_size, "total": len(df), "items": items.to_dict("records")}


@app.get(PREFIX + "/forecast-versions")
def forecast_versions(start_time: datetime, cutoff_time: str = Query(DEFAULT_CUTOFF, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")):
    if start_time.tzinfo is None:
        from fastapi import HTTPException
        raise HTTPException(422, "start_time must include a timezone")
    start = pd.Timestamp(start_time).tz_convert("UTC")

    if start < pd.Timestamp("2026-01-01", tz="UTC") or start >= pd.Timestamp("2026-02-01", tz="UTC"):
        from fastapi import HTTPException
        raise HTTPException(422, "start_time must fall within January 2026")
    forecasts = load_csv("wind_forecast_versions_january_2026.csv")

    if forecasts.empty:
        return {"startTime": start.isoformat(), "decision_cutoff": cutoff_for(start.tz_convert(LONDON).date(), cutoff_time).isoformat(), "eligible_version_count": 0, "selection_status": "missing_eligible_forecast", "versions": [], "status": "not_ingested"}
    forecasts["startTime"] = pd.to_datetime(forecasts.startTime, utc=True)
    group = forecasts[forecasts.startTime == start]
    delivery = start.tz_convert(LONDON).date()
    cutoff = cutoff_for(delivery, cutoff_time)
    version_rows = group.to_dict("records")
    chosen, eligible_versions = select_versions(version_rows, cutoff)
    actuals = load_csv("actual_wind_january_2026.csv")
    actuals["startTime"] = pd.to_datetime(actuals.startTime, utc=True) if not actuals.empty else pd.Series(dtype="datetime64[ns, UTC]")
    hour_actuals = actuals[actuals.startTime.isin([start, start + pd.Timedelta(minutes=30)])] if not actuals.empty else pd.DataFrame()
    actual = float(hour_actuals.generation_mw.mean()) if len(hour_actuals) == 2 else None
    versions = []

    for row in sorted(version_rows, key=lambda item: (pd.Timestamp(item["publishTime"]).tz_convert("UTC"), json.dumps(item, sort_keys=True, default=str))):
        eligible = pd.Timestamp(row["publishTime"]).tz_convert("UTC").to_pydatetime() <= cutoff
        is_selected = bool(chosen and row["publishTime"] == chosen["publishTime"] and row["generation_mw"] == chosen["generation_mw"])
        versions.append({**row, "startTime": start.isoformat(), "eligible": eligible, "selected": is_selected, "actual_generation_mw": actual, "reason": "selected latest eligible" if is_selected else "eligible, superseded by a later eligible version" if eligible else "published after decision cutoff"})
    return {"startTime": start.isoformat(), "decision_cutoff": cutoff.isoformat(), "eligible_version_count": len(eligible_versions), "selection_status": "selected_latest_eligible" if chosen else "missing_eligible_forecast", "versions": versions}


@app.get(PREFIX + "/data-quality")
def quality(cutoff_time: str = Query(DEFAULT_CUTOFF, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")):
    p = DATA.parent / "metadata" / "ingestion_report.json"
    report = json.loads(p.read_text()) if p.exists() else {"status": "not_ingested", "sources": ["FUELHH", "WINDFOR"]}
    matched = load_hourly_matched(cutoff_time)
    counts = matched.data_quality_status.value_counts().to_dict() if not matched.empty else {}
    eligible_starts = int(matched.loc[matched.eligible_forecast_versions > 0, "startTime"].nunique()) if not matched.empty else 0
    matched_count = int(counts.get("matched", 0))
    expected_count = len(matched)
    actuals = load_csv("actual_wind_january_2026.csv")
    forecasts = load_csv("wind_forecast_versions_january_2026.csv")
    expected_actual_count = 1488
    observed_actual_count = int(actuals.startTime.nunique()) if not actuals.empty else 0
    quality_counts = report.get("quality", {})
    return {
        **report,
        "cutoff_time": cutoff_time,
        "expected_actual_intervals": expected_actual_count,
        "actual_records_observed": observed_actual_count,
        "actual_coverage_percent": observed_actual_count / expected_actual_count * 100,
        "expected_hourly_delivery_starts": expected_count,
        "expected_intervals": expected_count,
        "coverage_denominator": "expected hourly delivery starts",
        "forecast_versions": len(forecasts),
        "forecast_delivery_starts_observed": int(forecasts.startTime.nunique()) if not forecasts.empty else 0,
        "eligible_forecast_delivery_intervals": eligible_starts,
        "forecast_availability_percent": eligible_starts / expected_count * 100 if expected_count else None,
        "matched_intervals_at_cutoff": matched_count,
        "coverage_percent": matched_count / expected_count * 100 if expected_count else None,
        "matched_hourly_coverage_percent": matched_count / expected_count * 100 if expected_count else None,
        "missing_forecasts_at_cutoff": int(counts.get("missing_forecast", 0)),
        "missing_actuals": expected_actual_count - observed_actual_count,
        "missing_hourly_actuals": int(counts.get("missing_actual", 0)),
        "invalid_source_records": int(quality_counts.get("invalid_records", 0)),
        "cache_status": "processed CSV cache; invalidated by file modification time",
        "resolution_method": "WINDFOR is hourly; FUELHH actual MW is averaged from the two half-hour records for each hour. An hourly actual is unavailable unless both half-hour records exist.",
        "forecast_resolution_note": "Metrics compare hourly WINDFOR starts against actual MW averaged from the matching pair of half-hour FUELHH records.",
    }


def csv_download(filename: str, data: pd.DataFrame):
    for column in data.select_dtypes(include=["object", "string"]).columns:
        data[column] = data[column].map(lambda value: "'" + value if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")) else value)
    buffer = io.StringIO()
    data.to_csv(buffer, index=False)
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.get(PREFIX + "/export/actuals.csv")
def export_actuals(): return csv_download("actuals.csv", load_csv("actual_wind_january_2026.csv"))
@app.get(PREFIX + "/export/forecasts.csv")
def export_forecasts(): return csv_download("forecasts.csv", load_csv("wind_forecast_versions_january_2026.csv"))
@app.get(PREFIX + "/export/matched.csv")
def export_matched(start_date: date = date(2026, 1, 1), end_date: date = date(2026, 2, 1), cutoff_time: str = Query(DEFAULT_CUTOFF, pattern=r"^([01]\d|2[0-3]):[0-5]\d$"), quality_status: Literal["matched", "missing_forecast", "missing_actual"] | None = None):
    df = selected(start_date, end_date, cutoff_time)
    if quality_status:
        df = df[df.data_quality_status == quality_status]
    return csv_download("matched.csv", df)
@app.get(PREFIX + "/export/daily-accuracy.csv")
def export_daily(cutoff_time: str = Query(DEFAULT_CUTOFF, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")): return csv_download("daily-accuracy.csv", pd.DataFrame(daily(cutoff_time)))
@app.get(PREFIX + "/export/hourly-matched.csv")
def export_hourly_matched(start_date: date = date(2026, 1, 1), end_date: date = date(2026, 2, 1), cutoff_time: str = Query(DEFAULT_CUTOFF, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")):
    return csv_download("hourly-matched.csv", selected(start_date, end_date, cutoff_time))
@app.get(PREFIX + "/export/ingestion-report.json")
def export_report(cutoff_time: str = Query(DEFAULT_CUTOFF, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")):
    report = json.dumps(quality(cutoff_time), indent=2)
    return StreamingResponse(iter([report]), media_type="application/json", headers={"Content-Disposition": 'attachment; filename="ingestion-report.json"'})
