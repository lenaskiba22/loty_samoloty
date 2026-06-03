import pyodbc
from config import CONN_STR

def get_connection():
    return pyodbc.connect(CONN_STR)


def truncate_and_load(df, table_name, conn):
    """to bo mamy typ1 scd więc nadpisujemy nowe dane starymi"""
    cursor = conn.cursor()
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
    """sprawdza czy dany plik BTS był już pomyślnie przetworzony, pozwala uruchamiać pipeline wielokrotnie bez duplikowania rekordów w Fact_Flights"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM ETL_Load_Log
        WHERE file_name = ? AND status = 'SUCCESS'
    """, file_name)
    return cursor.fetchone()[0] > 0

def log_file_load(file_name, records, conn):
    """informacje o pomyślnym załadowaniu pliku"""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ETL_Load_Log (file_name, loaded_at, records_loaded, status)
        VALUES (?, GETDATE(), ?, 'SUCCESS')
    """, file_name, records)
    conn.commit()

def log_error(file_name, error_msg, conn):
    """zapisuje błąd ładowania."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ETL_Load_Log (file_name, loaded_at, records_loaded, status)
        VALUES (?, GETDATE(), 0, ?)
    """, file_name, f'ERROR: {str(error_msg)[:90]}')
    conn.commit()