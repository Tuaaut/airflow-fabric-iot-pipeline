from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

import requests
from airflow.sdk import dag, task


COUNTRIES = ["THA", "VNM", "IDN", "MYS", "PHL"]
INDICATORS = {
    "NY.GDP.MKTP.CD": "gdp_current_usd",
    "SP.POP.TOTL": "population",
    "FP.CPI.TOTL.ZG": "inflation_annual_pct",
}
BASE_URL = "https://api.worldbank.org/v2/country/{countries}/indicator/{indicator}"
RAW_DIR = Path("/opt/airflow/data/raw/world_bank")
CURATED_DIR = Path("/opt/airflow/data/curated")


def fetch_indicator(indicator: str) -> list[dict]:
    countries = ";".join(COUNTRIES)
    url = BASE_URL.format(countries=countries, indicator=indicator)
    response = requests.get(
        url,
        params={"format": "json", "per_page": 20000, "date": "2015:2025"},
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()

    if not isinstance(payload, list) or len(payload) < 2:
        raise ValueError(f"Unexpected World Bank response for {indicator}")

    return payload[1]


@dag(
    dag_id="world_bank_indicators",
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["world-bank", "api", "demo"],
)
def world_bank_indicators():
    @task
    def extract_raw() -> str:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        extracted_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        rows = []

        for indicator, metric_name in INDICATORS.items():
            records = fetch_indicator(indicator)
            raw_path = RAW_DIR / f"{indicator}.json"
            raw_path.write_text(json.dumps(records, indent=2), encoding="utf-8")

            for record in records:
                value = record.get("value")
                if value is None:
                    continue

                rows.append(
                    {
                        "country_code": record["countryiso3code"],
                        "country_name": record["country"]["value"],
                        "year": int(record["date"]),
                        "indicator_code": indicator,
                        "metric_name": metric_name,
                        "metric_value": float(value),
                        "extracted_at": extracted_at,
                    }
                )

        staged_path = RAW_DIR / "staged_rows.json"
        staged_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        return str(staged_path)

    @task
    def transform_to_csv(staged_path: str) -> str:
        CURATED_DIR.mkdir(parents=True, exist_ok=True)
        rows = json.loads(Path(staged_path).read_text(encoding="utf-8"))
        rows = sorted(rows, key=lambda row: (row["country_code"], row["year"], row["metric_name"]))

        output_path = CURATED_DIR / "world_bank_country_indicators.csv"
        with output_path.open("w", newline="", encoding="utf-8") as csv_file:
            if not rows:
                raise ValueError("No World Bank rows found after filtering null values")

            writer = csv.DictWriter(csv_file, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

        return str(output_path)

    @task
    def validate_output(csv_path: str) -> None:
        with Path(csv_path).open(encoding="utf-8") as csv_file:
            row_count = sum(1 for _ in csv.DictReader(csv_file))

        minimum_rows = len(COUNTRIES) * len(INDICATORS) * 5
        if row_count < minimum_rows:
            raise ValueError(f"Only {row_count} rows found; expected at least {minimum_rows}")

    validate_output(transform_to_csv(extract_raw()))


world_bank_indicators()
