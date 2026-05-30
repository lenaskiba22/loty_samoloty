import pandas as pd
import requests
import time
import os
import glob
from timezonefinder import TimezoneFinder

# Zainstaluj jeśli nie masz:
# pip install timezonefinder

# ============================================================
# ŚCIEŻKI
# ============================================================
BTS_FOLDER   = r"C:\Users\admin\Desktop\project_bi\data\raw\bts"
AIRPORTS_CSV = r"C:\Users\admin\Desktop\project_bi\data\raw\airports\airports.csv"
WEATHER_OUT  = r"C:\Users\admin\Desktop\project_bi\data\raw\weather"
AIRPORTS_OUT = r"C:\Users\admin\Desktop\project_bi\data\raw\airports"
os.makedirs(WEATHER_OUT, exist_ok=True)

# ============================================================
# KROK 1: Unikalne lotniska z BTS
# ============================================================
print("Wczytuję pliki BTS...")
df_bts = pd.concat(
    [pd.read_csv(f, low_memory=False) for f in glob.glob(os.path.join(BTS_FOLDER, "*.csv"))],
    ignore_index=True
)
origins = set(df_bts['ORIGIN'].dropna().unique())
dests   = set(df_bts['DEST'].dropna().unique())
all_airports_iata = origins.union(dests)
print(f"Unikalnych lotnisk w BTS: {len(all_airports_iata)}")

# ============================================================
# KROK 2: Współrzędne z OurAirports
# ============================================================
print("Wczytuję OurAirports...")
df_ap = pd.read_csv(AIRPORTS_CSV, low_memory=False)

us_countries = ['US', 'PR', 'VI', 'MP']
df_us = df_ap[
    (df_ap['iso_country'].isin(us_countries)) &
    (df_ap['iata_code'].notna()) &
    (df_ap['iata_code'] != '')
][['iata_code', 'name', 'municipality', 'iso_region',
   'latitude_deg', 'longitude_deg', 'type']].copy()

df_us = df_us[df_us['iata_code'].isin(all_airports_iata)].copy()
df_us = df_us.drop_duplicates(subset='iata_code').reset_index(drop=True)
df_us['state'] = df_us['iso_region'].str.replace('US-', '', regex=False)

# ============================================================
# KROK 3: Dodaj strefę czasową przez TimezoneFinder
# ============================================================
print("Wyznaczam strefy czasowe z współrzędnych GPS...")
tf = TimezoneFinder()

df_us['timezone'] = df_us.apply(
    lambda row: tf.timezone_at(lat=row['latitude_deg'], lng=row['longitude_deg']),
    axis=1
)

nulls_tz = df_us['timezone'].isna().sum()
print(f"Lotnisk z dopasowanymi współrzędnymi: {len(df_us)}")
print(f"Brakujące strefy czasowe: {nulls_tz}")

# Zapisz słownik lotnisk
airports_matched_path = os.path.join(AIRPORTS_OUT, 'airports_us_matched.csv')
df_us.to_csv(airports_matched_path, index=False)
print(f"Zapisano: airports_us_matched.csv")
print(df_us[['iata_code','name','municipality','state','latitude_deg','longitude_deg','timezone']].head(5).to_string())

# ============================================================
# KROK 4: Pobierz pogodę z Open-Meteo
# ============================================================
DATE_RANGES = [
    ("2022-07-01", "2022-09-30"),
    ("2023-07-01", "2023-09-30"),
]

all_weather = []

print(f"\nPobieram pogodę dla {len(df_us)} lotnisk...")
print("To może potrwać kilka minut.\n")

for i, row in df_us.iterrows():
    iata     = row['iata_code']
    lat      = row['latitude_deg']
    lon      = row['longitude_deg']
    timezone = row['timezone'] if pd.notna(row['timezone']) else 'America/New_York'

    for start_date, end_date in DATE_RANGES:
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude":   lat,
            "longitude":  lon,
            "start_date": start_date,
            "end_date":   end_date,
            "hourly": [
                "temperature_2m",
                "precipitation",
                "windspeed_10m",
                "weathercode"
            ],
            "timezone": timezone
        }

        try:
            resp = requests.get(url, params=params, timeout=30)
            data = resp.json()

            if "hourly" not in data:
                print(f"  ⚠️  {iata} {start_date[:4]}: brak danych — {data.get('reason','?')}")
                continue

            df_w = pd.DataFrame(data["hourly"])
            df_w.rename(columns={"time": "observation_datetime"}, inplace=True)
            df_w['airport_iata']         = iata
            df_w['observation_datetime'] = pd.to_datetime(df_w['observation_datetime'])
            df_w['date']                 = df_w['observation_datetime'].dt.date
            df_w['hour']                 = df_w['observation_datetime'].dt.hour
            all_weather.append(df_w)

        except Exception as e:
            print(f"  ❌ {iata} {start_date[:4]}: błąd — {e}")

        time.sleep(0.15)

    if (i + 1) % 50 == 0:
        print(f"  Postęp: {i+1}/{len(df_us)} lotnisk...")

# ============================================================
# KROK 5: Zapisz pogodę
# ============================================================
if all_weather:
    df_weather_all = pd.concat(all_weather, ignore_index=True)
    out_path = os.path.join(WEATHER_OUT, "weather_raw.csv")
    df_weather_all.to_csv(out_path, index=False)
    print(f"\n✅ Zapisano: weather_raw.csv")
    print(f"   Rekordów:  {len(df_weather_all):,}")
    print(f"   Kolumny:   {list(df_weather_all.columns)}")
else:
    print("❌ Brak danych do zapisania.")