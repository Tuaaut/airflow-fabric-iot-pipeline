# Fabric Workspace And Capacity Inventory

Last inspected/updated: 2026-06-13 18:45 Bangkok

## Document Map

Read these in order:

1. [README.md](README.md): GitHub-facing project pitch and showcase overview.
2. [PROJECT_DETAILS.md](PROJECT_DETAILS.md): full project concept, architecture, domain, and operating model.
3. [PROJECT_STATUS.md](PROJECT_STATUS.md): current implementation status, completed work, caveats, and next steps.
4. [FABRIC_CLEANUP_INVENTORY.md](FABRIC_CLEANUP_INVENTORY.md): Fabric workspace and capacity inventory.

## Purpose

Track Fabric workspaces, Fabric capacities, and cleanup decisions for the Airflow + Fabric + Power BI demo.

This file originally captured the pre-F2 trial inventory. It now records the current paid F2 setup and remaining cleanup notes.

## Active Paid Capacity

```text
Capacity name:  fabf2sea01
Capacity type:  Microsoft Fabric
SKU:            F2
Region:         Southeast Asia
Resource group: rg-fabric-capacities
Subscription:   Azure subscription 1
State:          Paused
```

Important:

```text
F2 is billable while Active.
F2 should normally show Status = Paused in Azure.
The Azure portal should show a Resume button when idle.
The Fabric UI may show a user trial such as "Trials activated: 29 days left"; that does not make paid F2 capacity free.
```

Airflow pause/resume:

```text
Airflow resumes F2 at the start of the pipeline.
Airflow pauses F2 after semantic model refresh.
```

## Deleted Test Capacity

```text
Capacity name: fabf2wus201
Region:        West US 2
State:         Deleted
Reason:        Region mismatch / no longer needed
```

## Budget Guardrail

```text
Budget name: budget-fabric-demo-20usd
Scope:       subscription
Amount:      $20/month
Alerts:      50%, 80%, 100%
Recipient:   Pattaratua@gmail.com
```

Budget alerts are notifications only. They are not a hard spending stop.

Alert recipient was updated to `Pattaratua@gmail.com` together with the Databricks project budget alerts.

Latest cost snapshot on 2026-06-13:

```text
Month-to-date Azure actual cost: about $0.738 USD
fabf2sea01: about $0.726 USD
fabf2wus201 historical deleted test capacity: about $0.012 USD
Budget current spend: about $0.738 / $20
Cost data can lag by several hours.
```

## Active Project Workspace

### airflow-fabric-demo-dev

```text
Workspace ID: <fabric-workspace-id>
Region:       Southeast Asia
Capacity:     fabf2sea01
Status:       Keep
```

Items:

```text
Lakehouse:      lh_qr_printing_demo
SQLEndpoint:    lh_qr_printing_demo
Notebook:       nb_qr_printing_transform
Notebook:       nb_semantic_model_setup
SemanticModel:  sm_qr_printing_demo
```

Recommendation:

```text
Keep. This is the active Airflow + Fabric + Power BI project workspace.
```

Raw data cleanup on 2026-06-13:

```text
Problem:
  Old high-volume raw files from early simulator settings were still in OneLake.
  They caused the transform notebook to produce about 47,776 rows for a one-hour batch.

Deleted high-volume raw inputs:
  Files/raw/qr_printing/machine_api_response.json
  Files/raw/qr_printing/start_hour=2026061207
  Files/raw/qr_printing/start_hour=2026061215

Kept reduced-volume raw inputs:
  Files/raw/qr_printing/start_hour=2026061200
  Files/raw/qr_printing/start_hour=2026061203
  Files/raw/qr_printing/start_hour=2026061210

Notebook fix:
  nb_qr_printing_transform now prefers uploaded_at=... folders.
  If no uploaded_at=... folder exists, it selects the most recently modified machine_api_response.json.
  The fixed notebook was deployed through Fabric item definition API and manually rerun successfully.
```

## Other Workspaces From Earlier Inventory

These were seen during the earlier trial-capacity inventory. They should not be moved to the paid F2 capacity unless intentionally revived.

### My workspace

```text
Type: Personal
Workspace ID: 82ecaf6d-77bd-46db-95d5-ec825238e0cd
Previous capacity: Trial
```

Recommendation:

```text
Review manually before deleting anything.
Do not assign to paid F2 by default.
```

### fabric-churn-analytics

```text
Workspace ID: 2091f799-24d0-4989-8d2e-b4ec90ec09df
Previous capacity: Trial
```

Items seen earlier:

```text
Lakehouse:      churn_lakehouse
Notebook:       01_bronze_silver_gold_churn
Report:         Customer Churn Intelligence Dashboard
SQLEndpoint:    churn_lakehouse
SemanticModel:  Churn Analytics Semantic Model
```

Recommendation:

```text
Candidate for archive/delete if the old churn project is no longer needed.
Do not assign to paid F2 by default.
```

### fabric-jewelry-analytics

```text
Workspace ID: 44485047-abd2-4424-a61d-e1095bde4d5a
Previous capacity: Trial
```

Items seen earlier:

```text
Lakehouse:      jewelry_lakehouse
Notebook:       01_build_lakehouse_tables
Notebook:       02_configure_semantic_model
Notebook:       03_validate_jewelry_platform
Report:         Jewelry Manufacturing Intelligence Dashboard
SQLEndpoint:    jewelry_lakehouse
SemanticModel:  Jewelry Manufacturing Semantic Model
```

Recommendation:

```text
Likely dev/test jewelry workspace.
Candidate for delete if production copy is enough.
Do not assign to paid F2 by default.
```

### fabric-jewelry-analytics-prod

```text
Workspace ID: 387f937f-7d2f-4552-b269-d65bb3e5f20e
Previous capacity: Trial
```

Items seen earlier:

```text
Lakehouse:      jewelry_lakehouse
Notebook:       01_build_lakehouse_tables
Notebook:       02_configure_semantic_model
Notebook:       03_validate_jewelry_platform
Report:         Jewelry Manufacturing Intelligence Dashboard
SQLEndpoint:    jewelry_lakehouse
SemanticModel:  Jewelry Manufacturing Semantic Model
```

Recommendation:

```text
Keep only if this jewelry project is still useful as a portfolio/demo project.
Otherwise archive/delete before adding anything else to paid capacity.
```

## Cleanup Rule

Keep the paid F2 capacity scoped only to:

```text
airflow-fabric-demo-dev
```

Avoid assigning old or unused workspaces to `fabf2sea01`.

## CLI Commands

List Fabric workspaces:

```bash
TOKEN=$(az account get-access-token --resource https://api.fabric.microsoft.com --query accessToken -o tsv)

curl -sS "https://api.fabric.microsoft.com/v1/workspaces" \
  -H "Authorization: Bearer $TOKEN" | jq
```

List items in a workspace:

```bash
curl -sS "https://api.fabric.microsoft.com/v1/workspaces/<WORKSPACE_ID>/items" \
  -H "Authorization: Bearer $TOKEN" | jq
```

Check F2 capacity state through Azure ARM:

```bash
az resource show \
  --ids /subscriptions/<azure-subscription-id>/resourceGroups/rg-fabric-capacities/providers/Microsoft.Fabric/capacities/fabf2sea01 \
  --api-version 2023-11-01 \
  --query '{state:properties.state, provisioningState:properties.provisioningState}' \
  -o json
```

## Deletion Notes

Deleting a workspace removes contained Fabric/Power BI items.

Before deleting:

1. Export/download anything needed later.
2. Check whether reports or semantic models are used in a portfolio.
3. Confirm the workspace is not needed by another project.
4. Delete from Fabric UI first unless there is a strong reason to automate deletion.
