import os

# to powinnyście dopasować do swojej ścieżki z danymi
DATA_ROOT = r"C:\Users\admin\Desktop\project_bi_2\project_bi\data\raw"

CONN_STR = (
    "DRIVER={SQL Server};"
    "SERVER=localhost;"
    "DATABASE=flight_dw;"
    "Trusted_Connection=yes"
)

PATHS = {
    "bts":      os.path.join(DATA_ROOT, "bts"),
    "airports": os.path.join(DATA_ROOT, "airports", "airports_us_matched.csv"),
    "weather":  os.path.join(DATA_ROOT, "weather", "weather_raw.csv"),
    "airlines": os.path.join(DATA_ROOT, "airports", "iata_airlines.csv"),
    "airports_full": os.path.join(DATA_ROOT, "airports", "airports.csv"),
}