with open('routes_ops.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update the process_docket_async UPDATE query
old_update = """                    SET docket_number = ?, actual_weight = ?, total_packages = ?, 
                        ai_original_docket_number = ?, ai_original_actual_weight = ?, ai_original_total_packages = ?,"""

new_update = """                    SET docket_number = ?, actual_weight = ?, total_packages = ?, invoice_no = ?, invoice_value = ?,
                        ai_original_docket_number = ?, ai_original_actual_weight = ?, ai_original_total_packages = ?, ai_original_invoice_no = ?, ai_original_invoice_value = ?,"""

text = text.replace(old_update, new_update)

old_update_args = """                    docket_num, 
                    parsed_data.get('actual_weight'), 
                    parsed_data.get('total_packages'),
                    str(parsed_data.get('docket_number')) if parsed_data.get('docket_number') is not None else None,
                    str(parsed_data.get('actual_weight')) if parsed_data.get('actual_weight') is not None else None,
                    str(parsed_data.get('total_packages')) if parsed_data.get('total_packages') is not None else None,"""

new_update_args = """                    docket_num, 
                    parsed_data.get('actual_weight'), 
                    parsed_data.get('total_packages'),
                    parsed_data.get('invoice_no'),
                    parsed_data.get('invoice_value'),
                    str(parsed_data.get('docket_number')) if parsed_data.get('docket_number') is not None else None,
                    str(parsed_data.get('actual_weight')) if parsed_data.get('actual_weight') is not None else None,
                    str(parsed_data.get('total_packages')) if parsed_data.get('total_packages') is not None else None,
                    str(parsed_data.get('ai_original_invoice_no')) if parsed_data.get('ai_original_invoice_no') is not None else None,
                    str(parsed_data.get('ai_original_invoice_value')) if parsed_data.get('ai_original_invoice_value') is not None else None,"""

text = text.replace(old_update_args, new_update_args)

# 2. Update ops_docket_action fields
old_fields = "        for field in ['docket_number', 'actual_weight', 'total_packages']:"
new_fields = "        for field in ['docket_number', 'actual_weight', 'total_packages', 'invoice_no', 'invoice_value']:"
text = text.replace(old_fields, new_fields)

with open('routes_ops.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("routes_ops.py updated")
