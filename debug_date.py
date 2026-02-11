import requests
from bs4 import BeautifulSoup
import sys

# Wrap output
sys.stdout.reconfigure(encoding='utf-8')

def check_date_extraction(keyval):
    url = f"https://planningaccess.york.gov.uk/online-applications/applicationDetails.do?activeTab=summary&keyVal={keyval}"
    print(f"Fetching {url}")
    headers = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')

    # Method 1: Exact TH text match
    th = soup.find('th', string='Decision Issued Date')
    if th:
        print(f"Method 1: {th.find_next_sibling('td').get_text(strip=True)}")
    else:
        print("Method 1: Failed")

    # Method 2: Partial text match
    th2 = soup.find('th', string=lambda t: t and 'Decision Issued Date' in t)
    if th2:
        print(f"Method 2: {th2.text.strip()} -> {th2.find_next_sibling('td').get_text(strip=True)}")
    else:
        print("Method 2: Failed")
        
    # Method 3: Table row iteration
    print("\n--- Rows with Date ---")
    for tr in soup.find_all('tr'):
        text = tr.get_text(" ", strip=True)
        if "Decision Issued Date" in text:
            print(f"Row Content: {text}")

check_date_extraction('T6ZSXXSJI5I00')
