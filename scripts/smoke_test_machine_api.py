from __future__ import annotations

import argparse
from collections import Counter

import requests


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test the QR printing machine API.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--line-id", default="LINE_01")
    parser.add_argument("--start-ts", default="2026-06-12T01:00:00Z")
    parser.add_argument("--end-ts", default="2026-06-12T02:00:00Z")
    args = parser.parse_args()

    response = requests.get(
        f"{args.base_url}/v1/qr-printing/lines/{args.line_id}/window",
        params={"start_ts": args.start_ts, "end_ts": args.end_ts},
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()

    event_count = len(payload["print_events"])
    telemetry_count = len(payload["machine_telemetry"])
    telemetry_items = sum(row["items_processed"] for row in payload["machine_telemetry"])
    reject_count = sum(1 for row in payload["print_events"] if row["reject_flag"])
    fault_counts = Counter(row["fault_code"] for row in payload["machine_logs"])

    if event_count != telemetry_items:
        raise ValueError(f"Print events ({event_count}) do not match telemetry items ({telemetry_items})")

    print(f"line_id={payload['line_id']}")
    print(f"window={payload['start_ts']} to {payload['end_ts']}")
    print(f"print_events={event_count}")
    print(f"machine_telemetry_rows={telemetry_count}")
    print(f"machine_logs={len(payload['machine_logs'])}")
    print(f"reject_rate_pct={reject_count / event_count:.2%}")
    print(f"fault_counts={dict(fault_counts)}")


if __name__ == "__main__":
    main()
