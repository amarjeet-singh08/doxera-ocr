with open('excel_exporter.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_row = """            row = {
                'Docket No': d['docket_number'],
                'Actual Weight': d['actual_weight'],
                'Total Packages': d['total_packages']
            }"""

new_row = """            row = {
                'Docket No': d['docket_number'],
                'Invoice No': d['invoice_no'],
                'Invoice Value': d['invoice_value'],
                'Actual Weight': d['actual_weight'],
                'Total Packages': d['total_packages']
            }"""
text = text.replace(old_row, new_row)

old_row_rej = """            row = {
                'Docket No': d['docket_number'] or '[Not Found]',
                'Actual Weight': d['actual_weight'],
                'Total Packages': d['total_packages']
            }"""

new_row_rej = """            row = {
                'Docket No': d['docket_number'] or '[Not Found]',
                'Invoice No': d['invoice_no'],
                'Invoice Value': d['invoice_value'],
                'Actual Weight': d['actual_weight'],
                'Total Packages': d['total_packages']
            }"""
text = text.replace(old_row_rej, new_row_rej)

with open('excel_exporter.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("excel_exporter.py updated")
