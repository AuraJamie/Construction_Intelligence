import requests
from bs4 import BeautifulSoup
import sys

def check_details(keyval):
    # Try the 'details' tab
    url = f"https://planningaccess.york.gov.uk/online-applications/applicationDetails.do?activeTab=details&keyVal={keyval}"
    print(f"Fetching: {url}")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        print("\n--- Searching for 'Agent Company Name' ---")
        # Search for th with text 'Agent Company Name'
        agent_row = soup.find('th', string=lambda text: text and 'Agent Company Name' in text)
        if agent_row:
            print("Found Agent Row!")
            print(f"Value: {agent_row.find_next_sibling('td').get_text(strip=True)}")
        else:
            print("Agent Company Name NOT found.")

        print("\n--- Searching for 'Address' on this tab ---")
        address_row = soup.find('th', string=lambda text: text and 'Address' in text)
        if address_row:
             print(f"Address: {address_row.find_next_sibling('td').get_text(strip=True)}")
        else:
             print("Address NOT found on this tab.")
             
        # Dump tables just in case
        # print("\n--- Table Dump ---")
        # for table in soup.find_all('table'):
        #     for row in table.find_all('tr'):
        #         print([cell.get_text(strip=True) for cell in row.find_all(['th', 'td'])])

    except Exception as e:
        print(f"Error: {e}")

# Use the user's example keyval
test_key = "T6DTARSJHZK00"
check_details(test_key)
