import json
import sqlite3
import os
from datetime import datetime

DB_NAME = "construction_intelligence.db"
JSON_FILE = "addresses.json"

def migrate():
    if not os.path.exists(JSON_FILE):
        print(f"No {JSON_FILE} found. Skipping migration.")
        return

    print("Loading JSON cache...")
    try:
        with open(JSON_FILE, 'r') as f:
            data = json.load(f)
    except:
        print("Failed to read JSON.")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    updated_count = 0
    scraped_count = 0 
    
    for keyval, val in data.items():
        # Clean Keyval
        keyval = keyval.strip()
        if not keyval: continue
        
        # Determine values
        address = None
        agent = None
        decision_date = None
        
        if isinstance(val, dict):
            address = val.get('address')
            agent = val.get('agent')
            decision_date = val.get('decision_date')
            
            # If agent is "Independent" or actual name, we consider it scraped.
            # If agent is missing, it needs scrape.
        else:
            # Old format: String is address
            address = str(val)
            agent = None # Unscraped
            
        # Update DB
        # Only update enrichment fields. Do not touch status/ref/coords as they come from CSV sync.
        # But if the record doesn't exist (CSV hasn't synced it yet?), we can insert a stub?
        # Ideally we only update existing records. 
        # But if the JSON has it, it implies we saw it recently.
        # Let's simple UPDATE.
        
        if agent:
             # Full update
             # Parse decision_date back to iso format for DB? 
             # DB 'decision_date' column is DATE.
             # Scraper returns "dd/mm/yy". SQLite stores dates as strings (ISO 8601 pref).
             # We should convert '04/02/26' -> '2026-02-04'.
             db_date = None
             if decision_date:
                 try:
                     dt = datetime.strptime(decision_date, '%d/%m/%y')
                     db_date = dt.strftime('%Y-%m-%d')
                 except:
                     pass # Keep None
             
             cursor.execute("""
                UPDATE applications SET 
                address = ?, 
                agent_name = ?, 
                decision_date = ?,
                last_scraped_details = ?,
                needs_scrape = 0
                WHERE keyval = ?
             """, (address, agent, db_date, datetime.now(), keyval))
             scraped_count += 1
        else:
             # Partial update (Address only)
             cursor.execute("""
                UPDATE applications SET 
                address = ?,
                needs_scrape = 1 -- Force scrape to get agent
                WHERE keyval = ?
             """, (address, keyval))
             
        if cursor.rowcount > 0:
            updated_count += 1
            
    conn.commit()
    conn.close()
    print(f"Migration Complete. Updated {updated_count} records. Fully Scraped: {scraped_count}")

if __name__ == "__main__":
    migrate()
