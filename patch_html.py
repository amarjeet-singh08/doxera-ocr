with open('templates/docket_detail.html', 'r', encoding='utf-8') as f:
    text = f.read()

old_fields = """                    {{ field_editor('Docket Number', 'docket_number', docket.docket_number) }}
                    {{ field_editor('Actual Weight (kg)', 'actual_weight', docket.actual_weight, 'number') }}
                    {{ field_editor('Total Packages', 'total_packages', docket.total_packages, 'number') }}"""

new_fields = """                    {{ field_editor('Docket Number', 'docket_number', docket.docket_number) }}
                    {{ field_editor('Invoice No.', 'invoice_no', docket.invoice_no) }}
                    {{ field_editor('Invoice Value', 'invoice_value', docket.invoice_value, 'number') }}
                    {{ field_editor('Actual Weight (kg)', 'actual_weight', docket.actual_weight, 'number') }}
                    {{ field_editor('Total Packages', 'total_packages', docket.total_packages, 'number') }}"""

text = text.replace(old_fields, new_fields)

with open('templates/docket_detail.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("docket_detail.html updated")
