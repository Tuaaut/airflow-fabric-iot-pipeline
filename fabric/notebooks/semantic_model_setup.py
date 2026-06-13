# Fabric Notebook: Semantic Model Setup
#
# Purpose:
# - Add relationships
# - Add DAX measures
# - Keep semantic model setup versioned as code
#
# Run this in a Fabric notebook after creating semantic model:
# sm_qr_printing_demo

%pip install semantic-link-labs

from sempy_labs.tom import connect_semantic_model


WORKSPACE_NAME = "airflow-fabric-demo-dev"
SEMANTIC_MODEL_NAME = "sm_qr_printing_demo"


relationships = [
    ("fact_print_event", "machine_id", "dim_machine", "machine_id"),
    ("fact_machine_telemetry_minute", "machine_id", "dim_machine", "machine_id"),
    ("fact_machine_log", "machine_id", "dim_machine", "machine_id"),
    ("hourly_kpi_summary", "machine_id", "dim_machine", "machine_id"),
    ("fact_print_event", "line_id", "dim_line", "line_id"),
    ("fact_machine_telemetry_minute", "line_id", "dim_line", "line_id"),
    ("fact_machine_log", "line_id", "dim_line", "line_id"),
    ("hourly_kpi_summary", "line_id", "dim_line", "line_id"),
    ("fact_print_event", "product_sku", "dim_product", "product_sku"),
    ("hourly_kpi_summary", "product_sku", "dim_product", "product_sku"),
    ("fact_machine_log", "fault_code", "dim_fault_code", "fault_code"),
]


measures = {
    "Items Processed": "SUM('hourly_kpi_summary'[items_processed])",
    "Printed Items": "SUM('hourly_kpi_summary'[printed_items])",
    "QR Read Success Count": "SUM('hourly_kpi_summary'[qr_read_success_count])",
    "QR Read Fail Count": "SUM('hourly_kpi_summary'[qr_read_fail_count])",
    "Reject Count": "SUM('hourly_kpi_summary'[reject_count])",
    "Missing Code Count": "SUM('hourly_kpi_summary'[missing_code_count])",
    "Duplicate Code Count": "SUM('hourly_kpi_summary'[duplicate_code_count])",
    "QR Read Rate %": "DIVIDE([QR Read Success Count], [Items Processed])",
    "Reject Rate %": "DIVIDE([Reject Count], [Items Processed])",
    "Average QR Grade Score": "AVERAGE('hourly_kpi_summary'[avg_grade_score])",
    "Average Position Error mm": "AVERAGE('hourly_kpi_summary'[avg_position_error_mm])",
    "Average Planned Speed CPM": "AVERAGE('hourly_kpi_summary'[avg_planned_speed_cpm])",
    "Average Actual Speed CPM": "AVERAGE('hourly_kpi_summary'[avg_actual_speed_cpm])",
    "Performance %": "DIVIDE([Average Actual Speed CPM], [Average Planned Speed CPM])",
    "Average Printhead Temperature C": "AVERAGE('hourly_kpi_summary'[avg_printhead_temp_c])",
    "Average Vibration mm/s": "AVERAGE('hourly_kpi_summary'[avg_vibration_mm_s])",
    "Ink Consumed ml": "SUM('hourly_kpi_summary'[ink_consumed_ml])",
    "Ink ml per 1,000 Prints": "DIVIDE([Ink Consumed ml], [Items Processed]) * 1000",
    "Downtime Seconds": "SUM('hourly_kpi_summary'[downtime_seconds])",
    "Downtime Minutes": "DIVIDE([Downtime Seconds], 60)",
    "Availability %": "DIVIDE(60 - [Downtime Minutes], 60)",
    "Quality %": "DIVIDE([QR Read Success Count], [Items Processed])",
    "OEE %": "[Availability %] * [Performance %] * [Quality %]",
    "Fault Count": "COUNTROWS('fact_machine_log')",
}


def relationship_exists(tom, from_table, from_column, to_table, to_column):
    for rel in tom.model.Relationships:
        if (
            rel.FromTable.Name == from_table
            and rel.FromColumn.Name == from_column
            and rel.ToTable.Name == to_table
            and rel.ToColumn.Name == to_column
        ):
            return True
    return False


def measure_exists(tom, table_name, measure_name):
    for table in tom.model.Tables:
        if table.Name == table_name:
            for measure in table.Measures:
                if measure.Name == measure_name:
                    return True
    return False


with connect_semantic_model(
    dataset=SEMANTIC_MODEL_NAME,
    workspace=WORKSPACE_NAME,
    readonly=False,
) as tom:
    for from_table, from_column, to_table, to_column in relationships:
        if relationship_exists(tom, from_table, from_column, to_table, to_column):
            print(f"Relationship already exists: {from_table}[{from_column}] -> {to_table}[{to_column}]")
            continue

        tom.add_relationship(
            from_table=from_table,
            from_column=from_column,
            to_table=to_table,
            to_column=to_column,
            from_cardinality="Many",
            to_cardinality="One",
            cross_filtering_behavior="OneDirection",
            is_active=True,
        )
        print(f"Added relationship: {from_table}[{from_column}] -> {to_table}[{to_column}]")

    for measure_name, expression in measures.items():
        if measure_exists(tom, "hourly_kpi_summary", measure_name):
            print(f"Measure already exists: {measure_name}")
            continue

        tom.add_measure(
            table_name="hourly_kpi_summary",
            measure_name=measure_name,
            expression=expression,
            format_string="0.00%" if measure_name.endswith("%") else None,
        )
        print(f"Added measure: {measure_name}")

    tom.mark_primary_keys()

print("Semantic model setup completed.")

