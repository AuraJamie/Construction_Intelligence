from flask import Flask, render_template, jsonify, request
import sqlite3
from datetime import datetime
import scraper
import sync_manager
import threading

app = Flask(__name__)
DB_NAME = "construction_intelligence.db"

is_syncing = False

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/sync', methods=['POST'])
def trigger_sync():
    global is_syncing
    if is_syncing:
        return jsonify({'status': 'running', 'message': 'Sync already in progress'})
    
    def run_sync():
        global is_syncing
        is_syncing = True
        try:
            sync_manager.sync_from_open_data()
        except Exception as e:
            print(f"Sync failed: {e}")
        finally:
            is_syncing = False
            
    thread = threading.Thread(target=run_sync)
    thread.daemon = True
    thread.start()
    
    return jsonify({'status': 'started', 'message': 'Background sync started'})

@app.route('/api/status')
def system_status():
    global is_syncing
    conn = get_db()
    last_sync = conn.execute("SELECT max(last_synced_api) FROM applications").fetchone()[0]
    conn.close()
    return jsonify({
        'is_syncing': is_syncing,
        'last_sync': last_sync
    })

@app.route('/api/agents')
def get_agents():
    conn = get_db()
    cursor = conn.cursor()
    # Return top 50 agents by activity
    # Exclude null or 'Independent' if you only want companies, but 'Independent' is valid filter
    rows = cursor.execute("""
        SELECT agent_name, count(*) as c 
        FROM applications 
        WHERE agent_name IS NOT NULL AND agent_name != 'Independent' 
        GROUP BY agent_name 
        ORDER BY c DESC 
        LIMIT 50
    """ ).fetchall()
    
    agents = [r['agent_name'] for r in rows]
    conn.close()
    return jsonify(agents)

@app.route('/api/data')
def get_data():
    # Filters
    # Handle both 'status' and 'status[]' conventions just in case, but standard is same key multiple times
    statuses = request.args.getlist('status') 
    # If no status passed, or ['ALL'], default to ALL (no filter)
    if 'ALL' in statuses or not statuses:
        statuses = []
        
    limit = request.args.get('limit', 50)
    sort_dir = request.args.get('sort_dir', request.args.get('sort', 'desc'))
    if sort_dir.lower() not in ['asc', 'desc']: sort_dir = 'desc'
    
    sort_field = request.args.get('sort_by', 'received_date')
    valid_sorts = ['received_date', 'validated_date', 'decision_date']
    if sort_field not in valid_sorts: sort_field = 'received_date'
    
    search_term = request.args.get('search', '').strip()
    agent_filter = request.args.get('agent', '').strip()
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Build Base Clause
    where_clauses = ["1=1"]
    params = []
    
    # Status
    if statuses:
        # Handle 'PENDING' special group if present
        # If mixed with others, it's tricky. Let's assume user selects precise statuses OR 'Starting Groups'.
        # For now, simplistic IN clause, unless 'PENDING' string is passed.
        
        status_placeholders = []
        pending_logic = False
        
        cleaned_statuses = []
        for s in statuses:
            if s == 'PENDING':
                pending_logic = True
            else:
                cleaned_statuses.append(s)
                
        if cleaned_statuses:
            ph = ','.join(['?']*len(cleaned_statuses))
            clause = f"status IN ({ph})"
            # Params added later
            
            if pending_logic:
                clause = f"({clause} OR status IN ('Pending', 'PCO', 'W', 'Unknown') OR status IS NULL)"
            
            where_clauses.append(clause)
            params.extend(cleaned_statuses)
        elif pending_logic:
             where_clauses.append("(status IN ('Pending', 'PCO', 'W', 'Unknown') OR status IS NULL)")
    
    # Search (Proposal, Address, Ref, Keyval)
    if search_term:
        term = f"%{search_term}%"
        where_clauses.append("(proposal LIKE ? OR address LIKE ? OR reference LIKE ? OR keyval LIKE ?)")
        params.extend([term, term, term, term])
        
    # Agent
    if agent_filter:
        term = f"%{agent_filter}%"
        where_clauses.append("agent_name LIKE ?")
        params.append(term)
        
    # Dates
    if start_date:
        where_clauses.append("received_date >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append("received_date <= ?")
        params.append(end_date)
        
    where_sql = " AND ".join(where_clauses)
    
    # 2. Stats Query (Count total matches before limit)
    count_query = f"SELECT count(*) FROM applications WHERE {where_sql}"
    # Breakdown stats?
    # Calculating breakdown for arbitrary filter is expensive (requires Group By).
    # Group By Status
    stats_query = f"SELECT status, count(*) FROM applications WHERE {where_sql} GROUP BY status"
    
    total_matches = cursor.execute(count_query, params).fetchone()[0]
    
    # Run breakdown
    # Reuse params!
    # SQLite cursor.execute requires fresh params list usually ok to reuse? Yes.
    stat_rows = cursor.execute(stats_query, params).fetchall()
    
    happ_count = 0
    pending_count = 0
    ref_count = 0
    
    for r in stat_rows:
        s = r['status']
        c = r[1]
        if s == 'HAPP': happ_count += c
        elif s in ['Pending', 'PCO', 'W', None, 'Unknown']: pending_count += c
        elif s == 'REF': ref_count += c
        
    stats = {
        'total_loaded': total_matches,
        'happ_count': happ_count,
        'pending_count': pending_count,
        'ref_count': ref_count
    }

    # 3. Fetch Data
    query = f"SELECT * FROM applications WHERE {where_sql} ORDER BY {sort_field} {sort_dir}"
    
    try:
        limit = int(limit)
    except: limit = 50
    query += f" LIMIT {limit}"
    
    rows = cursor.execute(query, params).fetchall()

    # 3. Format Records
    records = []

    def fmt_date(d_str):
        if not d_str: return '-'
        s = str(d_str).strip()
        if not s or s == 'None': return '-'
        
        # Remove time if present
        s = s.split('T')[0].split(' ')[0]
        
        # Normalize separators to slash
        s_clean = s.replace('-', '/')
        
        try:
            parts = s_clean.split('/')
            if len(parts) == 3:
                p0, p1, p2 = int(parts[0]), int(parts[1]), int(parts[2])
                
                day, month, year = 0, 0, 0
                
                # Check for Year at start (YYYY/MM/DD)
                if p0 > 31: 
                    year, month, day = p0, p1, p2
                else: 
                    # Assume DD/MM/YYYY (UK standard)
                    day, month, year = p0, p1, p2
                
                # Expand 2-digit year
                if year < 100: year += 2000
                
                return f"{day:02d}/{month:02d}/{year:04d}"
        except: pass
        
        return s

    for row in rows:
        scraped_needed = False
        if not row['agent_name'] or row['needs_scrape']:
             scraped_needed = True
        
        addr_disp = row['address'] if row['address'] else "Loading..."
        agent_disp = row['agent_name'] if row['agent_name'] else "Loading..."
        
        
        # URL Construction: Use Portal KeyVal if available (Self-healed), otherwise original KeyVal
        # We prefer direct KeyVal deep-link as Search-by-Ref relies on session
        active_keyval = row['portal_keyval'] if row['portal_keyval'] else row['keyval']
        council_url = f"https://planningaccess.york.gov.uk/online-applications/applicationDetails.do?activeTab=summary&keyVal={active_keyval}"

        records.append({
            'ref': row['reference'] or row['keyval'],
            'keyval': row['keyval'], 
            'status': row['status'] or 'Unknown',
            'proposal': row['proposal'] or '',
            'date': fmt_date(row['received_date']), # Fallback for sorting logic
            'received_date_fmt': fmt_date(row['received_date']),
            'validated_date_fmt': fmt_date(row['validated_date']),
            'decision_date_fmt': fmt_date(row['decision_date']),
            'address': addr_disp,
            'agent': agent_disp,
            'lat': row['latitude'],
            'lon': row['longitude'],
            'needs_scrape': scraped_needed,
            'council_url': council_url,
            'validation_warning': row['validation_warning']
        })
    
    conn.close()
    return jsonify({'records': records, 'stats': stats})

@app.route('/api/fetch-address/<keyval>')
def fetch_address(keyval):
    conn = get_db()
    cursor = conn.cursor()
    
    # Get reference for self-healing & current status for validation
    row = cursor.execute("SELECT reference, status FROM applications WHERE keyval=?", (keyval,)).fetchone()
    ref_num = row['reference'] if row else None
    api_status = row['status'] if row else 'Unknown'
    
    data = scraper.scrape_application_details(keyval, reference=ref_num)
    
    response_data = {'address': 'Unavailable', 'agent': '-', 'decision_date': None, 'council_url': '#', 'validation_warning': None}
    
    if data['success']:
        db_date = None
        ui_date = None
        if data['decision_date']:
             ui_date = data['decision_date']
             try:
                 dt = datetime.strptime(ui_date, '%d/%m/%y')
                 db_date = dt.strftime('%Y-%m-%d')
             except: pass
        
        # Portal Keyval Update
        portal_keyval = data.get('portal_keyval')
        
        # Cross Validation (Phase 3)
        validation_msg = None
        scraped_st = data.get('scraped_status', '').lower()
        if 'refused' in scraped_st and api_status not in ['REF']:
             validation_msg = f"Mismatch: Portal says '{data['scraped_status']}', API says '{api_status}'"
        elif 'approved' in scraped_st and api_status not in ['HAPP', 'PER', 'NOBJ']:
             validation_msg = f"Mismatch: Portal says '{data['scraped_status']}', API says '{api_status}'"

        cursor.execute("""
            UPDATE applications SET 
            address = ?, 
            agent_name = ?, 
            decision_date = ?,
            last_scraped_details = ?,
            needs_scrape = 0,
            portal_keyval = COALESCE(?, portal_keyval),
            validation_warning = ?
            WHERE keyval = ?
        """, (data['address'], data['agent'], db_date, datetime.now(), portal_keyval, validation_msg, keyval))
        conn.commit()
        
        # Return updated URL & Warning
        active_kv = portal_keyval if portal_keyval else keyval
        new_url = f"https://planningaccess.york.gov.uk/online-applications/applicationDetails.do?activeTab=summary&keyVal={active_kv}"
        
        response_data = {
            'address': data['address'],
            'agent': data['agent'],
            'decision_date': ui_date,
            'council_url': new_url,
            'validation_warning': validation_msg
        }
    
    conn.close()
    return jsonify(response_data)

@app.route('/api/application/<keyval>')
def get_application_details(keyval):
    conn = get_db()
    cursor = conn.cursor()
    
    # Fetch Main Record
    row = cursor.execute("SELECT * FROM applications WHERE keyval = ?", (keyval,)).fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Not found'}), 404
        
    # Convert Row to dict
    app_data = dict(row)
    
    # Fetch History
    try:
        history_rows = cursor.execute("SELECT * FROM status_history WHERE keyval = ? ORDER BY change_date DESC", (keyval,)).fetchall()
        history = [dict(r) for r in history_rows]
    except:
        history = []
    
    conn.close()
    
    return jsonify({
        'application': app_data,
        'history': history
    })

if __name__ == '__main__':
    print("Starting York Construction Intelligence Database Server...")
    app.run(debug=True, port=5000)
