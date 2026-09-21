import bcrypt
import os
import shutil
from database import init_db, get_db_connection
from config import Config

def create_admin():
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('SELECT * FROM users WHERE username = ?', (Config.ADMIN_USERNAME,))
    if not c.fetchone():
        password = Config.ADMIN_PASSWORD.encode('utf-8')
        hashed = bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')
        c.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'ADMIN')", 
                  (Config.ADMIN_USERNAME, hashed))
        print(f"Admin user '{Config.ADMIN_USERNAME}' created.")
    else:
        print(f"Admin user '{Config.ADMIN_USERNAME}' already exists.")
        
    conn.commit()
    conn.close()

def setup():
    print("Initializing Database...")
    Config.init_app()
    init_db()
    create_admin()
    
    # Create empty .env if it doesn't exist
    if not os.path.exists('.env'):
        shutil.copy('.env.example', '.env')
        print("Created .env from .env.example. Please update your GEMINI_API_KEY inside .env")
        
    print("Setup complete.")

if __name__ == '__main__':
    setup()
