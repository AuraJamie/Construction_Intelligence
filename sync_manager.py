import requests
import sqlite3
import pandas as pd
from datetime import datetime
import json
import io
import sys
import live_search

sys.stdout.reconfigure(encoding='utf-8')

DB_NAME = "construction_intelligence.db"
# If API fails, we use the specific CSV URL which is reliable
CSV_URL = "https://data-cyc.opendata.arcgis.com/datasets/7044d1920639460da3fc4a3fa9273107_5.csv"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def sync_from_open_data():
    print(f"[{datetime.now()}] Starting Sync from York Open Data...")
    
    # Check last sync time
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Fetch Data (CSV for now as it's reliable)
    # Ideally we use API "where objectid > max_id" but CSV is fast enough for 5MB
    print("Downloading CSV via requests...")
    
    session = requests.Session()
    retries = requests.adapters.HTTPAdapter(max_retries=3)
    session.mount('https://', retries)

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = session.get(CSV_URL, headers=headers, timeout=60)
        response.raise_for_status()
        csv_content = response.content.decode('utf-8')
        df = pd.read_csv(io.StringIO(csv_content))
        print(f"Downloaded {len(df)} records.")
    except Exception as e:
        print(f"Download FAILED: {type(e).__name__}: {e}")
        # Re-raise to ensure workflow knows it failed
        raise e

    # 2. Process & Upsert
    # Fields: DATEAPRECV, DCSTAT, KEYVAL, OBJ, PROPOSAL, LATITUDE, LONGITUDE, REF, ADDRESS?
    # Inspect columns
    # print(df.columns)
    
    # Normalize
    records_added = 0
    records_updated = 0
    
    for index, row in df.iterrows():
        keyval = str(row.get('KEYVAL', '')).strip()
        if not keyval: continue
        
        # Prepare data
        ref = row.get('REFVAL', row.get('REF', row.get('REFERENCE', keyval))) # Use REFVAL (Human Readable)
        # Note: CSV might not have ADDRESS column explicitly?
        # Based on previous context, we scraped it. But check if CSV has it.
        # User CSV had 'OBJ' (Object ID).
        
        # We need to map CSV columns to DB columns
        status = row.get('DCSTAT', 'Unknown')
        proposal = row.get('PROPOSAL', '')
        lat = row.get('LATITUDE', 0)
        lon = row.get('LONGITUDE', 0)
        obj_id = row.get('OBJ', 0)
        
        # Date parsing
        date_recv = None
        date_valid = None
        
        # Validated Date
        try:
            d_val = row.get('DATEAPVAL')
            if pd.notna(d_val):
                date_valid = str(d_val)[:10] # ISO often: YYYY-MM-DD...
        except: pass

        # Received Date
        raw_date = str(row.get('DATEAPRECV', ''))
        try:
             if isinstance(row.get('DATEAPRECV'), (pd.Timestamp, datetime)):
                 date_recv = row.get('DATEAPRECV').date()
             else:
                 date_recv = str(raw_date)[:10]
        except: pass

        # Check existing
        cursor.execute("SELECT status, needs_scrape FROM applications WHERE keyval = ?", (keyval,))
        existing = cursor.fetchone()
        
        if existing:
            # Calculate scrape flag
            new_scrape_val = existing['needs_scrape']
            if existing['status'] != status:
                new_scrape_val = 1
                # AUDIT LOGGING (Phase 3)
                try:
                    cursor.execute("INSERT INTO status_history (keyval, old_status, new_status, change_date) VALUES (?, ?, ?, ?)", 
                                  (keyval, existing['status'], status, datetime.now()))
                    # print(f"Logged status change for {keyval}: {existing['status']} -> {status}")
                except Exception as e:
                    print(f"Audit log failed: {e}")
            
            # Update (Always update Reference to fix missing values from previous bug)
            cursor.execute("""
                UPDATE applications SET 
                status = ?, 
                reference = ?,
                validated_date = ?,
                last_synced_api = ?,
                needs_scrape = ?
                WHERE keyval = ?
             """, (status, ref, date_valid, datetime.now(), new_scrape_val, keyval))
            records_updated += 1
        else:
            # Insert New
            cursor.execute("""
                INSERT INTO applications (
                    keyval, reference, proposal, status, 
                    received_date, validated_date, latitude, longitude, 
                    source_object_id, last_synced_api, needs_scrape
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (keyval, ref, proposal, status, date_recv, date_valid, lat, lon, obj_id, datetime.now()))
            records_added += 1
            
    conn.commit()
    conn.close()
    print(f"Sync Complete. Added: {records_added}, Updated: {records_updated}")

    # 3. Live Sync (Recent Decisions)
    try:
        print("Starting Live Sync for Recent Decisions...")
        recent = live_search.search_recent_decisions(days=7)
        if not recent:
            print("No recent decisions found.")
        else:
            conn = get_db_connection()
            l_cursor = conn.cursor()
            l_updates = 0
            
            for item in recent:
                kv = item['keyval']
                st = item['status']
                dd_str = item['decision_date'] # e.g. 10/02/2026
                
                # Convert Date Format -> YYYY-MM-DD
                dd_db = None
                try:
                    dt = datetime.strptime(dd_str, '%d/%m/%Y')
                    dd_db = dt.strftime('%Y-%m-%d')
                except:
                    # Try other formats?
                    pass
                
                if dd_db:
                    l_cursor.execute("UPDATE applications SET status = ?, decision_date = ? WHERE keyval = ?", (st, dd_db, kv))
                    if l_cursor.rowcount > 0:
                        l_updates += 1
                        
            conn.commit()
            conn.close()
            print(f"Live Sync Updated {l_updates} records with decision dates.")
            
    except Exception as e:
        print(f"Live sync error: {e}")

    # 4. Targeted Backfill for Missing Decision Dates
    # 4. robust Scraping (Address, Agent, Decision Date)
    # Target applications that need scraping (new or updated status)
    conn = get_db_connection()
    c = conn.cursor()
    
    # Priority: Newest applications first (received_date DESC)
    # Limit to 50 per run to avoid timeout/blocking (run every 6 hours = 200/day)
    rows = c.execute("""
        SELECT keyval, reference, status FROM applications 
        WHERE needs_scrape = 1 
        ORDER BY received_date DESC 
        LIMIT 500
    """).fetchall()
    
    if rows:
        print(f"Found {len(rows)} applications needing details. Scraping (max 50)...")
        import scraper
        import time
        count = 0
        
        for r in rows:
            kv = r['keyval']
            # ref = r['reference'] 
            print(f"Scraping details for {kv}...")
            
            try:
                # Scrape
                details = scraper.scrape_application_details(kv)
                
                if details['success']:
                     # Prepare Updates
                     updates = []
                     start_params = []
                     
                     # Address
                     if details['address']:
                         updates.append("address = ?")
                         start_params.append(details['address'])
                         
                     # Agent
                     if details['agent']:
                         updates.append("agent_name = ?")
                         start_params.append(details['agent'])
                         
                     # Decision Date
                     # Convert dd/mm/yy -> YYYY-MM-DD
                     db_date = None
                     if details['decision_date']:
                         try:
                             dt = datetime.strptime(details['decision_date'], '%d/%m/%y')
                             db_date = dt.strftime('%Y-%m-%d')
                             updates.append("decision_date = ?")
                             start_params.append(db_date)
                         except: pass

                     # Portal Keyval (Self-healing)
                     if details['portal_keyval']:
                         updates.append("portal_keyval = ?")
                         start_params.append(details['portal_keyval'])

                     # Always update meta
                     updates.append("last_scraped_details = ?")
                     start_params.append(datetime.now())
                     
                     updates.append("needs_scrape = 0")
                     
                     # Validation Warning (Phase 3 Idea - optional)
                     # if details['scraped_status'] != ...
                     
                     sql = f"UPDATE applications SET {', '.join(updates)} WHERE keyval = ?"
                     start_params.append(kv)
                     
                     c.execute(sql, start_params)
                     count += 1
                     print(f"Updated {kv}: Addr={bool(details['address'])}, Agent={bool(details['agent'])}")
                     
                else:
                    print(f"Scrape failed for {kv}: {details.get('error')}")
                    # Maybe increment a retry counter? For now, leave needs_scrape=1 to retry next time
                    # Or set to 0 if we want to give up? Let's leave it 1 but maybe add 'failed_attempts' column later.
                    
            except Exception as e:
                print(f"Scrape loop error {kv}: {e}")
                
            # Polite Delay
            time.sleep(1)
                
        conn.commit()
        print(f"Scraped and updated {count} applications.")
    
    conn.close()

if __name__ == "__main__":
    sync_from_open_data()
