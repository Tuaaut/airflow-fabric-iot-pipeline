# Project Status: Airflow + Fabric + Power BI Demo

Last updated: 2026-09-05 Bangkok

## Shared Retail integration (2026-09-05)

The existing Airflow now also hosts `retail_dbt_daily` at 07:30 Bangkok, ingesting the previous day's synthetic retail data. See the [Retail blueprint](../DBT/my_dbt_project/DeploymentAndLogic.md) for its model, progress and recovery notes.

- No additional persistent services: only the existing worker uses extended image `local/airflow-retail:3.2.2`, with dbt isolated in `/opt/retail-venv`.
- All three DAGs use one-slot `shared_pipeline`; worker concurrency is 1. World Bank remains paused. IoT scheduling/business logic is unchanged.
- Retail data uses a separate named DuckDB volume; timestamped DBeaver snapshots are exported to the Retail project, never to the IoT data folders.
- Daily start remains 06:40 and now unpauses both IoT and Retail. Safe-stop remains 08:00 and additionally requires today's scheduled Retail run to succeed. It pauses both DAGs and rechecks active runs before stopping Docker.
- Integration fixture: repeated/resized/backfilled dates, 21 models + 84 tests, and a held-open snapshot reader passed. Three live Retail runs passed; worker recreation preserved the DB hash and 100 unique orders. All 8 services are healthy. Safe-stop CheckOnly passed without stopping Docker or triggering Fabric. Full evidence is in the Retail blueprint.
- Earlier operational descriptions mentioning only the main DAG's start/stop gates are superseded by this section. The next real unattended combined cycle is 2026-09-06; it has not yet been observed.

## Windows Migration Progress

This section is the authoritative progress log for the completed macOS-to-Windows migration.

| Step | Status | Evidence / result |
|---:|---|---|
| 1. Recover Git repository and `.env.example` | Complete | Restored `.git` from `origin/main`, preserved newer local documentation, restored tracked `.env.example`, and verified `main...origin/main`. |
| 2. Repair Docker Desktop PATH and WSL2 access to `E:` | Complete | Docker Desktop 4.89.0 / Engine 29.7.2 / Compose 5.5.0 work; a Linux container successfully read a bind mount from this project on `E:`. The current Codex process needs a PATH prefix until Codex is restarted. |
| 3. Create a safe Windows `.env` | Complete | Created a Git-ignored `.env` with newly generated local secrets. Local validation used `FABRIC_MODE=local`; after validation, the required cloud IDs and a new one-year Windows service-principal credential were added for scheduled Fabric runs. |
| 4. Validate Compose and start local mode | Complete | `docker compose config --quiet` passed; initialization exited 0; all 8 services were verified healthy. The final resting state is intentionally stopped by the safe-stop task. |
| 5. Test Machine API and local Airflow without resuming F2 | Complete | Machine API and Airflow health endpoints passed; no DAG import errors; manual validation run `windows-local-validation-20260904T143500Z` completed all 9 tasks; DAG was paused again; Azure reported F2 state `Paused` afterward. |
| 6. Verify Fabric/Azure authentication on Windows | Complete | Azure CLI user authentication can read F2. Fabric CLI 1.7.0 is authenticated as `airflow-fabric-demo-sp` and can list the target workspace plus its Lakehouse, notebooks, SQL endpoint, and semantic model. A Windows-specific one-year app credential was appended without removing the existing credential; non-secret cloud IDs and the new secret are stored only in the Git-ignored `.env`. |
| 7. Controlled Fabric flow; confirm F2 returns to Paused | Complete | Controlled run `windows-fabric-validation-20260904T145100Z` completed all 9 tasks in about 3m17s: F2 resume, Machine API extract, OneLake upload, Fabric notebook, curated validation, Power BI refresh, and F2 pause. The DAG was paused again and Azure reported F2 `Paused` on two post-run checks. |
| 8. Replace macOS `launchd` with PowerShell + Task Scheduler | Complete | Replaced the macOS scripts with four PowerShell 5.1 scripts and installed `AirflowFabric-Start` (06:40) plus `AirflowFabric-SafeStop` (08:00). Verified pass/fail-closed gates, a real scheduled stop, a cold Docker Desktop start, and a second safe stop. Both tasks are `Ready`, last result 0, and retry up to 6 times every 10 minutes. Final state: Docker stopped and F2 `Paused`. |
| 9. Make Windows the documentation source of truth | Complete | Rewrote current runtime, safety, caveats, commands, and next steps for Windows; aligned `README.md`, `PROJECT_DETAILS.md`, `.env.example`, and the existing automation README. Stale-current-state scan and Markdown link checks passed. |

Migration status: 9/9 complete. The first unattended Windows schedule exposed a network-readiness gap; the incident and completed hardening are recorded below. Next operational checkpoint: verify the hardened unattended schedule on 2026-09-06 (06:40 start, 07:00 DAG, 08:00 safe stop).

## Unattended Schedule Incident and Hardening (2026-09-05)

| Item | Result |
|---|---|
| Scheduled start | `AirflowFabric-Start` ran at 06:40 and made all 8 local services healthy. |
| DAG outcome | `scheduled__2026-09-05T00:00:00+00:00` failed because both configured public DNS resolvers timed out inside Docker; `login.microsoftonline.com` could not be resolved. |
| Windows root cause | The laptop entered Modern Standby while connected to AC power. The AC display-idle timer is 10 minutes, while both AC sleep timers are set to Never. Its automatically preferred network was a phone hotspot, which disconnected overnight and was no longer visible. The home Wi-Fi profile was configured for manual connection, so Windows did not reconnect on its own and the laptop stayed offline until the morning. |
| Modern Standby prevention | Installed and verified `AirflowFabric-KeepAwakeOnAC` in `Running` state. The user-logon task holds a Windows system-required power request while the user remains signed in and AC is connected. It releases the request on battery and does not keep the display on. |
| Why migration validation missed it | The controlled validation ran while Windows already had Internet access. The original start script checked only Docker engine and local container health; it did not test Windows or worker DNS/HTTPS and did not simulate Modern Standby with no associated Wi-Fi network. |
| Wi-Fi correction | The home Wi-Fi profile is now auto-connect and first in priority order. The phone hotspot remains available as a secondary profile. |
| Scheduler correction | Both Windows tasks now require network availability while retaining wake-to-run, start-when-available, and the existing retry policy. |
| Startup correction | The start script waits for Windows DNS/HTTPS before starting Docker, then requires the Airflow worker to resolve and reach Microsoft login over HTTPS before the DAG can be unpaused. |
| Docker DNS correction | Removed fixed `1.1.1.1` / `8.8.8.8` overrides. Docker now forwards DNS through the active Windows network. |
| Live verification | At 08:30-08:32, both new connectivity gates passed, Microsoft login returned HTTP 200 from the worker, all 8 services were healthy, and active DAG runs were 0. |
| Remaining checkpoint | Confirm the full unattended 06:40 / 07:00 / 08:00 cycle on 2026-09-06. The failed 2026-09-05 DAG was not retried automatically. |

## Status Note (2026-09-04)

```text
Contabo VPS subscription: CANCELLED (paid period ended 2026-07-12, server deprovisioned).
Runtime NOW: Windows 11 + Docker Desktop + WSL2 from this repository on drive E:.
Docker Desktop is intentionally stopped outside the daily automation window.
Airflow UI while running: http://localhost:8080 (credentials are stored only in .env).
Schedule: Windows Task Scheduler starts Docker/Airflow at 06:40 Bangkok and safely stops
them at 08:00. The main DAG runs @daily at 00:00 UTC / 07:00 Bangkok.
Main DAG is paused while Docker is off; the start task unpauses it after health checks.
Secondary world_bank_indicators DAG remains paused.
Next scheduled run: 2026-09-05 00:00 UTC / 07:00 Bangkok.
Verified 2026-09-04: local validation and a controlled Fabric run completed all 9 tasks.
The Fabric run resumed F2, extracted Machine API data, uploaded to OneLake, ran the
notebook, validated curated tables, refreshed the semantic model, and paused F2.
Fabric F2 capacity fabf2sea01: Paused between runs; final Azure check = Paused.
Concurrency guard: main DAG max_active_runs=1.
Shutdown guard: daily DAG success + pause task success + zero active DAG runs + F2 Paused.
```

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
* Portable Docker Compose runtime (Windows 11 + WSL2 now; Linux host optional)

## Current Architecture

```text
Windows 11 host - Docker Desktop (WSL2 Linux containers) - Docker Compose
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

Previous local development architecture (historical):

```text
Mac Docker Compose
    ↓
Same Airflow → Machine API → Fabric → Power BI pipeline
```

## Current Operating State

```text
Runtime host: Windows 11, repository E:\DE-BI-ML-Projects\airflow-fabric-iot-pipeline
Container runtime: Docker Desktop 4.89.0, Engine 29.7.2, Compose 5.5.0, WSL2 backend
Airflow image: apache/airflow:3.2.2; CeleryExecutor; 8 healthy runtime services when started
Airflow UI while running: http://localhost:8080 (credentials stored only in Git-ignored .env)
Main DAG: qr_printing_machine_api_ingestion, @daily 00:00 UTC / 07:00 Bangkok, max_active_runs=1
Secondary DAG: world_bank_indicators, paused
Latest controlled Fabric run: windows-fabric-validation-20260904T145100Z - success, all 9 tasks
Next scheduled run: 2026-09-05 00:00 UTC / 07:00 Bangkok
Fabric capacity: fabf2sea01, F2, Southeast Asia - Paused
Fabric workspace: airflow-fabric-demo-dev (Lakehouse, 2 notebooks, SQL endpoint, semantic model)
Final resting state: Docker Desktop stopped; both Windows scheduled tasks Ready, last result 0
```

Important:

```text
Windows Task Scheduler owns the daily runtime window. AirflowFabric-Start runs at 06:40,
starts Docker/Compose, waits for all 8 services to become healthy, verifies zero active runs,
then unpauses the main DAG. AirflowFabric-SafeStop runs at 08:00 and stops Docker only after
the expected daily DAG and pause_fabric_capacity task succeed, all DAG runs are inactive,
and Azure reports F2 Paused. A failed gate leaves Docker running and retries every 10 minutes
up to 6 times. Both tasks use wake-to-run and the current user's interactive token, so the
user must remain signed in and Windows wake timers must be enabled.

Do not also enable Docker Desktop auto-start at sign-in unless these scheduled tasks are
disabled first. See scripts/docker-auto/README.md for installation and test commands.
```

## Latest Local Documentation Updates

Updated through 2026-09-04:

```text
Fabric CLI on Windows: fab version 1.7.0, authenticated as airflow-fabric-demo-sp
Alerting doc added: ALERTING_MONITORING.md
Logic Apps alert placeholders added to .env.example
Budget alert recipient documented as Pattaratua@gmail.com
Learning/quiz files created locally only, not pushed to GitHub
```

What is done:

```text
Azure budget alert recipient is documented as Pattaratua@gmail.com.
Daily pipeline completion email design is documented.
Recommended notification path is Airflow → Logic Apps → email.
```

What is not done yet:

```text
Airflow does not yet send an automatic email after the scheduled daily run.
Logic Apps workflow has not yet been created/authenticated.
Airflow DAG has not yet been modified with send_pipeline_alert_to_logic_app.
Fabric CLI authentication is working; the Windows service-principal credential expires 2027-09-04.
```

## Local-Only Learning Files

The Airflow/Fabric quiz and learning helper files are intentionally kept local and are not uploaded to GitHub.

Local-only files:

```text
LEARNING_AND_QUIZ.md
airflow_fabric_quiz.html
```

Reason:

```text
These files are personal learning aids for guided practice. The public GitHub repo should stay focused on the project showcase, architecture, implementation status, screenshots, and reusable documentation.
```

Git handling:

```text
The files remain local in the Windows workspace and are not committed or pushed.
```

## Files

Core Airflow DAG:

```text
dags/qr_printing_machine_api_dag.py
```

Local simulated Machine API:

```text
machine-api/app.py
machine-api/Dockerfile
machine-api/requirements.txt
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
* Windows Task Scheduler unpauses the main DAG only during the daily runtime window.
* Local stack was stopped on 2026-06-13 when the scheduler moved to the Contabo VPS; it returned to macOS on 2026-09-01 and migrated to Windows on 2026-09-04.

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

VPS details (HISTORICAL - server cancelled and deprovisioned 2026-07-12):

```text
Provider: Contabo
Plan: Cloud VPS 10 NVMe (no setup)
CPU/RAM: 4 vCPU / 8 GB RAM
Location: Hub Europe
OS: Ubuntu 24.04
IPv4: <vps-ip>
SSH user: <ssh-user>
Project path: /opt/airflow-fabric-iot-pipeline
Monthly price shown: EUR 5.50
Paid period ended: 2026-07-12
Status: CANCELLED - auto-renewal off, server no longer exists
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

Verified on 2026-09-04 on Windows:

```text
Git repository and .env.example restored; .env remains Git-ignored.
Docker Desktop PATH/WSL2/E: bind mounts verified.
Local-mode run: windows-local-validation-20260904T143500Z - success, all 9 tasks.
Fabric-mode run: windows-fabric-validation-20260904T145100Z - success, all 9 tasks.
Main DAG concurrency: max_active_runs=1.
Main DAG final state: paused (the start task unpauses it during the daily window).
Secondary DAG: paused.
F2 capacity final state: Paused, confirmed after the Fabric run and after automation tests.
Task Scheduler: AirflowFabric-Start and AirflowFabric-SafeStop Ready; last result 0.
Docker Desktop final state: stopped intentionally.
```

Historical Azure cost check from 2026-06-13 (not a current cost figure):

```text
Month-to-date actual cost shown by Azure Cost Management API: about $0.738 USD
fabf2sea01 current paid F2 capacity: about $0.726 USD
fabf2wus201 deleted old test F2 capacity: about $0.012 USD historical usage
Budget current spend: about $0.738 / $20
Cost data can lag by several hours.
```

## Important Caveats

### Windows Task Scheduler Owns the Runtime Window

```text
The Windows user must remain signed in; the tasks use Interactive logon type.
WakeToRun and StartWhenAvailable are enabled, but Windows wake timers must also be allowed.
If the 08:00 safety gate fails, Docker stays running and the task retries every 10 minutes.
Do not force-close Docker while F2 is Active or any DAG run is queued/running.
Do not enable Docker Desktop auto-start at sign-in while this schedule is active.
See scripts/docker-auto/README.md.
Editing a DAG file here takes effect on the next parse - no deploy step (the stack mounts ./dags).
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
http://localhost:8080 (only while the Windows Docker runtime is running)
```

This is HTTP. Keep Windows Firewall/network exposure restricted to the local machine unless remote access is intentionally secured.

For a longer-running or shared demo, add:

```text
Domain name
Reverse proxy such as Caddy or Nginx
Free Let's Encrypt certificate
Dedicated production identity instead of the local generated admin credential
Possibly IP allowlisting or VPN
```

## Alternative Runtime Options

The current source-of-truth runtime is Windows Task Scheduler + Docker Desktop.
The stack is Apache Airflow 3 CeleryExecutor with 8 runtime services. If an
always-on remote host is needed later, these remain alternatives:

Cheaper than the old Contabo VPS (EUR 5.50 / ~USD 12 per month):

| Option | Specs | Cost | Notes |
|---|---|---|---|
| **Oracle Cloud Always Free** (Ampere A1, ARM) | up to 4 OCPU / 24 GB | **USD 0 / month, forever** | ARM image compatibility must be revalidated before migration. Free-tier capacity can be scarce. |
| **Netcup** VPS ARM G11 | 4 vCPU / 8 GB / 256 GB | ~EUR 3.25 / month | Cheapest reliable paid, always-on. |
| **Hetzner Cloud** CX22 | 2 vCPU / 4 GB / 40 GB | ~EUR 3.79 / month | Note: Hetzner previously required extra ID verification. |
| **Azure VM B1s, auto-stopped** | 1 vCPU / 1 GB (too small alone) or B2s 2 vCPU / 4 GB | ~USD 0.10 / month run cost + ~USD 1.5 / month for the managed disk when deallocated | Only viable with a start/stop automation around each run; adds moving parts. |
| **GitHub Actions** (scheduled workflow) | ephemeral CI runner | **USD 0** (public repo) | No server. The workflow does `docker compose up`, triggers the DAG, waits, tears down. Changes the story from "Airflow on a server" to "Airflow in CI". |

Current recommendation: keep the verified Windows schedule. Revisit an always-on
host only if unattended execution while signed out becomes a requirement.

Deploy is identical on any of them: install Docker + the compose plugin,
`git clone` into `/opt/airflow-fabric-iot-pipeline`, `cp .env.example .env` and
fill it in, `docker compose up airflow-init` then `docker compose up -d`.

## Useful Windows Commands

Run these from the Windows project root. The current Codex process may need a
restart before it inherits Docker's machine-level PATH; Task Scheduler scripts
use the absolute Docker CLI path and are not affected.

Start the stack:

```bash
docker compose up -d
```

Check containers:

```bash
docker compose ps
```

Check Airflow health in PowerShell:

```bash
Invoke-RestMethod http://localhost:8080/api/v2/monitor/health
```

Check Machine API health in PowerShell:

```bash
Invoke-RestMethod http://localhost:8000/health
```

Open Airflow UI:

```text
http://localhost:8080   (or http://<host-ip>:8080 on a remote runtime)
```

To deploy to a new runtime host (generic):

```bash
# on the host, after installing docker + docker compose plugin:
git clone https://github.com/Tuaaut/airflow-fabric-iot-pipeline.git /opt/airflow-fabric-iot-pipeline
cd /opt/airflow-fabric-iot-pipeline
cp .env.example .env      # then fill in the real values
docker compose up -d
```

Test one hourly API window:

```bash
curl -s 'http://localhost:8000/v1/qr-printing/lines/LINE_01/window?start_ts=2026-06-12T15:00:00Z&end_ts=2026-06-12T16:00:00Z' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["record_counts"])'
```

Pause DAG:

```bash
docker compose exec --no-TTY airflow-scheduler airflow dags pause -y qr_printing_machine_api_ingestion
```

Unpause DAG:

```bash
docker compose exec --no-TTY airflow-scheduler airflow dags unpause -y qr_printing_machine_api_ingestion
```

Trigger manual DAG run:

```bash
docker compose exec --no-TTY airflow-scheduler airflow dags trigger qr_printing_machine_api_ingestion
```

Check DAG run state:

```bash
docker compose exec --no-TTY airflow-scheduler airflow dags state qr_printing_machine_api_ingestion '<RUN_ID>'
```

Check task states:

```bash
docker compose exec --no-TTY airflow-scheduler airflow tasks states-for-dag-run qr_printing_machine_api_ingestion '<RUN_ID>'
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

1. Let the first unattended Windows run fire on 2026-09-05: start task 06:40, DAG 07:00, safe-stop task 08:00 Bangkok. Keep the Windows user signed in, the PC powered, and wake timers enabled.
2. Confirm both scheduled tasks return result 0, the DAG completes all 9 tasks, F2 returns to `Paused`, and Docker Desktop stops.
3. Check Azure Cost Management later; cost data can lag several hours.

### Optional Improvements

1. Implement the documented Logic Apps completion/failure email alert.
2. Move the service-principal secret from `.env` to Key Vault or another runtime secret store.
3. Add HTTPS and access controls if the Airflow UI is ever exposed beyond localhost.
4. Consider an always-on runtime only if execution while the Windows user is signed out becomes necessary.

### Later

1. Build Power BI report/dashboard when pipeline work is stable.
2. Consider productionizing secrets with Key Vault or managed identity.
3. Consider moving from local `.env` secret handling to a safer deployment pattern.


## Laptop memory investigation — 2026-09-07

- Completed: Windows automatic pagefile management enabled (Windows restart pending). User WSL config now limits all WSL 2 distributions to memory=6GB and swap=4GB, with autoMemoryReclaim=dropCache, effective on next WSL start.
- Reviewed: Windows start/safe-stop tasks use IgnoreNew; Celery concurrency=1; primary DAGs max_active_runs=1. No demonstrated duplicate-run problem and no schedule/Compose changes made.
- Found: 06:40 start failed at 06:45:13 because Docker engine never became ready; 08:00 safe-stop failed because engine was unavailable. Windows memory events show host com.docker.backend.exe growing afterward. This process is outside the WSL memory ceiling; root cause remains unconfirmed.
- Checked: docker compose config --quiet passed. Docker/WSL were stopped; no cloud-connected workload was started for testing.
- Next: after Windows restart, verify effective limits and observe Docker startup, host backend memory, and WSL/container memory. Preserve Fabric pause/safe-stop checks.
- [Full investigation and progress log](C:/Users/Pattara_Personnel/Documents/Codex/2026-09-07/ple/outputs/laptop-stability.md)
