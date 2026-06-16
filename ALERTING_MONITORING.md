# Alerting and Monitoring

This project needs a business-level daily pipeline alert, not only infrastructure logs.

Recommended path:

```text
Airflow DAG run
→ collect pipeline stage status
→ send one structured payload to Azure Logic Apps Consumption
→ email summary to Pattaratua@gmail.com
```

Azure budget alerts already cover spend notifications. This alerting design covers whether the daily QR printing pipeline actually moved and refreshed data.

## Current Status

Implemented:

```text
Airflow DAG: qr_printing_machine_api_ingestion
Daily schedule: 00:00 UTC / 07:00 Bangkok
Raw extraction: Machine API → local raw JSON
Raw landing: Fabric OneLake / Lakehouse Files
Transform: Fabric notebook / PySpark
Curated validation: Fabric SQL analytics endpoint
Semantic refresh: Power BI / Fabric semantic model
Cost control: resume Fabric F2 before run, pause Fabric F2 after run
```

Missing piece:

```text
Automatic readable email alert after each run
```

Fabric CLI has been installed locally:

```bash
fab --version
```

Authentication is still interactive:

```bash
fab auth login
```

## Why Logic Apps

Airflow can send email directly, but Azure Logic Apps is cleaner for this demo:

- no Gmail password or SMTP secret stored in Airflow
- readable email formatting is handled outside the DAG
- the DAG only sends a structured JSON payload
- the same pattern can be reused for Teams, Slack, or Outlook later
- Consumption plan is low-cost for one daily alert

Azure Monitor is still useful for infrastructure alerts such as VM health, container failures, or Fabric/Azure cost alerts. Logic Apps is better for the daily business pipeline summary.

## Alert Coverage

The email should cover every important stage:

```text
Airflow DAG run started
Fabric F2 capacity resumed
Machine API extraction completed
Raw JSON file created
Raw JSON uploaded to Fabric OneLake
Fabric notebook transformation completed
Curated Delta tables validated
Semantic model refresh submitted
Fabric F2 capacity paused
Final run status
Cost reminder
```

## Suggested Email Subject

Success:

```text
QR Airflow Fabric Pipeline Updated - YYYY-MM-DD - SUCCESS
```

Failure:

```text
QR Airflow Fabric Pipeline Failed - YYYY-MM-DD - FAILED_AT_<stage>
```

## Suggested Email Body

Include these fields:

```text
Pipeline name
Business date / data interval
Airflow DAG run ID
Final status
Failed stage, if any
Run start time
Run end time
Duration
Machine API base URL
Raw local path
Fabric raw path
Raw payload counts
Curated table validation result
Semantic model refresh status
Fabric capacity final state
Budget reminder
Airflow UI run link, if stable
```

Useful raw payload counts:

```text
print_events
machine_telemetry
machine_logs
source_windows
```

Useful curated table checks:

```text
fact_print_event row count
fact_machine_telemetry_minute row count
fact_machine_log row count
dim_machine row count
dim_product row count
hourly_kpi_summary row count
```

## Recommended Implementation

Add one final Airflow task:

```text
build_pipeline_alert_payload
```

Then add one delivery task:

```text
send_pipeline_alert_to_logic_app
```

The delivery task should POST JSON to a Logic Apps HTTP trigger URL stored in `.env`:

```text
LOGIC_APP_PIPELINE_ALERT_URL=replace_me
ALERT_EMAIL_TO=Pattaratua@gmail.com
```

Use Airflow `TriggerRule.ALL_DONE` so the alert still sends when an upstream task fails.

Recommended dependency shape:

```text
resume_fabric_capacity
→ extract_from_api
→ validate_raw
→ load_raw_to_fabric_lakehouse
→ trigger_fabric_transformation
→ wait_for_fabric_transformation
→ validate_curated_tables
→ refresh_semantic_model
→ pause_fabric_capacity
→ build_pipeline_alert_payload
→ send_pipeline_alert_to_logic_app
```

Failure callback option:

```text
on_failure_callback
```

Use this later for immediate failure alerts if the final alert task cannot run.

## Logic Apps Workflow

Create a Logic Apps Consumption workflow:

```text
Trigger: When an HTTP request is received
Action: Parse JSON
Action: Send email with Gmail or Outlook connector
```

The connector authorization requires interactive sign-in in Azure Portal.

Start with one simple email action. Add Teams/Slack later only if needed.

## Example Payload

```json
{
  "pipeline_name": "qr_printing_machine_api_ingestion",
  "business_date": "2026-06-16",
  "run_id": "scheduled__2026-06-16T00:00:00+00:00",
  "status": "SUCCESS",
  "failed_stage": null,
  "raw_counts": {
    "print_events": 4800,
    "machine_telemetry": 1440,
    "machine_logs": 60
  },
  "fabric": {
    "workspace": "AirflowVM-Fabric-PowerBI",
    "lakehouse": "lh_qr_printing_demo",
    "capacity": "fabf2sea01",
    "final_capacity_state": "Paused"
  },
  "semantic_model_refresh": "submitted",
  "cost_reminder": "Confirm Fabric F2 is paused after the run."
}
```

## Manual Checks

Check Fabric CLI:

```bash
fab --version
fab auth login
fab ls
```

Check Airflow DAG state from the VPS:

```bash
docker compose exec airflow-apiserver airflow dags state qr_printing_machine_api_ingestion '<RUN_ID>'
docker compose exec airflow-apiserver airflow tasks states-for-dag-run qr_printing_machine_api_ingestion '<RUN_ID>'
```

Check Airflow health:

```bash
curl http://localhost:8080/api/v2/monitor/health
```

## Next Build Step

Implement the Airflow alert tasks after Logic Apps HTTP trigger URL is created.

Do not store the Logic Apps URL in Git. Put it in `.env` only.

