"""Integration test in a disposable database: repeat, resize, backfill, dbt and snapshot."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import duckdb

PROJECT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="retail-validation-") as temporary:
    root = Path(temporary)
    env = {**os.environ, "RETAIL_DB_PATH": str(root / "demo.duckdb"), "RETAIL_EXPORT_DIR": str(root / "exports"), "DBT_TARGET_PATH": str(root / "target"), "DBT_LOG_PATH": str(root / "logs")}
    def command(action, day, count=100):
        subprocess.run([sys.executable, str(PROJECT / "pipeline/retail.py"), action, "--date", day, "--orders", str(count)], env=env, check=True)
    for day, count in [("2026-09-04", 100), ("2026-09-05", 100), ("2026-09-04", 100), ("2026-09-03", 50), ("2026-09-03", 25)]:
        command("generate", day, count)
        command("load", day)
    with duckdb.connect(env["RETAIL_DB_PATH"], read_only=True) as con:
        assert con.execute("select count(*), count(distinct order_id) from landing.orders").fetchone() == (225, 225)
        assert con.execute("select count(*) from landing.order_items i left join landing.orders o using(order_id) where o.order_id is null").fetchone()[0] == 0
    subprocess.run([str(Path(sys.executable).with_name("dbt")), "build", "--project-dir", str(PROJECT), "--profiles-dir", str(PROJECT)], env=env, check=True)
    command("snapshot", "2026-09-05")
    first = json.loads((root / "exports/latest.json").read_text())["snapshot"]
    with duckdb.connect(str(root / "exports" / first), read_only=True) as viewer:
        # Keeping a snapshot open must not block the next pipeline date or snapshot.
        command("generate", "2026-09-06")
        command("load", "2026-09-06")
        subprocess.run([str(Path(sys.executable).with_name("dbt")), "build", "--project-dir", str(PROJECT), "--profiles-dir", str(PROJECT)], env=env, check=True)
        command("snapshot", "2026-09-06")
        assert viewer.execute("select count(*) from fct_orders").fetchone()[0] == 225
    latest = json.loads((root / "exports/latest.json").read_text())
    assert latest["orders"] == 325 and latest["snapshot"] != first
    print("PASS: repeat, partition replacement, backfill, 2 dbt builds and concurrent snapshot reader")
