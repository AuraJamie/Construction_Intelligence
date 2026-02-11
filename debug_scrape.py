import requests
from bs4 import BeautifulSoup
import sys

def debug_scrape(keyval):
    # Wrap output
    original_stdout = sys.stdout
    with open("table_dump.txt", "w", encoding="utf-8") as f:
        sys.stdout = f
        
        url = f"https://planningaccess.york.gov.uk/online-applications/applicationDetails.do?activeTab=summary&keyVal={keyval}"
        print(f"Fetching: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f"Status: {response.status_code}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Dump all table data to see structure
            print("\n--- Table Dump ---")
            tables = soup.find_all('table')
            for i, table in enumerate(tables):
                print(f"Table {i}:")
                for row in table.find_all('tr'):
                    print([cell.get_text(strip=True) for cell in row.find_all(['th', 'td'])])
                    
        except Exception as e:
            print(f"Error: {e}")
        finally:
             sys.stdout = original_stdout

test_key = "SSEKKLSJLSF00"
debug_scrape(test_key)
