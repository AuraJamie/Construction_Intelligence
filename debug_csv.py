import pandas as pd
df = pd.read_csv('Planning_Applications.csv')
print("--- COLUMNS ---")
print(sorted(df.columns))

row = df.iloc[0]
print("--- SEARCHING ROW FOR REF ---")
for c in df.columns:
    val = str(row[c])
    if '/' in val and len(val) < 20: 
        print(f"FOUND POTENTIAL REF: {c} = {val}")
