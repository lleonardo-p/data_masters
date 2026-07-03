import time
import requests
import pandas as pd

url = "https://eonet.gsfc.nasa.gov/api/v3/events"

params = {
    "status": "all",
    "start": "2024-01-01",
    "end": "2024-12-31",
    "bbox": "-74.0,5.5,-34.0,-34.0",
    "limit": 100
}

for attempt in range(5):
    response = requests.get(url, params=params, timeout=60)

    if response.status_code == 200:
        data = response.json()
        events = data.get("events", [])

        df = pd.json_normalize(events)
        df.to_csv("nasa_events_brazil_2024.csv", index=False, encoding="utf-8-sig")

        print(df.head())
        print(f"Eventos encontrados: {len(df)}")
        break

    print(f"Tentativa {attempt + 1} falhou: {response.status_code}")
    time.sleep(10)
else:
    print("API indisponível após 5 tentativas.")