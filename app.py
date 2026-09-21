import os
import bcrypt
from flask import Flask, redirect, url_for
from config import Config
from database import init_db, get_db_connection

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    Config.init_app()
    
    # Auto-initialize database and admin user on startup
    init_db()
    conn = get_db_connection()
    existing = conn.execute('SELECT * FROM users WHERE role = ?', ('ADMIN',)).fetchone()
    if not existing:
        pw_hash = bcrypt.hashpw(Config.ADMIN_PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        conn.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'ADMIN')",
                     (Config.ADMIN_USERNAME, pw_hash))
        conn.commit()
    conn.close()
    
    # Register Blueprints
    from routes_auth import auth_bp
    from routes_ops import ops_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(ops_bp)
    
    @app.route('/')
    def index():
        return redirect(url_for('ops.dashboard'))
        
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)
