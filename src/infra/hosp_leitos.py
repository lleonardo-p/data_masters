import requests
import pandas as pd

url = "https://apidadosabertos.saude.gov.br/assistencia-a-saude/hospitais-e-leitos"

params = {
    "limit": 5,
    "offset": 0
}

response = requests.get(url, params=params)
response.raise_for_status()

df = pd.DataFrame(response.json())

df.to_csv("hospitais_e_leitos.csv", index=False, encoding="utf-8-sig")

print(df.head())
print(f"Total de registros: {len(df)}")