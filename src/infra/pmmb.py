import requests
import pandas as pd

url = "https://apidadosabertos.saude.gov.br/atencao-primaria/pmmb-profissionais-ativos"

params = {
    "limit": 100,
    "offset": 0
}

response = requests.get(url, params=params)
response.raise_for_status()

df = pd.DataFrame(response.json())

df.to_csv("pmmb_profissionais_ativos.csv", index=False, encoding="utf-8-sig")

print(df.head())
print(f"Total de registros: {len(df)}")