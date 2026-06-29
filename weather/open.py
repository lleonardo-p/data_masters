import requests
import pandas as pd

url = "https://archive-api.open-meteo.com/v1/archive"

params = {
    "latitude": -22.0175,
    "longitude": -47.8908,
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "daily": "temperature_2m_max,temperature_2m_min,temperature_2m_mean,precipitation_sum,rain_sum,relative_humidity_2m_mean",
    "timezone": "America/Sao_Paulo"
}

response = requests.get(url, params=params, timeout=60)
response.raise_for_status()

data = response.json()

df = pd.DataFrame(data["daily"])

df.to_csv("clima_sao_carlos_2024_01.csv", index=False, encoding="utf-8-sig")

print(df.head())
print(f"Total de registros: {len(df)}")