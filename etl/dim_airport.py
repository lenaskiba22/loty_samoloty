import pandas as pd
import glob
import os
from timezonefinder import TimezoneFinder
from etl.utils import get_connection, truncate_and_load
from config import PATHS

def load_dim_airport():
    print("Dim_Airport")
    conn = get_connection()

    #extract
    print("kody lotnisk z plików BTS")
    dfs = []
    for f in glob.glob(os.path.join(PATHS["bts"], "*.csv")):
        df = pd.read_csv(
            f,
            usecols=["ORIGIN", "DEST", "ORIGIN_CITY_NAME"],
            low_memory=False
        )
        dfs.append(df)

    df_bts = pd.concat(dfs, ignore_index=True)

    # SELECT DISTINCT ORIGIN i DEST - scalenie w jedną listę niezaleznie od kierunku lotu
    origins = df_bts[["ORIGIN", "ORIGIN_CITY_NAME"]].drop_duplicates()
    origins.columns = ["airport_code", "city_raw"]

    dests = df_bts[["DEST"]].drop_duplicates()
    dests.columns = ["airport_code"]
    dests["city_raw"] = None

    all_codes = pd.concat([origins, dests], ignore_index=True) \
                  .drop_duplicates(subset=["airport_code"]) \
                  .reset_index(drop=True)

    print(f"unikalnych kodów lotnisk w BTS jest {len(all_codes)}")


    print("wczytywanie OurAirports")
    airports_raw = pd.read_csv(
        r"C:\Users\Magda\Desktop\project_bi\data\raw\airports\airports.csv",
        low_memory=False
    )

    #transform
    #filtrowanie tylko USA i terytoria zamorskie
    #bo US = kontynentalne USA + Alaska + Hawaje
    #i dodajemy terany zamorskie PR = Puerto Rico, VI = Wyspy Dziewicze, MP = Mariany Północne
    airports_us = airports_raw[
        airports_raw["iso_country"].isin(["US", "PR", "VI", "MP"])
    ].copy()

    print(f"Lotnisk US+terytoria zamorskie w OurAirports: {len(airports_us)}")

    #odfiltrowanie lotnisk bez kodu IATA bo małe lotniska niekomercyjne nie obchodzą nas
    airports_us = airports_us[
        airports_us["iata_code"].notna() &
        (airports_us["iata_code"].str.strip() != "")
    ].copy()

    print(f"Lotnisk z kodem IATA: {len(airports_us)}")

    #wyznaczenie state z iso_region
    #obsługa różnych formatów - USA: "US-CA" to "CA", a te nadmorskie to chcemy PR z PR-U-A

    def extract_state(iso_region):
        if pd.isna(iso_region):
            return None
        prefix = iso_region.split("-")[0]
        if prefix == "US":
            parts = iso_region.split("-")
            return parts[1] if len(parts) > 1 else None
        else:
            #dla terytoriów: zwróć prefix kraju
            return prefix

    airports_us["state"] = airports_us["iso_region"].apply(extract_state)

    #czyszczenie duże litery i spacje
    airports_us["iata_code"] = airports_us["iata_code"].str.strip().str.upper()

    #JOIN po iata_code aby pobrać name, lat, lon, state, type
    result = all_codes.merge(
        airports_us[[
            "iata_code", "name", "latitude_deg",
            "longitude_deg", "state", "type"
        ]],
        left_on="airport_code",
        right_on="iata_code",
        how="left"
    ).drop(columns=["iata_code"])

    #tylko city z ORIGIN_CITY_NAME - split po ', ' bo potem skrót nas nie obchodzi
    result["city"] = result["city_raw"] \
        .str.split(",").str[0] \
        .str.strip()
    result = result.drop(columns=["city_raw"])

    #zmiana nazw na zgodne z założeniami
    result = result.rename(columns={
        "name": "airport_name",
        "latitude_deg": "latitude",
        "longitude_deg": "longitude"
    })

    #uswuwanie lotniska bez współrzędnych
    no_coords = result[result["latitude"].isna() | result["longitude"].isna()]
    if not no_coords.empty:
        print(f" Usuwanie {len(no_coords)} lotnisk bez współrzędnych:")
        print(f"   {no_coords['airport_code'].tolist()}")
        result = result[
            result["latitude"].notna() & result["longitude"].notna()
        ].copy()

    #wyznaczenie strefy czasowej z lat/lon przez TimezoneFinder
    print(f"Wyznaczanie strefy czasowe dla {len(result)} lotnisk...")
    tf = TimezoneFinder()

    def get_timezone(row):
        try:
            tz = tf.timezone_at(lat=row["latitude"], lng=row["longitude"])
            return tz  #None jeśli nie znaleziono
        except Exception:
            return None

    result["timezone"] = result.apply(get_timezone, axis=1)

    #zraportowanie lotnisk bez strefy czasowej
    no_tz = result[result["timezone"].isna()]
    if not no_tz.empty:
        print(f" Brak strefy czasowej dla {len(no_tz)} lotnisk:")
        print(f"   {no_tz['airport_code'].tolist()}")
    else:
        print("Wszystkie lotniska mają strefę czasową")

    #kolumny zgodnie z DDL tabeli Dim_Airport
    result = result[[
        "airport_code", "airport_name", "city",
        "state", "latitude", "longitude", "timezone", "type"
    ]]

    # NaN na None dla SQL Server
    result = result.where(pd.notna(result), None)

    #weryfikacja
    print("\n--- Weryfikacja ---")

    #unikalność airport_code
    dupes = result[result["airport_code"].duplicated()]
    if dupes.empty:
        print(" Unikalność airport_code - brak duplikatów")
    else:
        print(f"Duplikaty: {dupes['airport_code'].tolist()}")
        result = result.drop_duplicates(subset=["airport_code"])

    #NULL w latitude lub longitude = 0
    nulls_coords = result[
        result["latitude"].isna() | result["longitude"].isna()
    ]
    if nulls_coords.empty:
        print("Brak NULL w latitude/longitude")
    else:
        print(f"NULL w współrzędnych: {len(nulls_coords)} lotnisk")

    #format state - dokładnie 2 znaki, brak prefiksu
    bad_state = result[
        result["state"].notna() &
        (result["state"].str.len() != 2)
    ]
    if bad_state.empty:
        print("Format state - wszystkie kody 2-znakowe")
    else:
        print(f" Niepoprawny format state ({len(bad_state)} lotnisk):")
        print(f"   {bad_state[['airport_code', 'state']].values.tolist()}")

    #czy powyżej 99.5% lotów z BTS ma dopasowane lotnisko
    total_bts = len(all_codes)
    matched = result["airport_name"].notna().sum()
    coverage = matched / total_bts * 100
    if coverage >= 99.499:
        print(f" Pokrycie lotnisk: {coverage:.1f}% (>99.5%)")
    else:
        print(f" Pokrycie lotnisk: {coverage:.1f}% (<99.5%)")
        #które lotniska nie mają dopasowania
        unmatched = result[result["airport_name"].isna()]
        print(f"   Niedopasowane: {unmatched['airport_code'].tolist()}")

    print(f"\nLotnisk do załadowania: {len(result)}")

    #load
    truncate_and_load(result, "Dim_Airport", conn)
    conn.close()

if __name__ == "__main__":
    load_dim_airport()