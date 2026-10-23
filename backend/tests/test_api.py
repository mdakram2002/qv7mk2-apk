from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_reports_readiness():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


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
