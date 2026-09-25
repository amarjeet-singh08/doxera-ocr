with open('database.py', 'r') as f:
    text = f.read()

table_sql = """
    # Images (For persistent storage on Render)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS docket_images (
            filename TEXT PRIMARY KEY,
            image_base64 TEXT,
            mimetype TEXT
        )
    ''')
"""

text = text.replace("    # Dockets", table_sql + "\n    # Dockets")

with open('database.py', 'w') as f:
    f.write(text)
print("database.py updated")
