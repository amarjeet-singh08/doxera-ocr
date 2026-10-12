from functools import wraps
from flask import session, redirect, url_for, flash, abort

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(roles):
    """
    roles can be a string 'ADMIN' or list ['ADMIN', 'REVIEWER']
    Supports users having multiple assigned roles (e.g. 'REVIEWER, AUDITOR').
    """
    if isinstance(roles, str):
        target_roles = {roles.strip().upper()}
    else:
        target_roles = {r.strip().upper() for r in roles}
        
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('auth.login'))
            
            raw_role = session.get('role', 'VIEWER')
            if isinstance(raw_role, list):
                user_roles = {str(r).strip().upper() for r in raw_role}
            else:
                user_roles = {str(r).strip().upper() for r in str(raw_role).split(',') if str(r).strip()}
                
            # If user has ADMIN role, grant access to everything
            if 'ADMIN' in user_roles:
                return f(*args, **kwargs)
                
            # Check if any of the user's roles matches any target role
            if not user_roles.intersection(target_roles):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
