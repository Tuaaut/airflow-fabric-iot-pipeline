"""Retail daily pipeline, sharing the existing Celery worker and one-slot pool."""
from datetime import date, timedelta
import subprocess

import pendulum
from airflow.sdk import dag, task, get_current_context, Param

PROJECT = "/opt/retail/project"
PYTHON = "/opt/retail-venv/bin/python"


@dag(
    dag_id="retail_dbt_daily",
    start_date=pendulum.datetime(2026, 9, 5, tz="Asia/Bangkok"),
    schedule="30 7 * * *",
    catchup=False,
    max_active_runs=1,
    max_active_tasks=1,
    default_args={"pool": "shared_pipeline", "retries": 2, "retry_delay": timedelta(minutes=2), "execution_timeout": timedelta(minutes=20)},
    params={"batch_date": Param("", type="string", description="Blank = previous Bangkok calendar day; override YYYY-MM-DD for backfill"), "orders_per_day": Param(100, type="integer", minimum=1, maximum=10000)},
    tags=["retail", "dbt", "duckdb", "local"],
)
def retail_dbt_daily():
    @task
    def generate_batch():
        context = get_current_context()
        requested = context["params"]["batch_date"]
        # Airflow cron intervals end on the trigger day. Ingest the completed prior day.
        end = context.get("data_interval_end") or context["dag_run"].run_after
        end = pendulum.instance(end)
        day = date.fromisoformat(requested) if requested else end.in_timezone("Asia/Bangkok").subtract(days=1).date()
        subprocess.run([PYTHON, f"{PROJECT}/pipeline/retail.py", "generate", "--date", str(day), "--orders", str(context["params"]["orders_per_day"])], check=True)
        return str(day)

    @task
    def load_batch(day: str):
        subprocess.run([PYTHON, f"{PROJECT}/pipeline/retail.py", "load", "--date", day], check=True)
        return day

    @task
    def dbt_build(day: str):
        subprocess.run(["/opt/retail-venv/bin/dbt", "build", "--project-dir", PROJECT, "--profiles-dir", PROJECT], cwd=PROJECT, check=True)
        return day

    @task
    def export_snapshot(day: str):
        subprocess.run([PYTHON, f"{PROJECT}/pipeline/retail.py", "snapshot", "--date", day], check=True)

    export_snapshot(dbt_build(load_batch(generate_batch())))


retail_dbt_daily()
