import pandas as pd
import requests
from bs4 import BeautifulSoup

def inspect_keyval(keyval):
    url = f"https://planningaccess.york.gov.uk/online-applications/applicationDetails.do?activeTab=details&keyVal={keyval}"
    print(f"\n--- Checking {keyval} ---")
    print(f"URL: {url}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        r = requests.get(url, headers=headers)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Look for headers
        headers_found = [th.get_text(strip=True) for th in soup.find_all('th')]
        print(f"Headers found on Details tab: {headers_found}")
        
        if 'Address' in headers_found:
            print("Address found OK.")
        else:
            print("!!! Address NOT found !!!")

        if 'Agent Company Name' in headers_found:
             print("Agent found OK.")
        else:
             print("Agent NOT found (could be independent).")
             
    except Exception as e:
        print(e)
        
# Load CSV
df = pd.read_csv("Planning_Applications.csv")
# Pick top 5
sample_keys = df['KEYVAL'].head(5).tolist()

for k in sample_keys:
    inspect_keyval(k)
