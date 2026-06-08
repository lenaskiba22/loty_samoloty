import pandas as pd
from etl.utils import get_connection

def run_quality_checks():
    print("\n=== QUALITY CHECKS ===")
    conn = get_connection()

    tests = [
        (
            "Laczna liczba rekordow >= 3 500 000",
            "SELECT COUNT(*) FROM Fact_Flights",
            lambda x: x >= 3500000
        ),
        (
            "FK Airline - brak lotow bez linii",
            """SELECT COUNT(*) FROM Fact_Flights f
               LEFT JOIN Dim_Airline a
               ON f.airline_code = a.airline_code
               WHERE a.airline_code IS NULL""",
            lambda x: x == 0
        ),
        (
            "FK Airport origin - brak niedopasowanych",
            """SELECT COUNT(*) FROM Fact_Flights f
               LEFT JOIN Dim_Airport a
               ON f.origin_airport_code = a.airport_code
               WHERE a.airport_code IS NULL""",
            lambda x: x == 0
        ),
        (
            "FK Airport dest - brak niedopasowanych",
            """SELECT COUNT(*) FROM Fact_Flights f
               LEFT JOIN Dim_Airport a
               ON f.dest_airport_code = a.airport_code
               WHERE a.airport_code IS NULL""",
            lambda x: x == 0
        ),
        (
            "FK Date - brak lotow bez daty",
            """SELECT COUNT(*) FROM Fact_Flights f
               LEFT JOIN Dim_Date d
               ON f.flight_date = d.flight_date
               WHERE d.flight_date IS NULL""",
            lambda x: x == 0
        ),
        (
            "FK Weather - brak lotow bez kategorii pogody",
            """SELECT COUNT(*) FROM Fact_Flights f
               LEFT JOIN Dim_Weather w
               ON f.weather_category_id = w.category_id
               WHERE w.category_id IS NULL""",
            lambda x: x == 0
        ),
        (
            "is_delayed = 1 tylko gdy arr_delay > 15",
            """SELECT COUNT(*) FROM Fact_Flights
               WHERE is_delayed = 1 AND arr_delay <= 15""",
            lambda x: x == 0
        ),
        (
            "carrier_delay bez NULL",
            """SELECT COUNT(*) FROM Fact_Flights
               WHERE carrier_delay IS NULL""",
            lambda x: x == 0
        ),
        (
            "Pokrycie pogoda >= 99%",
            """SELECT
               CAST(COUNT(weather_category_id) AS FLOAT)
               / COUNT(*) * 100
               FROM Fact_Flights""",
            lambda x: x >= 99.0
        ),
    ]

    all_passed = True
    for name, query, condition in tests:
        result = pd.read_sql(query, conn).iloc[0, 0]
        passed = condition(float(result))
        status = "PASS" if passed else "FAIL"
        print(f"  {status}: {name} (wynik: {result:,.2f})")
        if not passed:
            all_passed = False

    conn.close()

    if all_passed:
        print("\nWszystkie testy przeszly - dane gotowe")
    else:
        print("\nNiektore testy nie przeszly - sprawdz dane")

    return all_passed

if __name__ == "__main__":
    run_quality_checks()