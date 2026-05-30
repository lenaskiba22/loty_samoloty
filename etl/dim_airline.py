# etl/dim_airline.py
import pandas as pd
import glob
import os
from etl.utils import get_connection, truncate_and_load
from config import PATHS

def load_dim_airline():
    print("=== Dim_Airline ===")
    conn = get_connection()

    # ── EXTRACT ────────────────────────────────────────────────
    # Wczytaj unikalne kody linii z wszystkich 6 plików BTS
    print("Wczytuję kody linii z plików BTS...")
    dfs = []
    for f in glob.glob(os.path.join(PATHS["bts"], "*.csv")):
        df = pd.read_csv(f, usecols=["OP_UNIQUE_CARRIER"], low_memory=False)
        dfs.append(df)

    bts_codes = pd.concat(dfs, ignore_index=True) \
                  .drop_duplicates() \
                  .rename(columns={"OP_UNIQUE_CARRIER": "airline_code"})

    print(f"Unikalnych kodów w BTS: {len(bts_codes)}")

    # ── TRANSFORM ──────────────────────────────────────────────
    # Wczytaj słownik nazw z IATA
    print("Wczytuję słownik IATA...")
    iata = pd.read_csv(
        PATHS["airlines"],
        sep="^",
        usecols=["iata_code", "name"],
        low_memory=False
    )

    # Czyszczenie słownika IATA
    iata = iata.dropna(subset=["iata_code", "name"])
    iata["iata_code"] = iata["iata_code"].str.strip().str.upper()
    iata["name"] = iata["name"].str.strip()

    # Czyszczenie kodów BTS
    bts_codes["airline_code"] = bts_codes["airline_code"].str.strip().str.upper()

    # JOIN po kodzie IATA → pobierz pełną nazwę
    airlines = bts_codes.merge(
        iata[["iata_code", "name"]],
        left_on="airline_code",
        right_on="iata_code",
        how="left"
    ).drop(columns=["iata_code"]) \
     .rename(columns={"name": "airline_name"})

    # Kontrola jakości — sprawdź brakujące nazwy
    missing = airlines[airlines["airline_name"].isna()]
    if not missing.empty:
        print(f"Brak nazwy dla kodów: {missing['airline_code'].tolist()}")
        print("   → Te linie zostaną pominięte")

    # Usuń wiersze bez nazwy
    airlines = airlines.dropna(subset=["airline_name"])

    # Usuń duplikaty (na wypadek gdyby IATA miała duplikaty kodów)
    airlines = airlines.drop_duplicates(subset=["airline_code"])

    # Sortuj dla czytelności
    airlines = airlines.sort_values("airline_code").reset_index(drop=True)

    # ── WERYFIKACJA ────────────────────────────────────────────
    print(f"\nWynik transformacji:")
    print(airlines.to_string(index=False))
    print(f"\nLiczba linii do załadowania: {len(airlines)}")

    # Sprawdź czy airline_code ma max 2 znaki (zgodnie z VARCHAR(2))
    too_long = airlines[airlines["airline_code"].str.len() > 2]
    if not too_long.empty:
        print(f" Kody dłuższe niż 2 znaki: {too_long['airline_code'].tolist()}")
        airlines = airlines[airlines["airline_code"].str.len() <= 2]

    # Sprawdź czy airline_name nie jest pusty
    empty_names = airlines[airlines["airline_name"].str.strip() == ""]
    if not empty_names.empty:
        print(f"Puste nazwy dla: {empty_names['airline_code'].tolist()}")
        airlines = airlines[airlines["airline_name"].str.strip() != ""]

    # ── LOAD ───────────────────────────────────────────────────
    truncate_and_load(airlines, "Dim_Airline", conn)
    conn.close()

if __name__ == "__main__":
    load_dim_airline()