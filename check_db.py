from config import Config
import sqlite3

conn = sqlite3.connect(Config.DB_PATH)
conn.row_factory = sqlite3.Row
dockets = conn.execute('SELECT id, status, docket_number, actual_weight, total_packages FROM dockets ORDER BY uploaded_at DESC LIMIT 5').fetchall()
for d in dockets:
    print(f"ID: {d['id']}, Status: {d['status']}, Number: {d['docket_number']}, Weight: {d['actual_weight']}, Pkgs: {d['total_packages']}")
    dims = conn.execute('SELECT * FROM dimension_groups WHERE docket_id = ?', (d['id'],)).fetchall()
    print('  Dims:', len(dims))
