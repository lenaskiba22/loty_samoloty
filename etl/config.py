import os

# to powinnyście dopasować do swojej ścieżki z danymi
DATA_ROOT = os.environ.get("DATA_BASE_PATH", r"C:\Users\basia\Downloads\Lab7 - pliki-20260606\sbi-airflow-project\sbi-airflow-project\data\raw")

CONN_STR = (
    f"DRIVER={{ODBC Driver 18 for SQL Server}};"
    f"SERVER={os.environ.get('MSSQL_HOST', 'sqlserver')},"
          f"{os.environ.get('MSSQL_PORT', '1433')};"
    f"DATABASE={os.environ.get('MSSQL_DB', 'flight_dw')};"
    f"UID={os.environ.get('MSSQL_USER', 'sa')};"
    f"PWD={os.environ.get('MSSQL_PASSWORD', 'YourStrong!Pass123')};"
    "TrustServerCertificate=yes;"
)

PATHS = {
    "bts":      os.path.join(DATA_ROOT, "bts"),
    "airports": os.path.join(DATA_ROOT, "airports", "airports_us_matched.csv"),
    "weather":  os.path.join(DATA_ROOT, "weather", "weather_raw.csv"),
    "airlines": os.path.join(DATA_ROOT, "airports", "iata_airlines.csv"),
    "airports_full": os.path.join(DATA_ROOT, "airports", "airports.csv"),
}