# download_data.py
import requests
import os

DATA_URL = "https://raw.githubusercontent.com/jldbc/coffee-quality-database/main/data/arabica_data_cleaned.csv"
SAVE_PATH = "data/arabica_data_cleaned.csv"

print(f"Downloading data from {DATA_URL}...")
os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)

try:
    response = requests.get(DATA_URL, stream=True)
    response.raise_for_status()  # Raise an exception for bad status codes

    with open(SAVE_PATH, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Data saved successfully to {SAVE_PATH}")

except requests.exceptions.RequestException as e:
    print(f"Error downloading data: {e}")
except IOError as e:
    print(f"Error saving data: {e}")

# Run this script: python download_data.py