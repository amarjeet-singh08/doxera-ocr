with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_logic = 'today_count = conn.execute("SELECT COUNT(*) FROM dockets WHERE uploaded_at >= ?", (today_start,)).fetchone()[0]'
new_logic = 'today_count = conn.execute("SELECT COUNT(*) FROM audit_log WHERE action = \'UPLOADED\' AND timestamp >= ?", (today_start,)).fetchone()[0]'

text = text.replace(old_logic, new_logic)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("app.py quota logic updated with audit_log")
