from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
import json
import os
from functools import lru_cache
import math
from pathlib import Path

import pandas as pd
LONDON = ZoneInfo("Europe/London")
DATA = Path(os.getenv("DATA_DIR", "data/processed"))
DEFAULT_CUTOFF = os.getenv("DEFAULT_CUTOFF", "10:00")


def cutoff_for(delivery_date: date, cutoff_time: str = DEFAULT_CUTOFF) -> datetime:
    hour, minute = map(int, cutoff_time.split(":"))
    return datetime.combine(delivery_date - timedelta(days=1), time(hour, minute), LONDON).astimezone(timezone.utc)


def select_versions(versions: list[dict], cutoff: datetime) -> tuple[dict | None, list[dict]]:
    """Return eligible versions ordered by their actual instant, with a stable tie break."""
    cutoff_utc = pd.Timestamp(cutoff)
    if cutoff_utc.tzinfo is None:
        raise ValueError("cutoff must be timezone-aware")
    cutoff_utc = cutoff_utc.tz_convert("UTC")

    def published_at(row: dict) -> pd.Timestamp:
        value = pd.Timestamp(row["publishTime"])
        if value.tzinfo is None:
            raise ValueError("publishTime must be timezone-aware")
        return value.tz_convert("UTC")

    eligible = [v for v in versions if published_at(v) <= cutoff_utc]
    eligible.sort(key=lambda v: (published_at(v), json.dumps(v, sort_keys=True, default=str)))
    return (eligible[-1] if eligible else None), eligible


def deduplicate_records(records: list[dict], key_fields: tuple[str, ...]) -> tuple[list[dict], int, int]:
    """Collapse exact repeats; resolve conflicting keys deterministically and count them."""
    kept: dict[tuple, dict] = {}
    exact = conflicts = 0
    for record in records:
        key = tuple(record.get(field) for field in key_fields)
        previous = kept.get(key)
        if previous is None:
            kept[key] = record
        elif previous == record:
            exact += 1
        else:
            conflicts += 1
            if json.dumps(record, sort_keys=True) > json.dumps(previous, sort_keys=True):
                kept[key] = record
    return list(kept.values()), exact, conflicts


def validate_measurement(record: dict, *, forecast: bool = False) -> str | None:
    """Return a concise quality error, preserving zero as a valid measurement."""
    required = ("startTime", "publishTime", "generation") if forecast else ("startTime", "generation", "fuelType")
    if any(record.get(field) is None for field in required):
        return "missing_required_field"
    try:
        start = pd.Timestamp(record["startTime"])
        if start.tzinfo is None:
            return "naive_start_time"
        if forecast and pd.Timestamp(record["publishTime"]).tzinfo is None:
            return "naive_publish_time"
        value = float(record["generation"])
        if not math.isfinite(value):
            return "invalid_generation"
        if value < 0:
            return "negative_generation"
    except (TypeError, ValueError, KeyError):
        return "invalid_record"
    return None


def match_records(actuals: list[dict], forecasts: list[dict], delivery_date: date, cutoff_time: str = DEFAULT_CUTOFF) -> list[dict]:
    """Join one delivery date by normalized UTC startTime and apply cutoff selection."""
    actual_by_start = {pd.Timestamp(row["startTime"]).tz_convert("UTC"): row for row in actuals}
    grouped: dict[pd.Timestamp, list[dict]] = {}
    for row in forecasts:
        start = pd.Timestamp(row["startTime"]).tz_convert("UTC")
        grouped.setdefault(start, []).append(row)
    rows = []
    first = pd.Timestamp(datetime.combine(delivery_date, time.min, LONDON)).tz_convert("UTC")
    for start in pd.date_range(first, periods=48, freq="30min"):
        cutoff = cutoff_for(delivery_date, cutoff_time)
        chosen, _ = select_versions(grouped.get(start, []), cutoff)
        actual = actual_by_start.get(start)
        rows.append({"startTime": start.isoformat(), "selected_publishTime": chosen["publishTime"] if chosen else None, "forecast_generation_mw": chosen.get("generation") if chosen else None, "actual_generation_mw": actual.get("generation") if actual else None})
    return rows


def metrics(rows: pd.DataFrame) -> dict:
    valid = rows.dropna(subset=["actual_generation_mw", "forecast_generation_mw"]).copy() if not rows.empty else rows
    if not valid.empty:
        valid = valid[
            pd.to_numeric(valid.actual_generation_mw, errors="coerce").map(math.isfinite)
            & pd.to_numeric(valid.forecast_generation_mw, errors="coerce").map(math.isfinite)
        ]
    if valid.empty:
        return {"sample_count": 0, "mae_mw": None, "rmse_mw": None, "bias_mw": None, "wape_percent": None}
    errors = valid.forecast_generation_mw - valid.actual_generation_mw
    denom = valid.actual_generation_mw.sum()
    return {"sample_count": int(len(valid)), "mae_mw": float(errors.abs().mean()), "rmse_mw": float((errors.pow(2).mean()) ** .5), "bias_mw": float(errors.mean()), "wape_percent": float(errors.abs().sum() / denom * 100) if denom else None}


def load_csv(name: str) -> pd.DataFrame:
    path = DATA / name
    if not path.exists():
        return pd.DataFrame()
    return _read_csv(str(path.resolve()), path.stat().st_mtime_ns).copy()


@lru_cache(maxsize=16)
def _read_csv(path: str, modified_ns: int) -> pd.DataFrame:
    """Cache processed datasets; file modification invalidates the cache key."""
    return pd.read_csv(path)


def load_matched(cutoff_time: str = DEFAULT_CUTOFF) -> pd.DataFrame:
    actual = load_csv("actual_wind_january_2026.csv")
    forecasts = load_csv("wind_forecast_versions_january_2026.csv")
    if actual.empty:
        return pd.DataFrame()
    actual["startTime"] = pd.to_datetime(actual.startTime, utc=True)
    actual = actual.drop_duplicates("startTime").set_index("startTime")
    slots = pd.date_range("2026-01-01", "2026-02-01", freq="30min", inclusive="left", tz="UTC")
    result = pd.DataFrame(index=slots)
    result["actual_generation_mw"] = actual.generation_mw.reindex(slots)
    result["selected_publishTime"] = None
    result["forecast_generation_mw"] = None
    result["eligible_forecast_versions"] = 0
    result["selection_status"] = "missing_eligible_forecast"
    result["selection_reason"] = "no retrieved forecast was published by the decision cutoff"
    result["decision_cutoff"] = [cutoff_for(t.tz_convert(LONDON).date(), cutoff_time).isoformat() for t in slots]
    if not forecasts.empty:
        forecasts["startTime"] = pd.to_datetime(forecasts.startTime, utc=True)
        forecasts["publishTime"] = pd.to_datetime(forecasts.publishTime, utc=True)
        for start, group in forecasts.groupby("startTime"):
            if start not in result.index:
                continue
            cutoff = pd.Timestamp(result.at[start, "decision_cutoff"])
            chosen, eligible = select_versions(group.to_dict("records"), cutoff.to_pydatetime())
            result.at[start, "eligible_forecast_versions"] = len(eligible)
            if chosen:
                result.at[start, "selected_publishTime"] = chosen["publishTime"].isoformat()
                result.at[start, "forecast_generation_mw"] = chosen["generation_mw"]
                result.at[start, "selection_status"] = "selected_latest_eligible"
                result.at[start, "selection_reason"] = "latest retrieved version published by the decision cutoff"
    result.index.name = "startTime"
    result = result.reset_index()
    result["signed_error_mw"] = result.forecast_generation_mw - result.actual_generation_mw
    result["absolute_error_mw"] = result.signed_error_mw.abs()
    result["data_quality_status"] = result.apply(lambda r: "matched" if pd.notna(r.actual_generation_mw) and pd.notna(r.forecast_generation_mw) else "missing_forecast" if pd.notna(r.actual_generation_mw) else "missing_actual", axis=1)
    return result

