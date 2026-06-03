import pandas as pd
import glob
import os
from etl.utils import get_connection, truncate_and_load
from config import PATHS

def load_dim_airline():
    print("Dim_Airline")
    conn = get_connection()

    #extract
    print("kody linii z plików BTS")
    dfs = []
    for f in glob.glob(os.path.join(PATHS["bts"], "*.csv")):
        df = pd.read_csv(f, usecols=["OP_UNIQUE_CARRIER"], low_memory=False)
        dfs.append(df)

    bts_codes = pd.concat(dfs, ignore_index=True) \
                  .drop_duplicates() \
                  .rename(columns={"OP_UNIQUE_CARRIER": "airline_code"})

    print(f"Unikalnych kodów w BTS: {len(bts_codes)}")

    #transform

    print("wczytywanie słownika IATA")
    iata = pd.read_csv(
        PATHS["airlines"],
        sep="^",
        usecols=["iata_code", "name"],
        low_memory=False
    )

    #czyszczenie obu źródeł - spacje i wielkość liter
    iata = iata.dropna(subset=["iata_code", "name"])
    iata["iata_code"] = iata["iata_code"].str.strip().str.upper()
    iata["name"] = iata["name"].str.strip()

    #to samo co do kodów BTS
    bts_codes["airline_code"] = bts_codes["airline_code"].str.strip().str.upper()

    #JOIN po kodzie IATA - pełna nazwa
    airlines = bts_codes.merge(
        iata[["iata_code", "name"]],
        left_on="airline_code",
        right_on="iata_code",
        how="left"
    ).drop(columns=["iata_code"]) \
     .rename(columns={"name": "airline_name"})

    #linie bez nazwy wypisujemy i pomijamy
    missing = airlines[airlines["airline_name"].isna()]
    if not missing.empty:
        print(f"brak nazwy dla kodów: {missing['airline_code'].tolist()}")
        print("te linie zostaną pominięte")

    #usuwanie wierszy bez nazwy
    airlines = airlines.dropna(subset=["airline_name"])

    #usuwanie duplikatów gdyby iata miała duplikaty
    airlines = airlines.drop_duplicates(subset=["airline_code"])
    airlines = airlines.sort_values("airline_code").reset_index(drop=True)

    #weryfikacja
    print(f"\nWynik transformacji:")
    print(airlines.to_string(index=False))
    print(f"\nLiczba linii do załadowania: {len(airlines)}")

    #sprawdzanie czy airline_code ma max 2 znaki
    too_long = airlines[airlines["airline_code"].str.len() > 2]
    if not too_long.empty:
        print(f" Kody dłuższe niż 2 znaki: {too_long['airline_code'].tolist()}")
        airlines = airlines[airlines["airline_code"].str.len() <= 2]

    #czy airline_name nie jest pusty
    empty_names = airlines[airlines["airline_name"].str.strip() == ""]
    if not empty_names.empty:
        print(f"Puste nazwy dla: {empty_names['airline_code'].tolist()}")
        airlines = airlines[airlines["airline_name"].str.strip() != ""]

    #load
    truncate_and_load(airlines, "Dim_Airline", conn)
    conn.close()

if __name__ == "__main__":
    load_dim_airline()