# Retail dbt + DuckDB — Shared Airflow

โปรเจกต์ข้อมูลค้าปลีกจำลองรายวัน ใช้ Airflow เดิมร่วมกับ IoT และ World Bank โดยไม่เพิ่มชุด Airflow อีกชุด

## เริ่มอ่าน

- [Blueprint และบันทึกความคืบหน้า](DeploymentAndLogic.md)
- [Docker Compose ที่ควบคุมระบบ](../../airflow-fabric-iot-pipeline/docker-compose.yaml)
- [Airflow UI](http://localhost:8080/dags/retail_dbt_daily)
- [ข้อมูลสำเนาล่าสุดสำหรับ DBeaver](exports/latest.json)

## สถาปัตยกรรม

Airflow → Generate JSON → Transactional DuckDB landing → dbt build → DBeaver snapshot

Airflow, PostgreSQL, Redis และ worker ใช้ชุดเดิม ส่วนข้อมูล Retail อยู่ volume แยก มี virtual environment ของ dbt แยกภายใน worker

| # | รายการ | ค่า |
|---|---|---|
| 1 | DAG | `retail_dbt_daily` |
| 2 | Schedule | 07:30 Asia/Bangkok ทุกวัน ประมวลผลวันก่อนหน้า |
| 3 | Data | 100 orders/day, 120 customers, 12 stores, 60 products |
| 4 | dbt | 21 models, 84 data tests |
| 5 | Resource controls | Worker concurrency 1, shared pool 1 slot, dbt/DuckDB 1 thread, DuckDB 512MB |

## Query ใน DBeaver

เปิด `exports/latest.json` เพื่อดูชื่อไฟล์ล่าสุด แล้วสร้าง connection แบบ DuckDB โดยเลือกไฟล์ `.duckdb` นั้นในโฟลเดอร์ `exports` ใช้ read-only หาก driver รองรับ ไม่ต้องมี host/port ของ DuckDB

```sql
SELECT order_date, count(*) AS orders, sum(order_amount) AS order_value
FROM fct_orders
GROUP BY order_date
ORDER BY order_date;
```

สำเนาเป็นข้อมูล ณ เวลา export ไม่อัปเดตเอง แต่ละ run สร้างชื่อใหม่ จึงเปิดสำเนาเก่าค้างไว้ได้โดยไม่ล็อกฐานหลัก หากต้องการข้อมูลใหม่ให้เปลี่ยน connection ไปไฟล์ล่าสุด สำเนาเก่าเก็บไว้จนกว่าจะลบเองหลังปิด connection

Dashboard และการ deploy cloud ยังอยู่นอกขอบเขต
