import re

with open('excel_exporter.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update export signatures and logic
text = re.sub(r'def export_verified\(start_date=None, end_date=None, username=None\):', r'def export_verified(start_date=None, end_date=None):', text)
text = re.sub(r'def export_rejected\(start_date=None, end_date=None, username=None\):', r'def export_rejected(start_date=None, end_date=None):', text)

text = re.sub(r'\s*if username:\s*query \+= " AND uploaded_by = \?"\s*params\.append\(username\)', '', text)

# 2. Update columns inside export_verified
old_verified_cols = "        all_cols = ['Docket No', 'Actual Weight', 'Total Packages']"
new_verified_cols = "        all_cols = ['S.No', 'Date', 'Docket No', 'Invoice No', 'Invoice Value', 'Actual Weight', 'Total Packages']"
text = text.replace(old_verified_cols, new_verified_cols)

# Update row population in export_verified
old_verified_row = """        export_data = []
        for d in dockets:
            row = {
                'Docket No': d['docket_number'],
                'Invoice No': d['invoice_no'],
                'Invoice Value': d['invoice_value'],
                'Actual Weight': d['actual_weight'],
                'Total Packages': d['total_packages']
            }"""
new_verified_row = """        export_data = []
        for i, d in enumerate(dockets, 1):
            date_only = d['uploaded_at'][:10] if d['uploaded_at'] else ''
            row = {
                'S.No': i,
                'Date': date_only,
                'Docket No': d['docket_number'],
                'Invoice No': d['invoice_no'],
                'Invoice Value': d['invoice_value'],
                'Actual Weight': d['actual_weight'],
                'Total Packages': d['total_packages']
            }"""
text = text.replace(old_verified_row, new_verified_row)

# 3. Update columns inside export_rejected
old_rejected_cols = "        all_cols = ['Docket No', 'Actual Weight', 'Total Packages']"
new_rejected_cols = "        all_cols = ['S.No', 'Date', 'Docket No', 'Invoice No', 'Invoice Value', 'Actual Weight', 'Total Packages']"
text = text.replace(old_rejected_cols, new_rejected_cols)

old_rejected_row = """        export_data = []
        for d in dockets:
            row = {
                'Docket No': d['docket_number'] or '[Not Found]',
                'Invoice No': d['invoice_no'],
                'Invoice Value': d['invoice_value'],
                'Actual Weight': d['actual_weight'],
                'Total Packages': d['total_packages']
            }"""
new_rejected_row = """        export_data = []
        for i, d in enumerate(dockets, 1):
            date_only = d['uploaded_at'][:10] if d['uploaded_at'] else ''
            row = {
                'S.No': i,
                'Date': date_only,
                'Docket No': d['docket_number'] or '[Not Found]',
                'Invoice No': d['invoice_no'],
                'Invoice Value': d['invoice_value'],
                'Actual Weight': d['actual_weight'],
                'Total Packages': d['total_packages']
            }"""
text = text.replace(old_rejected_row, new_rejected_row)

with open('excel_exporter.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("excel_exporter.py patched")
