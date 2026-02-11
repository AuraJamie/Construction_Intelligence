import requests
from bs4 import BeautifulSoup

def check_summary_for_agent(keyval):
    url = f"https://planningaccess.york.gov.uk/online-applications/applicationDetails.do?activeTab=summary&keyVal={keyval}"
    print(f"Checking Summary Tab: {url}")
    
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(r.text, 'html.parser')
    
    headers = [th.get_text(strip=True) for th in soup.find_all('th')]
    print(f"Headers: {headers}")
    
    if 'Agent Company Name' in headers:
        print("Agent IS in Summary.")
    else:
        print("Agent is NOT in Summary.")

check_summary_for_agent('SSEKKLSJLSF00')
