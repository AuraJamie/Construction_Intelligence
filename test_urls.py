import requests
from bs4 import BeautifulSoup

# Sample from CSV
REF = "25/00417/CLU"
KEYVAL_CSV = "SSEKKLSJLSF00" 

# Headers (Mimic Browser)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def test_keyval():
    url = f"https://planningaccess.york.gov.uk/online-applications/applicationDetails.do?activeTab=summary&keyVal={KEYVAL_CSV}"
    print(f"Testing KeyVal Link: {url}")
    r = requests.get(url, headers=HEADERS)
    if "Details not available" in r.text or "Comparison" in r.text: # Comparison is the error page title often
        print("-> FAILED (Details not available)")
    elif REF in r.text:
        print("-> SUCCESS (Found Reference on page)")
    else:
        print(f"-> UNCERTAIN. Title: {BeautifulSoup(r.text, 'html.parser').title.string.strip()}")

def test_search():
    # Attempt to search by reference and get the redirect or result
    url = f"https://planningaccess.york.gov.uk/online-applications/simpleSearchResults.do?action=firstPage&searchType=Application&searchCriteria.reference={REF}"
    print(f"Testing Search Link: {url}")
    s = requests.Session()
    r = s.get(url, headers=HEADERS)
    
    soup = BeautifulSoup(r.text, 'html.parser')
    # If it lists results, we look for a link to details
    results = soup.find_all('a', href=True)
    found_link = None
    for a in results:
        if 'applicationDetails.do?activeTab=summary&keyVal=' in a['href']:
            found_link = a['href']
            break
            
    if found_link:
        print(f"-> Found Result Link: {found_link}")
        # Extract real keyval
        real_kv = found_link.split('keyVal=')[1]
        print(f"-> Real KeyVal seems to be: {real_kv}")
        if real_kv == KEYVAL_CSV:
            print("-> MATCHES CSV!")
        else:
            print("-> MISMATCH with CSV!")
    else:
        print("-> No results found or direct redirect?")
        if "Property/Application Details" in r.text or REF in r.text:
             print("-> Redirected directly to details?")

if __name__ == "__main__":
    test_keyval()
    print("-" * 20)
    test_search()
