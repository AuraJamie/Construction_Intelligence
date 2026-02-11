import requests
from bs4 import BeautifulSoup
import sys

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
    'Referer': 'https://planningaccess.york.gov.uk/online-applications/search.do?action=advanced'
}

def debug_scrape(keyval):
    print(f"DEBUG: Scraping {keyval}")
    session = requests.Session()
    url = f"https://planningaccess.york.gov.uk/online-applications/applicationDetails.do?activeTab=summary&keyVal={keyval}"
    
    try:
        res = session.get(url, headers=HEADERS, timeout=15)
        print(f"Status Code: {res.status_code}")
        
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Look for any row with "Decision" in it
        rows = soup.find_all('tr')
        print(f"Found {len(rows)} rows in summary.")
        
        found_decision = False
        for row in rows:
            text = row.get_text(strip=True)
            if "Decision" in text:
                print(f"Row Match: {text}")
                found_decision = True
                
        if not found_decision:
            print("No rows containing 'Decision' found.")
            
        # Check current scraper logic
        date_node = soup.find(string=lambda t: t and "Decision Issued Date" in t)
        if date_node:
            print(f"Current Logic Found Node: '{date_node}'")
            row = date_node.find_parent('tr')
            if row:
                td = row.find('td')
                if td:
                    print(f"Current Logic Extracted: '{td.get_text(strip=True)}'")
                else:
                    print("Current Logic: No TD found in row")
            else:
                print("Current Logic: No Parent TR found")
        else:
            print("Current Logic: 'Decision Issued Date' string NOT found.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_scrape("T7B58TSJI8O00")
