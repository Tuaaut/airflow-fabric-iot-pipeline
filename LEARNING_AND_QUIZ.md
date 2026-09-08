# Airflow and Fabric Learning Quiz Notes

This file tracks the learning path, quiz questions, correct answers, and review links for the Airflow + Microsoft Fabric QR printing project.

## Review Links

Clickable local quiz:

```text
airflow_fabric_quiz.html
```

If a local web server is running from this folder:

```text
http://127.0.0.1:8765/airflow_fabric_quiz.html
```

Main local/project review files:

```text
README.md
PROJECT_DETAILS.md
PROJECT_STATUS.md
ALERTING_MONITORING.md
FABRIC_CLEANUP_INVENTORY.md
```

Main UI areas to review:

```text
Airflow UI
Microsoft Fabric workspace
Fabric Lakehouse
Fabric SQL analytics endpoint
Fabric semantic model
Azure Portal capacity and budget pages
```

## Learning Goal

Understand the project in this order:

1. What Airflow does.
2. What a DAG is.
3. What tasks are.
4. How the Machine API creates QR printing data.
5. Why raw JSON is landed before transformation.
6. What OneLake and Fabric Lakehouse are.
7. What Fabric notebooks do.
8. What curated Delta tables are.
9. Why the semantic model is refreshed.
10. Why Fabric F2 must be paused after runs.
11. How the missing email-alerting piece should work.

## Core Mental Model

```text
Airflow = scheduler and orchestrator
DAG = pipeline recipe
Task = one step in the recipe
Machine API = simulated source system
Raw JSON = preserved source payload
OneLake / Lakehouse Files = Fabric raw landing area
Fabric notebook = transformation engine
Curated Delta tables = analytics-ready tables
SQL analytics endpoint = validation/query surface
Semantic model = business metric layer for reports
Fabric F2 capacity = billable compute that should be paused when idle
Logic Apps = email delivery layer for readable pipeline alerts
```

## Conceptual Quiz History

### Question 1

What is Airflow's main role in this project?

Correct answer:

```text
Airflow orchestrates the daily pipeline steps in the correct order.
```

Remember:

```text
Airflow is the conductor. Fabric is where the lakehouse work happens.
```

### Question 2

What is a DAG?

Correct answer:

```text
A DAG is the pipeline definition: tasks plus their order/dependencies.
```

In this project:

```text
qr_printing_machine_api_ingestion
```

### Question 3

What does `extract_from_api` do?

Correct answer:

```text
Calls the simulated Machine API, collects hourly QR printing data, and writes a daily raw JSON file.
```

### Question 4

Why do we keep raw JSON before transforming it?

Correct answer:

```text
Raw data is preserved so the pipeline can reprocess it later if logic, schema, or platform changes.
```

### Question 5

What is OneLake / Lakehouse Files used for?

Correct answer:

```text
It is the Fabric landing area for raw files before notebook transformation.
```

### Question 6

What does the Fabric notebook do?

Correct answer:

```text
Transforms raw QR printing JSON into curated facts, dimensions, and KPI tables.
```

### Question 7

What are curated Delta tables?

Correct answer:

```text
Cleaned, typed, analytics-ready tables stored in the Fabric Lakehouse.
```

Examples:

```text
fact_print_event
fact_machine_telemetry_minute
fact_machine_log
hourly_kpi_summary
```

### Question 8

Why refresh the semantic model?

Correct answer:

```text
So Power BI / Fabric reports can use the latest curated data and measures.
```

### Question 9

Why does the DAG resume and pause Fabric F2 capacity?

Correct answer:

```text
Fabric F2 is billable while active, so the pipeline resumes it for work and pauses it after the run.
```

### Question 10

What is the missing alerting piece?

Correct answer:

```text
A readable email alert after each DAG run showing stage status, row counts, semantic refresh status, and final Fabric capacity state.
```

## UI Quiz History

These questions are meant to be answered while looking at Airflow and Fabric.

### UI Question 1

In Airflow, where do you check whether the pipeline succeeded?

Correct answer:

```text
Open the DAG run or task grid for `qr_printing_machine_api_ingestion`.
```

### UI Question 2

Which task should happen first for cost-controlled Fabric runs?

Correct answer:

```text
resume_fabric_capacity
```

Why:

```text
The Fabric notebook and Lakehouse operations need active Fabric capacity.
```

### UI Question 3

Which task should happen near the end to control cost?

Correct answer:

```text
pause_fabric_capacity
```

### UI Question 4

Where do you inspect raw landed data in Fabric?

Correct answer:

```text
Fabric workspace -> Lakehouse -> Files
```

### UI Question 5

Where do you inspect curated tables in Fabric?

Correct answer:

```text
Fabric workspace -> Lakehouse -> Tables, or SQL analytics endpoint.
```

### UI Question 6

What does the SQL analytics endpoint help validate?

Correct answer:

```text
That curated tables are queryable and ready for analytics.
```

### UI Question 7

Where should you check cost safety after testing?

Correct answer:

```text
Azure Portal / Fabric capacity page, confirming Fabric F2 is Paused.
```

### UI Question 8

What should the future email alert tell you?

Correct answer:

```text
Whether each stage succeeded, how many raw/curated rows were produced, whether semantic refresh was submitted, and whether Fabric F2 ended paused.
```

## Cost Safety Checklist

After learning or testing:

1. Check Airflow DAG run status.
2. Confirm the last task reached `pause_fabric_capacity`.
3. Check Fabric F2 capacity state.
4. Confirm capacity is `Paused`.
5. Check Azure budget alerts remain configured.
6. Do not leave the local Mac Docker stack running unless testing locally.
7. Do not commit `.env` or Logic Apps webhook URLs.

Useful local checks:

```bash
fab --version
fab auth login
fab ls
```

Useful VPS checks:

```bash
docker compose exec airflow-apiserver airflow dags state qr_printing_machine_api_ingestion '<RUN_ID>'
docker compose exec airflow-apiserver airflow tasks states-for-dag-run qr_printing_machine_api_ingestion '<RUN_ID>'
```

## Suggested Learning Journey

Use short practice loops:

1. Learn one Airflow or Fabric concept.
2. Click the matching UI area.
3. Answer one quiz question.
4. Check why the answer is correct.
5. Confirm cost safety if Fabric capacity was started.

Recommended next lessons:

1. Airflow DAG graph: how tasks depend on each other.
2. Airflow task logs: how to debug one failed step.
3. Raw JSON: why landing files are kept.
4. Fabric Lakehouse: Files vs Tables.
5. Fabric notebook: transform raw to curated.
6. Semantic model: why reports need refresh.
7. Fabric F2 capacity: pause/resume and cost behavior.
8. Logic Apps alerting: how email delivery will work.

## Concerns

Keep learning focused on one screen at a time. The Codex in-app browser currently works best with one active page, so side-by-side Fabric plus quiz may be limited.

Best workaround:

```text
Use Airflow/Fabric UI in the browser, and keep quiz questions in chat.
```

For deeper review later, open:

```text
airflow_fabric_quiz.html
```

