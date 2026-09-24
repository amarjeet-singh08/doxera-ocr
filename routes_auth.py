from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import bcrypt
from database import get_db_connection, log_audit

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('ops.dashboard'))
        
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode('utf-8')
        
        conn = get_db_connection()
        try:
            user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
            
            if user and user['status'] == 'ACTIVE' and bcrypt.checkpw(password, user['password_hash'].encode('utf-8')):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                
                conn.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user['id'],))
                conn.commit()
                log_audit(username, 'LOGIN', details='User logged in successfully')
                
                return redirect(url_for('ops.dashboard'))
            else:
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
            username = request.form['username']
            password = request.form['password']
            role = request.form['role']
            pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            try:
                conn.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)', (username, pw_hash, role))
                conn.commit()
                log_audit(session['username'], 'USER_CREATED', details=f"Created user {username} with role {role}")
                flash(f'User {username} created successfully.', 'success')
            except sqlite3.IntegrityError:
                flash('Username already exists.', 'error')
        elif action == 'delete':
            user_id = request.form['user_id']
            target_user = conn.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
            
            if int(user_id) == session['user_id']:
                flash('Cannot delete yourself.', 'error')
            elif target_user and target_user['username'].lower() == 'ankur':
                flash('Security Alert: The master account (Ankur) cannot be deleted by anyone.', 'error')
            else:
                conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
                conn.commit()
                log_audit(session['username'], 'USER_DELETED', details=f"Deleted user id {user_id}")
                flash('User deleted.', 'success')
                
    users = conn.execute('SELECT id, username, role, status, last_login, created_at FROM users').fetchall()
    conn.close()
    return render_template('users.html', users=users)
