import os

# lokalnie używa ścieżki Windows, w Dockerze bierze z zmiennej środowiskowej
DATA_ROOT = os.environ.get(
    "DATA_BASE_PATH",
    r"C:\Users\admin\Desktop\project_bi_2\project_bi\data\raw"
)

# połączenie — Docker używa SA auth, lokalnie Windows Auth
_mssql_host = os.environ.get("MSSQL_HOST")

if _mssql_host:
    # środowisko Docker — SQL auth
    CONN_STR = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={_mssql_host},{os.environ.get('MSSQL_PORT', '1433')};"
        f"DATABASE={os.environ.get('MSSQL_DB', 'flight_dw')};"
        f"UID={os.environ.get('MSSQL_USER', 'sa')};"
        f"PWD={os.environ.get('MSSQL_PASSWORD', '')};"
        "TrustServerCertificate=yes"
    )
else:
    # środowisko lokalne — Windows Auth
    CONN_STR = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=localhost,1433;"
        "DATABASE=flight_dw;"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes"
    )

PATHS = {
    "bts":          os.path.join(DATA_ROOT, "bts"),
    "airports":     os.path.join(DATA_ROOT, "airports", "airports_us_matched.csv"),
    "weather":      os.path.join(DATA_ROOT, "weather", "weather_raw.csv"),
    "airlines":     os.path.join(DATA_ROOT, "airports", "iata_airlines.csv"),
    "airports_full": os.path.join(DATA_ROOT, "airports", "airports.csv"),
}