import requests
import pandas as pd

url = "https://apidadosabertos.saude.gov.br/arboviroses/chikungunya"

params = {
    "nu_ano": 2017,
    "limit": 10,
    "offset": 0
}

response = requests.get(url, params=params)
response.raise_for_status()

df = pd.DataFrame(response.json())

df.to_csv("chikungunya_2017.csv", index=False, encoding="utf-8-sig")

print(df.head())
print(f"Total de registros: {len(df)}")