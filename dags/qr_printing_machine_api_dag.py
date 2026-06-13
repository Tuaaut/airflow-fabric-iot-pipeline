from __future__ import annotations

import csv
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import requests
from requests import Response
from airflow.sdk import dag, get_current_context, task
from airflow.utils.trigger_rule import TriggerRule


API_BASE_URL = os.getenv("MACHINE_API_BASE_URL", "http://machine-api:8000")
LINE_ID = "LINE_01"
RAW_DIR = Path("/opt/airflow/data/raw/qr_printing")
CURATED_DIR = Path("/opt/airflow/data/curated/qr_printing")
FABRIC_MODE = os.getenv("FABRIC_MODE", "local")
FABRIC_SIM_DIR = Path("/opt/airflow/data/fabric_simulation/qr_printing")

AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID", "")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "")
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "")

FABRIC_WORKSPACE_ID = os.getenv("FABRIC_WORKSPACE_ID", "")
FABRIC_LAKEHOUSE_ID = os.getenv("FABRIC_LAKEHOUSE_ID", "")
FABRIC_LAKEHOUSE_NAME = os.getenv("FABRIC_LAKEHOUSE_NAME", "lh_qr_printing_demo")
FABRIC_NOTEBOOK_ID = os.getenv("FABRIC_NOTEBOOK_ID", "")
FABRIC_NOTEBOOK_JOB_TYPE = os.getenv("FABRIC_NOTEBOOK_JOB_TYPE", "RunNotebook")

POWER_BI_WORKSPACE_ID = os.getenv("POWER_BI_WORKSPACE_ID", FABRIC_WORKSPACE_ID)
POWER_BI_SEMANTIC_MODEL_ID = os.getenv("POWER_BI_SEMANTIC_MODEL_ID", "")

FABRIC_CAPACITY_AUTO_RESUME = os.getenv("FABRIC_CAPACITY_AUTO_RESUME", "false").lower() == "true"
FABRIC_CAPACITY_AUTO_PAUSE = os.getenv("FABRIC_CAPACITY_AUTO_PAUSE", "false").lower() == "true"
AZURE_SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID", "")
AZURE_RESOURCE_GROUP = os.getenv("AZURE_RESOURCE_GROUP", "")
FABRIC_CAPACITY_NAME = os.getenv("FABRIC_CAPACITY_NAME", "")

FABRIC_API_BASE_URL = "https://api.fabric.microsoft.com/v1"
POWER_BI_API_BASE_URL = "https://api.powerbi.com/v1.0/myorg"
ONELAKE_DFS_BASE_URL = "https://onelake.dfs.fabric.microsoft.com"
AZURE_MANAGEMENT_BASE_URL = "https://management.azure.com"
CAPACITY_POLL_SECONDS = 10
CAPACITY_TIMEOUT_SECONDS = 900
HTTP_RETRY_ATTEMPTS = 5
HTTP_RETRY_SECONDS = 30


def as_utc_datetime(value: object | None) -> datetime | None:
    if value is None:
        return None
    if hasattr(value, "in_timezone"):
        return value.in_timezone("UTC")
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return None


def utc_data_window() -> tuple[datetime, datetime]:
    context = get_current_context()
    start_ts = as_utc_datetime(context.get("data_interval_start"))
    end_ts = as_utc_datetime(context.get("data_interval_end"))

    if start_ts is not None and end_ts is not None and end_ts > start_ts:
        return start_ts, end_ts

    anchor = (
        as_utc_datetime(context.get("logical_date"))
        or end_ts
        or datetime.now(timezone.utc)
    )
    anchor = anchor.replace(minute=0, second=0, microsecond=0)
    return anchor - timedelta(days=1), anchor


def request_with_retry(method: str, url: str, **kwargs) -> Response:
    last_error: Exception | None = None
    for attempt in range(1, HTTP_RETRY_ATTEMPTS + 1):
        try:
            return requests.request(method, url, **kwargs)
        except requests.RequestException as exc:
            last_error = exc
            if attempt == HTTP_RETRY_ATTEMPTS:
                break
            time.sleep(HTTP_RETRY_SECONDS)

    raise RuntimeError(f"HTTP request failed after {HTTP_RETRY_ATTEMPTS} attempts: {url}") from last_error


def hourly_windows(start_ts: datetime, end_ts: datetime) -> list[tuple[datetime, datetime]]:
    windows = []
    current = start_ts
    while current < end_ts:
        next_hour = min(current + timedelta(hours=1), end_ts)
        windows.append((current, next_hour))
        current = next_hour
    return windows


def utc_partition_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def require_env(*names: str) -> None:
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")


def get_access_token(scope: str) -> str:
    require_env("AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET")
    response = request_with_retry(
        "POST",
        f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/token",
        data={
            "client_id": AZURE_CLIENT_ID,
            "client_secret": AZURE_CLIENT_SECRET,
            "grant_type": "client_credentials",
            "scope": scope,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def bearer_headers(scope: str) -> dict:
    return {"Authorization": f"Bearer {get_access_token(scope)}"}


def upload_file_to_onelake(local_path: Path, workspace_id: str, lakehouse_id: str, lakehouse_path: str) -> str:
    token_headers = bearer_headers("https://storage.azure.com/.default")
    quoted_path = "/".join(quote(part, safe="=") for part in lakehouse_path.split("/"))
    file_url = (
        f"{ONELAKE_DFS_BASE_URL}/{workspace_id}/"
        f"{lakehouse_id}/{quoted_path}"
    )

    create_response = request_with_retry(
        "PUT",
        file_url,
        params={"resource": "file"},
        headers=token_headers,
        timeout=60,
    )
    if not create_response.ok:
        raise RuntimeError(f"OneLake file create failed: {create_response.status_code} {create_response.text}")

    content = local_path.read_bytes()
    append_response = request_with_retry(
        "PATCH",
        file_url,
        params={"action": "append", "position": 0},
        headers={**token_headers, "Content-Type": "application/octet-stream"},
        data=content,
        timeout=120,
    )
    if not append_response.ok:
        raise RuntimeError(f"OneLake file append failed: {append_response.status_code} {append_response.text}")

    flush_response = request_with_retry(
        "PATCH",
        file_url,
        params={"action": "flush", "position": len(content)},
        headers=token_headers,
        timeout=120,
    )
    if not flush_response.ok:
        raise RuntimeError(f"OneLake file flush failed: {flush_response.status_code} {flush_response.text}")
    return f"Files/{lakehouse_path}"


def run_capacity_action(action: str) -> dict:
    require_env("AZURE_SUBSCRIPTION_ID", "AZURE_RESOURCE_GROUP", "FABRIC_CAPACITY_NAME")
    response = request_with_retry(
        "POST",
        (
            f"{AZURE_MANAGEMENT_BASE_URL}/subscriptions/{AZURE_SUBSCRIPTION_ID}"
            f"/resourceGroups/{AZURE_RESOURCE_GROUP}"
            f"/providers/Microsoft.Fabric/capacities/{FABRIC_CAPACITY_NAME}/{action}"
        ),
        params={"api-version": "2023-11-01"},
        headers=bearer_headers("https://management.azure.com/.default"),
        timeout=60,
    )
    if not response.ok:
        raise RuntimeError(
            f"Fabric capacity {action} failed: {response.status_code} {response.text}"
        )
    return {"action": action, "status_code": response.status_code}


def get_capacity_state() -> dict:
    require_env("AZURE_SUBSCRIPTION_ID", "AZURE_RESOURCE_GROUP", "FABRIC_CAPACITY_NAME")
    response = request_with_retry(
        "GET",
        (
            f"{AZURE_MANAGEMENT_BASE_URL}/subscriptions/{AZURE_SUBSCRIPTION_ID}"
            f"/resourceGroups/{AZURE_RESOURCE_GROUP}"
            f"/providers/Microsoft.Fabric/capacities/{FABRIC_CAPACITY_NAME}"
        ),
        params={"api-version": "2023-11-01"},
        headers=bearer_headers("https://management.azure.com/.default"),
        timeout=60,
    )
    response.raise_for_status()
    properties = response.json().get("properties", {})
    return {
        "state": properties.get("state"),
        "provisioning_state": properties.get("provisioningState"),
    }


def wait_for_capacity_state(target_state: str) -> dict:
    deadline = time.monotonic() + CAPACITY_TIMEOUT_SECONDS
    last_state = {}

    while time.monotonic() < deadline:
        last_state = get_capacity_state()
        if last_state["state"] == target_state:
            return last_state
        time.sleep(CAPACITY_POLL_SECONDS)

    raise TimeoutError(f"Fabric capacity did not reach {target_state}: {last_state}")


@dag(
    dag_id="qr_printing_machine_api_ingestion",
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["iot", "api", "qr-printing", "machine"],
)
def qr_printing_machine_api_ingestion():
    @task(retries=3, retry_delay=timedelta(minutes=5))
    def resume_fabric_capacity() -> dict:
        if FABRIC_MODE == "local" or not FABRIC_CAPACITY_AUTO_RESUME:
            return {"capacity_resume": "skipped"}
        current_state = get_capacity_state()
        if current_state["state"] == "Active":
            return {"capacity_resume": "already_active", **current_state}
        action_result = run_capacity_action("resume")
        return {**action_result, **wait_for_capacity_state("Active")}

    @task
    def extract_from_api() -> str:
        start_ts, end_ts = utc_data_window()
        payload = {
            "line_id": LINE_ID,
            "start_ts": start_ts.isoformat().replace("+00:00", "Z"),
            "end_ts": end_ts.isoformat().replace("+00:00", "Z"),
            "record_counts": {
                "print_events": 0,
                "machine_telemetry": 0,
                "machine_logs": 0,
            },
            "print_events": [],
            "machine_telemetry": [],
            "machine_logs": [],
            "source_windows": [],
        }

        for window_start, window_end in hourly_windows(start_ts, end_ts):
            response = request_with_retry(
                "GET",
                f"{API_BASE_URL}/v1/qr-printing/lines/{LINE_ID}/window",
                params={
                    "start_ts": window_start.isoformat().replace("+00:00", "Z"),
                    "end_ts": window_end.isoformat().replace("+00:00", "Z"),
                },
                timeout=120,
            )
            response.raise_for_status()
            hourly_payload = response.json()

            payload["print_events"].extend(hourly_payload["print_events"])
            payload["machine_telemetry"].extend(hourly_payload["machine_telemetry"])
            payload["machine_logs"].extend(hourly_payload["machine_logs"])
            payload["source_windows"].append({
                "start_ts": hourly_payload["start_ts"],
                "end_ts": hourly_payload["end_ts"],
                "record_counts": hourly_payload["record_counts"],
            })

        payload["record_counts"] = {
            "print_events": len(payload["print_events"]),
            "machine_telemetry": len(payload["machine_telemetry"]),
            "machine_logs": len(payload["machine_logs"]),
        }

        partition_dir = RAW_DIR / f"start_hour={start_ts:%Y%m%d%H}"
        partition_dir.mkdir(parents=True, exist_ok=True)
        raw_path = partition_dir / "machine_api_response.json"
        raw_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(raw_path)

    @task
    def validate_raw(raw_path: str) -> str:
        payload = json.loads(Path(raw_path).read_text(encoding="utf-8"))
        counts = payload["record_counts"]
        start_ts = datetime.fromisoformat(payload["start_ts"].replace("Z", "+00:00"))
        end_ts = datetime.fromisoformat(payload["end_ts"].replace("Z", "+00:00"))
        window_hours = max((end_ts - start_ts).total_seconds() / 3600, 1)

        if counts["machine_telemetry"] < int(window_hours * 50):
            raise ValueError("Machine telemetry sample is unexpectedly small")
        if counts["print_events"] < int(window_hours * 100):
            raise ValueError("Print event sample is unexpectedly small")

        return raw_path

    @task
    def load_raw_to_fabric_lakehouse(raw_path: str) -> dict:
        payload = json.loads(Path(raw_path).read_text(encoding="utf-8"))
        start_ts = datetime.fromisoformat(payload["start_ts"].replace("Z", "+00:00"))
        start_hour = f"{start_ts:%Y%m%d%H}"
        uploaded_at = utc_partition_timestamp()

        if FABRIC_MODE == "local":
            landing_dir = FABRIC_SIM_DIR / "raw_lakehouse_files" / f"uploaded_at={uploaded_at}" / f"start_hour={start_hour}"
            landing_dir.mkdir(parents=True, exist_ok=True)
            landing_path = landing_dir / "machine_api_response.json"
            landing_path.write_text(Path(raw_path).read_text(encoding="utf-8"), encoding="utf-8")
            fabric_uri = str(landing_path)
        else:
            require_env("FABRIC_WORKSPACE_ID", "FABRIC_LAKEHOUSE_ID")
            lakehouse_path = f"Files/raw/qr_printing/uploaded_at={uploaded_at}/start_hour={start_hour}/machine_api_response.json"
            fabric_uri = upload_file_to_onelake(
                Path(raw_path),
                FABRIC_WORKSPACE_ID,
                FABRIC_LAKEHOUSE_ID,
                lakehouse_path,
            )

        return {
            "raw_path": raw_path,
            "fabric_raw_uri": fabric_uri,
            "start_hour": start_hour,
            "uploaded_at": uploaded_at,
        }

    @task
    def trigger_fabric_transformation(load_result: dict) -> dict:
        if FABRIC_MODE != "local":
            require_env("FABRIC_WORKSPACE_ID", "FABRIC_NOTEBOOK_ID")
            response = request_with_retry(
                "POST",
                (
                    f"{FABRIC_API_BASE_URL}/workspaces/{FABRIC_WORKSPACE_ID}"
                    f"/items/{FABRIC_NOTEBOOK_ID}/jobs/{FABRIC_NOTEBOOK_JOB_TYPE}/instances"
                ),
                headers=bearer_headers("https://api.fabric.microsoft.com/.default"),
                json={},
                timeout=60,
            )
            response.raise_for_status()
            location = response.headers.get("Location", "")
            job_id = location.rstrip("/").split("/")[-1] if location else ""
            if not job_id:
                raise ValueError("Fabric notebook job was accepted but no job instance ID was returned")
            return {
                "fabric_job_id": job_id,
                "fabric_job_location": location,
                "status": "submitted",
                "start_hour": load_result["start_hour"],
                "curated_paths": [],
            }

        raw_path = load_result["raw_path"]
        payload = json.loads(Path(raw_path).read_text(encoding="utf-8"))
        start_hour = load_result["start_hour"]
        output_dir = CURATED_DIR / f"start_hour={start_hour}"

        outputs = {
            "fact_print_event.csv": payload["print_events"],
            "fact_machine_telemetry_minute.csv": payload["machine_telemetry"],
            "fact_machine_log.csv": payload["machine_logs"],
        }

        written_paths = []
        for filename, rows in outputs.items():
            output_path = output_dir / filename
            write_csv(output_path, rows)
            written_paths.append(str(output_path))

        return {
            "fabric_job_id": f"local-fabric-transform-{start_hour}",
            "status": "submitted",
            "curated_paths": written_paths,
            "start_hour": start_hour,
        }

    @task
    def wait_for_fabric_transformation(job_result: dict) -> dict:
        if FABRIC_MODE == "local":
            job_result["status"] = "succeeded"
            return job_result

        require_env("FABRIC_WORKSPACE_ID", "FABRIC_NOTEBOOK_ID")
        job_id = job_result["fabric_job_id"]
        headers = bearer_headers("https://api.fabric.microsoft.com/.default")

        for _ in range(60):
            response = request_with_retry(
                "GET",
                (
                    f"{FABRIC_API_BASE_URL}/workspaces/{FABRIC_WORKSPACE_ID}"
                    f"/items/{FABRIC_NOTEBOOK_ID}/jobs/instances/{job_id}"
                ),
                headers=headers,
                timeout=60,
            )
            response.raise_for_status()
            job = response.json()
            status = job.get("status")

            if status in {"Completed", "Deduped"}:
                job_result["status"] = status
                job_result["fabric_job"] = job
                return job_result
            if status in {"Failed", "Cancelled"}:
                raise RuntimeError(f"Fabric notebook job ended with status {status}: {job}")

            time.sleep(int(response.headers.get("Retry-After", "30")))

        raise TimeoutError(f"Fabric notebook job did not complete in time: {job_id}")

    @task
    def validate_curated_tables(job_result: dict) -> dict:
        if FABRIC_MODE != "local":
            job_result["row_counts"] = {"fabric_validation": "notebook_completed"}
            return job_result

        row_counts = {}

        for csv_path in job_result["curated_paths"]:
            with Path(csv_path).open(encoding="utf-8") as csv_file:
                row_counts[Path(csv_path).name] = max(sum(1 for _ in csv_file) - 1, 0)

        if row_counts.get("fact_machine_telemetry_minute.csv", 0) < 50:
            raise ValueError("Curated telemetry table failed row-count validation")
        if row_counts.get("fact_print_event.csv", 0) < 1000:
            raise ValueError("Curated print event table failed row-count validation")

        job_result["row_counts"] = row_counts
        return job_result

    @task
    def refresh_power_bi_semantic_model(validation_result: dict) -> dict:
        if FABRIC_MODE == "local":
            validation_result["power_bi_refresh"] = "skipped_local_mode"
            return validation_result

        require_env("POWER_BI_WORKSPACE_ID", "POWER_BI_SEMANTIC_MODEL_ID")
        response = request_with_retry(
            "POST",
            (
                f"{POWER_BI_API_BASE_URL}/groups/{POWER_BI_WORKSPACE_ID}"
                f"/datasets/{POWER_BI_SEMANTIC_MODEL_ID}/refreshes"
            ),
            headers={
                **bearer_headers("https://analysis.windows.net/powerbi/api/.default"),
                "Content-Type": "application/json",
            },
            json={"notifyOption": "NoNotification"},
            timeout=60,
        )
        response.raise_for_status()
        validation_result["power_bi_refresh"] = "submitted"
        return validation_result

    @task(trigger_rule=TriggerRule.ALL_DONE, retries=3, retry_delay=timedelta(minutes=5))
    def pause_fabric_capacity() -> dict:
        if FABRIC_MODE == "local" or not FABRIC_CAPACITY_AUTO_PAUSE:
            return {"capacity_pause": "skipped"}
        current_state = get_capacity_state()
        if current_state["state"] == "Paused":
            return {"capacity_pause": "already_paused", **current_state}
        action_result = run_capacity_action("suspend")
        return {**action_result, **wait_for_capacity_state("Paused")}

    capacity_ready = resume_fabric_capacity()
    extracted_path = extract_from_api()
    capacity_ready >> extracted_path
    raw_path = validate_raw(extracted_path)
    load_result = load_raw_to_fabric_lakehouse(raw_path)
    fabric_job = trigger_fabric_transformation(load_result)
    completed_job = wait_for_fabric_transformation(fabric_job)
    validated_job = validate_curated_tables(completed_job)
    refresh_result = refresh_power_bi_semantic_model(validated_job)
    refresh_result >> pause_fabric_capacity()


qr_printing_machine_api_ingestion()
