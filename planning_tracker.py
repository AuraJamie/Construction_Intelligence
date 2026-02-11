import requests
import json
import os
import pandas as pd
from datetime import datetime, timezone, timedelta

# Constants
CSV_URL = "https://data-cyc.opendata.arcgis.com/datasets/7044d1920639460da3fc4a3fa9273107_5.csv"
LOCAL_CSV_FILE = "Planning_Applications.csv"
STATE_FILE = "tracker_state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

def check_and_download_update(current_state):
    print("Checking for updates...")
    try:
        # Check server headers
        head_response = requests.head(CSV_URL, allow_redirects=True, timeout=10)
        head_response.raise_for_status()
        
        server_etag = head_response.headers.get('ETag', '').strip('"')
        local_etag = current_state.get('last_download_etag')
        
        if server_etag != local_etag:
            print(f"Update found (Server: {server_etag} != Local: {local_etag}). Downloading...")
            # Download file
            response = requests.get(CSV_URL, allow_redirects=True, timeout=30)
            response.raise_for_status()
            
            with open(LOCAL_CSV_FILE, 'wb') as f:
                f.write(response.content)
            
            print("Download complete.")
            
            # Update state with new ETag
            current_state['last_download_etag'] = server_etag
            # Note: We do NOT update last_check_timestamp here yet, 
            # because we haven't processed the rows yet.
            return True, current_state
        else:
            print("No file update required (ETag matches).")
            return False, current_state
            
    except Exception as e:
        print(f"Error checking/downloading update: {e}")
        return False, current_state

def find_new_approvals(current_state):
    print("Scanning for newly approved applications...")
    
    last_check_str = current_state.get('last_check_timestamp')
    if not last_check_str:
        # Default to very old if no existing state
        last_check_date = datetime.min.replace(tzinfo=timezone.utc)
    else:
        # Parse ISO format string
        try:
            last_check_date = datetime.fromisoformat(last_check_str)
        except ValueError:
             # Fallback for simple date handling if needed
             last_check_date = pd.to_datetime(last_check_str).to_pydatetime()
             if last_check_date.tzinfo is None:
                 last_check_date = last_check_date.replace(tzinfo=timezone.utc)

    print(f"Looking for approvals modified after: {last_check_date}")

    try:
        df = pd.read_csv(LOCAL_CSV_FILE)
        
        # Ensure DATE_MODIFIED is datetime
        # (Assuming DATE_MODIFIED is the column that updates when status changes to Approved)
        # Using 'coerce' to handle extensive errors, but usually we want to see them.
        df['DATE_MODIFIED'] = pd.to_datetime(df['DATE_MODIFIED'], errors='coerce')
        
        # Filter for Approvals
        # HAPP = Householder Approved?
        # PER = Permitted?
        # PERLHE = Permitted Large Home Extension
        # We will look for these positive statuses
        approval_codes = ['HAPP', 'PER', 'PERLHE', 'HREF'] # Added HREF (Refused) just in case user wants 'decisions', but prompt said 'approved'. Removing HREF for now to match prompt "newly approved".
        approval_codes = ['HAPP', 'PER', 'PERLHE', 'CER'] # CER = Certificate?
        
        # Actually filter
        approved_df = df[df['DECSN'].isin(approval_codes)].copy()
        
        # Filter by Date (Newer than last check)
        # Handle timezone awareness mismatch if necessary
        # The CSV dates seemed to have +00 timezone in previous view_file.
        
        if approved_df['DATE_MODIFIED'].dt.tz is None:
             # If CSV has no TZ, assume UTC or match last_check
             approved_df['DATE_MODIFIED'] = approved_df['DATE_MODIFIED'].dt.tz_localize('UTC')
        
        new_approvals = approved_df[approved_df['DATE_MODIFIED'] > last_check_date]
        
        print(f"Found {len(new_approvals)} new approvals.")
        
        if len(new_approvals) > 0:
            print("\n--- New Approvals List ---")
            for index, row in new_approvals.iterrows():
                ref = row.get('REFVAL', 'N/A')
                desc = row.get('PROPOSAL', 'No description')
                date_mod = row.get('DATE_MODIFIED')
                status = row.get('DECSN')
                
                # Truncate desc if too long
                if isinstance(desc, str) and len(desc) > 80:
                    desc = desc[:77] + "..."
                    
                print(f"[{date_mod}] {ref} ({status}): {desc}")
                
        return len(new_approvals) > 0

    except Exception as e:
        print(f"Error processing CSV: {e}")
        return False

def main():
    state = load_state()
    
    # 1. Update File
    updated, state = check_and_download_update(state)
    save_state(state) # Save ETag update immediately
    
    # 2. Check for Logic Updates
    found_new = find_new_approvals(state)
    
    # 3. Update 'Last Checked' to Now
    # Only update if we successfully ran the check.
    # Current time in UTC
    now_utc = datetime.now(timezone.utc).isoformat()
    state['last_check_timestamp'] = now_utc
    save_state(state)
    print(f"\nTracker run complete. Updated last check time to: {now_utc}")

if __name__ == "__main__":
    main()
