import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# Headers for requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
    'Referer': 'https://planningaccess.york.gov.uk/online-applications/search.do?action=advanced'
}

def scrape_application_details(keyval, reference=None):
    """
    Scrapes the 'activeTab=details' and 'activeTab=summary' pages for a given keyval.
    Includes self-healing logic to find the correct keyval if the initial one is invalid,
    using an optional 'reference' number.
    Returns a dictionary with:
      - address (str)
      - agent (str or None)
      - decision_date (str 'dd/mm/yy' or None)
      - success (bool)
      - portal_keyval (str or None) - The keyval actually used for scraping, if different from input.
    """
    if not keyval:
        return {'success': False, 'error': 'No KeyVal'}
        
    details = {'address': None, 'agent': None, 'decision_date': None, 'success': False, 'portal_keyval': None}
    
    session = requests.Session()
    active_kv = keyval
    
    try:
        # --- Step 0: Validate / Soft-Check KeyVal using Summary Tab ---
        # We start with summary because it's the main landing page
        url_summary = f"https://planningaccess.york.gov.uk/online-applications/applicationDetails.do?activeTab=summary&keyVal={keyval}"
        res_summary = session.get(url_summary, headers=HEADERS, timeout=15)
        
        # Self-Healing: Check if KeyVal is valid
        if "Details not available" in res_summary.text or "Comparison" in res_summary.text:
            if reference:
                print(f"[Heal] KeyVal {keyval} failed. Searching for ref {reference}...")
                search_url = f"https://planningaccess.york.gov.uk/online-applications/simpleSearchResults.do?action=firstPage&searchType=Application&searchCriteria.reference={reference}"
                res_search = session.get(search_url, headers=HEADERS, timeout=15)
                
                # Extract correct link
                soup_search = BeautifulSoup(res_search.text, 'html.parser')
                link = soup_search.find('a', href=lambda h: h and 'keyVal=' in h)
                
                if link:
                    try:
                        # href example: ...&keyVal=ABC...
                        new_kv = link['href'].split('keyVal=')[1].split('&')[0]
                        print(f"[Heal] Found replacement KeyVal: {new_kv}")
                        details['portal_keyval'] = new_kv
                        active_kv = new_kv
                        # Re-fetch summary with new KV
                        url_summary = f"https://planningaccess.york.gov.uk/online-applications/applicationDetails.do?activeTab=summary&keyVal={active_kv}"
                        res_summary = session.get(url_summary, headers=HEADERS, timeout=15)
                    except Exception as ex:
                        print(f"Failed to parse new keyval: {ex}")

        # --- Step 1: Parse Summary (Date & Address Fallback) ---
        soup_sum = BeautifulSoup(res_summary.text, 'html.parser')
        
        # Date
        date_node = soup_sum.find(string=lambda t: t and "Decision Issued Date" in t)
        if date_node:
            row = date_node.find_parent('tr')
            if row:
                td = row.find('td')
                if td:
                    raw_date = td.get_text(strip=True)
                    try:
                         # Format: Wed 04 Feb 2026 -> %a %d %b %Y
                        dt = datetime.strptime(raw_date, '%a %d %b %Y')
                        details['decision_date'] = dt.strftime('%d/%m/%y')
                    except: details['decision_date'] = raw_date
        
        # Status (Phase 3: Cross Validation)
        status_node = soup_sum.find('th', string=lambda t: t and 'Status' in t)
        if status_node:
             td = status_node.find_next_sibling('td')
             if td: details['scraped_status'] = td.get_text(strip=True)

        # Address (Fallback if not found in Details, but we parse here too)
        # Often in Summary tab, address is in a table too.
        if not details['address']:
             addr_th = soup_sum.find('th', string=lambda t: t and 'Address' in t)
             if addr_th:
                 td = addr_th.find_next_sibling('td')
                 if td: details['address'] = td.get_text(strip=True)

        # --- Step 2: Parse Details Tab (Agent & Primary Address) ---
        url_details = f"https://planningaccess.york.gov.uk/online-applications/applicationDetails.do?activeTab=details&keyVal={active_kv}"
        res_details = session.get(url_details, headers=HEADERS, timeout=15)
        soup_det = BeautifulSoup(res_details.text, 'html.parser')
        
        # Agent
        agent_th = soup_det.find('th', string=lambda t: t and 'Agent Company Name' in t)
        if agent_th:
            td = agent_th.find_next_sibling('td')
            if td: details['agent'] = td.get_text(strip=True)
            
        # Address (Primary check)
        if not details['address']:
            addr_th = soup_det.find('th', string=lambda t: t and 'Address' in t)
            if addr_th:
                td = addr_th.find_next_sibling('td')
                if td: details['address'] = td.get_text(strip=True)
        
        details['success'] = True
        
    except Exception as e:
        print(f"Scrape error {keyval}: {e}")
        details['error'] = str(e)
    
    if not details['agent']:
        details['agent'] = 'Independent'

    if not details['address']:
         details['address'] = "Address not available"
         
    return details
