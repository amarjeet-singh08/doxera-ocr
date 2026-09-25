with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace the quota logic
old_logic = 'today_count = conn.execute("SELECT COUNT(*) FROM dockets WHERE DATE(uploaded_at) = CURRENT_DATE").fetchone()[0]'
new_logic = 'today_count = conn.execute("SELECT COUNT(*) FROM audit_log WHERE action = \'UPLOADED\' AND DATE(timestamp) = CURRENT_DATE").fetchone()[0]'

if old_logic in text:
    text = text.replace(old_logic, new_logic)
else:
    print("WARNING: Quota logic not found in app.py!")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("app.py quota logic updated")
