"""Deterministic daily retail ingestion. DuckDB is opened only inside each command."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import shutil

import duckdb

PROJECT = Path(__file__).resolve().parents[1]
DB = Path(os.environ.get("RETAIL_DB_PATH", str(PROJECT / "data/demo.duckdb")))


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB), config={"threads": 1, "memory_limit": "512MB"})


def batch_path(day):
    return DB.parent / "batches" / f"{day.isoformat()}.json"


def generate(day, count):
    if not 1 <= count <= 10000:
        raise ValueError("orders_per_day must be between 1 and 10000")
    orders, items, payments = [], [], []
    for seq in range(1, count + 1):
        order_id = int(day.strftime("%Y%m%d")) * 100000 + seq
        status = "cancelled" if seq % 17 in (0, 1) else "pending" if seq % 7 == 0 else "completed"
        total = Decimal(0)
        for slot in range(1, 2 + (seq * 11) % 4):
            product = ((seq * 13 + slot * 7 + day.toordinal()) % 60) + 1001
            quantity = 1 + ((seq + slot) % 3)
            price = Decimal(35 + ((product - 1001) % 10) * 12 + ((product - 1001) % 3) * 5)
            amount = price * quantity
            total += amount
            items.append([order_id * 10 + slot, order_id, product, quantity, str(price), str(amount), day.isoformat()])
        orders.append([order_id, (seq - 1) % 120 + 1, (seq - 1) % 12 + 101, day.isoformat(), str(total), status])
        amounts = [total]
        if status == "completed" and seq % 4 == 0:
            first = (total * Decimal("0.6")).quantize(Decimal("0.01"))
            amounts = [first, total - first]
        for slot, amount in enumerate(amounts, 1):
            payments.append([order_id * 10 + slot, order_id, day.isoformat(), str(amount if status == "completed" else 0), "card" if slot == 1 else "wallet", "paid" if status == "completed" else "pending" if status == "pending" else "failed", day.isoformat()])
    payload = {"batch_date": day.isoformat(), "orders": orders, "items": items, "payments": payments}
    path = batch_path(day)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    temporary.replace(path)
    print(json.dumps({"batch": str(path), "orders": len(orders), "items": len(items)}))


def load(day):
    payload = json.loads(batch_path(day).read_text(encoding="utf-8"))
    if payload["batch_date"] != day.isoformat() or not payload["orders"]:
        raise ValueError("Invalid or empty batch")
    with connect() as con:
        con.execute("BEGIN")
        try:
            con.execute("CREATE SCHEMA IF NOT EXISTS landing")
            for name in ("customers", "stores", "products"):
                sql = (PROJECT / "pipeline/masters" / f"{name}.sql").read_text(encoding="utf-8")
                sql = re.sub(r"\{\{.*?\}\}", "", sql, flags=re.S)
                con.execute(f"CREATE TABLE IF NOT EXISTS landing.{name} AS {sql}")
            con.execute("CREATE TABLE IF NOT EXISTS landing.orders (order_id BIGINT PRIMARY KEY, customer_id BIGINT, store_id BIGINT, order_date DATE, order_amount DECIMAL(12,2), order_status VARCHAR)")
            con.execute("CREATE TABLE IF NOT EXISTS landing.order_items (order_line_id BIGINT PRIMARY KEY, order_id BIGINT, product_id BIGINT, quantity INTEGER, unit_price DECIMAL(10,2), line_amount DECIMAL(12,2), batch_date DATE)")
            con.execute("CREATE TABLE IF NOT EXISTS landing.payments (payment_id BIGINT PRIMARY KEY, order_id BIGINT, payment_date DATE, payment_amount DECIMAL(12,2), payment_method VARCHAR, payment_status VARCHAR, batch_date DATE)")
            for table, field, key, width in (("payments", "batch_date", "payments", 7), ("order_items", "batch_date", "items", 7), ("orders", "order_date", "orders", 6)):
                con.execute(f"DELETE FROM landing.{table} WHERE {field} = ?", [day])
                con.executemany(f"INSERT INTO landing.{table} VALUES ({','.join(['?'] * width)})", payload[key])
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
    print(f"Loaded {day}: {len(payload['orders'])} orders; replaced only this date")


def snapshot(day):
    export = Path(os.environ.get("RETAIL_EXPORT_DIR", str(PROJECT / "exports")))
    export.mkdir(parents=True, exist_ok=True)
    # Called after successful dbt build, with max_active_runs=1 and no other writer.
    with connect() as con:
        con.execute("CHECKPOINT")
        rows = con.execute("SELECT count(*) FROM fct_orders").fetchone()[0]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination = export / f"retail_{day}_{stamp}.duckdb"
    temporary = destination.with_suffix(".tmp")
    shutil.copyfile(DB, temporary)
    with duckdb.connect(str(temporary), read_only=True) as con:
        if con.execute("SELECT count(*) FROM fct_orders").fetchone()[0] != rows:
            raise ValueError("Snapshot count mismatch")
    temporary.replace(destination)
    with destination.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    metadata = {"snapshot": destination.name, "batch_date": str(day), "orders": rows, "sha256": digest}
    pointer = export / "latest.json.tmp"
    pointer.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    pointer.replace(export / "latest.json")
    print(json.dumps(metadata))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["generate", "load", "snapshot"])
    parser.add_argument("--date", required=True, type=date.fromisoformat)
    parser.add_argument("--orders", type=int, default=100)
    args = parser.parse_args()
    if args.action == "generate":
        generate(args.date, args.orders)
    elif args.action == "load":
        load(args.date)
    else:
        snapshot(args.date)
