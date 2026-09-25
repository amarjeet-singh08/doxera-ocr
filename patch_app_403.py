with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

errorhandler_code = """
@app.errorhandler(403)
def forbidden_error(error):
    from flask import render_template
    return render_template('403.html'), 403
"""

if "@app.errorhandler(403)" not in text:
    text = text.replace("if __name__ == '__main__':", errorhandler_code + "\nif __name__ == '__main__':")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("app.py patched for 403 handler")
