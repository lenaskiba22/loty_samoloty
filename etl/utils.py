import pyodbc
from config import CONN_STR


def get_connection():
    # tworzy i zwraca połączenie z bazą danych SQL Server
    return pyodbc.connect(CONN_STR)


def truncate_and_load(df, table_name, conn):
    # ładowanie DataFrame do wskazanej tabeli w trybie SCD Typ 1
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM {table_name}")

    cols         = ', '.join(df.columns)
    placeholders = ', '.join(['?' for _ in df.columns])

    for _, row in df.iterrows():
        cursor.execute(
            f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})",
            tuple(row)
        )

    conn.commit()
    print(f"  {table_name}: załadowano {len(df):,} wierszy")


def is_file_loaded(file_name, conn):
     # sprawdzanie czy dany plik BTS był już pomyślnie przetworzony w poprzednim uruchomieniu
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM ETL_Load_Log
        WHERE file_name = ? AND status = 'SUCCESS'
    """, file_name)
    return cursor.fetchone()[0] > 0


def log_file_load(file_name, records, conn):
    #zapisywanie informacji o pomyślnym załadowaniu pliku do ETL_Load_Log
    cursor = conn.cursor()
    cursor.execute("""
        IF EXISTS (SELECT 1 FROM ETL_Load_Log WHERE file_name = ?)
            UPDATE ETL_Load_Log
               SET loaded_at      = GETDATE(),
                   records_loaded = ?,
                   status         = 'SUCCESS'
             WHERE file_name = ?
        ELSE
            INSERT INTO ETL_Load_Log (file_name, loaded_at, records_loaded, status)
            VALUES (?, GETDATE(), ?, 'SUCCESS')
    """, file_name, records, file_name, file_name, records)
    conn.commit()


def log_error(file_name, error_msg, conn):
    # zapisywanie informacji o błędzie podczas ładowania pliku do ETL_Load_Log
    cursor = conn.cursor()
    cursor.execute("""
        IF EXISTS (SELECT 1 FROM ETL_Load_Log WHERE file_name = ?)
            UPDATE ETL_Load_Log
               SET loaded_at      = GETDATE(),
                   records_loaded = 0,
                   status         = 'ERROR'
             WHERE file_name = ?
        ELSE
            INSERT INTO ETL_Load_Log (file_name, loaded_at, records_loaded, status)
            VALUES (?, GETDATE(), 0, 'ERROR')
    """, file_name, file_name, file_name)
    conn.commit()