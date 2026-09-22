import os
import sqlite3
import re

try:
    import psycopg2
    from psycopg2.extras import DictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

class DBWrapper:
    def __init__(self, conn, is_postgres=False):
        self.conn = conn
        self.is_postgres = is_postgres
        if self.is_postgres:
            self.conn.autocommit = False

    def execute(self, query, params=()):
        if self.is_postgres:
            # Replace ? with %s for psycopg2
            pg_query = query.replace('?', '%s')
            
            # Special syntax replacements for Postgres compatibility during init
            if 'AUTOINCREMENT' in pg_query:
                pg_query = re.sub(r'INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT', 'SERIAL PRIMARY KEY', pg_query, flags=re.IGNORECASE)
            
            if 'BOOLEAN DEFAULT 0' in pg_query:
                pg_query = pg_query.replace('BOOLEAN DEFAULT 0', 'INTEGER DEFAULT 0')
                
            cursor = self.conn.cursor()
            cursor.execute(pg_query, params)
            return cursor
        else:
            return self.conn.execute(query, params)
            
    def commit(self):
        self.conn.commit()
        
    def close(self):
        self.conn.close()

    def cursor(self):
        return self.conn.cursor()

def get_connection(db_path):
    db_url = os.environ.get('DATABASE_URL')
    if db_url and PSYCOPG2_AVAILABLE:
        # Render sometimes provides postgres:// instead of postgresql://
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        conn = psycopg2.connect(db_url, cursor_factory=DictCursor)
        return DBWrapper(conn, is_postgres=True)
    else:
        conn = sqlite3.connect(db_path, timeout=15)
        conn.row_factory = sqlite3.Row
        return DBWrapper(conn, is_postgres=False)
