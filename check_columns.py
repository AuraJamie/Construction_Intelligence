import pandas as pd

CSV_URL = "https://data-cyc.opendata.arcgis.com/datasets/7044d1920639460da3fc4a3fa9273107_5.csv"

try:
    df = pd.read_csv(CSV_URL, nrows=5)
    print("Columns found:")
    for col in df.columns:
        print(f" - {col}")
except Exception as e:
    print(f"Error: {e}")
