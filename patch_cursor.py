with open('database.py', 'r') as f:
    content = f.read()

# Fix init_db
content = content.replace("c = conn.cursor()\n    \n    # Jobs\n    c.execute", "# Jobs\n    conn.execute")
content = content.replace("    c.execute('''\n        CREATE TABLE", "    conn.execute('''\n        CREATE TABLE")
content = content.replace("    c.execute('SELECT * FROM users", "    conn.execute('SELECT * FROM users")
content = content.replace('    c.execute("INSERT INTO users', '    conn.execute("INSERT INTO users')

# Fix check_duplicate_image
content = content.replace("c = conn.cursor()\n    c.execute(", "c = conn.execute(")

# Fix create_job
content = content.replace("c = conn.cursor()\n    if getattr(conn, 'is_postgres', False):\n        c.execute(", "if getattr(conn, 'is_postgres', False):\n        c = conn.execute(")
content = content.replace("    else:\n        c.execute(", "    else:\n        c = conn.execute(")

# Fix create_docket
content = content.replace("c = conn.cursor()\n    if getattr(conn, 'is_postgres', False):\n        c.execute(", "if getattr(conn, 'is_postgres', False):\n        c = conn.execute(")
content = content.replace("    else:\n        c.execute(", "    else:\n        c = conn.execute(")

# Fix log_audit
content = content.replace("c = conn.cursor()\n    c.execute(", "c = conn.execute(")

with open('database.py', 'w') as f:
    f.write(content)
