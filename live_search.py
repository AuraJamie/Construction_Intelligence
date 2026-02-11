import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import random
import time

# Headers for requests (Matched to scraper.py to look consistent)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
    'Referer': 'https://planningaccess.york.gov.uk/online-applications/search.do?action=advanced'
}

def search_recent_decisions(days=7):
    """
    Searches for applications decided in the last N days.
    """
    print(f"Searching for decisions in the last {days} days...")
    
    session = requests.Session()
    
    # Calculate Date Range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    start_str = start_date.strftime('%d/%m/%Y')
    end_str = end_date.strftime('%d/%m/%Y')
    
    # Simple Search URL - Often easier than Advanced for "Received" or "Decided"
    # But Advanced Search is better for date ranges.
    
    # 1. Get Session Cookie from Search Page First
    try:
        session.get("https://planningaccess.york.gov.uk/online-applications/search.do?action=advanced", headers=HEADERS)
    except Exception as e:
        print(f"Failed to init session: {e}")

    # URL for Advanced Search (POST)
    search_url = "https://planningaccess.york.gov.uk/online-applications/advancedSearchResults.do?action=firstPage"
    
    # Form Data for "Decided Between X and Y"
    payload = {
        'searchType': 'Application',
        'caseType': '',
        'decisionType': '',
        'date(applicationDecisionStart)': start_str,
        'date(applicationDecisionEnd)': end_str,
        'caseStatus': '' 
    }
    
    try:
        res = session.post(search_url, data=payload, headers=HEADERS, timeout=30)
        
        # DEBUG: unexpected redirect or error?
        if "matching results found" not in res.text and "Results" not in res.text and "searchresult" not in res.text:
             # Maybe monthly or weekly list is safer?
             print("Advanced search returned no obvious results list. Trying Weekly List method...")
             return search_weekly_list(session)
             
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Check for results list
        results = []
        items = soup.find_all('li', class_='searchresult')
        
        print(f"Found {len(items)} items on first page.")
        
        for item in items:
            link_tag = item.find('a', href=lambda h: h and 'keyVal=' in h)
            if not link_tag: continue
            
            href = link_tag['href']
            keyval = href.split('keyVal=')[1].split('&')[0]
            reference = link_tag.get_text(strip=True)
            
            addr_tag = item.find('p', class_='address')
            address = addr_tag.get_text(strip=True) if addr_tag else "Unknown Address"
            
            meta_tag = item.find('p', class_='metaInfo')
            meta_text = meta_tag.get_text(strip=True) if meta_tag else ""
            
            status = "Unknown"
            if "Status:" in meta_text:
                status = meta_text.split("Status:")[1].strip()
                
            results.append({
                'keyval': keyval,
                'reference': reference,
                'address': address,
                'status': status,
                'decision_date': end_str 
            })
            
        return results

    except Exception as e:
        print(f"Search failed: {e}")
        return []

def search_weekly_list(session):
    """
    Fallback: Scrape the 'Weakly List' for Decided applications.
    This is often more robust than advanced search form submission.
    """
    print("Searching Weekly List (Decided)...")
    url = "https://planningaccess.york.gov.uk/online-applications/weeklyListSearchResults.do?action=firstPage"
    
    # We want "Decided" applications for "This Week"
    # Usually requires parsing the "Weekly List" form first to get dates?
    # Let's try simple GET parameters if possible, otherwise POST.
    
    # Only reliable way is usually simulating the form post.
    # dateType: DC_Decided
    
    payload = {
        'searchType': 'Application',
        'dateType': 'DC_Decided', # Decided Applications
        'week': '0', # Current Week? Or explicit usage?
        # Typically the form sends 'week' as "10 Feb 2026" etc.
    }
    
    # Let's actually use the Monthly List as it covers more ground? Or just stick to Weekly.
    # Let's try to get the Weekly List page to find valid 'week' values.
    
    try:
         res_form = session.get("https://planningaccess.york.gov.uk/online-applications/search.do?action=weeklyList", headers=HEADERS)
         soup_form = BeautifulSoup(res_form.text, 'html.parser')
         
         # Find the Week Selector
         # <select name="week" id="week"> ... </select>
         select = soup_form.find('select', id='week')
         if not select:
             print("Could not find week selector.")
             return []
             
         options = select.find_all('option')
         if not options: return []
         
         # Take the first option (Current Week)
         latest_week = options[0]['value']
         print(f"Scraping Weekly List for week: {latest_week}")
         
         payload['week'] = latest_week
         
         res = session.post(url, data=payload, headers=HEADERS)
         soup = BeautifulSoup(res.text, 'html.parser')
         
         items = soup.find_all('li', class_='searchresult')
         results = []
         for item in items:
            link_tag = item.find('a', href=lambda h: h and 'keyVal=' in h)
            if not link_tag: continue
            
            href = link_tag['href']
            keyval = href.split('keyVal=')[1].split('&')[0]
            reference = link_tag.get_text(strip=True)
            
            addr_tag = item.find('p', class_='address')
            address = addr_tag.get_text(strip=True) if addr_tag else "Unknown Address"
            
            results.append({
                'keyval': keyval,
                'reference': reference,
                'address': address,
                'status': 'Decided', # Implicit
                'decision_date': 'This Week'
            })
            
         return results
         
    except Exception as e:
        print(f"Weekly search failed: {e}")
        return []

if __name__ == "__main__":
    results = search_recent_decisions(days=7)
    print(f"Found {len(results)} recent decisions.")
    for r in results:
        print(r)
