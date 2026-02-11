import sqlite3
import json
import os
from datetime import datetime

DB_NAME = "construction_intelligence.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def run():
    print("Generating static data for GitHub Pages...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Fetch All Applications
    # We fetch EVERYTHING so the frontend can filter/sort freely.
    # Be mindful of size. If > 10MB, might be slow on mobile.
    print("Fetching applications...")
    rows = cursor.execute("SELECT * FROM applications ORDER BY received_date DESC").fetchall()
    
    apps = []
    agent_counts = {}
    
    for row in rows:
        # Format Date Helper
        def fmt_date(d_str):
            if not d_str: return '-'
            s = str(d_str).strip()
            if not s or s == 'None': return '-'
            try:
                # DB format is YYYY-MM-DD
                dt = datetime.strptime(s, '%Y-%m-%d')
                return dt.strftime('%d/%m/%Y')
            except:
                return s

        # Agent Count Logic
        agent = row['agent_name']
        if agent and agent != 'Independent':
            agent_counts[agent] = agent_counts.get(agent, 0) + 1
            
        # URL Construction
        active_keyval = row['portal_keyval'] if row['portal_keyval'] else row['keyval']
        council_url = f"https://planningaccess.york.gov.uk/online-applications/applicationDetails.do?activeTab=summary&keyVal={active_keyval}"

        apps.append({
            'keyval': row['keyval'],
            'ref': row['reference'] or row['keyval'],
            'status': row['status'] or 'Unknown',
            'proposal': row['proposal'] or '',
            'received_date': row['received_date'], # Keep raw for sorting
            'validated_date': row['validated_date'],
            'decision_date': row['decision_date'],
            'received_date_fmt': fmt_date(row['received_date']),
            'validated_date_fmt': fmt_date(row['validated_date']),
            'decision_date_fmt': fmt_date(row['decision_date']),
            'address': row['address'] or 'Address not available',
            'agent': row['agent_name'] or '-',
            'lat': row['latitude'],
            'lon': row['longitude'],
            'needs_scrape': row['needs_scrape'],
            'council_url': council_url,
            'validation_warning': row['validation_warning']
        })
        
    conn.close()
    
    # 2. Process Agents (Top 50)
    sorted_agents = sorted(agent_counts.items(), key=lambda item: item[1], reverse=True)
    top_agents = [x[0] for x in sorted_agents[:100]] # Top 100 for static
    
    # 3. Compile Data
    final_data = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'applications': apps,
        'agents': top_agents
    }
    
    # 4. Write to file
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(final_data, f)
        
    print(f"Success! Generated data.json with {len(apps)} records.")

if __name__ == "__main__":
    run()
