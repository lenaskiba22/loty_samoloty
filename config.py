import os

DATA_ROOT = os.environ.get('DATA_ROOT', '/opt/airflow/data/raw')

CONN_STR = (
    'DRIVER={ODBC Driver 18 for SQL Server};'
    'SERVER=sqlserver,1433;'
    'DATABASE=flight_dw;'
    'UID=sa;'
    'PWD=YourStrong!Pass123;'
    'TrustServerCertificate=yes;'
)

PATHS = {
    'bts':      os.path.join(DATA_ROOT, 'bts'),
    'airports': os.path.join(DATA_ROOT, 'airports', 'airports_us_matched.csv'),
    'weather':  os.path.join(DATA_ROOT, 'weather', 'weather_raw.csv'),
    'airlines': os.path.join(DATA_ROOT, 'airports', 'iata_airlines.csv'),
    'airports_full': os.path.join(DATA_ROOT, 'airports', 'airports.csv'),
}
