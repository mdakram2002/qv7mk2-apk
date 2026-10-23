"""Live contract probe for official Elexon FUELHH and WINDFOR datasets."""
import argparse
import json

import httpx

BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"


def report(client: httpx.Client, url: str, params: dict) -> dict:
    response = client.get(url, params=params)
    print(f"\nURL: {response.url}\nHTTP: {response.status_code}\nContent-Type: {response.headers.get('content-type')}")
    response.raise_for_status()
    payload = response.json()
    rows = payload.get("data", payload) if isinstance(payload, dict) else payload
    rows = rows if isinstance(rows, list) else []
    fields = sorted({key for row in rows if isinstance(row, dict) for key in row})
    stamps = [row.get("startTime") for row in rows if isinstance(row, dict) and row.get("startTime")]
    pubs = [row.get("publishTime") for row in rows if isinstance(row, dict) and row.get("publishTime")]
    missing = {key: sum(row.get(key) is None for row in rows if isinstance(row, dict)) for key in fields}
    result = {"url": str(response.url), "status": response.status_code, "content_type": response.headers.get("content-type"), "record_count": len(rows), "fields": fields, "start_time_range": [min(stamps), max(stamps)] if stamps else None, "publish_time_range": [min(pubs), max(pubs)] if pubs else None, "missing_values": missing, "sample": rows[:3]}
    print(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Make real requests to Elexon")
    args = parser.parse_args()
    if not args.live:
        parser.error("Pass --live to make the requested live API checks")
    with httpx.Client(timeout=40, headers={"Accept": "application/json"}) as client:
        report(client, f"{BASE}/FUELHH", {"settlementDateFrom": "2026-01-01", "settlementDateTo": "2026-01-01", "fuelType": "WIND"})
        # A single day confirms the historical publication-time filter contract.
        report(client, f"{BASE}/WINDFOR", {"publishDateTimeFrom": "2025-12-31T00:00:00Z", "publishDateTimeTo": "2026-01-01T00:00:00Z"})


if __name__ == "__main__":
    main()
