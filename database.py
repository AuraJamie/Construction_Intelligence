import sqlite3
import os
from datetime import datetime

DB_NAME = "construction_intelligence.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Enable Write Ahead Logging for concurrency (API writing, User reading)
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    # Applications Table
    # keyval is the unique ID used by Idox (e.g., 'T6ZSXXSJI5I00')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS applications (
        keyval TEXT PRIMARY KEY,
        reference TEXT,
        address TEXT,
        proposal TEXT,
        status TEXT,
        received_date DATE,
        validated_date DATE, -- Missing column fixed
        decision_date DATE,
        agent_name TEXT,
        latitude REAL,
        longitude REAL,
        url TEXT,
        
        -- Meta fields
        source_object_id INTEGER, -- ArcGIS Object ID
        last_synced_api TIMESTAMP, -- When we fetched from ArcGIS
        last_scraped_details TIMESTAMP, -- When we visited Idox
        needs_scrape BOOLEAN DEFAULT 1, -- Priority flag for scraper
        portal_keyval TEXT, -- Alternate key for scraping
        validation_warning TEXT -- Warning validation messages
    )
    ''')
    
    # Status History Table (Audit Log)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS status_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyval TEXT,
        old_status TEXT,
        new_status TEXT,
        change_date TIMESTAMP
    )
    ''')
    
    # Index for fast searching/filtering
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON applications(status);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_date ON applications(received_date);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_needs_scrape ON applications(needs_scrape);')
    
    # ---------------------------------------------------------
    # MIGRATION: Check for missing columns (Self-healing schema)
    # ---------------------------------------------------------
    cursor.execute("PRAGMA table_info(applications)")
    columns = [r['name'] for r in cursor.fetchall()]
    
    if 'validated_date' not in columns:
        print("Migrating: Adding 'validated_date' column...")
        try:
            cursor.execute("ALTER TABLE applications ADD COLUMN validated_date DATE")
        except Exception as e:
            print(f"Migration error: {e}")

    if 'validation_warning' not in columns:
        print("Migrating: Adding 'validation_warning' column...")
        try:
            cursor.execute("ALTER TABLE applications ADD COLUMN validation_warning TEXT")
        except Exception as e:
           print(f"Migration error: {e}")

    if 'portal_keyval' not in columns:
        print("Migrating: Adding 'portal_keyval' column...")
        try:
            cursor.execute("ALTER TABLE applications ADD COLUMN portal_keyval TEXT")
        except Exception as e:
           print(f"Migration error: {e}")

    conn.commit()
    conn.close()
    print(f"Database {DB_NAME} initialized/verified successfully.")

if __name__ == "__main__":
    init_db()
