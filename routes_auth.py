from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import bcrypt
from database import get_db_connection, log_audit

import time

auth_bp = Blueprint('auth', __name__)

# Simple in-memory rate limiter for login brute-force protection
LOGIN_ATTEMPTS = {}

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('ops.dashboard'))
        
    if request.method == 'POST':
        ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
        now = time.time()
        
        # Cleanup old attempts (5 minute window)
        LOGIN_ATTEMPTS[ip] = [t for t in LOGIN_ATTEMPTS.get(ip, []) if now - t < 300]
        
        if len(LOGIN_ATTEMPTS[ip]) >= 10:
            flash('Security Alert: Too many failed login attempts. Please try again in 5 minutes.', 'error')
            return render_template('login.html')

        username = request.form['username']
        password = request.form['password'].encode('utf-8')
        
        conn = get_db_connection()
        try:
            user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
            
            if user and user['status'] == 'ACTIVE' and bcrypt.checkpw(password, user['password_hash'].encode('utf-8')):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                
                if ip in LOGIN_ATTEMPTS:
                    del LOGIN_ATTEMPTS[ip]
                
                conn.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user['id'],))
                conn.commit()
                log_audit(username, 'LOGIN', details='User logged in successfully')
                
                return redirect(url_for('ops.dashboard'))
            else:
                LOGIN_ATTEMPTS[ip].append(now)
                flash('Invalid username or password, or account disabled.', 'error')
        finally:
            conn.close()
            
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    if 'username' in session:
        log_audit(session['username'], 'LOGOUT', details='User logged out')
    session.clear()
    return redirect(url_for('auth.login'))
from decorators import login_required, role_required
import sqlite3

@auth_bp.route('/admin/users', methods=['GET', 'POST'])
@login_required
@role_required(['ADMIN'])
def user_management():
    conn = get_db_connection()
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            selected_roles = request.form.getlist('roles')
            
            # Fallback to single 'role' field if sent
            if not selected_roles:
                single_role = request.form.get('role', '').strip()
                if single_role:
                    selected_roles = [r.strip() for r in single_role.split(',') if r.strip()]

            if not username or not password:
                flash('Username and Password are required.', 'error')
            elif not selected_roles:
                flash('Please select at least one role/access level.', 'error')
            else:
                # 1. Check if username already exists (case-insensitive check)
                existing_user = conn.execute(
                    'SELECT id, username FROM users WHERE LOWER(username) = LOWER(?)', 
                    (username,)
                ).fetchone()

                if existing_user:
                    flash(f'Cannot create user: Username "{username}" is already stored in the system. Use Edit to change roles or reset password.', 'error')
                else:
                    # 2. Check if password is used by existing accounts (prevent identical ID & PW)
                    all_existing_users = conn.execute('SELECT username, password_hash FROM users').fetchall()
                    is_pw_reused = False
                    pw_bytes = password.encode('utf-8')
                    for u in all_existing_users:
                        try:
                            if bcrypt.checkpw(pw_bytes, u['password_hash'].encode('utf-8')):
                                is_pw_reused = True
                                break
                        except Exception:
                            pass
                    
                    if is_pw_reused:
                        flash('Security Policy: This password matches an existing account credential. Please choose a unique password.', 'error')
                    else:
                        roles_str = ', '.join(sorted(set(selected_roles)))
                        pw_hash = bcrypt.hashpw(pw_bytes, bcrypt.gensalt()).decode('utf-8')
                        try:
                            conn.execute(
                                'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)', 
                                (username, pw_hash, roles_str)
                            )
                            conn.commit()
                            log_audit(session['username'], 'USER_CREATED', details=f"Created user {username} with roles: {roles_str}")
                            flash(f'User "{username}" created successfully with roles: {roles_str}.', 'success')
                        except Exception as e:
                            conn.rollback()
                            flash(f'Could not create user: {str(e)}', 'error')

        elif action == 'update':
            user_id = request.form.get('user_id')
            selected_roles = request.form.getlist('roles')
            new_password = request.form.get('password', '').strip()

            if not user_id:
                flash('Invalid user ID provided.', 'error')
            elif not selected_roles:
                flash('At least one access role must be selected.', 'error')
            else:
                target_user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
                if not target_user:
                    flash('User not found.', 'error')
                else:
                    roles_str = ', '.join(sorted(set(selected_roles)))
                    if new_password:
                        # Check password uniqueness
                        all_existing_users = conn.execute('SELECT id, username, password_hash FROM users WHERE id != ?', (user_id,)).fetchall()
                        is_pw_reused = False
                        pw_bytes = new_password.encode('utf-8')
                        for u in all_existing_users:
                            try:
                                if bcrypt.checkpw(pw_bytes, u['password_hash'].encode('utf-8')):
                                    is_pw_reused = True
                                    break
                            except Exception:
                                pass
                        
                        if is_pw_reused:
                            flash('Security Policy: This password matches an existing account credential. Please choose a unique password.', 'error')
                        else:
                            pw_hash = bcrypt.hashpw(pw_bytes, bcrypt.gensalt()).decode('utf-8')
                            conn.execute(
                                'UPDATE users SET role = ?, password_hash = ? WHERE id = ?', 
                                (roles_str, pw_hash, user_id)
                            )
                            conn.commit()
                            log_audit(session['username'], 'USER_UPDATED', details=f"Updated user {target_user['username']} roles to {roles_str} and reset password")
                            flash(f'User "{target_user["username"]}" updated successfully (roles & password).', 'success')
                            
                            # If updating current session user
                            if int(user_id) == session.get('user_id'):
                                session['role'] = roles_str
                    else:
                        conn.execute('UPDATE users SET role = ? WHERE id = ?', (roles_str, user_id))
                        conn.commit()
                        log_audit(session['username'], 'USER_UPDATED', details=f"Updated user {target_user['username']} roles to {roles_str}")
                        flash(f'User "{target_user["username"]}" roles updated to: {roles_str}.', 'success')
                        
                        if int(user_id) == session.get('user_id'):
                            session['role'] = roles_str

        elif action == 'delete':
            user_id = request.form.get('user_id')
            target_user = conn.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
            
            if not target_user:
                flash('User not found.', 'error')
            elif int(user_id) == session['user_id']:
                flash('Cannot delete yourself.', 'error')
            elif target_user['username'].lower() == 'ankur':
                flash('Security Alert: The master account (Ankur) cannot be deleted by anyone.', 'error')
            else:
                conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
                conn.commit()
                log_audit(session['username'], 'USER_DELETED', details=f"Deleted user id {user_id} ({target_user['username']})")
                flash(f'User "{target_user["username"]}" deleted.', 'success')
                
    users = conn.execute('SELECT id, username, role, status, last_login, created_at FROM users ORDER BY id ASC').fetchall()
    conn.close()
    return render_template('users.html', users=users)
