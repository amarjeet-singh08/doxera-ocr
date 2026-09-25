import re

with open('routes_ops.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update dashboard queries
text = re.sub(r'WHERE uploaded_by = \? AND ', r'WHERE ', text)
text = re.sub(r'WHERE id = \? AND uploaded_by = \?', r'WHERE id = ?', text)
text = re.sub(r"WHERE uploaded_by = \?'", r"'", text)

# Remove the session['username'] from params of these queries
# Dashboard
text = re.sub(r'\(session\[\'username\'\],\s*(.*?)\)', r'(\1)', text)
# Where session['username'] was the ONLY parameter
text = re.sub(r'\(session\[\'username\'\],\)', r'()', text)
# Where session['username'] is the second parameter (id = ? AND uploaded_by = ?)
text = re.sub(r'\(docket_id,\s*session\[\'username\'\]\)', r'(docket_id,)', text)

# For query = "SELECT * FROM dockets WHERE uploaded_by = ? AND is_archived = 0 "
text = re.sub(r'query = "SELECT \* FROM dockets WHERE uploaded_by = \? AND is_archived = 0 "\s*params = \[session\[\'username\'\]\]', 
              'query = "SELECT * FROM dockets WHERE is_archived = 0 "\n    params = []', text)

# 2. Fix the export route calling (remove session['username'] argument)
text = re.sub(r'filename = ExcelExporter\.export_verified\(start_date, end_date, session\[\'username\'\]\)', 
              'filename = ExcelExporter.export_verified(start_date, end_date)', text)
text = re.sub(r'filename = ExcelExporter\.export_rejected\(start_date, end_date, session\[\'username\'\]\)', 
              'filename = ExcelExporter.export_rejected(start_date, end_date)', text)

with open('routes_ops.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("routes_ops.py stripped of user isolation")
