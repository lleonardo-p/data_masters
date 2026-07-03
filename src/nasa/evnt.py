import requests
import pandas as pd

url = "https://eonet.gsfc.nasa.gov/api/v3/events"

params = {
    "status": "all",
    "days": 30,
    "bbox": "-74.0,5.5,-34.0,-34.0",
    "limit": 100
}

response = requests.get(url, params=params)
response.raise_for_status()

events = response.json()["events"]

df = pd.json_normalize(events)

df.to_csv("nasa_events_brazil.csv", index=False, encoding="utf-8-sig")

print(df.head())
print(f"Eventos encontrados: {len(df)}")