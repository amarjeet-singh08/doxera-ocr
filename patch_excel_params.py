with open('excel_exporter.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re

# Insert params = [] in export_all
text = re.sub(
    r'(query = "SELECT \* FROM dockets WHERE is_archived = 0"\s+)if start_date:',
    r'\1params = []\n        if start_date:',
    text
)

with open('excel_exporter.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("params = [] added to export_all")
