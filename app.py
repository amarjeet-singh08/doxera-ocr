import os
import bcrypt
from flask import Flask, redirect, url_for, session, render_template, request
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
    
    # Import inside function to avoid circular imports if any
    from ocr_engine import EXHAUSTED_KEYS
    
    global _quota_cache
    
    # Cache for 60 seconds to avoid spamming OpenRouter API on every page load
    if time.time() - _quota_cache['last_checked'] > 60:
        total_remaining = 0
        all_keys_failed = True
        
        for key in Config.ROUTER_API_KEYS:
            if key in EXHAUSTED_KEYS:
                continue
                
            try:
                headers = {'Authorization': f'Bearer {key}'}
                res = requests.get('https://openrouter.ai/api/v1/auth/key', headers=headers, timeout=5)
                if res.status_code == 200:
                    data = res.json().get('data', {})
                    free_reqs = data.get('free_model_daily_requests')
                    if free_reqs and 'remaining' in free_reqs:
                        total_remaining += free_reqs['remaining']
                        all_keys_failed = False
                elif res.status_code in (401, 403):
                    EXHAUSTED_KEYS.add(key)
            except Exception:
                pass
                
        if not all_keys_failed:
            _quota_cache['remaining'] = total_remaining
        elif not Config.ROUTER_API_KEYS:
             _quota_cache['remaining'] = 0
             
        _quota_cache['last_checked'] = time.time()
            
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
    
    pw_hash = bcrypt.hashpw(Config.ADMIN_PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    admin_user = (Config.ADMIN_USERNAME or 'admin').strip()
    try:
        # 1. First check if a user with the configured admin username already exists (case-insensitive)
        existing_by_name = conn.execute(
            'SELECT id, username, role FROM users WHERE LOWER(username) = LOWER(?)',
            (admin_user,)
        ).fetchone()

        if existing_by_name:
            # User already exists: update password and ensure ADMIN role is present without touching username
            raw_roles = str(existing_by_name['role'] or '')
            current_roles = [r.strip().upper() for r in raw_roles.split(',') if r.strip()]
            if 'ADMIN' not in current_roles:
                current_roles.append('ADMIN')
            roles_str = ', '.join(sorted(set(current_roles)))
            conn.execute(
                "UPDATE users SET password_hash = ?, role = ? WHERE id = ?",
                (pw_hash, roles_str, existing_by_name['id'])
            )
        else:
            # 2. Check if a legacy 'admin' account exists that should be renamed
            legacy_admin = conn.execute(
                "SELECT id, username FROM users WHERE LOWER(username) = 'admin'"
            ).fetchone()

            if legacy_admin and admin_user.lower() != 'admin':
                # Safely rename legacy admin to the configured ADMIN_USERNAME
                conn.execute(
                    "UPDATE users SET username = ?, password_hash = ?, role = 'ADMIN' WHERE id = ?",
                    (admin_user, pw_hash, legacy_admin['id'])
                )
            else:
                # 3. Create fresh admin account
                conn.execute(
                    "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'ADMIN')",
                    (admin_user, pw_hash)
                )
        conn.commit()
    except Exception as e:
        import sys
        print(f"CRITICAL WARNING: Failed to sync ADMIN credentials on startup! Error: {e}", file=sys.stderr)
        try:
            conn.rollback()
        except:
            pass
    conn.close()
    
    # Register Blueprints
    from routes_auth import auth_bp
    from routes_ops import ops_bp
    from routes_sales import sales_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(ops_bp)
    app.register_blueprint(sales_bp)
    
    @app.route('/')
    def index():
        return redirect(url_for('ops.dashboard'))

    @app.context_processor
    def inject_notifications():
        try:
            from database import get_db_connection
            from datetime import datetime, timezone
            conn = get_db_connection()
            today_start = datetime.now(timezone.utc).strftime("%Y-%m-%d 00:00:00")
            
            pending = conn.execute("SELECT COUNT(*) FROM dockets WHERE is_archived = 0 AND status IN ('REVIEW_REQUIRED', 'MODIFIED_REVERIFICATION_REQUIRED')").fetchone()[0]
            failed = conn.execute("SELECT COUNT(*) FROM dockets WHERE is_archived = 0 AND status = 'FAILED'").fetchone()[0]
            rejected = conn.execute("SELECT COUNT(*) FROM dockets WHERE is_archived = 0 AND status = 'REJECTED'").fetchone()[0]
            
            # Calculate rate limit remaining using OpenRouter actual API limit
            rate_limit_left = get_openrouter_quota()
            
            conn.close()

            def user_has_role(*required_roles):
                try:
                    raw_role = session.get('role', 'VIEWER')
                except Exception:
                    raw_role = 'VIEWER'
                if isinstance(raw_role, list):
                    u_roles = {str(r).strip().upper() for r in raw_role}
                else:
                    u_roles = {str(r).strip().upper() for r in str(raw_role).split(',') if str(r).strip()}
                if 'ADMIN' in u_roles:
                    return True
                req_set = {str(r).strip().upper() for r in required_roles}
                return bool(u_roles.intersection(req_set))

            return dict(
                notif_pending=pending,
                notif_failed=failed,
                notif_rejected=rejected,
                notif_limit=rate_limit_left,
                notif_total=pending + failed + rejected,
                user_has_role=user_has_role
            )
        except Exception as e:
            def user_has_role(*required_roles):
                try:
                    raw_role = session.get('role', 'VIEWER')
                except Exception:
                    raw_role = 'VIEWER'
                u_roles = {str(r).strip().upper() for r in str(raw_role).split(',') if str(r).strip()}
                if 'ADMIN' in u_roles:
                    return True
                return bool(u_roles.intersection({str(r).strip().upper() for r in required_roles}))
            return dict(notif_total=0, user_has_role=user_has_role)

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('500.html'), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('403.html'), 403
        
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)
