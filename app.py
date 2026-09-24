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
        
        # Handle datetime objects directly
        if hasattr(value, 'strftime'):
            dt = value
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            ist = timezone(timedelta(hours=5, minutes=30))
            return dt.astimezone(ist).strftime('%Y-%m-%d %I:%M %p')
            
        value_str = str(value)
        if len(value_str) >= 19 and value_str[10] in (' ', 'T'):
            clean_val = value_str[:19].replace('T', ' ')
            dt = datetime.strptime(clean_val, '%Y-%m-%d %H:%M:%S')
            dt = dt.replace(tzinfo=timezone.utc)
            ist = timezone(timedelta(hours=5, minutes=30))
            return dt.astimezone(ist).strftime('%Y-%m-%d %I:%M %p')
        return value_str[:19] if value_str else value_str
    except Exception:
        return str(value)[:19] if value else value


_quota_cache = {'remaining': 50, 'last_checked': 0}

def get_openrouter_quota():
    import time, requests
    from config import Config
    global _quota_cache
    
    # Cache for 60 seconds to avoid spamming OpenRouter API on every page load
    if time.time() - _quota_cache['last_checked'] > 60:
        try:
            headers = {'Authorization': f'Bearer {Config.ROUTER_API_KEY}'}
            res = requests.get('https://openrouter.ai/api/v1/auth/key', headers=headers, timeout=5)
            if res.status_code == 200:
                data = res.json().get('data', {})
                free_reqs = data.get('free_model_daily_requests')
                if free_reqs and 'remaining' in free_reqs:
                    _quota_cache['remaining'] = free_reqs['remaining']
            _quota_cache['last_checked'] = time.time()
        except Exception:
            pass
            
    return _quota_cache['remaining']

def create_app():
    app = Flask(__name__)
    app.jinja_env.filters['localdt'] = format_datetime
    app.config.from_object(Config)
    Config.init_app()
    
    # Auto-initialize database and admin user on startup
    init_db()
    conn = get_db_connection()
    
    # Reset any dockets that were stuck in PROCESSING due to a server restart
    conn.execute("UPDATE dockets SET status = 'FAILED', rejection_reasons = '[\"Server restarted unexpectedly during processing.\"]' WHERE status = 'PROCESSING'")
    
    existing = conn.execute('SELECT * FROM users WHERE role = ?', ('ADMIN',)).fetchone()
    pw_hash = bcrypt.hashpw(Config.ADMIN_PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    try:
        if not existing:
            conn.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'ADMIN')",
                         (Config.ADMIN_USERNAME, pw_hash))
        else:
            # Force sync admin credentials with environment variables to allow easy password changes
            conn.execute("UPDATE users SET username = ?, password_hash = ? WHERE role = 'ADMIN'",
                         (Config.ADMIN_USERNAME, pw_hash))
        conn.commit()
    except Exception as e:
        import sys
        print(f"CRITICAL WARNING: Failed to sync ADMIN credentials on startup! Ensure the username '{Config.ADMIN_USERNAME}' doesn't already exist as a normal user. Error: {e}", file=sys.stderr)
        try:
            conn.rollback()
        except:
            pass
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
        from datetime import timezone
        today_start = datetime.now(timezone.utc).strftime("%Y-%m-%d 00:00:00")
        
        pending = conn.execute("SELECT COUNT(*) FROM dockets WHERE is_archived = 0 AND status IN ('REVIEW_REQUIRED', 'MODIFIED_REVERIFICATION_REQUIRED')").fetchone()[0]
        failed = conn.execute("SELECT COUNT(*) FROM dockets WHERE is_archived = 0 AND status = 'FAILED'").fetchone()[0]
        rejected = conn.execute("SELECT COUNT(*) FROM dockets WHERE is_archived = 0 AND status = 'REJECTED'").fetchone()[0]
        
        # Calculate rate limit remaining using OpenRouter actual API limit
        rate_limit_left = get_openrouter_quota()
        
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



@app.errorhandler(500)
def internal_error(error):
    from flask import render_template
    return render_template('500.html'), 500

@app.errorhandler(403)
def forbidden_error(error):
    from flask import render_template
    return render_template('403.html'), 403

if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)
