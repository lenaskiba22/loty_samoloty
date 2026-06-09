from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.standard.operators.empty import EmptyOperator

default_args = {
    "owner": "etl",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

def _load_dim_airline():
    from etl.dim_airline import load_dim_airline
    load_dim_airline()

def _load_dim_airport():
    from etl.dim_airport import load_dim_airport
    load_dim_airport()

def _load_dim_date():
    from etl.dim_date import load_dim_date
    load_dim_date()

def _load_dim_weather():
    from etl.dim_weather import load_dim_weather
    load_dim_weather()

def _load_fact_flights():
    from etl.fact_flight import load_fact_flights
    load_fact_flights()

with DAG(
    dag_id="flight_dw__initial_load",
    description="Jednorazowy pełny load hurtowni danych lotów",
    start_date=datetime(2024, 1, 1),
    schedule=None,              
    catchup=False,
    default_args=default_args,
    tags=["flight_dw", "initial", "etl"],
) as dag:

    start = EmptyOperator(task_id="start")
    end   = EmptyOperator(task_id="end")
    
    t_airline = PythonOperator(task_id="load_dim_airline", python_callable=_load_dim_airline)
    t_airport = PythonOperator(task_id="load_dim_airport", python_callable=_load_dim_airport)
    t_date    = PythonOperator(task_id="load_dim_date",    python_callable=_load_dim_date)
    t_weather = PythonOperator(task_id="load_dim_weather", python_callable=_load_dim_weather)
    t_facts   = PythonOperator(task_id="load_fact_flights", python_callable=_load_fact_flights)

start >> t_airline >> t_airport >> t_date >> t_weather >> t_facts >> end