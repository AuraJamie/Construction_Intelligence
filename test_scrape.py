import requests
from bs4 import BeautifulSoup
import time

def scrape_address(keyval):
    url = f"https://planningaccess.york.gov.uk/online-applications/applicationDetails.do?activeTab=summary&keyVal={keyval}"
    print(f"Fetching: {url}")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"Failed with status: {response.status_code}")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Based on typical Idox systems (which York uses):
        # Look for the row with "Address"
        address_row = soup.find('th', string='Address')
        if address_row:
            address_cell = address_row.find_next_sibling('td')
            if address_cell:
                return address_cell.get_text(strip=True)
        
        # Fallback search if standard table scrape fails
        # Inspecting the HTML structure loosely
        summary_tab = soup.find(id='simpleDetailsTable')
        if summary_tab:
            for row in summary_tab.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) > 0:
                     print(f"Cell content sample: {cells[0].get_text(strip=True)[:20]}")

        return None

    except Exception as e:
        print(f"Error: {e}")
        return None

# Test with a likely keyval from the CSV snippet
# From snippet: ...,SSEKKLSJLSF00,... (This looks like a KEYVAL)
test_key = "SSEKKLSJLSF00" # From the previous `inspect_columns` output actually
print(f"Testing scrape for {test_key}")
addr = scrape_address(test_key)
print(f"\nResult: {addr}")
