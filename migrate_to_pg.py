import os
import sqlite3
import psycopg2
from psycopg2.extras import DictCursor

def migrate():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print('No DATABASE_URL set. Cannot migrate.')
        return

    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)

    pg_conn = psycopg2.connect(db_url)
    pg_conn.autocommit = True
    pg_cur = pg_conn.cursor()

    sl_conn = sqlite3.connect('dockets.db')
    sl_conn.row_factory = sqlite3.Row
    sl_cur = sl_conn.cursor()

    print('Creating tables in PostgreSQL...')
    pg_cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'VIEWER',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS processing_jobs (
            id SERIAL PRIMARY KEY,
            batch_id TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT,
            total_images INTEGER DEFAULT 0,
            processed_count INTEGER DEFAULT 0,
            verified_count INTEGER DEFAULT 0,
            review_count INTEGER DEFAULT 0,
            rejected_count INTEGER DEFAULT 0,
            failed_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'PROCESSING'
        );
        CREATE TABLE IF NOT EXISTS dockets (
            id SERIAL PRIMARY KEY,
            job_id INTEGER,
            image_filename TEXT,
            image_hash TEXT,
            original_filename TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            uploaded_by TEXT,
            status TEXT DEFAULT 'UPLOADED',
            docket_number TEXT,
            actual_weight TEXT,
            total_packages TEXT,
            ai_original_docket_number TEXT,
            ai_original_actual_weight TEXT,
            ai_original_total_packages TEXT,
            ai_raw_response TEXT,
            ai_confidence_notes TEXT,
            rejection_reasons TEXT,
            processed_at TIMESTAMP,
            human_reviewed INTEGER DEFAULT 0,
            human_reviewer TEXT,
            human_reviewed_at TIMESTAMP,
            is_archived INTEGER DEFAULT 0,
            reopen_reason TEXT
        );
        CREATE TABLE IF NOT EXISTS dimension_groups (
            id SERIAL PRIMARY KEY,
            docket_id INTEGER,
            group_index INTEGER,
            length TEXT,
            breadth TEXT,
            height TEXT,
            num_packages TEXT,
            dimension_weight REAL,
            ai_original_length TEXT,
            ai_original_breadth TEXT,
            ai_original_height TEXT,
            ai_original_num_packages TEXT
        );
        CREATE TABLE IF NOT EXISTS corrections (
            id SERIAL PRIMARY KEY,
            docket_id INTEGER,
            field_name TEXT,
            original_value TEXT,
            corrected_value TEXT,
            corrected_by TEXT,
            corrected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            id SERIAL PRIMARY KEY,
            "user" TEXT,
            action TEXT,
            docket_id INTEGER,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    tables = ['users', 'processing_jobs', 'dockets', 'dimension_groups', 'corrections', 'audit_log']
    
    for table in tables:
        print(f'Migrating table {table}...')
        sl_cur.execute(f'SELECT * FROM {table}')
        rows = sl_cur.fetchall()
        
        if not rows:
            continue
            
        columns = rows[0].keys()
        col_names = ', '.join(columns)
        placeholders = ', '.join(['%s'] * len(columns))
        
        try:
            pg_cur.execute(f'TRUNCATE TABLE {table} RESTART IDENTITY CASCADE')
        except Exception as e:
            print(f"Truncate failed for {table}: {e}")
        
        insert_query = f'INSERT INTO {table} ({col_names}) VALUES ({placeholders})'
        
        for row in rows:
            pg_cur.execute(insert_query, tuple(row))
            
        print(f'  -> Migrated {len(rows)} rows.')

    pg_conn.close()
    sl_conn.close()
    print('Migration complete!')

if __name__ == '__main__':
    migrate()
