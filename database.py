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
    

    # Images (For persistent storage on Render)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS docket_images (
            filename TEXT PRIMARY KEY,
            image_base64 TEXT,
            mimetype TEXT
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
            
            invoice_no TEXT,
            invoice_value TEXT,
            
            ai_original_docket_number TEXT,
            ai_original_actual_weight TEXT,
            ai_original_total_packages TEXT,
            ai_original_invoice_no TEXT,
            ai_original_invoice_value TEXT,
            
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

    # Sales Intelligence Tables (Isolated from OCR)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sales_customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_code TEXT UNIQUE,
            customer_name TEXT,
            sales_person TEXT,
            location TEXT,
            city TEXT,
            state TEXT,
            gst_no TEXT,
            reporting_manager TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sales_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id TEXT UNIQUE,
            title TEXT,
            period_label TEXT,
            billed_filename TEXT,
            unbilled_filename TEXT,
            booking_filename TEXT,
            total_sales REAL DEFAULT 0,
            billed_sales REAL DEFAULT 0,
            unbilled_sales REAL DEFAULT 0,
            total_shipments INTEGER DEFAULT 0,
            total_weight REAL DEFAULT 0,
            avg_shipment_value REAL DEFAULT 0,
            top_sales_person TEXT,
            top_customer TEXT,
            report_data_json TEXT,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sales_shipments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER,
            awb_no TEXT,
            booking_date TEXT,
            customer_code TEXT,
            customer_name TEXT,
            sales_person TEXT,
            shipper TEXT,
            consignee TEXT,
            origin TEXT,
            destination TEXT,
            service_mode TEXT,
            transport_mode TEXT,
            weight REAL DEFAULT 0,
            chargeable_weight REAL DEFAULT 0,
            boxes INTEGER DEFAULT 1,
            appoint_date TEXT,
            bill_no TEXT,
            delivery_status TEXT,
            total_amt REAL DEFAULT 0,
            source_type TEXT,
            FOREIGN KEY (report_id) REFERENCES sales_reports(id) ON DELETE CASCADE
        )
    ''')
    conn.commit()

    # Safe upgrade helper for existing databases (SQLite & PostgreSQL)
    def column_exists(table, column, conn):
        try:
            if getattr(conn, 'is_postgres', False):
                c = conn.execute(
                    "SELECT column_name FROM information_schema.columns WHERE lower(table_name)=lower(%s) AND lower(column_name)=lower(%s)",
                    (table, column)
                )
                return c.fetchone() is not None
            else:
                c = conn.execute(f"PRAGMA table_info({table})")
                columns = [col[1] for col in c.fetchall()]
                return column in columns
        except Exception:
            if getattr(conn, 'is_postgres', False):
                try:
                    conn.rollback()
                except Exception:
                    pass
            return False

    # Safe upgrade checks
    for tbl, col in [
        ('sales_reports', 'booking_filename'),
        ('sales_shipments', 'bill_no'),
        ('sales_shipments', 'delivery_status'),
        ('dockets', 'invoice_no'),
        ('dockets', 'invoice_value'),
        ('dockets', 'ai_original_invoice_no'),
        ('dockets', 'ai_original_invoice_value'),
    ]:
        if not column_exists(tbl, col, conn):
            try:
                conn.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} TEXT")
                conn.commit()
            except Exception:
                conn.rollback()
    
    # Auto-seed sales customers if empty
    try:
        cust_cnt = conn.execute("SELECT COUNT(*) FROM sales_customers").fetchone()[0]
        if cust_cnt == 0:
            import os, json
            seed_path = os.path.join(Config.BASE_DIR, 'data', 'customers_seed.json')
            if os.path.exists(seed_path):
                with open(seed_path, 'r', encoding='utf-8') as fp:
                    seeds = json.load(fp)
                is_pg = getattr(conn, 'is_postgres', False)
                conflict_clause = "ON CONFLICT (customer_code) DO NOTHING" if is_pg else ""
                insert_verb = "INSERT INTO" if is_pg else "INSERT OR IGNORE INTO"
                
                for s in seeds:
                    conn.execute(f'''
                        {insert_verb} sales_customers 
                        (customer_code, customer_name, sales_person, location, city, state, gst_no, reporting_manager)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        {conflict_clause}
                    ''', (
                        s.get('customer_code'),
                        s.get('customer_name'),
                        s.get('sales_person'),
                        s.get('location'),
                        s.get('city'),
                        s.get('state'),
                        s.get('gst_no'),
                        s.get('reporting_manager')
                    ))
                conn.commit()
    except Exception as e:
        print(f"Notice: sales_customers seed check: {e}")
        conn.rollback()

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

def create_docket(job_id, image_filename, image_hash, original_filename, uploaded_by, invoice_no=None, invoice_value=None, ai_invoice_no=None, ai_invoice_value=None):
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
