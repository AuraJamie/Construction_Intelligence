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
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(CSV_URL, headers=headers, timeout=30)
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
    # If status suggests a decision but date is missing, force a scrape.
    conn = get_db_connection()
    c = conn.cursor()
    # Common decision statuses: HAPP, PER, REF, APP, CDN, NOBJ
    rows = c.execute("""
        SELECT keyval, reference FROM applications 
        WHERE status IN ('HAPP', 'PER', 'REF', 'APP', 'CDN', 'NOBJ', 'SPL', 'WDN') 
        AND decision_date IS NULL
        LIMIT 50
    """).fetchall()
    
    if rows:
        print(f"Found {len(rows)} decided applications with missing decision dates. Scraping details...")
        import scraper
        count = 0
        for r in rows:
            kv = r['keyval']
            # ref = r['reference'] # Pass ref for self-healing if needed
            print(f"Backfilling date for {kv}...")
            try:
                # Scrape
                details = scraper.scrape_application_details(kv)
                if details['success'] and details['decision_date']:
                     # Update DB
                     # details['decision_date'] is dd/mm/yy (e.g. 10/02/26)
                     # Convert to YYYY-MM-DD
                     d_str = details['decision_date']
                     try:
                         dt = datetime.strptime(d_str, '%d/%m/%y')
                         db_date = dt.strftime('%Y-%m-%d')
                         c.execute("UPDATE applications SET decision_date = ? WHERE keyval = ?", (db_date, kv))
                         count += 1
                     except: 
                        print(f"Date parse error for {d_str}")
                else:
                    print(f"Scrape failed/no date for {kv}")
            except Exception as e:
                print(f"Backfill error {kv}: {e}")
                
        conn.commit()
        print(f"Backfilled {count} decision dates.")
    
    conn.close()

if __name__ == "__main__":
    sync_from_open_data()
