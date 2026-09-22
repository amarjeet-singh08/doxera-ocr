import re

with open('routes_ops.py', 'r') as f:
    content = f.read()

# dashboard
content = content.replace(
    'today = conn.execute("SELECT COUNT(*) FROM dockets WHERE uploaded_at >= ?", (today_start,)).fetchone()[0]',
    'today = conn.execute("SELECT COUNT(*) FROM dockets WHERE uploaded_by = ? AND uploaded_at >= ?", (session[\'username\'], today_start,)).fetchone()[0]'
)
content = content.replace(
    'processing = conn.execute("SELECT COUNT(*) FROM dockets WHERE status IN (\'PROCESSING\', \'UPLOADED\')").fetchone()[0]',
    'processing = conn.execute("SELECT COUNT(*) FROM dockets WHERE uploaded_by = ? AND status IN (\'PROCESSING\', \'UPLOADED\')", (session[\'username\'],)).fetchone()[0]'
)
content = content.replace(
    'verified = conn.execute("SELECT COUNT(*) FROM dockets WHERE status = \'VERIFIED\'").fetchone()[0]',
    'verified = conn.execute("SELECT COUNT(*) FROM dockets WHERE uploaded_by = ? AND status = \'VERIFIED\'", (session[\'username\'],)).fetchone()[0]'
)
content = content.replace(
    'review = conn.execute("SELECT COUNT(*) FROM dockets WHERE status = \'REVIEW_REQUIRED\' OR status = \'MODIFIED_REVERIFICATION_REQUIRED\'").fetchone()[0]',
    'review = conn.execute("SELECT COUNT(*) FROM dockets WHERE uploaded_by = ? AND (status = \'REVIEW_REQUIRED\' OR status = \'MODIFIED_REVERIFICATION_REQUIRED\')", (session[\'username\'],)).fetchone()[0]'
)
content = content.replace(
    'rejected = conn.execute("SELECT COUNT(*) FROM dockets WHERE status = \'REJECTED\'").fetchone()[0]',
    'rejected = conn.execute("SELECT COUNT(*) FROM dockets WHERE uploaded_by = ? AND status = \'REJECTED\'", (session[\'username\'],)).fetchone()[0]'
)
content = content.replace(
    'failed = conn.execute("SELECT COUNT(*) FROM dockets WHERE status = \'FAILED\'").fetchone()[0]',
    'failed = conn.execute("SELECT COUNT(*) FROM dockets WHERE uploaded_by = ? AND status = \'FAILED\'", (session[\'username\'],)).fetchone()[0]'
)
content = content.replace(
    'jobs = conn.execute("SELECT * FROM processing_jobs ORDER BY created_at DESC LIMIT 3").fetchall()',
    'jobs = conn.execute("SELECT * FROM processing_jobs WHERE created_by = ? ORDER BY created_at DESC LIMIT 3", (session[\'username\'],)).fetchall()'
)
content = content.replace(
    'dockets = conn.execute("SELECT * FROM dockets WHERE is_archived = 0 ORDER BY uploaded_at DESC LIMIT 10").fetchall()',
    'dockets = conn.execute("SELECT * FROM dockets WHERE uploaded_by = ? AND is_archived = 0 ORDER BY uploaded_at DESC LIMIT 10", (session[\'username\'],)).fetchall()'
)

# dockets
content = content.replace(
    'query = "SELECT * FROM dockets WHERE is_archived = 0 "',
    'query = "SELECT * FROM dockets WHERE uploaded_by = ? AND is_archived = 0 "\n    params = [session[\'username\']]'
)
content = content.replace(
    'params = []\n    \n    if status_filter',
    'if status_filter'
)

# review
content = content.replace(
    'rows = conn.execute("SELECT * FROM dockets WHERE is_archived = 0 AND (status = \'REVIEW_REQUIRED\' OR status = \'MODIFIED_REVERIFICATION_REQUIRED\') ORDER BY uploaded_at ASC").fetchall()',
    'rows = conn.execute("SELECT * FROM dockets WHERE uploaded_by = ? AND is_archived = 0 AND (status = \'REVIEW_REQUIRED\' OR status = \'MODIFIED_REVERIFICATION_REQUIRED\') ORDER BY uploaded_at ASC", (session[\'username\'],)).fetchall()'
)

# docket_detail & ops_docket_action
content = content.replace(
    "docket = conn.execute('SELECT * FROM dockets WHERE id = ?', (docket_id,)).fetchone()",
    "docket = conn.execute('SELECT * FROM dockets WHERE id = ? AND uploaded_by = ?', (docket_id, session['username'])).fetchone()"
)

# Bulk actions
content = content.replace(
    "dockets = conn.execute('SELECT id FROM dockets').fetchall()",
    "dockets = conn.execute('SELECT id FROM dockets WHERE uploaded_by = ?', (session['username'],)).fetchall()"
)
content = content.replace(
    "dockets = conn.execute(\"SELECT id FROM dockets WHERE status IN ('REVIEW_REQUIRED', 'MODIFIED_REVERIFICATION_REQUIRED')\").fetchall()",
    "dockets = conn.execute(\"SELECT id FROM dockets WHERE uploaded_by = ? AND status IN ('REVIEW_REQUIRED', 'MODIFIED_REVERIFICATION_REQUIRED')\", (session['username'],)).fetchall()"
)
content = content.replace(
    "dockets = conn.execute('SELECT id FROM dockets WHERE status = ?', (status,)).fetchall()",
    "dockets = conn.execute('SELECT id FROM dockets WHERE uploaded_by = ? AND status = ?', (session['username'], status)).fetchall()"
)

# excel exporter calls
content = content.replace(
    "filepath = ExcelExporter.export_verified(start_date, end_date)",
    "filepath = ExcelExporter.export_verified(start_date, end_date, session['username'])"
)
content = content.replace(
    "filepath = ExcelExporter.export_rejected(start_date, end_date)",
    "filepath = ExcelExporter.export_rejected(start_date, end_date, session['username'])"
)

with open('routes_ops.py', 'w') as f:
    f.write(content)

with open('excel_exporter.py', 'r') as f:
    content = f.read()

content = content.replace(
    "def export_verified(start_date=None, end_date=None):",
    "def export_verified(start_date=None, end_date=None, username=None):"
)
content = content.replace(
    "def export_rejected(start_date=None, end_date=None):",
    "def export_rejected(start_date=None, end_date=None, username=None):"
)

content = content.replace(
    "query = \"SELECT * FROM dockets WHERE status = 'VERIFIED' AND is_archived = 0\"",
    "query = \"SELECT * FROM dockets WHERE status = 'VERIFIED' AND is_archived = 0\"\n        params = []\n        if username:\n            query += \" AND uploaded_by = ?\"\n            params.append(username)"
)
content = content.replace(
    "query = \"SELECT * FROM dockets WHERE status = 'REJECTED' AND is_archived = 0\"",
    "query = \"SELECT * FROM dockets WHERE status = 'REJECTED' AND is_archived = 0\"\n        params = []\n        if username:\n            query += \" AND uploaded_by = ?\"\n            params.append(username)"
)
content = content.replace("params = []\n        if start_date:", "if start_date:")

with open('excel_exporter.py', 'w') as f:
    f.write(content)

print("Patched successfully")
