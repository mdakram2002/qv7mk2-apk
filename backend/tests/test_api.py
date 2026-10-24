import csv
import io
import math
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_reports_readiness():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_cors_allows_configured_local_frontend_origin():
    response = client.get("/api/v1/health", headers={"Origin": "http://localhost:8080"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:8080"


def test_cutoff_time_validation_and_metadata():
    assert client.get("/api/v1/summary", params={"cutoff_time": "25:90"}).status_code == 422
    response = client.get("/api/v1/metadata")
    assert response.status_code == 200
    assert response.json()["timezone"] == "Europe/London"


def test_range_validation_and_metrics_endpoint():
    bad = client.get("/api/v1/summary", params={"start_date": "2025-12-31"})
    assert bad.status_code == 422
    response = client.get("/api/v1/summary")
    assert response.status_code == 200
    assert response.json()["expected_intervals"] == 1488


def test_csv_export_headers():
    response = client.get("/api/v1/export/actuals.csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]


def test_interval_pagination():
    response = client.get("/api/v1/intervals", params={"page": 2, "page_size": 10})
    assert response.status_code == 200
    assert response.json()["page"] == 2
    assert len(response.json()["items"]) <= 10
    first = client.get("/api/v1/intervals", params={"start_date": "2026-01-01", "end_date": "2026-01-02", "page_size": 1}).json()["items"][0]
    assert first["eligible_forecast_versions"] > 0
    assert first["selection_status"] == "selected_latest_eligible"
    assert first["selection_reason"]


def test_sorting_and_quality_filter():
    response = client.get("/api/v1/intervals", params={"sort_by": "signed_error_mw", "sort_order": "desc", "quality_status": "matched", "page_size": 5})
    assert response.status_code == 200
    assert all(row["data_quality_status"] == "matched" for row in response.json()["items"])


def test_daily_monthly_and_forecast_history_contracts():
    daily = client.get("/api/v1/accuracy/daily").json()
    monthly = client.get("/api/v1/accuracy/monthly").json()
    assert len(daily) == 31
    assert daily[0]["expected_interval_count"] == 48
    assert monthly["expected_interval_count"] == 1488
    assert monthly["matched_interval_count"] == 744
    versions = client.get("/api/v1/forecast-versions", params={"start_time": "2026-01-01T00:00:00Z"}).json()
    assert any(version["selected"] for version in versions["versions"])
    assert all(version["eligible"] or not version["selected"] for version in versions["versions"])


def test_forecast_history_requires_zoned_january_delivery_start():
    assert client.get("/api/v1/forecast-versions", params={"start_time": "2026-01-01T00:00:00"}).status_code == 422
    assert client.get("/api/v1/forecast-versions", params={"start_time": "2026-02-01T00:00:00Z"}).status_code == 422


def test_matched_export_respects_date_and_quality_filters():
    response = client.get("/api/v1/export/matched.csv", params={
        "start_date": "2026-01-01", "end_date": "2026-01-02", "quality_status": "matched",
    })
    assert response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert len(rows) == 24
    assert {row["data_quality_status"] for row in rows} == {"matched"}


def test_cutoff_changes_selected_forecast_when_new_versions_become_eligible():
    endpoint = "/api/v1/forecast-versions?start_time=2026-01-01T00%3A00%3A00Z"
    midnight = client.get(endpoint + "&cutoff_time=00%3A00").json()
    morning = client.get(endpoint + "&cutoff_time=10%3A00").json()
    selected_midnight = next(row for row in midnight["versions"] if row["selected"])
    selected_morning = next(row for row in morning["versions"] if row["selected"])
    assert selected_midnight["publishTime"] != selected_morning["publishTime"]
    assert selected_midnight["eligible"] and selected_morning["eligible"]


def test_quality_and_json_export_report_cutoff_specific_counts():
    quality = client.get("/api/v1/data-quality", params={"cutoff_time": "10:00"}).json()
    report = client.get("/api/v1/export/ingestion-report.json", params={"cutoff_time": "10:00"}).json()
    assert quality["expected_actual_intervals"] == 1488
    assert quality["matched_intervals_at_cutoff"] == 744
    assert quality["eligible_forecast_delivery_intervals"] == 744
    assert report["cutoff_time"] == "10:00"
    assert report["missing_forecasts_at_cutoff"] == 744


def test_summary_reconciles_to_independent_matched_csv_calculation():
    path = Path("data/processed/matched_wind_january_2026.csv")
    with path.open(newline="", encoding="utf-8") as file:
        records = [row for row in csv.DictReader(file) if row["data_quality_status"] == "matched"]
    errors = [float(row["forecast_generation_mw"]) - float(row["actual_generation_mw"]) for row in records]
    actual_total = sum(float(row["actual_generation_mw"]) for row in records)
    absolute_total = sum(abs(error) for error in errors)
    expected = {
        "sample_count": len(records),
        "mae_mw": absolute_total / len(errors),
        "rmse_mw": math.sqrt(sum(error * error for error in errors) / len(errors)),
        "bias_mw": sum(errors) / len(errors),
        "wape_percent": absolute_total / actual_total * 100,
    }
    response = client.get("/api/v1/summary").json()
    assert response["expected_intervals"] == 1488
    assert response["matched_intervals"] == 744
    for key, value in expected.items():
        assert math.isclose(response[key], value, rel_tol=1e-10)
