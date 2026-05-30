import pandas as pd

AIRPORTS = r"C:\Users\admin\Desktop\project_bi\data\raw\airports\airports_us_matched.csv"
WEATHER  = r"C:\Users\admin\Desktop\project_bi\data\raw\weather\weather_raw.csv"

# ============================================================
# OurAirports
# ============================================================
df_ap = pd.read_csv(AIRPORTS)

print("=" * 60)
print("OurAirports — airports_us_matched.csv")
print("=" * 60)
print(f"Wiersze:  {len(df_ap):,}")
print(f"Kolumny:  {df_ap.shape[1]}")
print(f"\nKolumny i typy:\n{df_ap.dtypes}")
print(f"\nPuste wartości:")
print(df_ap.isnull().sum()[df_ap.isnull().sum() > 0])
print(f"\nTypy lotnisk:\n{df_ap['type'].value_counts()}")
print(f"\nUnikalne strefy czasowe:\n{df_ap['timezone'].value_counts()}")

# ============================================================
# Open-Meteo
# ============================================================
df_w = pd.read_csv(WEATHER)

print("\n" + "=" * 60)
print("Open-Meteo — weather_raw.csv")
print("=" * 60)
print(f"Wiersze:  {len(df_w):,}")
print(f"Kolumny:  {df_w.shape[1]}")
print(f"\nKolumny i typy:\n{df_w.dtypes}")
print(f"\nPuste wartości:")
nulls = df_w.isnull().sum()
print(nulls[nulls > 0] if nulls[nulls > 0].any() else "Brak pustych wartości")
print(f"\nPrzykładowe wiersze:\n{df_w.head(5).to_string()}")
print(f"\nStatystyki:\n{df_w[['temperature_2m','precipitation','windspeed_10m','weathercode']].describe()}")
print(f"\nUnikalne kody WMO: {sorted(df_w['weathercode'].dropna().unique().astype(int).tolist())}")
print(f"\nZakres dat: {df_w['date'].min()} → {df_w['date'].max()}")
print(f"Unikalnych lotnisk w pogodzie: {df_w['airport_iata'].nunique()}")