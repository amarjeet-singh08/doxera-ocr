with open('routes_ops.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Fix Dashboard
text = text.replace(
    'today = conn.execute("SELECT COUNT(*) FROM dockets WHERE uploaded_by = ? AND uploaded_at >= ?", (session[\'username\'], today_start,)).fetchone()[0]',
    'today = conn.execute("SELECT COUNT(*) FROM dockets WHERE uploaded_at >= ?", (today_start,)).fetchone()[0]'
)
text = text.replace(
    'processing = conn.execute("SELECT COUNT(*) FROM dockets WHERE uploaded_by = ? AND status IN (\'PROCESSING\', \'UPLOADED\')", (session[\'username\'],)).fetchone()[0]',
    'processing = conn.execute("SELECT COUNT(*) FROM dockets WHERE status IN (\'PROCESSING\', \'UPLOADED\')").fetchone()[0]'
)
text = text.replace(
    'verified = conn.execute("SELECT COUNT(*) FROM dockets WHERE uploaded_by = ? AND status = \'VERIFIED\'", (session[\'username\'],)).fetchone()[0]',
    'verified = conn.execute("SELECT COUNT(*) FROM dockets WHERE status = \'VERIFIED\'").fetchone()[0]'
)
text = text.replace(
    'review = conn.execute("SELECT COUNT(*) FROM dockets WHERE uploaded_by = ? AND (status = \'REVIEW_REQUIRED\' OR status = \'MODIFIED_REVERIFICATION_REQUIRED\')", (session[\'username\'],)).fetchone()[0]',
    'review = conn.execute("SELECT COUNT(*) FROM dockets WHERE (status = \'REVIEW_REQUIRED\' OR status = \'MODIFIED_REVERIFICATION_REQUIRED\')").fetchone()[0]'
)
text = text.replace(
    'rejected = conn.execute("SELECT COUNT(*) FROM dockets WHERE uploaded_by = ? AND status = \'REJECTED\'", (session[\'username\'],)).fetchone()[0]',
    'rejected = conn.execute("SELECT COUNT(*) FROM dockets WHERE status = \'REJECTED\'").fetchone()[0]'
)
text = text.replace(
    'failed = conn.execute("SELECT COUNT(*) FROM dockets WHERE uploaded_by = ? AND status = \'FAILED\'", (session[\'username\'],)).fetchone()[0]',
    'failed = conn.execute("SELECT COUNT(*) FROM dockets WHERE status = \'FAILED\'").fetchone()[0]'
)
text = text.replace(
    'jobs = conn.execute("SELECT * FROM processing_jobs WHERE created_by = ? ORDER BY created_at DESC LIMIT 3", (session[\'username\'],)).fetchall()',
    'jobs = conn.execute("SELECT * FROM processing_jobs ORDER BY created_at DESC LIMIT 3").fetchall()'
)
text = text.replace(
    'dockets = conn.execute("SELECT * FROM dockets WHERE uploaded_by = ? AND is_archived = 0 ORDER BY uploaded_at DESC LIMIT 10", (session[\'username\'],)).fetchall()',
    'dockets = conn.execute("SELECT * FROM dockets WHERE is_archived = 0 ORDER BY uploaded_at DESC LIMIT 10").fetchall()'
)

# 2. Fix dockets() search
old_dockets = """@ops_bp.route('/dockets')
@login_required
def dockets():
    status_filter = request.args.get('status', 'ALL')
    conn = get_db_connection()
    
    query = "SELECT * FROM dockets WHERE uploaded_by = ? AND is_archived = 0 "
    params = [session['username']]
    if status_filter != 'ALL':
        if status_filter == 'REVIEW':
            query += " AND (status = 'REVIEW_REQUIRED' OR status = 'MODIFIED_REVERIFICATION_REQUIRED')"
        else:
            query += " AND status = ?"
            params.append(status_filter)
            
    query += " ORDER BY uploaded_at DESC LIMIT 100"
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return render_template('dockets.html', dockets=rows, current_filter=status_filter)"""

new_dockets = """@ops_bp.route('/dockets')
@login_required
def dockets():
    status_filter = request.args.get('status', 'ALL')
    search_query = request.args.get('search', '').strip()
    conn = get_db_connection()
    
    query = "SELECT * FROM dockets WHERE is_archived = 0"
    params = []
    
    if search_query:
        query += " AND docket_number = ?"
        params.append(search_query)
        
    if status_filter != 'ALL':
        if status_filter == 'REVIEW':
            query += " AND (status = 'REVIEW_REQUIRED' OR status = 'MODIFIED_REVERIFICATION_REQUIRED')"
        else:
            query += " AND status = ?"
            params.append(status_filter)
            
    query += " ORDER BY uploaded_at DESC LIMIT 100"
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return render_template('dockets.html', dockets=rows, current_filter=status_filter, search_query=search_query)"""
text = text.replace(old_dockets, new_dockets)

# 3. Fix review_center
text = text.replace(
    'rows = conn.execute("SELECT * FROM dockets WHERE uploaded_by = ? AND is_archived = 0 AND (status = \'REVIEW_REQUIRED\' OR status = \'MODIFIED_REVERIFICATION_REQUIRED\') ORDER BY uploaded_at ASC", (session[\'username\'],)).fetchall()',
    'rows = conn.execute("SELECT * FROM dockets WHERE is_archived = 0 AND (status = \'REVIEW_REQUIRED\' OR status = \'MODIFIED_REVERIFICATION_REQUIRED\') ORDER BY uploaded_at ASC").fetchall()'
)

# 4. Fix docket_detail
text = text.replace(
    'docket = conn.execute(\'SELECT * FROM dockets WHERE id = ? AND uploaded_by = ?\', (docket_id, session[\'username\'])).fetchone()',
    'docket = conn.execute(\'SELECT * FROM dockets WHERE id = ?\', (docket_id,)).fetchone()'
)

# 5. Fix edit_all
# (Replaced by the same text replacement above since it's the exact same query)

# 6. Fix delete_all_dockets
old_delete_all = """    if status == 'ALL':
        dockets = conn.execute('SELECT id FROM dockets WHERE uploaded_by = ?', (session['username'],)).fetchall()
    elif status == 'REVIEW':
        dockets = conn.execute("SELECT id FROM dockets WHERE uploaded_by = ? AND status IN ('REVIEW_REQUIRED', 'MODIFIED_REVERIFICATION_REQUIRED')", (session['username'],)).fetchall()
    else:
        dockets = conn.execute('SELECT id FROM dockets WHERE uploaded_by = ? AND status = ?', (session['username'], status)).fetchall()"""

new_delete_all = """    if status == 'ALL':
        dockets = conn.execute('SELECT id FROM dockets').fetchall()
    elif status == 'REVIEW':
        dockets = conn.execute("SELECT id FROM dockets WHERE status IN ('REVIEW_REQUIRED', 'MODIFIED_REVERIFICATION_REQUIRED')").fetchall()
    else:
        dockets = conn.execute('SELECT id FROM dockets WHERE status = ?', (status,)).fetchall()"""
text = text.replace(old_delete_all, new_delete_all)

# 7. Fix exports
text = text.replace(
    "filename = ExcelExporter.export_verified(start_date, end_date, session['username'])",
    "filename = ExcelExporter.export_verified(start_date, end_date)"
)
text = text.replace(
    "filename = ExcelExporter.export_rejected(start_date, end_date, session['username'])",
    "filename = ExcelExporter.export_rejected(start_date, end_date)"
)

with open('routes_ops.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("routes_ops.py fully restored and carefully patched")
