with open('migrate_to_pg.py', 'r') as f:
    content = f.read()

old_create = """            ai_original_docket_number TEXT,
            ai_original_actual_weight TEXT,
            ai_original_total_packages TEXT,"""

new_create = """            invoice_no TEXT,
            invoice_value TEXT,
            
            ai_original_docket_number TEXT,
            ai_original_actual_weight TEXT,
            ai_original_total_packages TEXT,
            ai_original_invoice_no TEXT,
            ai_original_invoice_value TEXT,"""

content = content.replace(old_create, new_create)

with open('migrate_to_pg.py', 'w') as f:
    f.write(content)
print("migrate_to_pg.py updated")
