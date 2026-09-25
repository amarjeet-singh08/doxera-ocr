import os

with open('database.py', 'r') as f:
    content = f.read()

# 1. Update CREATE TABLE dockets
old_create = """            ai_original_docket_number TEXT,
            ai_original_actual_weight TEXT,
            ai_original_total_packages TEXT,"""

new_create = """            invoice_no TEXT,
            invoice_value TEXT,
            
            ai_original_docket_number TEXT,
            ai_original_actual_weight TEXT,
            ai_original_total_packages TEXT,
            ai_original_invoice_no TEXT,
            ai_original_invoice_value TEXT,"""

content = content.replace(old_create, new_create)

# 2. Add ALTER TABLE logic after init_db creates all tables
alter_logic = """
    # Safe upgrade for existing databases
    def column_exists(table, column, conn):
        if getattr(conn, 'is_postgres', False):
            c = conn.execute("SELECT column_name FROM information_schema.columns WHERE table_name=%s AND column_name=%s", (table, column))
            return c.fetchone() is not None
        else:
            c = conn.execute(f"PRAGMA table_info({table})")
            columns = [col[1] for col in c.fetchall()]
            return column in columns

    if not column_exists('dockets', 'invoice_no', conn):
        conn.execute("ALTER TABLE dockets ADD COLUMN invoice_no TEXT")
    if not column_exists('dockets', 'invoice_value', conn):
        conn.execute("ALTER TABLE dockets ADD COLUMN invoice_value TEXT")
    if not column_exists('dockets', 'ai_original_invoice_no', conn):
        conn.execute("ALTER TABLE dockets ADD COLUMN ai_original_invoice_no TEXT")
    if not column_exists('dockets', 'ai_original_invoice_value', conn):
        conn.execute("ALTER TABLE dockets ADD COLUMN ai_original_invoice_value TEXT")

    conn.commit()
    conn.close()
"""

# Replace the end of init_db
old_end_init = """    conn.commit()
    conn.close()"""
content = content.replace(old_end_init, alter_logic, 1)

# 3. Update create_docket
old_create_docket_def = "def create_docket(job_id, image_filename, image_hash, original_filename, uploaded_by):"
new_create_docket_def = "def create_docket(job_id, image_filename, image_hash, original_filename, uploaded_by, invoice_no=None, invoice_value=None, ai_invoice_no=None, ai_invoice_value=None):"
content = content.replace(old_create_docket_def, new_create_docket_def)

# Update postgres insert
old_pg_insert = """        c = conn.execute('''
            INSERT INTO dockets (job_id, image_filename, image_hash, original_filename, uploaded_by) 
            VALUES (?, ?, ?, ?, ?) RETURNING id
        ''', (job_id, image_filename, image_hash, original_filename, uploaded_by))"""
new_pg_insert = """        c = conn.execute('''
            INSERT INTO dockets (job_id, image_filename, image_hash, original_filename, uploaded_by, invoice_no, invoice_value, ai_original_invoice_no, ai_original_invoice_value) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id
        ''', (job_id, image_filename, image_hash, original_filename, uploaded_by, invoice_no, invoice_value, ai_invoice_no, ai_invoice_value))"""
content = content.replace(old_pg_insert, new_pg_insert)

# Update sqlite insert
old_sq_insert = """        c = conn.execute('''
            INSERT INTO dockets (job_id, image_filename, image_hash, original_filename, uploaded_by) 
            VALUES (?, ?, ?, ?, ?)
        ''', (job_id, image_filename, image_hash, original_filename, uploaded_by))"""
new_sq_insert = """        c = conn.execute('''
            INSERT INTO dockets (job_id, image_filename, image_hash, original_filename, uploaded_by, invoice_no, invoice_value, ai_original_invoice_no, ai_original_invoice_value) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (job_id, image_filename, image_hash, original_filename, uploaded_by, invoice_no, invoice_value, ai_invoice_no, ai_invoice_value))"""
content = content.replace(old_sq_insert, new_sq_insert)

with open('database.py', 'w') as f:
    f.write(content)
print("database.py updated")
