# etl/utils.py
import pyodbc
import pandas as pd
from config import CONN_STR

def get_connection():
    return pyodbc.connect(CONN_STR)


def truncate_and_load(df, table_name, conn):
    """Czyści tabelę i ładuje nowe dane - dla wymiarów."""
    cursor = conn.cursor()

    # DELETE działa nawet gdy są FK constraints (w przeciwieństwie do TRUNCATE)
    cursor.execute(f"DELETE FROM {table_name}")

    cols = ', '.join(df.columns)
    placeholders = ', '.join(['?' for _ in df.columns])

    for _, row in df.iterrows():
        cursor.execute(
            f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})",
            tuple(row)
        )

    conn.commit()
    print(f" {table_name}: załadowano {len(df):,} wierszy")
def is_file_loaded(file_name, conn):
    """Sprawdza czy plik BTS był już przetworzony - ekstrakcja przyrostowa."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM ETL_Load_Log
        WHERE file_name = ? AND status = 'SUCCESS'
    """, file_name)
    return cursor.fetchone()[0] > 0

def log_file_load(file_name, records, conn):
    """Zapisuje info o przetworzonym pliku."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ETL_Load_Log (file_name, loaded_at, records_loaded, status)
        VALUES (?, GETDATE(), ?, 'SUCCESS')
    """, file_name, records)
    conn.commit()

def log_error(file_name, error_msg, conn):
    """Zapisuje błąd ładowania."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ETL_Load_Log (file_name, loaded_at, records_loaded, status)
        VALUES (?, GETDATE(), 0, ?)
    """, file_name, f'ERROR: {str(error_msg)[:90]}')
    conn.commit()