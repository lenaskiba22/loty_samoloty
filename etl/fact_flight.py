import pandas as pd
import numpy as np
import glob
import os
from etl.utils import get_connection, is_file_loaded, log_file_load, log_error
from config import PATHS


def get_weather_category_id(weathercode):
    # mapowanie surowego kod WMO z Open-Meteo na category_id z Dim_Weather

    if pd.isna(weathercode):
        return None
    wc = int(weathercode)
    if wc == 0:  return 0
    if wc <= 3:  return 1
    if wc <= 48: return 2
    if wc <= 55: return 3
    if wc <= 57: return 4
    if wc <= 65: return 5
    if wc <= 67: return 6
    if wc <= 75: return 7
    if wc <= 77: return 8
    if wc <= 82: return 9
    if wc <= 86: return 10
    if wc <= 95: return 11
    if wc <= 99: return 12
    return None


def nan_to_none(val):

    # konwertuje NaN/NaT/pd.NA na None
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    return val


def row_to_tuple(row):
    # konwertuje wiersz DataFrame na tuple z None zamiast NaN
    return tuple(nan_to_none(v) for v in row)


def load_Fact_Flights():
    print("=== Fact_Flights ===")
    conn = get_connection()

    cursor = conn.cursor()
    cursor.fast_executemany = True

    # ekstrakcja przyrostowa
    all_files = sorted(glob.glob(os.path.join(PATHS["bts"], "*.csv")))
    new_files = [
        f for f in all_files
        if not is_file_loaded(os.path.basename(f), conn)
    ]

    if not new_files:
        print("Brak nowych plików — pipeline aktualny.")
        conn.close()
        return

    print(f"Nowe pliki do przetworzenia: {len(new_files)}")
    for f in new_files:
        print(f"  {os.path.basename(f)}")

    print("\nWczytuję dane pogodowe...")
    weather = pd.read_csv(PATHS["weather"], low_memory=False)
    weather["date"]         = weather["date"].astype(str)
    weather["hour"]         = weather["hour"].astype(int)
    weather["airport_iata"] = weather["airport_iata"].str.strip().str.upper()
    weather["weather_category_id"] = weather["weathercode"].apply(
        get_weather_category_id
    )
    print(f"Rekordów pogodowych: {len(weather):,}")

    # pobieranie zbioru lotniska z Dim_Airport
    # używanie do filtrowania lotów z nieznanymi kodami DEST/ORIGIN
    cursor.execute("SELECT airport_code FROM Dim_Airport")
    valid_airports = set(row[0] for row in cursor.fetchall())
    print(f"Lotnisk w Dim_Airport: {len(valid_airports)}")

    # pobieranie aktualny max flight_id
    cursor.execute("SELECT ISNULL(MAX(flight_id), 0) FROM Fact_Flights")
    current_id = int(cursor.fetchone()[0])
    print(f"Aktualny max flight_id w bazie: {current_id}")

    BTS_COLS = [
        "FL_DATE", "OP_UNIQUE_CARRIER",
        "ORIGIN", "DEST",
        "CRS_DEP_TIME",
        "ARR_DELAY", "DEP_DELAY",
        "CARRIER_DELAY", "WEATHER_DELAY", "NAS_DELAY",
        "SECURITY_DELAY", "LATE_AIRCRAFT_DELAY",
        "TAXI_OUT", "TAXI_IN",
        "CRS_ELAPSED_TIME", "AIR_TIME",
        "DISTANCE",
        "CANCELLED", "CANCELLATION_CODE", "DIVERTED"
    ]

    RESULT_COLS = [
        "flight_id", "airline_code",
        "origin_airport_code", "dest_airport_code",
        "flight_date", "weather_category_id",
        "arr_delay", "dep_delay",
        "carrier_delay", "weather_delay", "nas_delay",
        "security_delay", "late_aircraft_delay",
        "taxi_out", "taxi_in",
        "crs_elapsed_time", "air_time",
        "distance",
        "cancelled", "cancellation_code", "diverted",
        "is_delayed",
        "temperature_c", "precipitation_mm", "windspeed_kmh"
    ]

    sql = (
        f"INSERT INTO Fact_Flights ({', '.join(RESULT_COLS)}) "
        f"VALUES ({', '.join(['?' for _ in RESULT_COLS])})"
    )

    for file_path in new_files:
        file_name = os.path.basename(file_path)
        print(f"\n--- Przetwarzam: {file_name} ---")

        try:
            # extract
            df = pd.read_csv(file_path, usecols=BTS_COLS, low_memory=False)
            print(f"  Wczytano {len(df):,} rekordów")

            # transform

            # czyszczenie kodów przed JOINami i filtrowaniem
            df["ORIGIN"] = df["ORIGIN"].str.strip().str.upper()
            df["DEST"]   = df["DEST"].str.strip().str.upper()
            df["OP_UNIQUE_CARRIER"] = df["OP_UNIQUE_CARRIER"].str.strip().str.upper()

            # data lotu jako string YYYY-MM-DD
            df["flight_date"] = (
                pd.to_datetime(df["FL_DATE"], format="mixed")
                .dt.date
                .astype(str)
            )

            # godzina odlotu z CRS_DEP_TIME (HHMM -> H), 2400 -> 0
            dep_time    = df["CRS_DEP_TIME"].fillna(0).astype(int)
            df["dep_hour"] = (dep_time // 100).replace(24, 0).clip(0, 23)

            # filtrowanie FK: usuń loty z nieznanym ORIGIN lub DEST
            before = len(df)
            mask_origin = df["ORIGIN"].isin(valid_airports)
            mask_dest   = df["DEST"].isin(valid_airports)
            rejected = df[~mask_origin | ~mask_dest]
            if not rejected.empty:
                unknown_origins = set(df.loc[~mask_origin, "ORIGIN"].unique())
                unknown_dests   = set(df.loc[~mask_dest,   "DEST"].unique())
                print(f"  UWAGA: odrzucam {len(rejected):,} lotów z nieznanymi lotniskami")
                if unknown_origins:
                    print(f"    Nieznane ORIGIN ({len(unknown_origins)}): {sorted(unknown_origins)}")
                if unknown_dests:
                    print(f"    Nieznane DEST   ({len(unknown_dests)}):   {sorted(unknown_dests)}")
            df = df[mask_origin & mask_dest].copy()
            print(f"  Po filtrowaniu FK lotnisk: {len(df):,} rekordów (odrzucono {before - len(df):,})")

            # JOIN z pogodą po: lotnisko wylotu + data + godzina
            df = df.merge(
                weather[[
                    "airport_iata", "date", "hour",
                    "temperature_2m", "precipitation",
                    "windspeed_10m", "weather_category_id"
                ]],
                left_on=["ORIGIN", "flight_date", "dep_hour"],
                right_on=["airport_iata", "date", "hour"],
                how="left"
            )

            # fillna(0) dla kolumn przyczyn opóźnień
            delay_cols = [
                "CARRIER_DELAY", "WEATHER_DELAY", "NAS_DELAY",
                "SECURITY_DELAY", "LATE_AIRCRAFT_DELAY"
            ]
            df[delay_cols] = df[delay_cols].fillna(0)

            # flagi jako int
            df["CANCELLED"] = df["CANCELLED"].fillna(0).astype(int)
            df["DIVERTED"]  = df["DIVERTED"].fillna(0).astype(int)

            # is_delayed: NULL dla anulowanych, 0/1 dla pozostałych (def. DOT > 15 min)
            is_not_cancelled = df["CANCELLED"] == 0
            df["is_delayed"] = np.where(
                is_not_cancelled,
                (df["ARR_DELAY"] > 15).astype("Int64"),
                pd.NA
            )

            # generuj flight_id (kontynuacja od ostatniego w bazie)
            df["flight_id"] = range(current_id + 1, current_id + 1 + len(df))
            current_id += len(df)

            # zmianaa nazw kolumn
            df = df.rename(columns={
                "OP_UNIQUE_CARRIER":   "airline_code",
                "ORIGIN":              "origin_airport_code",
                "DEST":                "dest_airport_code",
                "ARR_DELAY":           "arr_delay",
                "DEP_DELAY":           "dep_delay",
                "CARRIER_DELAY":       "carrier_delay",
                "WEATHER_DELAY":       "weather_delay",
                "NAS_DELAY":           "nas_delay",
                "SECURITY_DELAY":      "security_delay",
                "LATE_AIRCRAFT_DELAY": "late_aircraft_delay",
                "TAXI_OUT":            "taxi_out",
                "TAXI_IN":             "taxi_in",
                "CRS_ELAPSED_TIME":    "crs_elapsed_time",
                "AIR_TIME":            "air_time",
                "DISTANCE":            "distance",
                "CANCELLED":           "cancelled",
                "CANCELLATION_CODE":   "cancellation_code",
                "DIVERTED":            "diverted",
                "temperature_2m":      "temperature_c",
                "precipitation":       "precipitation_mm",
                "windspeed_10m":       "windspeed_kmh",
            })

            result = df[RESULT_COLS].copy()

            # weryfikacja pezed załadowaniem
            print(f"\n  --- Weryfikacja {file_name} ---")

            weather_nulls = result["weather_category_id"].isna().sum()
            weather_pct   = (1 - weather_nulls / len(result)) * 100
            status = "OK" if weather_pct >= 99 else "UWAGA: poniżej 99%"
            print(f"  Pokrycie pogoda: {weather_pct:.1f}% ({status})")

            delayed_vals = result["is_delayed"].dropna()
            delayed_pct  = float(delayed_vals.astype(int).mean()) * 100
            status = "OK" if 20 <= delayed_pct <= 40 else "UWAGA: poza przedziałem"
            print(f"  % opóźnionych: {delayed_pct:.1f}% ({status})")

            nulls_arr = result[
                result["arr_delay"].isna() &
                (result["cancelled"] == 0) &
                (result["diverted"]  == 0)
            ]
            if nulls_arr.empty:
                print("  NULL w arr_delay tylko dla anulowanych (OK)")
            else:
                print(f"  UWAGA: {len(nulls_arr)} NULL w arr_delay dla nieanulowanych")

            print(f"  Rekordów do załadowania: {len(result):,}")

            # konwersja typów przed load
            # jawna konwersja każdej kolumny, NaN jako float powoduje błąd 22003
            # przy fast_executemany (pyodbc nie konwertuje nan -> NULL automatycznie)

            for col in ["flight_id", "cancelled", "diverted"]:
                result[col] = result[col].astype(int)

            for col in ["weather_category_id", "is_delayed"]:
                result[col] = result[col].apply(
                    lambda x: int(x) if pd.notna(x) else None
                )

            float_cols = [
                "arr_delay", "dep_delay",
                "carrier_delay", "weather_delay", "nas_delay",
                "security_delay", "late_aircraft_delay",
                "taxi_out", "taxi_in",
                "crs_elapsed_time", "air_time", "distance",
                "temperature_c", "precipitation_mm", "windspeed_kmh"
            ]
            for col in float_cols:
                result[col] = result[col].apply(
                    lambda x: float(x) if pd.notna(x) else None
                )

            for col in ["airline_code", "origin_airport_code",
                        "dest_airport_code", "flight_date",
                        "cancellation_code"]:
                result[col] = result[col].apply(
                    lambda x: str(x).strip() if pd.notna(x) else None
                )

            # load
            rows = [row_to_tuple(row) for row in result.itertuples(index=False)]
            cursor.executemany(sql, rows)
            conn.commit()

            log_file_load(file_name, len(rows), conn)
            print(f"  Załadowano {len(rows):,} rekordów ✓")

        except Exception as e:
            conn.rollback()
            log_error(file_name, str(e), conn)
            print(f"  BŁĄD przy {file_name}: {e}")
            raise

    conn.close()
    print("\n=== Fact_Flights: zakończono ===")


if __name__ == "__main__":
    load_Fact_Flights()