with open('routes_ops.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_jobs = 'jobs = conn.execute("SELECT * FROM processing_jobs ORDER BY created_at DESC LIMIT 3").fetchall()'

new_jobs = """# Pipeline Jobs: Admin sees all, others see only their own
    if session.get('role') == 'ADMIN':
        jobs = conn.execute("SELECT * FROM processing_jobs ORDER BY created_at DESC LIMIT 5").fetchall()
    else:
        jobs = conn.execute("SELECT * FROM processing_jobs WHERE created_by = ? ORDER BY created_at DESC LIMIT 5", (session['username'],)).fetchall()"""

text = text.replace(old_jobs, new_jobs)

with open('routes_ops.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Processing jobs privacy patched")
