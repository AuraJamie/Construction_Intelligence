import sqlite3

DB_NAME = "construction_intelligence.db"

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()
rows = cursor.execute("SELECT received_date, validated_date, decision_date FROM applications LIMIT 10").fetchall()
conn.close()

print("Raw date output from DB:")
for r in rows:
    print(r)
