from __future__ import annotations

import hashlib
import os
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Query


app = FastAPI(title="QR Printing Machine API", version="1.0.0")

PRINT_EVENTS_PER_HOUR = int(os.getenv("MACHINE_PRINT_EVENTS_PER_HOUR", "200"))

LINES = {
    "LINE_01": {
        "machine_id": "QR_PRINTER_01",
        "planned_speed_cpm": 850,
        "product_skus": ["BEER_330_CAN", "BEER_500_CAN", "SODA_330_CAN"],
    }
}
FAULTS = {
    "INK_LOW": "Ink level below threshold",
    "VISION_DIRTY_LENS": "Vision camera lens requires cleaning",
    "PRINTHEAD_TEMP_HIGH": "Printhead temperature above normal band",
    "ENCODER_SIGNAL_LOSS": "Conveyor encoder signal unstable",
    "REJECT_GATE_JAM": "Reject gate did not complete movement",
}


def parse_ts(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid timestamp: {value}") from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def seeded_rng(*parts: Any) -> random.Random:
    seed_text = "|".join(str(part) for part in parts)
    seed = int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest()[:16], 16)
    return random.Random(seed)


def minute_range(start_ts: datetime, end_ts: datetime) -> list[datetime]:
    current = start_ts.replace(second=0, microsecond=0)
    minutes = []
    while current < end_ts:
        minutes.append(current)
        current += timedelta(minutes=1)
    return minutes


def machine_status_for(minute: datetime, rng: random.Random) -> tuple[str, str | None, int]:
    minute_of_day = minute.hour * 60 + minute.minute
    planned_stop = 2 <= minute.hour < 3

    if planned_stop:
        return "PLANNED_STOP", None, 60
    if minute_of_day % 211 in {0, 1, 2}:
        return "FAULTED", "REJECT_GATE_JAM", 60
    if minute_of_day % 97 == 0:
        return "FAULTED", "VISION_DIRTY_LENS", 60
    if rng.random() < 0.025:
        return "FAULTED", rng.choice(list(FAULTS)), 60
    return "RUNNING", None, 0


def demo_print_events_for_minute(minute: datetime) -> int:
    base_events, extra_events = divmod(PRINT_EVENTS_PER_HOUR, 60)
    return base_events + (1 if minute.minute < extra_events else 0)


def build_payload(line_id: str, start_ts: datetime, end_ts: datetime) -> dict[str, Any]:
    if line_id not in LINES:
        raise HTTPException(status_code=404, detail=f"Unknown line_id: {line_id}")
    if end_ts <= start_ts:
        raise HTTPException(status_code=400, detail="end_ts must be after start_ts")
    if end_ts - start_ts > timedelta(hours=1):
        raise HTTPException(status_code=400, detail="Maximum request window is 1 hour")

    config = LINES[line_id]
    machine_id = config["machine_id"]
    planned_speed = config["planned_speed_cpm"]
    telemetry = []
    logs = []
    print_events = []

    for minute in minute_range(start_ts, end_ts):
        rng = seeded_rng(line_id, minute.isoformat())
        status, fault_code, downtime_seconds = machine_status_for(minute, rng)
        speed_factor = 0 if status != "RUNNING" else rng.uniform(0.88, 1.03)
        actual_speed = min(int(planned_speed * speed_factor), demo_print_events_for_minute(minute))
        ink_level = max(5.0, 98.0 - ((minute.timetuple().tm_yday * 24 * 60 + minute.hour * 60 + minute.minute) % 7000) / 80)
        printhead_temp = round(rng.normalvariate(41, 2.8) + (2.5 if actual_speed > planned_speed else 0), 2)
        vibration = round(max(0.4, rng.normalvariate(1.8, 0.45) + (0.5 if fault_code else 0)), 3)
        pressure = round(rng.normalvariate(5.8, 0.15), 2)

        batch_id = f"B{minute:%Y%m%d}{minute.hour // 4 + 1}"
        product_sku = config["product_skus"][(minute.hour // 4) % len(config["product_skus"])]

        telemetry.append(
            {
                "timestamp_minute": minute.isoformat().replace("+00:00", "Z"),
                "line_id": line_id,
                "machine_id": machine_id,
                "machine_status": status,
                "planned_speed_cpm": planned_speed,
                "actual_speed_cpm": actual_speed,
                "printhead_temp_c": printhead_temp,
                "ink_level_pct": round(ink_level, 2),
                "ink_consumed_ml": round(actual_speed * 0.0032, 3),
                "vibration_mm_s": vibration,
                "air_pressure_bar": pressure,
                "items_processed": actual_speed,
                "downtime_seconds": downtime_seconds,
            }
        )

        if status == "FAULTED" and fault_code:
            logs.append(
                {
                    "log_id": f"LOG-{line_id}-{minute:%Y%m%d%H%M}-{fault_code}",
                    "log_timestamp": minute.isoformat().replace("+00:00", "Z"),
                    "line_id": line_id,
                    "machine_id": machine_id,
                    "event_type": "FAULT",
                    "severity": "HIGH" if fault_code in {"REJECT_GATE_JAM", "ENCODER_SIGNAL_LOSS"} else "MEDIUM",
                    "fault_code": fault_code,
                    "fault_description": FAULTS[fault_code],
                    "operator_id": f"OP{rng.randint(1, 6):03d}",
                    "state_from": "RUNNING",
                    "state_to": "FAULTED",
                    "duration_seconds": downtime_seconds,
                }
            )

        for index in range(actual_speed):
            item_rng = seeded_rng(line_id, minute.isoformat(), index)
            missing_code = item_rng.random() < 0.0015
            duplicate_code = item_rng.random() < 0.0008
            position_error = round(item_rng.normalvariate(0.15, 0.08) + (0.18 if vibration > 2.4 else 0), 3)
            vision_fail = missing_code or duplicate_code or abs(position_error) > 0.45 or item_rng.random() < 0.006
            print_success = not missing_code and item_rng.random() > 0.003
            reject_flag = (not print_success) or vision_fail

            print_events.append(
                {
                    "event_id": f"EVT-{line_id}-{minute:%Y%m%d%H%M}-{index:04d}",
                    "event_timestamp": (minute + timedelta(seconds=index * 60 / max(actual_speed, 1)))
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "line_id": line_id,
                    "machine_id": machine_id,
                    "product_sku": product_sku,
                    "batch_id": batch_id,
                    "qr_code": None if missing_code else f"{batch_id}-{line_id}-{minute:%H%M}-{index:04d}",
                    "print_result": "SUCCESS" if print_success else "FAILED",
                    "vision_result": "FAIL" if vision_fail else "PASS",
                    "reject_flag": reject_flag,
                    "reject_reason": "MISSING_CODE" if missing_code else "DUPLICATE_CODE" if duplicate_code else "VISION_FAIL" if vision_fail else None,
                    "position_error_mm": position_error,
                    "grade_score": None if missing_code else round(max(0, min(100, item_rng.normalvariate(94, 4) - abs(position_error) * 20)), 2),
                }
            )

    return {
        "line_id": line_id,
        "start_ts": start_ts.isoformat().replace("+00:00", "Z"),
        "end_ts": end_ts.isoformat().replace("+00:00", "Z"),
        "record_counts": {
            "print_events": len(print_events),
            "machine_telemetry": len(telemetry),
            "machine_logs": len(logs),
        },
        "print_events": print_events,
        "machine_telemetry": telemetry,
        "machine_logs": logs,
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/qr-printing/lines/{line_id}/window")
def get_line_window(
    line_id: str,
    start_ts: str = Query(..., description="UTC ISO timestamp"),
    end_ts: str = Query(..., description="UTC ISO timestamp"),
) -> dict[str, Any]:
    return build_payload(line_id, parse_ts(start_ts), parse_ts(end_ts))
