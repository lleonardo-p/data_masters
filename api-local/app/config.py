import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://dengue_api:change-me@db:5432/dengue",
)

API_KEY = os.getenv("API_KEY", "")
FETCH_SIZE = int(os.getenv("FETCH_SIZE", "2000"))