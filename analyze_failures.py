import sqlite3
import pandas as pd

conn = sqlite3.connect('construction_intelligence.db')
cursor = conn.cursor()

# Get stats of records that failed scraping (address unavailable)
print("--- Statuses of Failed Scrapes ---")
rows = cursor.execute("""
    SELECT status, count(*), min(reference) 
    FROM applications 
    WHERE address = 'Address not available' OR address IS NULL 
    GROUP BY status 
    ORDER BY count(*) DESC
""").fetchall()

for r in rows:
    print(f"Status: {r[0]} | Count: {r[1]} | Sample: {r[2]}")

print("\n--- Statuses of Successful Scrapes ---")
rows_ok = cursor.execute("""
    SELECT status, count(*) 
    FROM applications 
    WHERE address != 'Address not available' AND address IS NOT NULL 
    GROUP BY status
""").fetchall()
for r in rows_ok:
    print(f"Status: {r[0]} | Count: {r[1]}")
    
conn.close()
