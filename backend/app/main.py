from datetime import date
import io
import json
import os
from pathlib import Path
from typing import Literal

import pandas as pd
from fastapi import FastAPI, Query
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.core import DATA, DEFAULT_CUTOFF, LONDON, cutoff_for, load_csv, load_matched, metrics, select_versions

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
    quality_counts: dict[str, int]


def selected(start_date: date, end_date: date, cutoff_time: str):
    if start_date < date(2026, 1, 1) or end_date > date(2026, 2, 1) or start_date >= end_date:
        from fastapi import HTTPException
        raise HTTPException(422, "Date range must be within January 2026 and end_date must be later than start_date")
    df = load_matched(cutoff_time)
    if df.empty:
        return df
    stamps = pd.to_datetime(df.startTime, utc=True).dt.tz_convert(LONDON).dt.date
    return df[(stamps >= start_date) & (stamps < end_date)].copy()


@app.get(PREFIX + "/health", response_model=HealthResponse)
def health():
    ready = (DATA / "actual_wind_january_2026.csv").exists() and (DATA / "wind_forecast_versions_january_2026.csv").exists()
    return {"status": "ok", "version": app.version, "ready": ready}


@app.get(PREFIX + "/metadata")
def metadata():
    report = Path("data/metadata/ingestion_report.json")
    return {"period": {"start": "2026-01-01", "end_exclusive": "2026-02-01"}, "timezone": "Europe/London", "cutoff_default": DEFAULT_CUTOFF, "sources": ["FUELHH", "WINDFOR"], "schema": {"time_fields": ["startTime", "publishTime"], "generation_field": "generation_mw", "generation_unit": "MW"}, "ingestion": json.loads(report.read_text()) if report.exists() else {"status": "not_ingested"}}


@app.get(PREFIX + "/summary", response_model=SummaryResponse)
def summary(start_date: date = date(2026, 1, 1), end_date: date = date(2026, 2, 1), cutoff_time: str = Query(DEFAULT_CUTOFF, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")):
    df = selected(start_date, end_date, cutoff_time)
    return {**metrics(df), "expected_intervals": len(df) if not df.empty else (end_date - start_date).days * 48, "matched_intervals": metrics(df)["sample_count"], "coverage_percent": metrics(df)["sample_count"] / (len(df) or 1) * 100 if not df.empty else None, "quality_counts": df.data_quality_status.value_counts().to_dict() if not df.empty else {}}


@app.get(PREFIX + "/timeseries")
def timeseries(start_date: date = date(2026, 1, 1), end_date: date = date(2026, 2, 1), cutoff_time: str = Query(DEFAULT_CUTOFF, pattern=r"^([01]\d|2[0-3]):[0-5]\d$"), delivery_date: date | None = None):
    if delivery_date:
        start_date, end_date = delivery_date, date.fromordinal(delivery_date.toordinal() + 1)
    df = selected(start_date, end_date, cutoff_time)
    return df.astype(object).where(pd.notna(df), None).to_dict("records")


@app.get(PREFIX + "/accuracy/daily")
def daily(cutoff_time: str = Query(DEFAULT_CUTOFF, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")):
    df = load_matched(cutoff_time)
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
    df = load_matched(cutoff_time)
    result = metrics(df)
    return {"month": "2026-01", "expected_interval_count": len(df), "matched_interval_count": result["sample_count"], "coverage_percent": result["sample_count"] / len(df) * 100 if len(df) else None, **result}


@app.get(PREFIX + "/intervals")
def intervals(start_date: date = date(2026, 1, 1), end_date: date = date(2026, 2, 1), cutoff_time: str = Query(DEFAULT_CUTOFF, pattern=r"^([01]\d|2[0-3]):[0-5]\d$"), page: int = Query(1, ge=1), page_size: int = Query(48, ge=1, le=500), quality_status: str | None = None, sort_by: Literal["startTime", "forecast_generation_mw", "actual_generation_mw", "signed_error_mw", "absolute_error_mw", "selected_publishTime"] = "startTime", sort_order: Literal["asc", "desc"] = "asc"):
    df = selected(start_date, end_date, cutoff_time)
    if quality_status:
        df = df[df.data_quality_status == quality_status]
    df = df.sort_values(sort_by, ascending=sort_order == "asc", na_position="last")
    items = df.iloc[(page-1)*page_size:page*page_size].astype(object).where(pd.notna(df.iloc[(page-1)*page_size:page*page_size]), None)
    return {"page": page, "page_size": page_size, "total": len(df), "items": items.to_dict("records")}


@app.get(PREFIX + "/forecast-versions")
def forecast_versions(start_time: str, cutoff_time: str = Query(DEFAULT_CUTOFF, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")):
    forecasts = load_csv("wind_forecast_versions_january_2026.csv")
    if forecasts.empty:
        return {"versions": [], "status": "not_ingested"}
    forecasts["startTime"] = pd.to_datetime(forecasts.startTime, utc=True)
    group = forecasts[forecasts.startTime == pd.Timestamp(start_time)]
    delivery = pd.Timestamp(start_time).tz_convert(LONDON).date()
    cutoff = cutoff_for(delivery, cutoff_time)
    version_rows = group.to_dict("records")
    chosen, _ = select_versions(version_rows, cutoff)
    actuals = load_csv("actual_wind_january_2026.csv")
    actuals["startTime"] = pd.to_datetime(actuals.startTime, utc=True) if not actuals.empty else pd.Series(dtype="datetime64[ns, UTC]")
    actual = actuals[actuals.startTime == pd.Timestamp(start_time)].generation_mw.iloc[0] if not actuals.empty and (actuals.startTime == pd.Timestamp(start_time)).any() else None
    versions = []
    for row in sorted(version_rows, key=lambda item: (item["publishTime"], item["generation_mw"])):
        eligible = pd.Timestamp(row["publishTime"]).to_pydatetime() <= cutoff
        is_selected = bool(chosen and row["publishTime"] == chosen["publishTime"] and row["generation_mw"] == chosen["generation_mw"])
        versions.append({**row, "eligible": eligible, "selected": is_selected, "actual_generation_mw": actual, "reason": "selected latest eligible" if is_selected else "eligible, superseded by a later eligible version" if eligible else "published after decision cutoff"})
    return {"decision_cutoff": cutoff.isoformat(), "versions": versions}


@app.get(PREFIX + "/data-quality")
def quality():
    p = Path("data/metadata/ingestion_report.json")
    report = json.loads(p.read_text()) if p.exists() else {"status": "not_ingested", "sources": ["FUELHH", "WINDFOR"]}
    return {**report, "cache_status": "processed CSV cache; invalidated by file modification time"}


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
def export_matched(cutoff_time: str = DEFAULT_CUTOFF): return csv_download("matched.csv", load_matched(cutoff_time))
@app.get(PREFIX + "/export/daily-accuracy.csv")
def export_daily(cutoff_time: str = Query(DEFAULT_CUTOFF, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")): return csv_download("daily-accuracy.csv", pd.DataFrame(daily(cutoff_time)))
@app.get(PREFIX + "/export/ingestion-report.json")
def export_report():
    path = Path("data/metadata/ingestion_report.json")
    return StreamingResponse(iter([path.read_text() if path.exists() else "{}"]), media_type="application/json", headers={"Content-Disposition": 'attachment; filename="ingestion-report.json"'})
