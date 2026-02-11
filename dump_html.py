import requests
from bs4 import BeautifulSoup
import sys

# Wrap output
sys.stdout.reconfigure(encoding='utf-8')

def dump_html(keyval):
    url = f"https://planningaccess.york.gov.uk/online-applications/applicationDetails.do?activeTab=summary&keyVal={keyval}"
    print(f"Fetching {url}")
    headers = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    
    # Find the simpleDetailsTable
    table = soup.find(id='simpleDetailsTable')
    if table:
        print(table.prettify())
    else:
        print("simpleDetailsTable not found. Dumping all tables...")
        for t in soup.find_all('table'):
            print(t.prettify())

dump_html('T6ZSXXSJI5I00')
