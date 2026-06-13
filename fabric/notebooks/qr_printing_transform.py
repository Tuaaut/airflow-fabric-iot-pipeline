# Fabric Notebook: QR Printing Machine Transform
#
# Attach this notebook to Lakehouse:
# lh_qr_printing_demo

from pyspark.sql import functions as F
from pyspark.sql import types as T


def list_dir(path):
    try:
        return notebookutils.fs.ls(path)
    except NameError:
        return mssparkutils.fs.ls(path)


def item_modified_time(item):
    for attr_name in ("modifyTime", "modifiedTime", "modificationTime", "lastModified", "lastModifiedTime"):
        value = getattr(item, attr_name, None)
        if value is not None:
            return value
    return None


def collect_raw_json_files(base_path):
    items = list_dir(base_path)
    candidates = []

    for item in items:
        if item.name == "machine_api_response.json":
            candidates.append(
                {
                    "path": item.path,
                    "modified_time": item_modified_time(item),
                }
            )
        elif item.isDir:
            candidates.extend(collect_raw_json_files(item.path))

    return candidates


def find_raw_json_file(base_path):
    items = list_dir(base_path)

    uploaded_at_dirs = [
        item for item in items
        if item.isDir and item.name.startswith("uploaded_at=")
    ]
    for item in sorted(uploaded_at_dirs, key=lambda entry: entry.name, reverse=True):
        candidates = collect_raw_json_files(item.path)
        if candidates:
            return sorted(
                candidates,
                key=lambda candidate: (
                    candidate["modified_time"] is not None,
                    candidate["modified_time"] or "",
                    candidate["path"],
                ),
                reverse=True,
            )[0]["path"]

    candidates = collect_raw_json_files(base_path)
    if candidates:
        return sorted(
            candidates,
            key=lambda candidate: (
                candidate["modified_time"] is not None,
                candidate["modified_time"] or "",
                candidate["path"],
            ),
            reverse=True,
        )[0]["path"]

    start_hour_dirs = [
        item for item in items
        if item.isDir and item.name.startswith("start_hour=")
    ]
    for item in sorted(start_hour_dirs, key=lambda entry: entry.name, reverse=True):
        found_path = find_raw_json_file(item.path)
        if found_path:
            return found_path

    for item in items:
        if item.name == "machine_api_response.json":
            return item.path

    for item in items:
        if item.isDir and not item.name.startswith("start_hour="):
            found_path = find_raw_json_file(item.path)
            if found_path:
                return found_path

    return None


RAW_JSON_PATH = find_raw_json_file("Files/raw/qr_printing")

if RAW_JSON_PATH is None:
    raise FileNotFoundError("Could not find machine_api_response.json under Files/raw/qr_printing")

raw_df = spark.read.option("multiLine", "true").json(RAW_JSON_PATH)
raw_df.select("line_id", "start_ts", "end_ts").show(1, truncate=False)

print(f"Reading raw JSON from: {RAW_JSON_PATH}")

print_events_df = (
    raw_df
    .select(F.explode("print_events").alias("event"))
    .select("event.*")
    .withColumn("event_timestamp", F.to_timestamp("event_timestamp"))
    .withColumn("event_date", F.to_date("event_timestamp"))
    .withColumn("event_hour", F.date_trunc("hour", "event_timestamp"))
)

telemetry_df = (
    raw_df
    .select(F.explode("machine_telemetry").alias("telemetry"))
    .select("telemetry.*")
    .withColumn("timestamp_minute", F.to_timestamp("timestamp_minute"))
    .withColumn("event_date", F.to_date("timestamp_minute"))
    .withColumn("event_hour", F.date_trunc("hour", "timestamp_minute"))
)

log_schema = T.StructType([
    T.StructField("log_timestamp", T.StringType(), True),
    T.StructField("line_id", T.StringType(), True),
    T.StructField("machine_id", T.StringType(), True),
    T.StructField("event_type", T.StringType(), True),
    T.StructField("severity", T.StringType(), True),
    T.StructField("fault_code", T.StringType(), True),
    T.StructField("fault_description", T.StringType(), True),
    T.StructField("operator_id", T.StringType(), True),
    T.StructField("state_from", T.StringType(), True),
    T.StructField("state_to", T.StringType(), True),
    T.StructField("duration_seconds", T.LongType(), True),
])

machine_logs_field = raw_df.schema["machine_logs"]
machine_logs_is_struct_array = (
    isinstance(machine_logs_field.dataType, T.ArrayType)
    and isinstance(machine_logs_field.dataType.elementType, T.StructType)
)

if machine_logs_is_struct_array:
    logs_df = (
        raw_df
        .select(F.explode("machine_logs").alias("log"))
        .select("log.*")
    )
else:
    logs_df = spark.createDataFrame([], log_schema)

logs_df = (
    logs_df
    .withColumn("log_timestamp", F.to_timestamp("log_timestamp"))
    .withColumn("event_date", F.to_date("log_timestamp"))
    .withColumn("event_hour", F.date_trunc("hour", "log_timestamp"))
)


dim_machine_df = (
    telemetry_df
    .select("line_id", "machine_id")
    .distinct()
    .withColumn("machine_type", F.lit("High-speed QR printer"))
    .withColumn("manufacturer", F.lit("Demo Industrial Systems"))
)

dim_line_df = (
    telemetry_df
    .select("line_id")
    .distinct()
    .withColumn("line_name", F.concat(F.lit("Beverage QR Printing "), F.col("line_id")))
    .withColumn("plant_name", F.lit("Demo Beverage Plant"))
)

dim_product_df = (
    print_events_df
    .select("product_sku")
    .distinct()
    .withColumn(
        "package_type",
        F.when(F.col("product_sku").contains("CAN"), F.lit("Can")).otherwise(F.lit("Bottle")),
    )
    .withColumn(
        "package_size_ml",
        F.regexp_extract("product_sku", r"_(\\d+)_", 1).cast("int"),
    )
)

dim_fault_code_df = (
    logs_df
    .select("fault_code", "fault_description", "severity")
    .where(F.col("fault_code").isNotNull())
    .distinct()
)


hourly_kpi_summary_df = (
    print_events_df
    .groupBy("event_hour", "line_id", "machine_id", "product_sku", "batch_id")
    .agg(
        F.count("*").alias("items_processed"),
        F.sum(F.when(F.col("print_result") == "SUCCESS", 1).otherwise(0)).alias("printed_items"),
        F.sum(F.when(F.col("vision_result") == "PASS", 1).otherwise(0)).alias("qr_read_success_count"),
        F.sum(F.when(F.col("vision_result") == "FAIL", 1).otherwise(0)).alias("qr_read_fail_count"),
        F.sum(F.when(F.col("reject_flag") == True, 1).otherwise(0)).alias("reject_count"),
        F.sum(F.when(F.col("reject_reason") == "MISSING_CODE", 1).otherwise(0)).alias("missing_code_count"),
        F.sum(F.when(F.col("reject_reason") == "DUPLICATE_CODE", 1).otherwise(0)).alias("duplicate_code_count"),
        F.avg("grade_score").alias("avg_grade_score"),
        F.avg("position_error_mm").alias("avg_position_error_mm"),
    )
)


telemetry_hourly_df = (
    telemetry_df
    .groupBy("event_hour", "line_id", "machine_id")
    .agg(
        F.avg("planned_speed_cpm").alias("avg_planned_speed_cpm"),
        F.avg("actual_speed_cpm").alias("avg_actual_speed_cpm"),
        F.avg("printhead_temp_c").alias("avg_printhead_temp_c"),
        F.avg("vibration_mm_s").alias("avg_vibration_mm_s"),
        F.avg("air_pressure_bar").alias("avg_air_pressure_bar"),
        F.sum("ink_consumed_ml").alias("ink_consumed_ml"),
        F.sum("downtime_seconds").alias("downtime_seconds"),
    )
)


hourly_kpi_summary_df = (
    hourly_kpi_summary_df
    .join(telemetry_hourly_df, ["event_hour", "line_id", "machine_id"], "left")
    .withColumn("reject_rate_pct", F.col("reject_count") / F.col("items_processed"))
    .withColumn("qr_read_rate_pct", F.col("qr_read_success_count") / F.col("items_processed"))
    .withColumn("performance_pct", F.col("avg_actual_speed_cpm") / F.col("avg_planned_speed_cpm"))
    .withColumn("ink_ml_per_1000_prints", F.col("ink_consumed_ml") / F.col("items_processed") * 1000)
)


tables = {
    "fact_print_event": print_events_df,
    "fact_machine_telemetry_minute": telemetry_df,
    "fact_machine_log": logs_df,
    "dim_machine": dim_machine_df,
    "dim_line": dim_line_df,
    "dim_product": dim_product_df,
    "dim_fault_code": dim_fault_code_df,
    "hourly_kpi_summary": hourly_kpi_summary_df,
}

for table_name, table_df in tables.items():
    (
        table_df
        .write
        .mode("overwrite")
        .format("delta")
        .saveAsTable(table_name)
    )
    print(f"Wrote {table_name}: {table_df.count()} rows")
