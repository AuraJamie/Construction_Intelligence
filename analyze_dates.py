import sqlite3
from datetime import datetime
import statistics

DB_NAME = "construction_intelligence.db"

def parse_date(date_str):
    if not date_str:
        return None
    
    clean_str = str(date_str).strip()
    # Remove T separator if present (ISO)
    if 'T' in clean_str:
        clean_str = clean_str.split('T')[0]
        
    formats = [
        '%Y/%m/%d',      # 2025/02/28 - The format we saw
        '%Y-%m-%d',      # 2023-01-01
        '%d/%m/%Y',      # 01/01/2023
        '%d/%m/%y',      # 01/01/23
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(clean_str, fmt)
        except ValueError:
            continue
            
    # As a fallback, try to parse simpler if separated by / or -
    # But usually strptime is best.
    return None

def analyze_dates():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    print("Fetching data...")
    rows = cursor.execute("SELECT received_date, validated_date, decision_date FROM applications").fetchall()
    conn.close()
    
    recv_to_valid_days = []
    valid_to_dec_days = []
    recv_to_dec_days = []
    
    valid_record_count = 0
    
    for row in rows:
        r_str, v_str, d_str = row
        
        r_date = parse_date(r_str)
        v_date = parse_date(v_str)
        d_date = parse_date(d_str)
        
        has_some_data = False
        
        # 1. Received to Validated
        if r_date and v_date:
            delta = (v_date - r_date).days
            recv_to_valid_days.append(delta)
            has_some_data = True
            
        # 2. Validated to Decision
        if v_date and d_date:
            delta = (d_date - v_date).days
            valid_to_dec_days.append(delta)
            has_some_data = True
            
        # 3. Received to Decision
        if r_date and d_date:
            delta = (d_date - r_date).days
            recv_to_dec_days.append(delta)
            has_some_data = True
            
        if has_some_data:
            valid_record_count += 1

    print(f"\nProcessed {len(rows)} total records.")
    print(f"Found {valid_record_count} records with at least one valid date pair.")

    def print_stat(name, data):
        if not data:
            print(f"{name}: No valid data points.")
            return
            
        avg = statistics.mean(data)
        try:
            median = statistics.median(data)
        except: median = 0
        
        print(f"\n{name}:")
        print(f"  Count: {len(data)}")
        print(f"  Mean: {avg:.2f} days")
        print(f"  Median: {median:.2f} days")

    print("\n--- Summary Statistics ---")
    print_stat("Received -> Validated", recv_to_valid_days)
    print_stat("Validated -> Decision", valid_to_dec_days)
    print_stat("Received -> Decision", recv_to_dec_days)

if __name__ == "__main__":
    analyze_dates()
