import os
import bcrypt
from flask import Flask, redirect, url_for
from config import Config
from database import init_db, get_db_connection

def format_datetime(value):
    if not value:
        return value
    try:
        from datetime import datetime, timedelta, timezone
        # Check if the string matches SQLite timestamp format
        if len(value) == 19 and value[10] == ' ':
            dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            dt = dt.replace(tzinfo=timezone.utc)
            ist = timezone(timedelta(hours=5, minutes=30))
            return dt.astimezone(ist).strftime('%Y-%m-%d %I:%M %p')
        return value
    except Exception:
        return value

def create_app():
    app = Flask(__name__)
    app.jinja_env.filters['localdt'] = format_datetime
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


@app.context_processor
def inject_notifications():
    try:
        from database import get_db_connection
        from datetime import datetime
        conn = get_db_connection()
        today_start = datetime.now().strftime("%Y-%m-%d 00:00:00")
        
        pending = conn.execute("SELECT COUNT(*) FROM dockets WHERE is_archived = 0 AND status IN ('REVIEW_REQUIRED', 'MODIFIED_REVERIFICATION_REQUIRED')").fetchone()[0]
        failed = conn.execute("SELECT COUNT(*) FROM dockets WHERE is_archived = 0 AND status = 'FAILED'").fetchone()[0]
        rejected = conn.execute("SELECT COUNT(*) FROM dockets WHERE is_archived = 0 AND status = 'REJECTED'").fetchone()[0]
        
        # Calculate rate limit remaining (assume 50 limit per day)
        today_count = conn.execute("SELECT COUNT(*) FROM dockets WHERE uploaded_at >= ?", (today_start,)).fetchone()[0]
        rate_limit_left = max(0, 50 - today_count)
        
        conn.close()
        return dict(
            notif_pending=pending,
            notif_failed=failed,
            notif_rejected=rejected,
            notif_limit=rate_limit_left,
            notif_total=pending + failed + rejected
        )
    except Exception as e:
        return dict(notif_total=0)

if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)
