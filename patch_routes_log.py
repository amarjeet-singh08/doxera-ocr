with open('routes_ops.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace("log_audit('EXPORTED', details=f\"Generated All Dockets Excel: {filename}\")", "log_audit(session['username'], 'EXPORTED', details=f\"Generated All Dockets Excel: {filename}\")")

with open('routes_ops.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("routes_ops.py log_audit fixed")
