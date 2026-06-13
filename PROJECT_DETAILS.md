# Project Details: Airflow + Fabric Orchestration Demo

## Document Map

Read these in order:

1. [README.md](README.md): GitHub-facing project pitch and showcase overview.
2. [PROJECT_DETAILS.md](PROJECT_DETAILS.md): full project concept, architecture, domain, and phases.
3. [PROJECT_STATUS.md](PROJECT_STATUS.md): current implementation status, completed work, caveats, restart notes, and next steps.
4. [FABRIC_CLEANUP_INVENTORY.md](FABRIC_CLEANUP_INVENTORY.md): Fabric workspace, item, capacity, and cleanup inventory.

Internal instruction file:

```text
AGENTS.md
```

## Objective

Build a cloud-based data engineering and BI demo project that demonstrates:

* Linux administration
* Docker
* Apache Airflow
* Microsoft Fabric
* Data Warehouse concepts
* Power BI Semantic Models
* Cost optimization using Fabric Pause/Resume

The goal is to learn Airflow while keeping cloud costs as low as possible.

## Final Architecture

```text
Contabo Ubuntu VPS
    ↓
Docker Compose
    ↓
Apache Airflow
    ↓
Machine API
    ↓
Raw API JSON to Fabric Lakehouse Files
    ↓
Fabric Notebook / Pipeline Transformation
    ↓
Microsoft Fabric Lakehouse / Warehouse
    ↓
Power BI Semantic Model (Import Mode)
    ↓
Power BI Dashboard
```

Local Mac Docker remains for development/testing only.

## Current Implementation Snapshot

As of 2026-06-13, the working implementation has moved from local Mac Docker to a Contabo VPS:

```text
Contabo Cloud VPS 10 NVMe / Ubuntu 24.04
    ↓
Docker Compose Airflow stack
    ↓
Daily DAG at 00:00 UTC / 07:00 Bangkok
    ↓
Machine API called for 24 hourly windows
    ↓
Merged daily raw JSON uploaded to Fabric OneLake
    ↓
Fabric notebook transforms latest uploaded raw JSON
    ↓
Lakehouse Delta tables and SQL endpoint
    ↓
Power BI semantic model refresh
    ↓
Airflow pauses Fabric F2 capacity
```

Current VPS access:

```text
VPS IP: <vps-ip>
SSH user: <ssh-user>
Project path: /opt/airflow-warehouse-dashboard
Airflow UI: http://<vps-ip>:8080
Machine API health: http://<vps-ip>:8000/health
Airflow login: <airflow-user> / <airflow-password>
```

Important:

```text
Do not store the VPS root password in this repo.
Airflow currently uses plain HTTP by IP address, so Chrome shows "Not Secure".
For a longer-running or shared demo, add a domain, HTTPS, and a stronger Airflow password.
Local Mac Docker Airflow is stopped; the VPS is the scheduler.
```

Contabo billing state:

```text
Plan: Cloud VPS 10 NVMe
Monthly price shown: EUR 5.50
Next payment date: 2026-07-12
Cancellation scheduled at: 2026-07-12
Meaning: auto-renewal should be stopped at the end of the current paid period.
```

Current data volume:

```text
MACHINE_PRINT_EVENTS_PER_HOUR=200
Expected daily print events: about 4,800
Expected daily telemetry rows: about 1,440
```

Current cost-control state:

```text
Fabric capacity: fabf2sea01
SKU: F2
Region: Southeast Asia
Idle state: Paused
Azure budget: budget-fabric-demo-20usd
Budget alerts: 50%, 80%, 100%
Month-to-date Azure cost checked on 2026-06-13: about $0.738 USD
```

Important:

```text
Budget alerts are notifications only.
They are not a hard cost stop.
F2 is billable while Active even if the Fabric/Power BI trial banner is visible.
```

## Why This Architecture

### Airflow

Purpose:

* Scheduling
* Dependency management
* Retries
* Monitoring
* Orchestration
* Triggering Fabric and Power BI jobs

Skills learned:

* DAGs
* Operators
* Scheduling
* Logging
* API orchestration
* External job monitoring
* Validation after cloud processing
* Data engineering best practices

### Fabric

Purpose:

* Data storage
* Data transformation
* Lakehouse
* Notebook or pipeline execution
* Curated Delta/Warehouse tables
* Warehouse
* Future Fabric learning

Using Fabric instead of BigQuery allows learning Microsoft's modern data platform.

### Power BI

Purpose:

* Semantic Model
* DAX
* Dashboarding
* Visualization

Power BI is the presentation layer.

## Fabric Cost Optimization Strategy

### Important

DO NOT leave Fabric F2 running 24/7.

If left running continuously:

```text
F2 ≈ $260-$320/month
```

Instead use:

```text
Resume Capacity
    ↓
Run Pipeline
    ↓
Refresh Semantic Model
    ↓
Pause Capacity
```

Microsoft supports pause/resume for F-SKU capacities.

## Daily Schedule Example

Current schedule:

```text
07:00 Bangkok / 00:00 UTC
Airflow starts daily run
Airflow resumes Fabric F2
Airflow processes previous 24 hours
Airflow triggers Fabric notebook
Airflow refreshes semantic model
Airflow pauses Fabric F2
```

Older conceptual example:

```text
05:55 Resume Fabric F2

06:00 Airflow starts

06:05 Load incremental data

06:10 Update Lakehouse/Warehouse

06:15 Refresh Semantic Model

06:25 Validation

06:30 Pause Fabric F2
```

Expected monthly Fabric cost:

```text
~$5-$15/month
```

for a small demo workload.

## Power BI Design

### Use Import Mode

Recommended:

```text
Fabric
    ↓
Import
    ↓
Power BI Semantic Model
```

Benefits:

* Fast dashboards
* Predictable costs
* Users can filter reports all day

Avoid:

```text
Direct Lake
DirectQuery
```

for this demo because they may require Fabric compute to remain available.

## Workspace Strategy

Recommended:

Workspace A:

```text
Fabric Workspace
```

Contains:

* Lakehouse
* Warehouse
* Notebooks
* Pipelines

Workspace B:

```text
Power BI Workspace
```

Contains:

* Semantic Model
* Reports
* Dashboards

Reason:

If Fabric capacity is paused, Fabric workloads become unavailable. Separating Power BI assets from Fabric workloads provides more flexibility.

## Licensing

Developer:

```text
Power BI Pro
```

Customer:

```text
Power BI Pro
```

Because F2 does not remove the Power BI Pro requirement for normal Power BI Service consumption.

F64 and above are the tiers where free users can consume Power BI content directly through the Power BI Service.

Current trial note:

```text
The Fabric UI currently shows "Trials activated: 29 days left" for the user account.
That trial can help with Power BI/Fabric user features during the trial window.
It does not make the paid Azure Fabric F2 capacity free.
After trial expiry, Power BI Pro is still expected for creators/viewers unless the content is on a higher capacity tier such as F64+.
```

## Ubuntu VM Specification

Recommended smooth VM:

```text
Ubuntu 22.04 LTS

2 vCPU
4 GB RAM
30 GB SSD
```

Software:

```text
Docker
Docker Compose
Apache Airflow
Python
Git
```

Future Azure free-tier VM review:

```text
After local scheduling is stable, evaluate whether Airflow can run on an Azure free-tier VM.
```

Current free-tier candidate plan:

```text
Ubuntu
Standard_B2ats_v2
2 vCPU
1 GiB RAM
x86/AMD
2 GiB swap file
```

Free-tier candidate comparison:

```text
Standard_B1s:      1 vCPU, 1 GiB RAM, x86-64, likely too small
Standard_B2pts_v2: 2 vCPU, 1 GiB RAM, ARM64, less ideal for Docker images
Standard_B2ats_v2: 2 vCPU, 1 GiB RAM, AMD x86-64, best free-tier candidate
```

Swap file meaning:

```text
A swap file uses disk as emergency memory when real RAM is full.
It is slower than RAM, but helps prevent Airflow/Docker crashes on a 1 GiB VM.
```

Cost caveat:

```text
Free-tier VM compute may be covered for 750 hours/month for 12 months,
but disk, static public IP, bandwidth, snapshots, backups, and monitoring can still cost.
```

## Demo Data Domain

Use a high-speed beverage can/bottle QR code printing line.

Business scenario:

```text
Each can or bottle must receive a unique readable QR code for traceability.
The line includes a printer or laser marker, conveyor encoder, vision camera, PLC, and reject gate.
```

Target grain:

```text
Production events: 1 row per printed item
Machine telemetry: 1 row per machine per minute
System logs: 1 row per machine event, fault, warning, or state change
```

## Source Data Design

### Transaction Data

These records represent production and traceability events.

Table:

```text
fact_print_event
```

Example columns:

```text
event_id
event_timestamp
line_id
machine_id
product_sku
batch_id
qr_code
print_result
vision_result
reject_flag
reject_reason
position_error_mm
grade_score
```

Use for:

* Items processed
* Printed items
* Good QR count
* Bad QR count
* Missing code count
* Duplicate code count
* Reject count
* Traceability audit
* Quality rate

### Machine Telemetry

These records represent sensor readings and machine condition.

Table:

```text
fact_machine_telemetry_minute
```

Example columns:

```text
timestamp_minute
line_id
machine_id
machine_status
planned_speed_cpm
actual_speed_cpm
printhead_temp_c
ink_level_pct
ink_consumed_ml
vibration_mm_s
air_pressure_bar
items_processed
```

Use for:

* Throughput
* Speed loss
* Ink consumption
* Temperature trend
* Vibration trend
* Machine health monitoring
* Hourly aggregation

### System Logs

These records represent faults, warnings, operator actions, and state changes.

Table:

```text
fact_machine_log
```

Example columns:

```text
log_id
log_timestamp
line_id
machine_id
event_type
severity
fault_code
fault_description
operator_id
state_from
state_to
duration_seconds
```

Use for:

* Downtime events
* Fault count
* Warning count
* MTBF
* MTTR
* Availability
* Root-cause analysis

### Reference Tables

Dimension tables:

```text
dim_machine
dim_line
dim_product
dim_batch
dim_fault_code
dim_date
dim_time
```

Use for filtering, grouping, and clean dashboard labels.

## Modeling Rule

Keep source data and BI calculations separate.

Store these as source facts:

```text
Events
Sensor readings
Fault logs
Machine states
Reject reasons
Batch and product attributes
```

Create these as Power BI measures:

```text
Rates
Ratios
Averages
OEE
MTBF
MTTR
Performance %
Availability %
Quality %
```

## Power BI Measures

Create these in the Power BI Semantic Model, not as raw source columns.

Production measures:

```text
Items Processed = COUNTROWS(fact_print_event)
Printed Items = COUNTROWS(FILTER(fact_print_event, fact_print_event[print_result] = "SUCCESS"))
Reject Count = COUNTROWS(FILTER(fact_print_event, fact_print_event[reject_flag] = TRUE()))
Reject Rate % = DIVIDE([Reject Count], [Items Processed])
```

QR quality measures:

```text
QR Read Success Count
QR Read Fail Count
QR Read Rate %
Missing Code Count
Duplicate Code Count
Average QR Grade Score
Average Position Error mm
```

Machine performance measures:

```text
Average Actual Speed CPM
Average Planned Speed CPM
Performance % = DIVIDE([Average Actual Speed CPM], [Average Planned Speed CPM])
Ink ml per 1,000 Prints
Average Printhead Temperature C
Average Vibration mm/s
```

Downtime measures:

```text
Downtime Minutes
Fault Count
Warning Count
MTBF Minutes
MTTR Minutes
Availability %
```

OEE measures:

```text
Availability % = DIVIDE([Run Time Minutes], [Planned Production Minutes])
Performance % = DIVIDE([Actual Output], [Target Output])
Quality % = DIVIDE([Good QR Count], [Items Processed])
OEE % = [Availability %] * [Performance %] * [Quality %]
```

## Dashboard Pages

Recommended pages:

```text
Production Overview
QR Quality & Traceability
Machine Health
Downtime & Faults
Ink & Consumables
```

## Airflow Data Simulation

For the demo, a local Machine API will generate realistic synthetic machine data.

Airflow will call the API on a schedule. This keeps the project close to a real source-system ingestion pattern.

Reason:

* No external API key needed
* Can run daily while still simulating hourly source windows
* Matches real factory data patterns
* Easy to replace later with MQTT, Azure IoT Hub, OPC-UA, or vendor API

Expected pipeline:

```text
Machine API
    ↓
Airflow HTTP extraction
    ↓
Write raw API response as JSON
    ↓
Validate data quality
    ↓
Load raw JSON to Fabric Lakehouse
    ↓
Trigger Fabric Notebook / Pipeline
    ↓
Wait for Fabric transformation job
    ↓
Fabric builds curated fact and dimension tables
    ↓
Airflow validates curated output
    ↓
Refresh Power BI Semantic Model
```

Target Airflow DAG:

```text
extract_from_api
    ↓
validate_raw
    ↓
load_raw_to_fabric_lakehouse
    ↓
trigger_fabric_transformation
    ↓
wait_for_fabric_transformation
    ↓
validate_curated_tables
    ↓
refresh_power_bi_semantic_model
```

Current local mode:

```text
FABRIC_MODE=local
```

In local mode, the DAG simulates the Fabric Lakehouse landing zone and transformation output under:

```text
data/fabric_simulation/
data/curated/
```

Real Fabric mode:

```text
FABRIC_MODE=fabric
```

When enabled, the Airflow DAG does this:

```text
Resume Fabric capacity (optional)
    ↓
Call Machine API
    ↓
Upload raw JSON to OneLake Lakehouse Files
    ↓
Trigger Fabric notebook
    ↓
Poll Fabric notebook job status
    ↓
Submit Power BI semantic model refresh
    ↓
Pause Fabric capacity (optional)
```

Required `.env` values:

```text
AZURE_TENANT_ID
AZURE_CLIENT_ID
AZURE_CLIENT_SECRET
FABRIC_WORKSPACE_ID
FABRIC_LAKEHOUSE_NAME
FABRIC_NOTEBOOK_ID
POWER_BI_WORKSPACE_ID
POWER_BI_SEMANTIC_MODEL_ID
```

Optional pause/resume values:

```text
FABRIC_CAPACITY_AUTO_RESUME=true
FABRIC_CAPACITY_AUTO_PAUSE=true
AZURE_SUBSCRIPTION_ID
AZURE_RESOURCE_GROUP
FABRIC_CAPACITY_NAME
```

Schedule behavior:

```text
Airflow @daily run
    ↓
Uses Airflow data_interval_start and data_interval_end for the previous 24 hours
    ↓
Calls the Machine API once per hour, 24 calls total
    ↓
Merges hourly responses into one daily raw JSON payload
    ↓
Stores the merged response under uploaded_at=<upload-utc>/start_hour=<daily-window-start>
    ↓
Uploads the merged response to OneLake
    ↓
Triggers Fabric transform and semantic model refresh
    ↓
Pauses F2
```

Current demo volume:

```text
MACHINE_PRINT_EVENTS_PER_HOUR=200
Expected print events/day: about 4,800
Expected telemetry rows/day: about 1,440
```

Raw-file selection rule:

```text
The Fabric transform notebook prefers the newest uploaded_at=... raw folder.
If no uploaded_at=... folder exists, it falls back to the most recently modified machine_api_response.json.
This avoids accidentally selecting old high-volume start_hour=... test folders.
```

Local API:

```text
http://localhost:8000
```

Health check:

```text
http://localhost:8000/health
```

Hourly source endpoint:

```text
/v1/qr-printing/lines/LINE_01/window?start_ts=2026-06-12T01:00:00Z&end_ts=2026-06-12T02:00:00Z
```

## Local Airflow Setup

This repo uses the official Apache Airflow Docker Compose setup.

Current state:

```text
Local Docker Compose Airflow is stopped.
Use local Docker only for development/testing.
The Contabo VPS runs the live daily scheduler.
```

Start Airflow:

```bash
docker compose up airflow-init
docker compose up -d
```

Open Airflow:

```text
http://localhost:8080
```

Login:

```text
Username: airflow
Password: airflow
```

Starter DAG:

```text
qr_printing_machine_api_ingestion
```

Output files:

```text
data/raw/qr_printing/
data/fabric_simulation/qr_printing/
data/curated/qr_printing/
```

Optional validation DAG:

```text
world_bank_indicators
```

## Phase 1

Infrastructure

Tasks:

* Create Ubuntu VM
* Install Docker
* Install Airflow
* Access Airflow UI

Success Criteria:

```text
Airflow UI accessible
DAG runs successfully
```

## Phase 2

Data Ingestion

Tasks:

* Call Machine API
* Store production events, telemetry, and logs
* Store raw API response
* Land raw data for Fabric processing

Success Criteria:

```text
Raw machine data loaded into Fabric
```

## Phase 3

Transformation

Tasks:

* Trigger Fabric Notebook or Pipeline
* Clean machine data in Fabric
* Build fact and dimension tables in Fabric
* Apply incremental logic
* Run data quality checks
* Return job status to Airflow

Success Criteria:

```text
Curated machine monitoring tables available
```

## Phase 4

Semantic Model

Tasks:

* Create Power BI Semantic Model
* Create DAX measures
* Publish dashboard

Success Criteria:

```text
Dashboard available
```

## Phase 5

Cost Optimization

Tasks:

* Automate Fabric Resume
* Execute Fabric pipeline
* Refresh semantic model
* Pause Fabric

Success Criteria:

```text
Fabric active only during refresh window
```

## Final Deliverable

```text
Ubuntu VM
    ↓
Docker Airflow
    ↓
Machine API
    ↓
Raw data to Fabric Lakehouse
    ↓
Fabric Notebook / Pipeline
    ↓
Fabric Lakehouse / Warehouse
    ↓
Power BI Semantic Model
    ↓
Power BI Dashboard
```

Skills demonstrated:

* Linux
* Docker
* Airflow
* Python
* ETL
* Data Engineering
* Fabric
* Power BI
* Cost Optimization
* Cloud Architecture
