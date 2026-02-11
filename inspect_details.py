import requests
from bs4 import BeautifulSoup

def inspect_details_headers(keyval):
    url = f"https://planningaccess.york.gov.uk/online-applications/applicationDetails.do?activeTab=details&keyVal={keyval}"
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(r.text, 'html.parser')
    
    headers = [th.get_text(strip=True) for th in soup.find_all('th')]
    print(f"Details Tab Headers for {keyval}:")
    for h in headers:
        print(f" - '{h}'")

inspect_details_headers('SSEKKLSJLSF00')
