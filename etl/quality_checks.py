import pandas as pd
from etl.utils import get_connection


def run_quality_checks():
    print("\n=== QUALITY CHECKS ===")
    conn = get_connection()

    tests = [
        # ── DIM_AIRLINE ───────────────────────────────────────────────────────
        (
            "Dim_Airline: liczba wierszy = 17",
            "SELECT COUNT(*) FROM Dim_Airline",
            lambda x: x == 17
        ),
        (
            "Dim_Airline: brak NULL w airline_name",
            "SELECT COUNT(*) FROM Dim_Airline WHERE airline_name IS NULL",
            lambda x: x == 0
        ),
        (
            "Dim_Airline: brak kodow dluzszych niz 2 znaki",
            "SELECT COUNT(*) FROM Dim_Airline WHERE LEN(airline_code) > 2",
            lambda x: x == 0
        ),
        # duplikaty airline_code — analogicznie jak airport_code ponizej
        (
            "Dim_Airline: brak duplikatow w airline_code",
            """SELECT COUNT(*) FROM (
               SELECT airline_code, COUNT(*) cnt
               FROM Dim_Airline GROUP BY airline_code
               HAVING COUNT(*) > 1) x""",
            lambda x: x == 0
        ),

        # ── DIM_AIRPORT ───────────────────────────────────────────────────────
        (
            "Dim_Airport: liczba wierszy >= 360",
            "SELECT COUNT(*) FROM Dim_Airport",
            lambda x: x >= 360
        ),
        (
            "Dim_Airport: brak duplikatow w airport_code",
            """SELECT COUNT(*) FROM (
               SELECT airport_code, COUNT(*) cnt
               FROM Dim_Airport GROUP BY airport_code
               HAVING COUNT(*) > 1) x""",
            lambda x: x == 0
        ),
        (
            "Dim_Airport: brak NULL w latitude i longitude",
            """SELECT COUNT(*) FROM Dim_Airport
               WHERE latitude IS NULL OR longitude IS NULL""",
            lambda x: x == 0
        ),
        (
            "Dim_Airport: brak NULL w timezone",
            "SELECT COUNT(*) FROM Dim_Airport WHERE timezone IS NULL",
            lambda x: x == 0
        ),
        (
            "Dim_Airport: format state - wszystkie kody 2-znakowe",
            """SELECT COUNT(*) FROM Dim_Airport
               WHERE state IS NOT NULL AND LEN(state) != 2""",
            lambda x: x == 0
        ),
        # pokrycie lotnisk >= 99.5%
        # (brak nazwy = lotnisko nie znalazlo dopasowania w OurAirports)
        (
            "Dim_Airport: pokrycie nazw lotnisk >= 99.5%",
            """SELECT CAST(
                   COUNT(airport_name) AS FLOAT
               ) / COUNT(*) * 100
               FROM Dim_Airport""",
            lambda x: x >= 99.5
        ),

        # ── DIM_DATE ─────────────────────────────────────────────────────────
        (
            "Dim_Date: liczba wierszy = 184",
            "SELECT COUNT(*) FROM Dim_Date",
            lambda x: x == 184
        ),
        (
            "Dim_Date: brak duplikatow w flight_date",
            """SELECT COUNT(*) FROM (
               SELECT flight_date, COUNT(*) cnt
               FROM Dim_Date GROUP BY flight_date
               HAVING COUNT(*) > 1) x""",
            lambda x: x == 0
        ),
        (
            "Dim_Date: is_us_holiday = 1 dla 4 dat",
            "SELECT COUNT(*) FROM Dim_Date WHERE is_us_holiday = 1",
            lambda x: x == 4
        ),
        (
            "Dim_Date: zakres dat tylko Q3 2022 i Q3 2023",
            """SELECT COUNT(*) FROM Dim_Date
               WHERE flight_date < '2022-07-01'
                  OR (flight_date > '2022-09-30'
                      AND flight_date < '2023-07-01')
                  OR flight_date > '2023-09-30'""",
            lambda x: x == 0
        ),

        # ── DIM_WEATHER ───────────────────────────────────────────────────────
        (
            "Dim_Weather: liczba wierszy = 13",
            "SELECT COUNT(*) FROM Dim_Weather",
            lambda x: x == 13
        ),
        (
            "Dim_Weather: brak duplikatow w category_id",
            """SELECT COUNT(*) FROM (
               SELECT category_id, COUNT(*) cnt
               FROM Dim_Weather GROUP BY category_id
               HAVING COUNT(*) > 1) x""",
            lambda x: x == 0
        ),
        (
            "Dim_Weather: brak NULL w weather_category",
            "SELECT COUNT(*) FROM Dim_Weather WHERE weather_category IS NULL",
            lambda x: x == 0
        ),
        (
            "Dim_Weather: is_adverse tylko 0 lub 1",
            """SELECT COUNT(*) FROM Dim_Weather
               WHERE is_adverse NOT IN (0, 1)""",
            lambda x: x == 0
        ),

        # ── FACT_FLIGHTS ──────────────────────────────────────────────────────
        (
            "Fact_Flights: laczna liczba rekordow >= 3 500 000",
            "SELECT COUNT(*) FROM Fact_Flights",
            lambda x: x >= 3500000
        ),
        (
            "Fact_Flights: FK Airline - brak lotow bez linii",
            """SELECT COUNT(*) FROM Fact_Flights f
               LEFT JOIN Dim_Airline a
               ON f.airline_code = a.airline_code
               WHERE a.airline_code IS NULL""",
            lambda x: x == 0
        ),
        (
            "Fact_Flights: FK Airport origin - brak niedopasowanych",
            """SELECT COUNT(*) FROM Fact_Flights f
               LEFT JOIN Dim_Airport a
               ON f.origin_airport_code = a.airport_code
               WHERE a.airport_code IS NULL""",
            lambda x: x == 0
        ),
        (
            "Fact_Flights: FK Airport dest - brak niedopasowanych",
            """SELECT COUNT(*) FROM Fact_Flights f
               LEFT JOIN Dim_Airport a
               ON f.dest_airport_code = a.airport_code
               WHERE a.airport_code IS NULL""",
            lambda x: x == 0
        ),
        (
            "Fact_Flights: FK Date - brak lotow bez daty",
            """SELECT COUNT(*) FROM Fact_Flights f
               LEFT JOIN Dim_Date d
               ON f.flight_date = d.flight_date
               WHERE d.flight_date IS NULL""",
            lambda x: x == 0
        ),
        (
            "Fact_Flights: FK Weather - brak lotow bez kategorii pogody",
            """SELECT COUNT(*) FROM Fact_Flights f
               LEFT JOIN Dim_Weather w
               ON f.weather_category_id = w.category_id
               WHERE w.category_id IS NULL""",
            lambda x: x == 0
        ),
        (
            "Fact_Flights: is_delayed = 1 tylko gdy arr_delay > 15",
            """SELECT COUNT(*) FROM Fact_Flights
               WHERE is_delayed = 1 AND arr_delay <= 15""",
            lambda x: x == 0
        ),
        (
            "Fact_Flights: carrier_delay bez NULL",
            "SELECT COUNT(*) FROM Fact_Flights WHERE carrier_delay IS NULL",
            lambda x: x == 0
        ),
        (
            "Fact_Flights: pokrycie pogoda >= 99%",
            """SELECT CAST(COUNT(weather_category_id) AS FLOAT)
               / COUNT(*) * 100
               FROM Fact_Flights""",
            lambda x: x >= 99.0
        ),
        (
            "Fact_Flights: cancelled bez NULL",
            "SELECT COUNT(*) FROM Fact_Flights WHERE cancelled IS NULL",
            lambda x: x == 0
        ),
        (
            "Fact_Flights: cancellation_reason tylko dla anulowanych",
            """SELECT COUNT(*)
               FROM Fact_Flights
               WHERE cancellation_reason IS NOT NULL
                 AND cancelled = 0""",
            lambda x: x == 0
        ),
        (
            "Fact_Flights: diverted bez NULL",
            "SELECT COUNT(*) FROM Fact_Flights WHERE diverted IS NULL",
            lambda x: x == 0
        ),
        (
            "Fact_Flights: distance zawsze dodatnia",
            "SELECT COUNT(*) FROM Fact_Flights WHERE distance <= 0",
            lambda x: x == 0
        ),
        (
            "Fact_Flights: air_time dodatni gdy nie NULL",
            "SELECT COUNT(*) FROM Fact_Flights WHERE air_time <= 0",
            lambda x: x == 0
        ),
        (
            "Fact_Flights: zakres dat tylko Q3 2022 i Q3 2023",
            """SELECT COUNT(*) FROM Fact_Flights
               WHERE flight_date < '2022-07-01'
                  OR (flight_date > '2022-09-30'
                      AND flight_date < '2023-07-01')
                  OR flight_date > '2023-09-30'""",
            lambda x: x == 0
        ),
        # procent opoznionych
        (
            "Fact_Flights: procent opoznionych w przedziale 20-40% (benchmark DOT dla Q3)",
            """SELECT CAST(
                   100.0 * SUM(CASE WHEN is_delayed = 1 THEN 1 ELSE 0 END)
                   / NULLIF(COUNT(CASE WHEN is_delayed IS NOT NULL THEN 1 END), 0)
               AS DECIMAL(5, 2))
               FROM Fact_Flights""",
            lambda x: 20.0 <= x <= 40.0
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