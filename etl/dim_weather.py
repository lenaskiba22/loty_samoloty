# etl/dim_weather.py
import pandas as pd
from etl.utils import get_connection, truncate_and_load
import glob

def load_dim_weather(files: list[str] | None = None):
    print("=== Dim_Weather ===")


    weather_categories = pd.DataFrame([
        {
            'category_id': 1,
            'wmo_code_from': 0,
            'wmo_code_to': 3,
            'wmo_description': 'Clear sky / Mainly clear, partly cloudy, and overcast',
            'weather_category': 'Clear',
            'is_adverse': 0
        },
        {
            'category_id': 2,
            'wmo_code_from': 45,
            'wmo_code_to': 48,
            'wmo_description': 'Fog and depositing rime fog',
            'weather_category': 'Fog',
            'is_adverse': 0
        },
        {
            'category_id': 3,
            'wmo_code_from': 51,
            'wmo_code_to': 55,
            'wmo_description': 'Drizzle: Light, moderate, and dense intensity',
            'weather_category': 'Rain',
            'is_adverse': 1
        },
        {
            'category_id': 4,
            'wmo_code_from': 56,
            'wmo_code_to': 57,
            'wmo_description': 'Freezing Drizzle: Light and dense intensity',
            'weather_category': 'Freezing Rain',
            'is_adverse': 1
        },
        {
            'category_id': 5,
            'wmo_code_from': 61,
            'wmo_code_to': 65,
            'wmo_description': 'Rain: Slight, moderate and heavy intensity',
            'weather_category': 'Rain',
            'is_adverse': 1
        },
        {
            'category_id': 6,
            'wmo_code_from': 66,
            'wmo_code_to': 67,
            'wmo_description': 'Freezing Rain: Light and heavy intensity',
            'weather_category': 'Freezing Rain',
            'is_adverse': 1
        },
        {
            'category_id': 7,
            'wmo_code_from': 71,
            'wmo_code_to': 75,
            'wmo_description': 'Snow fall: Slight, moderate, and heavy intensity',
            'weather_category': 'Snow',
            'is_adverse': 1
        },
        {
            'category_id': 8,
            'wmo_code_from': 77,
            'wmo_code_to': 77,
            'wmo_description': 'Snow grains',
            'weather_category': 'Snow',
            'is_adverse': 1
        },
        {
            'category_id': 9,
            'wmo_code_from': 80,
            'wmo_code_to': 82,
            'wmo_description': 'Rain showers: Slight, moderate, and violent',
            'weather_category': 'Rain',
            'is_adverse': 1
        },
        {
            'category_id': 10,
            'wmo_code_from': 85,
            'wmo_code_to': 86,
            'wmo_description': 'Snow showers slight and heavy',
            'weather_category': 'Snow',
            'is_adverse': 1
        },
        {
            'category_id': 11,
            'wmo_code_from': 95,
            'wmo_code_to': 95,
            'wmo_description': 'Thunderstorm: Slight or moderate',
            'weather_category': 'Storm',
            'is_adverse': 1
        },
        {
            'category_id': 12,
            'wmo_code_from': 96,
            'wmo_code_to': 99,
            'wmo_description': 'Thunderstorm with slight and heavy hail',
            'weather_category': 'Storm',
            'is_adverse': 1
        },
    ])
    conn = get_connection()
    truncate_and_load(weather_categories, "Dim_Weather", conn)
    conn.close()

if __name__ == "__main__":
    load_dim_weather()