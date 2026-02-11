import requests
from bs4 import BeautifulSoup
import sys

# Wrap output
sys.stdout.reconfigure(encoding='utf-8')

def inspect_dates(keyval):
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # Check Summary
    url_summary = f"https://planningaccess.york.gov.uk/online-applications/applicationDetails.do?activeTab=summary&keyVal={keyval}"
    print(f"Checking Summary: {url_summary}")
    r = requests.get(url_summary, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    
    # Text search
    text_content = soup.get_text()
    if "Decision Issued Date" in text_content:
        print("Phrase 'Decision Issued Date' found.")
        el = soup.find(string=lambda t: t and "Decision Issued Date" in t)
        if el:
            # Try finding the row
            row = el.find_parent('tr')
            if row:
                print(f"Date Row: {row.get_text(separator='|', strip=True)}")
    
    if "Agent" in text_content:
        print("Phrase 'Agent' found in Summary.")
        el = soup.find(string=lambda t: t and "Agent" in t)
        if el:
            row = el.find_parent('tr')
            if row:
                print(f"Agent Row: {row.get_text(separator='|', strip=True)}")
            else:
                 print(f"Agent Element parent: {el.parent}")
    else:
        print("Phrase 'Agent' NOT found in Summary.")
        
inspect_dates('T6ZSXXSJI5I00')
