import sqlite3
import json
from config import Config
from db_adapter import get_connection

def get_db_connection():
    return get_connection(Config.DB_PATH)

def init_db():
    conn = get_db_connection()
    # Jobs
    conn.execute('''
        CREATE TABLE IF NOT EXISTS processing_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        )
    ''')
    
    # Dockets
    conn.execute('''
        CREATE TABLE IF NOT EXISTS dockets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            image_filename TEXT,
            image_hash TEXT,
            original_filename TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            uploaded_by TEXT,
            status TEXT DEFAULT 'UPLOADED',
            
            docket_number TEXT,
            actual_weight REAL,
            total_packages INTEGER,
            
            ai_original_docket_number TEXT,
            ai_original_actual_weight TEXT,
            ai_original_total_packages TEXT,
            
            ai_raw_response TEXT,
            ai_confidence_notes TEXT,
            rejection_reasons TEXT,
            
            processed_at TIMESTAMP,
            
            human_reviewed BOOLEAN DEFAULT 0,
            human_reviewer TEXT,
            human_reviewed_at TIMESTAMP,
            
            reopen_reason TEXT,
            is_archived BOOLEAN DEFAULT 0,
            
            FOREIGN KEY (job_id) REFERENCES processing_jobs(id)
        )
    ''')
    
    # Dimensions
    conn.execute('''
        CREATE TABLE IF NOT EXISTS dimension_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            docket_id INTEGER,
            group_index INTEGER,
            length REAL,
            breadth REAL,
            height REAL,
            num_packages INTEGER,
            dimension_weight REAL,
            
            ai_original_length TEXT,
            ai_original_breadth TEXT,
            ai_original_height TEXT,
            ai_original_num_packages TEXT,
            
            FOREIGN KEY (docket_id) REFERENCES dockets(id)
        )
    ''')
    
    # Corrections
    conn.execute('''
        CREATE TABLE IF NOT EXISTS corrections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            docket_id INTEGER,
            field_name TEXT,
            original_value TEXT,
            corrected_value TEXT,
            corrected_by TEXT,
            corrected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reason TEXT,
            FOREIGN KEY (docket_id) REFERENCES dockets(id)
        )
    ''')
    
    # Audit Log
    conn.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            "user" TEXT,
            action TEXT,
            docket_id INTEGER,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Users
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            role TEXT DEFAULT 'REVIEWER',
            status TEXT DEFAULT 'ACTIVE',
            last_login TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Exports
    conn.execute('''
        CREATE TABLE IF NOT EXISTS exports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            export_type TEXT,
            records_count INTEGER,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def check_duplicate_image(image_hash):
    conn = get_db_connection()
    c = conn.execute('SELECT id, docket_number FROM dockets WHERE image_hash = ?', (image_hash,))
    result = c.fetchone()
    conn.close()
    return result

def create_job(batch_id, total_images, created_by):
    conn = get_db_connection()
    if getattr(conn, 'is_postgres', False):
        c = conn.execute('INSERT INTO processing_jobs (batch_id, total_images, created_by) VALUES (?, ?, ?) RETURNING id', 
                  (batch_id, total_images, created_by))
        job_id = c.fetchone()[0]
    else:
        c = conn.execute('INSERT INTO processing_jobs (batch_id, total_images, created_by) VALUES (?, ?, ?)', 
                  (batch_id, total_images, created_by))
        job_id = c.lastrowid
    conn.commit()
    conn.close()
    return job_id

def create_docket(job_id, image_filename, image_hash, original_filename, uploaded_by):
    conn = get_db_connection()
    if getattr(conn, 'is_postgres', False):
        c = conn.execute('''
            INSERT INTO dockets (job_id, image_filename, image_hash, original_filename, uploaded_by)
            VALUES (?, ?, ?, ?, ?) RETURNING id
        ''', (job_id, image_filename, image_hash, original_filename, uploaded_by))
        docket_id = c.fetchone()[0]
    else:
        c = conn.execute('''
            INSERT INTO dockets (job_id, image_filename, image_hash, original_filename, uploaded_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (job_id, image_filename, image_hash, original_filename, uploaded_by))
        docket_id = c.lastrowid
    conn.commit()
    conn.close()
    return docket_id

def log_audit(user, action, docket_id=None, details=None, conn=None):
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
        
    c = conn.execute('INSERT INTO audit_log ("user", action, docket_id, details) VALUES (?, ?, ?, ?)',
              (user, action, docket_id, details))
              
    if close_conn:
        conn.commit()
        conn.close()
