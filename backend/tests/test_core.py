from datetime import date, datetime, timezone

import pandas as pd

from app.core import cutoff_for, deduplicate_records, match_records, metrics, select_versions, validate_measurement


def test_cutoff_is_timezone_aware_and_january_gmt():
    assert cutoff_for(date(2026, 1, 2)).isoformat() == "2026-01-01T10:00:00+00:00"


def test_select_latest_at_or_before_cutoff():
    rows = [{"publishTime": "2026-01-01T09:00:00Z", "generation_mw": 1}, {"publishTime": "2026-01-01T10:00:00Z", "generation_mw": 2}, {"publishTime": "2026-01-01T11:00:00Z", "generation_mw": 3}]
    selected, eligible = select_versions(rows, datetime(2026, 1, 1, 10, tzinfo=timezone.utc))
    assert selected["generation_mw"] == 2
    assert len(eligible) == 2


def test_equal_publication_time_is_deterministic_and_timezone_safe():
    cutoff = datetime(2026, 1, 1, 10, tzinfo=timezone.utc)
    rows = [{"publishTime": "2026-01-01T11:00:00+01:00", "generation": 7}, {"publishTime": "2026-01-01T10:00:00Z", "generation": 2}]
    chosen_a, _ = select_versions(rows, cutoff)
    chosen_b, _ = select_versions(list(reversed(rows)), cutoff)
    assert chosen_a == chosen_b
    assert chosen_a["generation"] == 7


def test_no_eligible_version():
    selected, _ = select_versions([{"publishTime": "2026-01-01T11:00:00Z"}], datetime(2026, 1, 1, 10, tzinfo=timezone.utc))
    assert selected is None


def test_duplicate_rules_and_validation():
    rows = [{"startTime": "a", "publishTime": "b", "generation": 1}, {"startTime": "a", "publishTime": "b", "generation": 1}, {"startTime": "a", "publishTime": "b", "generation": 2}]
    clean, exact, conflicts = deduplicate_records(rows, ("startTime", "publishTime"))
    assert len(clean) == 1 and exact == 1 and conflicts == 1
    assert clean[0]["generation"] == 2
    assert validate_measurement({"startTime": "2026-01-01T00:00:00Z", "generation": 0, "fuelType": "WIND"}) is None
    assert validate_measurement({"startTime": "2026-01-01", "generation": 2, "fuelType": "WIND"}) == "naive_start_time"
    assert validate_measurement({"startTime": "2026-01-01T00:00:00Z", "generation": -1, "fuelType": "WIND"}) == "negative_generation"
    assert validate_measurement({"startTime": "2026-01-01T00:00:00Z", "generation": "NaN", "fuelType": "WIND"}) == "invalid_generation"


def test_matching_uses_normalized_utc_start_and_marks_missing():
    actuals = [{"startTime": "2026-01-01T00:00:00Z", "generation": 10}]
    forecasts = [{"startTime": "2026-01-01T01:00:00+01:00", "publishTime": "2025-12-31T10:00:00Z", "generation": 12}]
    rows = match_records(actuals, forecasts, date(2026, 1, 1))
    assert rows[0]["actual_generation_mw"] == 10
    assert rows[0]["forecast_generation_mw"] == 12
    assert rows[1]["forecast_generation_mw"] is None


def test_metrics_and_zero_denominator():
    data = pd.DataFrame({"actual_generation_mw": [0.0, 100.0], "forecast_generation_mw": [10.0, 120.0]})
    result = metrics(data)
    assert result["mae_mw"] == 15
    assert result["rmse_mw"] == (250**.5)
    assert result["bias_mw"] == 15
    assert result["wape_percent"] == 30
    assert metrics(data.iloc[:0])["mae_mw"] is None
    assert metrics(pd.DataFrame({"actual_generation_mw": [0], "forecast_generation_mw": [2]}))["wape_percent"] is None
    missing = pd.DataFrame({"actual_generation_mw": [10, None], "forecast_generation_mw": [15, 3]})
    assert metrics(missing)["sample_count"] == 1
