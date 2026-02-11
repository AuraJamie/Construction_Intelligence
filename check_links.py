import requests
import sqlite3
from bs4 import BeautifulSoup
import concurrent.futures

HEADERS = {
    'User-Agent': 'Mozilla/5.0'
}

def check_link(row):
    keyval = row['keyval']
    ref = row['reference']
    
    # Method 1: KeyVal Direct
    url = f"https://planningaccess.york.gov.uk/online-applications/applicationDetails.do?activeTab=summary&keyVal={keyval}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if "Details not available" in r.text or "Comparison" in r.text: # "Comparison" appears in title of error page usually?
            # Check purely if reference is found on page
            if ref and ref in r.text:
                 return (keyval, True, "OK")
            return (keyval, False, "Details Missing")
        return (keyval, True, "OK")
    except:
        return (keyval, False, "Error")

conn = sqlite3.connect('construction_intelligence.db')
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT keyval, reference FROM applications ORDER BY RANDOM() LIMIT 5").fetchall()
conn.close()

print(f"Checking {len(rows)} random records...")
for row in rows:
    kv, success, msg = check_link(row)
    print(f"Ref: {row['reference']} | KeyVal: {kv} -> {success} ({msg})")
