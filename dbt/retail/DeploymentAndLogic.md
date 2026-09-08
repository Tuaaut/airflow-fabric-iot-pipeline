# Retail Pipeline Blueprint and Progress

Updated: 2026-09-05 (Asia/Bangkok). This replaces the legacy Mac-only blueprint, preserved in the backup below.

## Document map

- [Project overview and DBeaver instructions](README.md)
- [Shared Airflow status](../../airflow-fabric-iot-pipeline/PROJECT_STATUS.md)
- [Compose](../../airflow-fabric-iot-pipeline/docker-compose.yaml)
- [Daily DAG](../../airflow-fabric-iot-pipeline/dags/retail_dbt_daily.py)
- [Windows start/stop operations](../../airflow-fabric-iot-pipeline/scripts/docker-auto/README.md)

## Approved architecture

Use existing Airflow 3.2.2 at port 8080. Preserve IoT and paused World Bank. No additional persistent containers, no dashboard, no cloud services or credentials for Retail.

Existing Airflow services, PostgreSQL metadata DB and Redis queue are shared. Only the Celery worker uses the extended image `local/airflow-retail:3.2.2`; its `/opt/retail-venv` isolates dbt dependencies from Airflow. The other services retain their original image.

Compose mounts:
- Project folder → `/opt/retail/project`, read-only.
- Named volume `airflow-fabric-iot-pipeline_retail-db-volume` → `/opt/retail/data`.
- Host `exports` directory → `/opt/retail/exports` for Windows/DBeaver access.

The original root `demo.duckdb` remains untouched as legacy data. The new operational database is `/opt/retail/data/demo.duckdb` in the named volume. It starts with new daily batches; the old synthetic 2024 orders are not silently merged.

## Data model

`pipeline/retail.py generate` produces deterministic daily JSON, using date-derived BIGINT identifiers. Default 100 orders, configurable 1–10000. Each order has 1–4 item lines. Completed orders may have split payments; pending/cancelled orders have zero successful payments. Master SQL under `pipeline/masters` initializes 120 customers, 12 stores and 60 products once.

`load` transactionally replaces only the requested date in `landing.orders`, `landing.order_items` and `landing.payments`. It preserves other dates and rolls back if any insert fails. Date reruns can change batch size without leaving orphan rows. Generated JSON is retained in the volume for inspection.

| Layer | Models | Materialization | Purpose |
|---|---:|---|---|
| Raw | 6 | views | dbt sources in landing schema |
| Staging | 6 | views | casing, numeric types and keys |
| Intermediate | 4 | views | order/item enrichment, payment and item rollups |
| Marts | 5 | tables | 2 facts + 3 dimensions |

Facts: `fct_orders` one row/order; `fct_order_items` one row/order line. Dimensions: customers, stores, products. Existing dimension metrics intentionally include all order statuses and represent order value, not recognized revenue. For completed sales filter `order_status='completed'`; for cash use `total_paid_amount`. Marts currently rebuild fully for this small demo; ingestion is incremental by date.

84 tests = original 82 structural checks + order/payment reconciliation + item multiplication checks.

## Orchestration and memory

DAG `retail_dbt_daily`: generate_batch → load_batch → dbt_build → export_snapshot.

Schedule 07:30 Bangkok; default batch is the previous Bangkok calendar date. Override `batch_date` (YYYY-MM-DD) and `orders_per_day` in the Airflow trigger dialog to backfill. `catchup=False`, `max_active_runs=1`, `max_active_tasks=1`. Each task retries twice after 2 minutes; execution timeout 20 minutes.

All three DAGs use pool `shared_pipeline` with one slot. Worker concurrency is also one, preventing task overlap even on manual runs or retries. This serializes tasks, not entire DAG runs. Retail has only one active run, so separate steps cannot conflict with another Retail writer. dbt and DuckDB use one thread; DuckDB memory limit 512MB does not cap total process/container RAM.

Windows start remains 06:40, IoT 07:00, Retail 07:30, safe-stop 08:00. Start unpauses IoT and Retail after existing network/health gates. Stop requires today's scheduled Retail success in addition to existing IoT success/Fabric pause/all-DAG-idle gates; it pauses both schedules and checks activity again before stopping. World Bank remains paused. If a gate fails, Docker stays running and the scheduled task retries as before.

## DBeaver snapshots

After successful dbt build, checkpoint and close the writer, copy into a unique timestamped file, open read-only to verify row counts, then publish `exports/latest.json` with filename/count/hash. Existing snapshot files are never overwritten; DBeaver can keep one open while the next batch runs. Snapshot queries do not expose the live volume. Snapshot retention is manual: disconnect and delete old exports when no longer needed. Do not point DBeaver at the operational file or run another writer concurrently.

## Commands

Run these from the shared Airflow project directory:

```powershell
docker compose build airflow-worker
docker compose up -d --no-deps airflow-worker
docker compose exec -T airflow-scheduler airflow pools set shared_pipeline 1 "Shared pipelines"
docker compose run --rm --no-deps --entrypoint /opt/retail-venv/bin/python airflow-worker /opt/retail/project/pipeline/verify.py
```

For a newly created empty volume only, initialize ownership before running Retail:

```powershell
docker compose run --rm --no-deps --user root --entrypoint sh airflow-worker -c 'mkdir -p /opt/retail/data && chown 50000:0 /opt/retail/data'
```

Use Airflow UI to trigger batches. Keep Docker running during processing. Do not use `docker compose down -v` to stop daily work: it removes named data volumes.

## Backup and recovery

Full pre-change backup: [backup folder](../backups/my_dbt_project_20260905_before_airflow/my_dbt_project).
Original DuckDB SHA256: `04C66358B51396972C0D55C09452F60EA43ADA556CECA61E7A91C48FFB8E9A66`, verified identical in backup.

Existing shared-repository uncommitted user changes were preserved. Retail's legacy database is retained. To revert the worker, restore its original inherited image/volume configuration only after stopping Retail runs; preserve the volume. Reverting Retail integration also requires restoring the old Windows gates and DAG pool defaults, not merely deleting the DAG file.

## Progress log

| Step | Status | Evidence |
|---|---|---|
| 1. Inspect/backup | Complete | Shared runtime inspected; full Retail backup with matching DB hash |
| 2. Isolated dependencies | Complete | Airflow and dbt environments pass pip check |
| 3. Daily ingestion | Complete | Deterministic generate; transactional date replacement |
| 4. Models/tests | Complete | 21 models + 84 tests pass twice in integration fixture |
| 5. Repeat/backfill/snapshot | Complete | 225 rows after rerun/resize/backfill; 325 after next day; old snapshot stayed readable |
| 6. Live Airflow integration | Complete | Scheduled run + explicit-date manual run + blank-date manual run all succeeded; export mount issue corrected and retry verified |
| 7. Operational schedule | Complete | Syntax passed; live safe-stop CheckOnly passed with existing successful IoT run, today Retail success, zero active runs and F2 Paused |
| 8. Final handoff | Complete | Worker recreated idle; DB hash unchanged and 100 orders retained; all 8 services healthy; next Retail 2026-09-06 07:30 Bangkok |

Implementation: 8/8 complete. Local Git initialized (no remote push). Next optional operational observation: the combined unattended cycle on 2026-09-06; not yet verified. Dashboard remains deferred.

### Final validation evidence
- Live runs: scheduled__2026-09-05T00:30:00+00:00, retail-validation-20260905, retail-default-date-validation-20260905: success.
- All three processed 2026-09-04; operational database still has exactly 100 unique orders (not 300).
- DB SHA256 before/after worker recreation: 555146071ff9ddcf6899cc1ee57b60141dc4b6566989b8ff93f80de055c53f4a.
- Safe-stop check used existing successful IoT run manual-connectivity-check-20260905T033000Z; no Fabric execution was triggered. Actual stop was not performed.
- Eight running services healthy; observed summed container memory around 1.7 GiB when idle (not a peak or total WSL measurement).
- Invariant Gregorian date formatting added for the safe-stop default run ID to avoid Thai Buddhist-calendar year formatting.

