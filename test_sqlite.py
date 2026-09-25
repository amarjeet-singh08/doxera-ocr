import sqlite3
conn = sqlite3.connect(':memory:')
conn.execute('CREATE TABLE audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, "user" TEXT)')
conn.execute('INSERT INTO audit_log ("user") VALUES (?)', ('test',))
print(conn.execute('SELECT * FROM audit_log').fetchall())
