# etl/dim_date.py
import pandas as pd
import holidays
import glob
import os
from etl.utils import get_connection, truncate_and_load
from config import PATHS

def load_dim_date():
    print("Dim_Date")
    conn = get_connection()


    print("daty z plików BTS")
    all_data = []
    for f in glob.glob(os.path.join(PATHS["bts"], "*.csv")):
        df = pd.read_csv(f, usecols=["FL_DATE", "CRS_DEP_TIME"], low_memory=False)
        all_data.append(df)

    df = pd.concat(all_data, ignore_index=True).drop_duplicates()

    #parsowanie daty
    df['flight_date'] = pd.to_datetime(df['FL_DATE'], format='mixed').dt.date

    #ustalenei atrybutów
    df_dates = pd.to_datetime(df['flight_date'])
    df['year']        = df_dates.dt.year
    df['quarter']     = df_dates.dt.quarter
    df['month']       = df_dates.dt.month
    df['day_of_week'] = df_dates.dt.day_name()
    df['is_weekend']  = (df_dates.dt.dayofweek >= 5).astype(int)

    #święta federalne USA z biblioteki holidays
    years = df_dates.dt.year.unique().tolist()
    us_holidays = holidays.US(years=years)
    df['is_us_holiday'] = df['flight_date'].apply(
        lambda d: 1 if d in us_holidays else 0
    )

    #usuwanie duplikatów po dacie
    result = df[[
        'flight_date', 'year', 'quarter', 'month',
        'day_of_week', 'is_weekend', 'is_us_holiday'
    ]].drop_duplicates(subset='flight_date')

    #konwersja flight_date na string dla SQL Servera bo nie działa inaczej
    result['flight_date'] = result['flight_date'].astype(str)

    print(f"Unikalnych dat: {len(result)}")
    truncate_and_load(result, "Dim_Date", conn)
    conn.close()

if __name__ == "__main__":
    load_dim_date()