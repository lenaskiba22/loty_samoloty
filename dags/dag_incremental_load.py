from __future__ import annotations

import glob
import os
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator, BranchPythonOperator
from airflow.providers.standard.operators.empty import EmptyOperator

BTS_DIR = os.environ.get("BTS_DIR", "/opt/airflow/data/raw/bts")

default_args = {
    "owner": "etl",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=3),
    "email_on_failure": False,
}

def _get_new_files() -> list[str]:
    from etl.utils import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT file_name FROM ETL_Load_Log WHERE status = 'SUCCESS'")
    loaded = {row[0] for row in cursor.fetchall()}
    conn.close()
    all_files = sorted(glob.glob(os.path.join(BTS_DIR, "bts_*.csv")))
    return [f for f in all_files if Path(f).name not in loaded]

def _check_new_files(**ctx) -> str:
    new_files = _get_new_files()
    ctx["ti"].xcom_push(key="new_files", value=new_files)
    if new_files:
        print(f"Nowe pliki ({len(new_files)}): {new_files}")
        return "upsert_dim_airline"
    print("Brak nowych plików.")
    return "no_new_files"

def _upsert_dim_airline(**ctx):
    from etl.dim_airline import load_dim_airline
    load_dim_airline()

def _upsert_dim_airport(**ctx):
    from etl.dim_airport import load_dim_airport
    load_dim_airport()

def _upsert_dim_weather(**ctx):
    from etl.dim_weather import load_dim_weather
    load_dim_weather()

def _extend_dim_date(**ctx):
    from etl.dim_date import load_dim_date
    new_files = ctx["ti"].xcom_pull(key="new_files", task_ids="check_new_files")
    load_dim_date(files=new_files)

def _load_new_facts(**ctx):
    from etl.fact_flight import load_fact_flights
    new_files = ctx["ti"].xcom_pull(key="new_files", task_ids="check_new_files")
    if not new_files:
        return
    load_fact_flights(files=new_files)

def _mark_files_loaded(**ctx):
    from etl.utils import get_connection
    from pathlib import Path
    new_files = ctx["ti"].xcom_pull(key="new_files", task_ids="check_new_files")
    if not new_files:
        return
    conn = get_connection()
    cursor = conn.cursor()
    for filepath in new_files:
        fname = Path(filepath).name
        cursor.execute("""
            MERGE ETL_Load_Log AS target
            USING (VALUES (?)) AS source (file_name)
            ON target.file_name = source.file_name
            WHEN MATCHED THEN
                UPDATE SET loaded_at = GETDATE(), status = 'SUCCESS'
            WHEN NOT MATCHED THEN
                INSERT (file_name, loaded_at, status) VALUES (?, GETDATE(), 'SUCCESS');
        """, fname, fname)
    conn.commit()
    conn.close()

with DAG(
    dag_id="flight_dw__incremental_load",
    description="Przyrostowy load — wykrywa i ładuje nowe pliki BTS",
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
    catchup=False,
    default_args=default_args,
    tags=["flight_dw", "incremental", "etl"],
    max_active_runs=1,
) as dag:

    start = EmptyOperator(task_id="start")
    end   = EmptyOperator(task_id="end")

    check = BranchPythonOperator(task_id="check_new_files", python_callable=_check_new_files)

    no_new = EmptyOperator(task_id="no_new_files", trigger_rule="none_failed")

    t_airline = PythonOperator(task_id="upsert_dim_airline", python_callable=_upsert_dim_airline)
    t_airport = PythonOperator(task_id="upsert_dim_airport", python_callable=_upsert_dim_airport)
    t_weather = PythonOperator(task_id="upsert_dim_weather", python_callable=_upsert_dim_weather)
    t_date    = PythonOperator(task_id="extend_dim_date",    python_callable=_extend_dim_date)

    t_facts = PythonOperator(task_id="load_new_facts",      python_callable=_load_new_facts)
    t_log   = PythonOperator(task_id="mark_files_loaded",   python_callable=_mark_files_loaded,
                             trigger_rule="all_success")

    start >> check
    check >> no_new >> end
    check >> [t_airline, t_airport, t_weather, t_date] >> t_facts >> t_log >> end
