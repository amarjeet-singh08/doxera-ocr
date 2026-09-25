with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

handler_500 = """
@app.errorhandler(500)
def internal_error(error):
    from flask import render_template
    return render_template('500.html'), 500
"""

if "@app.errorhandler(500)" not in text:
    text = text.replace("@app.errorhandler(403)", handler_500 + "\n@app.errorhandler(403)")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("app.py patched for 500 handler")
