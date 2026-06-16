# Project Status: Airflow + Fabric + Power BI Demo

Last updated: 2026-06-13 18:45 Bangkok

## Document Map

Read these in order:

1. [README.md](README.md): GitHub-facing project pitch and showcase overview.
2. [PROJECT_DETAILS.md](PROJECT_DETAILS.md): full project concept, architecture, domain, and operating model.
3. [PROJECT_STATUS.md](PROJECT_STATUS.md): current implementation status, completed work, caveats, and next steps.
4. [ALERTING_MONITORING.md](ALERTING_MONITORING.md): daily pipeline email-alerting design.
5. [FABRIC_CLEANUP_INVENTORY.md](FABRIC_CLEANUP_INVENTORY.md): Fabric workspace and capacity inventory.

## Current Goal

Build a realistic Airflow orchestration demo for an industrial high-speed QR printing machine used in beverage bottle/can traceability.

The project demonstrates:

* Dockerized Apache Airflow
* API-based machine data ingestion
* Microsoft Fabric Lakehouse raw landing
* Fabric notebook transformation
* Fabric Delta tables and SQL endpoint validation
* Power BI semantic model refresh
* Paid Fabric F2 pause/resume cost control
* Migration from local Mac Docker to a low-cost Ubuntu VPS

## Current Architecture

```text
Contabo Ubuntu VPS Docker Compose
    ↓
Apache Airflow
    ↓
Machine API container
    ↓
Raw JSON uploaded to Fabric OneLake / Lakehouse Files
    ↓
Fabric notebook transforms latest raw JSON
    ↓
Fabric Lakehouse Delta tables
    ↓
SQL analytics endpoint validates tables
    ↓
Power BI semantic model refresh
    ↓
Airflow pauses Fabric F2 capacity
```

Previous local development architecture:

```text
Mac Docker Compose
    ↓
Same Airflow → Machine API → Fabric → Power BI pipeline
```

## Current Operating State

```text
Airflow UI: http://<vps-ip>:8080
Airflow login: <airflow-user> / <airflow-password>
Machine API health: http://<vps-ip>:8000/health
Main DAG: qr_printing_machine_api_ingestion
DAG schedule: daily at 00:00 UTC / 07:00 Bangkok
DAG state: unpaused
Runtime host: Contabo Cloud VPS 10 NVMe
VPS IP: <vps-ip>
VPS SSH user: <ssh-user>
Project path on VPS: /opt/airflow-warehouse-dashboard
Fabric capacity: fabf2sea01, F2, Southeast Asia
Fabric capacity state: Paused
Daily data volume: about 4,800 print events/day
```

Important:

```text
The production-style demo scheduler now runs on the Contabo VPS.
The Mac no longer needs to stay awake for the daily Airflow schedule.
The local Mac copy remains useful for development and editing.
The local Docker Compose Airflow stack is currently stopped.
```

## Files

Core Airflow DAG:

```text
dags/qr_printing_machine_api_dag.py
```

Local simulated Machine API:

```text
machine_api/app.py
machine_api/Dockerfile
machine_api/requirements.txt
```

Fabric notebook source files:

```text
fabric/notebooks/qr_printing_transform.py
fabric/notebooks/semantic_model_setup.py
```

Validation/helper script:

```text
scripts/smoke_test_machine_api.py
```

Infrastructure/config:

```text
docker-compose.yaml
.env
README.md
AGENTS.md
PROJECT_STATUS.md
FABRIC_CLEANUP_INVENTORY.md
```

## Completed Work

### 1. Local Airflow Stack

Completed:

* Docker Compose Airflow stack was built and tested locally.
* Local Airflow services were previously healthy:
  * apiserver
  * scheduler
  * dag processor
  * triggerer
  * worker
  * postgres
  * redis
* Main DAG is visible in Airflow UI.
* DAG has been changed from hourly to daily.
* DAG is unpaused for daily automation.
* Local stack was stopped on 2026-06-13 with `docker compose down` because the VPS is now the scheduler.

Current schedule:

```text
0 0 * * *
00:00 UTC daily
07:00 Bangkok daily
```

### 1A. Contabo VPS Airflow Deployment

Completed on 2026-06-13:

* Chose Contabo after Hetzner required additional ID verification.
* Ordered Contabo Cloud VPS 10 NVMe.
* Installed Docker and Docker Compose on Ubuntu 24.04.
* Synced this project to the VPS.
* Initialized Airflow metadata DB and admin user.
* Started the Airflow Docker Compose stack.
* Opened firewall ports for SSH, Airflow, and the Machine API.
* Cancelled Contabo auto-renewal at the end of the paid period.

VPS details:

```text
Provider: Contabo
Plan: Cloud VPS 10 NVMe (no setup)
CPU/RAM: 4 vCPU / 8 GB RAM
Location: Hub Europe
OS: Ubuntu 24.04
IPv4: <vps-ip>
SSH user: <ssh-user>
Project path: /opt/airflow-warehouse-dashboard
Monthly price shown: EUR 5.50
Next payment date: 2026-07-12
Cancellation date: 2026-07-12
Auto-renewal status: cancellation scheduled for end of current paid period
```

Do not store the VPS root password in this repo.

Installed server packages:

```text
docker.io
docker-compose-v2
git
rsync
ufw
curl
```

Verified versions:

```text
Docker: 29.1.3
Docker Compose: 2.40.3+ds1-0ubuntu1~24.04.1
```

Firewall state:

```text
OpenSSH allowed
8080/tcp allowed for Airflow UI/API
8000/tcp allowed for Machine API
```

Verified public endpoints:

```text
Airflow UI: http://<vps-ip>:8080
Machine API health: http://<vps-ip>:8000/health
Machine API health response: {"status":"ok"}
Airflow public HTTP status: 200
```

Running Docker services on VPS:

```text
airflow-apiserver
airflow-scheduler
airflow-dag-processor
airflow-triggerer
airflow-worker
postgres
redis
machine-api
```

Note:

```text
The Airflow URL currently uses plain HTTP by IP address.
Chrome shows "Not Secure" because HTTPS is not configured yet.
This is normal for the current demo setup, but do not use it for sensitive production access.
```

### 2. Machine API

Completed:

* Local FastAPI service simulates realistic QR printing machine data.
* Endpoint accepts a maximum 1-hour window.
* Airflow daily DAG calls the API 24 times, one call per hour, then merges the responses.

Endpoint pattern:

```text
/v1/qr-printing/lines/LINE_01/window?start_ts=...&end_ts=...
```

Generated data:

* `print_events`
* `machine_telemetry`
* `machine_logs`
* `record_counts`
* `source_windows` in the merged daily payload

Current simulator volume:

```text
MACHINE_PRINT_EVENTS_PER_HOUR=200
1 hour = 200 print events + 60 telemetry rows
24 hours = about 4,800 print events + 1,440 telemetry rows
```

Reason for reducing volume:

```text
The original simulator generated about 47,000+ print events/hour.
That would create about 1.1M print events/day and keep F2 active longer.
The current 200/hour setting is better for low-cost demo operation.
```

### 3. Fabric Workspace and Lakehouse

Active workspace:

```text
airflow-fabric-demo-dev
Workspace ID: <fabric-workspace-id>
Region: Southeast Asia
Capacity: fabf2sea01
```

Active Fabric items:

```text
Lakehouse:      lh_qr_printing_demo
SQLEndpoint:    lh_qr_printing_demo
Notebook:       nb_qr_printing_transform
Notebook:       nb_semantic_model_setup
SemanticModel:  sm_qr_printing_demo
```

### 4. Fabric Transform Notebook

Fabric notebook:

```text
nb_qr_printing_transform
```

Local source:

```text
fabric/notebooks/qr_printing_transform.py
```

Completed fixes:

* Notebook handles empty `machine_logs` without failing.
* Notebook was fixed on 2026-06-13 to avoid choosing the largest `start_hour=...` folder.
* Notebook now prefers newest `uploaded_at=...` folders.
* When no `uploaded_at=...` folders exist yet, notebook falls back to the most recently modified `machine_api_response.json`.
* Notebook successfully writes selected raw data to Delta tables with overwrite mode.

Tables produced:

```text
dim_fault_code
dim_line
dim_machine
dim_product
fact_machine_log
fact_machine_telemetry_minute
fact_print_event
hourly_kpi_summary
```

Old high-volume validation example from SQL endpoint:

```text
batch_id:  B202606124
latest_ts: 2026-06-12 15:59:59
rows:      48,858
```

That large batch was created before the simulator was reduced to 200 rows/hour.

Important cleanup on 2026-06-13:

```text
Problem:
  Old high-volume raw folders had later start_hour values than the newer reduced daily runs.
  The notebook selected start_hour=2026061215 / 2026061216-style data and produced about 47,776 rows for a one-hour batch.

Deleted wrong high-volume raw inputs from OneLake:
  Files/raw/qr_printing/machine_api_response.json
  Files/raw/qr_printing/start_hour=2026061207
  Files/raw/qr_printing/start_hour=2026061215

Remaining reduced-volume raw folders:
  Files/raw/qr_printing/start_hour=2026061200
  Files/raw/qr_printing/start_hour=2026061203
  Files/raw/qr_printing/start_hour=2026061210

Cloud notebook update:
  nb_qr_printing_transform was updated through Fabric item definition API.
  Fixed transform notebook was run manually and completed successfully at about 2026-06-13 11:41 UTC.
```

### 5. Power BI Semantic Model

Semantic model:

```text
sm_qr_printing_demo
Semantic model ID: <semantic-model-id>
```

Semantic setup notebook:

```text
nb_semantic_model_setup
```

Local source:

```text
fabric/notebooks/semantic_model_setup.py
```

Completed:

* Relationships created.
* Measures created.
* Relationship check passed in Fabric model view.
* Airflow successfully submits semantic model refresh.

Important measures include:

```text
OEE %
Availability %
Performance %
Quality %
QR Read Rate %
Reject Rate %
Items Processed
Fault Count
Average QR Grade Score
Average Printhead Temperature C
Average Vibration mm/s
```

Report/dashboard is intentionally skipped for now. Current focus is Airflow and pipeline automation.

### 6. Azure / Entra / Service Principal

Completed:

* Azure CLI installed and logged in.
* Entra app registration created:

```text
airflow-fabric-demo-sp
```

* Service principal created.
* Client secret added to local `.env`.
* Service principal added to Fabric workspace as Contributor.
* Service principal granted Azure Contributor on the Fabric F2 capacity so it can resume and suspend capacity.

Do not commit `.env` because it contains secrets.

### 7. Paid Fabric F2 Capacity

Completed:

```text
Capacity name:  fabf2sea01
Resource group: rg-fabric-capacities
Region:         Southeast Asia
SKU:            F2
State:          Paused when idle
Capacity ID:    <fabric-capacity-id>
```

Workspace assignment:

```text
Workspace: airflow-fabric-demo-dev
Capacity:  fabf2sea01
Status:    Assigned
```

Deleted old test capacity:

```text
fabf2wus201
Region: West US 2
```

### 8. Budget Guardrail

Azure budget created:

```text
Budget name: budget-fabric-demo-20usd
Scope:       Azure subscription 1
Amount:      $20/month
Alerts:      50%, 80%, 100%
Recipient:   Pattaratua@gmail.com
```

Important:

```text
Budget alerts are notifications only.
They are not a hard spending stop.
```

Budget alert recipient was updated to `Pattaratua@gmail.com` for this Fabric budget and the related Databricks project budgets.

### 9. End-to-End Automation Test

Controlled full-flow test completed:

```text
Run ID: manual_full_flow_test_patch_20260612T171134Z
DAG state: success
F2 final state: Paused
```

VPS manual run completed on 2026-06-13:

```text
Run ID: manual__2026-06-13T10:43:05.121078+00:00
DAG state: success
Start: 2026-06-13 17:43:05 Bangkok
End:   2026-06-13 17:53:31 Bangkok
Duration: about 10 minutes 25 seconds
F2 final state: Paused
```

Notes from this run:

```text
resume_fabric_capacity retried once, then succeeded.
extract_from_api, validate_raw, load_raw_to_fabric_lakehouse, trigger_fabric_transformation,
wait_for_fabric_transformation, validate_curated_tables, refresh_power_bi_semantic_model,
and pause_fabric_capacity all succeeded.

Power BI refresh history confirmed latest API refresh completed:
startTime: 2026-06-13T10:51:15.817Z
endTime:   2026-06-13T10:51:18.303Z
status:    Completed
```

Successful task flow:

```text
resume_fabric_capacity          success
extract_from_api                success
validate_raw                    success
load_raw_to_fabric_lakehouse    success
trigger_fabric_transformation   success
wait_for_fabric_transformation  success
validate_curated_tables         success
refresh_power_bi_semantic_model success
pause_fabric_capacity           success
```

This proves:

```text
Airflow can resume F2
Airflow can ingest API data
Airflow can upload to OneLake
Airflow can trigger Fabric notebook
Airflow can wait for notebook completion
Airflow can refresh Power BI semantic model
Airflow can pause F2 afterward
```

### 10. Daily Automation Setup

Current design:

```text
Airflow runs once daily at 07:00 Bangkok.
It processes the previous 24-hour data window.
It calls the Machine API once per hour, 24 calls total.
It merges the hourly responses into one daily raw JSON payload.
It uploads that payload into OneLake under uploaded_at=<upload-utc>/start_hour=<daily-window-start>.
It triggers the Fabric transform notebook.
It refreshes the semantic model.
It pauses F2.
```

Expected daily volume:

```text
Print events: about 4,800/day
Telemetry:    about 1,440/day
Logs:         variable
```

## Current Safety State

Verified on 2026-06-13:

```text
Runtime host: Contabo VPS
Airflow containers: running / healthy after startup
Machine API: healthy
DAG: unpaused
Public Airflow URL: http://<vps-ip>:8080
Public Machine API health URL: http://<vps-ip>:8000/health
F2 capacity: Paused
```

Azure cost check on 2026-06-13:

```text
Month-to-date actual cost shown by Azure Cost Management API: about $0.738 USD
fabf2sea01 current paid F2 capacity: about $0.726 USD
fabf2wus201 deleted old test F2 capacity: about $0.012 USD historical usage
Budget current spend: about $0.738 / $20
Cost data can lag by several hours.
```

Local Mac note:

```text
Mac Docker Desktop is no longer the required scheduler for daily automation.
Use it only for local development/testing unless intentionally moving the schedule back.
```

Current macOS power finding:

```text
AC power sleep = 0
```

That means the Mac should not idle-sleep while plugged in. No `pmset` scheduled wake command has been applied yet.

## Important Caveats

### Local Mac Is No Longer the Scheduler

This was true before the VPS migration.

Current state:

```text
Airflow now runs on the Contabo VPS.
The Mac does not need to remain awake for scheduled runs.
```

Residual caveat:

```text
If new code is changed locally, it must be synced/deployed to the VPS before it affects the running Airflow instance.
```

Current unsynced change:

```text
The local DAG now writes future raw uploads to uploaded_at=<UTC_RUN_TIME>/start_hour=<DATA_WINDOW>/...
This local DAG change must be deployed to the VPS before the scheduled VPS run uses the new upload layout.
The cloud Fabric notebook has already been updated.
```

### F2 Is Billable While Active

Fabric F2 is pay-as-you-go and not part of the Azure free tier.

Airflow should pause it after each run, but this should be checked after early scheduled runs.

### Budget Is Not A Hard Stop

The `$20/month` budget only sends alerts. It does not automatically stop F2.

### SQL Endpoint May Lag Briefly

After the Fabric notebook writes Delta tables, the SQL analytics endpoint may take a short time to show the latest results.

If a saved SQL query tab says "Can't find SQL analytics endpoint object", close that query tab and create a new SQL query.
That message can happen after Fabric refreshes/discards a blank query object; it does not mean the Delta tables were deleted.

### Airflow Is Exposed Over HTTP

Current Airflow access:

```text
http://<vps-ip>:8080
```

This is not HTTPS. Chrome will show "Not Secure".

For a longer-running or shared demo, add:

```text
Domain name
Reverse proxy such as Caddy or Nginx
Free Let's Encrypt certificate
Stronger Airflow admin password
Possibly IP allowlisting or VPN
```

## Useful Commands

Start local stack:

```bash
docker compose up -d
```

SSH to VPS:

```bash
ssh <ssh-user>@<vps-ip>
```

Go to project on VPS:

```bash
cd /opt/airflow-warehouse-dashboard
```

Start VPS stack:

```bash
docker compose up -d
```

Check VPS containers:

```bash
docker compose ps
```

Check VPS Airflow health:

```bash
curl http://localhost:8080/api/v2/monitor/health
```

Check VPS Machine API:

```bash
curl http://localhost:8000/health
```

Check local containers:

```bash
docker compose ps
```

Open Airflow:

```text
Local: http://localhost:8080
VPS:   http://<vps-ip>:8080
```

Check Machine API:

```text
Local: curl http://localhost:8000/health
VPS:   curl http://<vps-ip>:8000/health
```

Test one hourly API window:

```bash
curl -s 'http://localhost:8000/v1/qr-printing/lines/LINE_01/window?start_ts=2026-06-12T15:00:00Z&end_ts=2026-06-12T16:00:00Z' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["record_counts"])'
```

Pause DAG:

```bash
docker compose exec airflow-apiserver airflow dags pause qr_printing_machine_api_ingestion
```

Unpause DAG:

```bash
docker compose exec airflow-apiserver airflow dags unpause qr_printing_machine_api_ingestion
```

Trigger manual DAG run:

```bash
docker compose exec airflow-apiserver airflow dags trigger qr_printing_machine_api_ingestion
```

Check DAG run state:

```bash
docker compose exec airflow-apiserver airflow dags state qr_printing_machine_api_ingestion '<RUN_ID>'
```

Check task states:

```bash
docker compose exec airflow-apiserver airflow tasks states-for-dag-run qr_printing_machine_api_ingestion '<RUN_ID>'
```

Check Fabric capacity state:

```bash
az resource show \
  --ids /subscriptions/<azure-subscription-id>/resourceGroups/rg-fabric-capacities/providers/Microsoft.Fabric/capacities/fabf2sea01 \
  --api-version 2023-11-01 \
  --query '{state:properties.state, provisioningState:properties.provisioningState}' \
  -o json
```

## SQL Checks

Latest batch/table check:

```sql
SELECT
    batch_id,
    MIN(event_timestamp) AS first_ts,
    MAX(event_timestamp) AS latest_ts,
    COUNT(*) AS rows
FROM fact_print_event
GROUP BY batch_id
ORDER BY latest_ts DESC;
```

Recent rows:

```sql
SELECT TOP 20
    batch_id,
    event_id,
    event_timestamp,
    grade_score,
    line_id,
    machine_id
FROM fact_print_event
ORDER BY event_timestamp DESC;
```

## Previous Azure VM Plan

This was the previous infrastructure idea before choosing Contabo:

```text
Move Airflow Docker stack from local Mac to Azure Ubuntu VM.
```

Current decision:

```text
Use Contabo Cloud VPS 10 NVMe instead for lower cost and simpler setup.
Azure VM plan is parked for now.
```

Cleanup verification on 2026-06-13:

```text
Azure:
  No active Azure VM-related resources were found.
  Checked virtual machines, managed disks, public IPs, NICs, VNets, NSGs, NAT gateways, and load balancers.
  Active Azure resource found: Fabric capacity fabf2sea01 only.

Oracle Cloud / OCI:
  OCI CLI checked subscribed region ap-singapore-1.
  No compute instances, boot volumes, block volumes, reserved public IPs, VCNs, NAT gateways, service gateways, or load balancers were found.
  Only non-billable account/IAM/tag resources were visible.
```

Preferred free-tier candidate:

```text
Ubuntu
Standard_B2ats_v2
2 vCPU
1 GiB RAM
x86/AMD
2 GiB swap file
```

Why swap:

```text
Airflow Docker services need more memory than 1 GiB gives comfortably.
A swap file uses disk as emergency memory.
It is slower than RAM, but can prevent crashes from memory spikes.
```

Other free-tier candidates:

```text
Standard_B1s:      1 vCPU, 1 GiB RAM, x86-64, likely too small
Standard_B2pts_v2: 2 vCPU, 1 GiB RAM, ARM64, less ideal for Docker image compatibility
Standard_B2ats_v2: 2 vCPU, 1 GiB RAM, AMD x86-64, best free-tier candidate
```

VM cost notes:

```text
Eligible VM compute may be free for 750 hours/month for 12 months.
Disk, public IP, bandwidth, snapshots, backups, and monitoring can still create small charges.
```

Possible VM schedule:

```text
Always-on free-tier experiment:
  Keep VM running if compute stays within free allowance.

Cost-paranoid mode:
  Start VM around 06:30 Bangkok.
  Let Airflow run at 07:00.
  Deallocate VM around 08:00.
```

Deallocated means:

```text
CPU/RAM billing stops.
OS disk remains saved.
Disk and some attached resources may still cost.
```

## Next Steps

### Immediate

1. Deploy the local DAG change to the VPS so future uploads use `uploaded_at=<UTC_RUN_TIME>/start_hour=<DATA_WINDOW>/...`.
2. Let the next scheduled VPS Airflow run execute at 07:00 Bangkok.
3. Confirm the DAG run succeeds in Airflow.
4. Confirm `fabf2sea01` returns to `Paused`.
5. Confirm SQL endpoint shows reduced-volume data, not the old 47,776-row high-volume test batch.
6. Check Azure Cost Management later because cost data can lag.

### Next Infrastructure Step

1. Define a simple deployment flow from local Mac to VPS, for example `rsync`.
2. Change the default Airflow password.
3. Add HTTPS with a domain and Caddy/Nginx if this demo will be shared.
4. Consider adding a small Airflow/Fabric validation task that records selected raw path and row count.

### Later

1. Build Power BI report/dashboard when pipeline work is stable.
2. Consider productionizing secrets with Key Vault or managed identity.
3. Consider moving from local `.env` secret handling to a safer deployment pattern.
