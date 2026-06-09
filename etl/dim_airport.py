# etl/dim_airport.py
import pandas as pd
import glob
import os
from timezonefinder import TimezoneFinder
from etl.utils import get_connection, truncate_and_load
from etl.config import PATHS

def load_dim_airport(files: list[str] | None = None):
    print("=== Dim_Airport ===")
    

    # ── EXTRACT ────────────────────────────────────────────────
    # Źródło 1: BTS CSV - ORIGIN, DEST, ORIGIN_CITY_NAME
    print("Wczytuję kody lotnisk z plików BTS...")
    dfs = []
    for f in glob.glob(os.path.join(PATHS["bts"], "*.csv")):
        df = pd.read_csv(
            f,
            usecols=["ORIGIN", "DEST", "ORIGIN_CITY_NAME"],
            low_memory=False
        )
        dfs.append(df)

    df_bts = pd.concat(dfs, ignore_index=True)

    # SELECT DISTINCT ORIGIN i DEST - scalenie w jedną listę
    origins = df_bts[["ORIGIN", "ORIGIN_CITY_NAME"]].drop_duplicates()
    origins.columns = ["airport_code", "city_raw"]

    dests = df_bts[["DEST"]].drop_duplicates()
    dests.columns = ["airport_code"]
    dests["city_raw"] = None

    all_codes = pd.concat([origins, dests], ignore_index=True) \
                  .drop_duplicates(subset=["airport_code"]) \
                  .reset_index(drop=True)

    print(f"Unikalnych kodów lotnisk w BTS: {len(all_codes)}")

    # Źródło 2: OurAirports airports.csv
    print("Wczytuję OurAirports...")
    airports_raw = pd.read_csv(
        PATHS["airports_full"],
        low_memory=False
    )

    # ── TRANSFORM ──────────────────────────────────────────────
    # Krok 1: Filtrowanie tylko USA i terytoria zamorskie
    # US = kontynentalne USA + Alaska + Hawaje
    # PR = Puerto Rico, VI = Wyspy Dziewicze, MP = Mariany Północne
    airports_us = airports_raw[
        airports_raw["iso_country"].isin(["US", "PR", "VI", "MP"])
    ].copy()

    print(f"Lotnisk US+terytoria w OurAirports: {len(airports_us)}")

    # Krok 2: Odfiltruj lotniska bez kodu IATA (małe lotniska niekomercyjne)
    airports_us = airports_us[
        airports_us["iata_code"].notna() &
        (airports_us["iata_code"].str.strip() != "")
    ].copy()

    print(f"Lotnisk z kodem IATA: {len(airports_us)}")

    # Krok 3: Wyznacz state z iso_region
    # Obsługa różnych formatów:
    # US-CA → CA, US-NY → NY (kontynentalne USA)
    # PR-U-A → PR (Puerto Rico)
    # VI-ST → VI (Wyspy Dziewicze)
    # MP-U-A → MP (Mariany Północne)
    def extract_state(iso_region):
        if pd.isna(iso_region):
            return None
        prefix = iso_region.split("-")[0]
        if prefix == "US":
            parts = iso_region.split("-")
            return parts[1] if len(parts) > 1 else None
        else:
            # Dla terytoriów: zwróć prefix kraju jako state
            return prefix

    airports_us["state"] = airports_us["iso_region"].apply(extract_state)

    # Krok 4: Czyszczenie kodów IATA
    airports_us["iata_code"] = airports_us["iata_code"].str.strip().str.upper()

    # Krok 5: JOIN po iata_code → pobranie name, lat, lon, state, type
    result = all_codes.merge(
        airports_us[[
            "iata_code", "name", "latitude_deg",
            "longitude_deg", "state", "type"
        ]],
        left_on="airport_code",
        right_on="iata_code",
        how="left"
    ).drop(columns=["iata_code"])

    # Krok 6: Pobierz city z ORIGIN_CITY_NAME - split po ', '
    result["city"] = result["city_raw"] \
        .str.split(",").str[0] \
        .str.strip()
    result = result.drop(columns=["city_raw"])

    # Krok 7: Przemianowanie kolumn
    result = result.rename(columns={
        "name": "airport_name",
        "latitude_deg": "latitude",
        "longitude_deg": "longitude"
    })

    # Krok 8: Usuń lotniska bez współrzędnych przed TimezoneFinder
    no_coords = result[result["latitude"].isna() | result["longitude"].isna()]
    if not no_coords.empty:
        print(f" Usuwam {len(no_coords)} lotnisk bez współrzędnych:")
        print(f"   {no_coords['airport_code'].tolist()}")
        result = result[
            result["latitude"].notna() & result["longitude"].notna()
        ].copy()

    # Krok 9: Wyznaczenie strefy czasowej z lat/lon przez TimezoneFinder
    print(f"Wyznaczam strefy czasowe dla {len(result)} lotnisk...")
    tf = TimezoneFinder()

    def get_timezone(row):
        try:
            tz = tf.timezone_at(lat=row["latitude"], lng=row["longitude"])
            return tz  # None jeśli nie znaleziono - nie zakłamujemy
        except Exception:
            return None

    result["timezone"] = result.apply(get_timezone, axis=1)

    # Zaraportuj lotniska bez strefy czasowej
    no_tz = result[result["timezone"].isna()]
    if not no_tz.empty:
        print(f" Brak strefy czasowej dla {len(no_tz)} lotnisk:")
        print(f"   {no_tz['airport_code'].tolist()}")
    else:
        print("Wszystkie lotniska mają strefę czasową")

    # Krok 10: Uporządkuj kolumny zgodnie z DDL tabeli
    result = result[[
        "airport_code", "airport_name", "city",
        "state", "latitude", "longitude", "timezone", "type"
    ]]

    # Zamień NaN na None dla SQL Server
    result = result.where(pd.notna(result), None)

    # ── WERYFIKACJA ────────────────────────────────────────────
    print("\n--- Weryfikacja ---")

    # Test 1: Unikalność airport_code
    dupes = result[result["airport_code"].duplicated()]
    if dupes.empty:
        print(" Unikalność airport_code - brak duplikatów")
    else:
        print(f"Duplikaty: {dupes['airport_code'].tolist()}")
        result = result.drop_duplicates(subset=["airport_code"])

    # Test 2: NULL w latitude lub longitude = 0
    nulls_coords = result[
        result["latitude"].isna() | result["longitude"].isna()
    ]
    if nulls_coords.empty:
        print("Brak NULL w latitude/longitude")
    else:
        print(f"NULL w współrzędnych: {len(nulls_coords)} lotnisk")

    # Test 3: Format state - dokładnie 2 znaki, brak prefiksu
    bad_state = result[
        result["state"].notna() &
        (result["state"].str.len() != 2)
    ]
    if bad_state.empty:
        print("Format state - wszystkie kody 2-znakowe")
    else:
        print(f" Niepoprawny format state ({len(bad_state)} lotnisk):")
        print(f"   {bad_state[['airport_code', 'state']].values.tolist()}")

    # Test 4: Co najmniej 99.5% lotów z BTS ma dopasowane lotnisko
    total_bts = len(all_codes)
    matched = result["airport_name"].notna().sum()
    coverage = matched / total_bts * 100
    if coverage >= 99.499:
        print(f" Pokrycie lotnisk: {coverage:.1f}% (>99.5%)")
    else:
        print(f" Pokrycie lotnisk: {coverage:.1f}% (<99.5%)")
        # Pokaż które lotniska nie mają dopasowania
        unmatched = result[result["airport_name"].isna()]
        print(f"   Niedopasowane: {unmatched['airport_code'].tolist()}")

    print(f"\nLotnisk do załadowania: {len(result)}")

    # ── LOAD ───────────────────────────────────────────────────
    conn = get_connection()
    truncate_and_load(result, "Dim_Airport", conn)
    conn.close()

if __name__ == "__main__":
    load_dim_airport()