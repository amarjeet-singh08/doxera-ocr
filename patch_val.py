import re

with open('validation_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

helpers = """    @staticmethod
    def _clean_alphanumeric(val_str):
        if val_str is None or str(val_str).strip() == "":
            return None
        val_str = str(val_str).strip()
        if 'extracted_' in val_str or 'here' in val_str or '...' in val_str:
            return None
        # Keep letters and digits
        cleaned = re.sub(r'[^a-zA-Z0-9]', '', val_str)
        return cleaned if cleaned else None

    @staticmethod
    def _clean_currency(val_str):
        if val_str is None or str(val_str).strip() == "":
            return None
        val_str = str(val_str).strip()
        if 'extracted_' in val_str or 'here' in val_str or '...' in val_str:
            return None
        # Remove anything that isn't digit or dot
        cleaned = re.sub(r'[^0-9.]', '', val_str)
        try:
            return float(cleaned)
        except ValueError:
            return None

"""
# Find _clean_number and insert before it
text = text.replace("    def _clean_number(val_str):", helpers + "    def _clean_number(val_str):")

# Add parse block in validate_docket
parse_block = """
        # ==============================================================================
        # 5. INVOICE NO
        # ==============================================================================
        inv_no_field = ocr_data.get('invoice_no', {})
        if ValidationEngine._is_field_unreadable(inv_no_field):
            review_reasons.append("Invoice No is UNREADABLE or missing")
        elif ValidationEngine._is_field_uncertain(inv_no_field):
            review_reasons.append(f"Invoice No has uncertain confidence ({inv_no_field.get('confidence')})")
        
        inv_no_str = inv_no_field.get('value') if isinstance(inv_no_field, dict) else None
        parsed_data['invoice_no'] = ValidationEngine._clean_alphanumeric(inv_no_str)
        parsed_data['ai_original_invoice_no'] = inv_no_str
        
        # ==============================================================================
        # 6. INVOICE VALUE
        # ==============================================================================
        inv_val_field = ocr_data.get('invoice_value', {})
        if ValidationEngine._is_field_unreadable(inv_val_field):
            review_reasons.append("Invoice Value is UNREADABLE or missing")
        elif ValidationEngine._is_field_uncertain(inv_val_field):
            review_reasons.append(f"Invoice Value has uncertain confidence ({inv_val_field.get('confidence')})")
        
        inv_val_str = inv_val_field.get('value') if isinstance(inv_val_field, dict) else None
        parsed_data['invoice_value'] = ValidationEngine._clean_currency(inv_val_str)
        parsed_data['ai_original_invoice_value'] = inv_val_str
        
"""

# Insert before '6. PACKAGE COUNT MATCH'
target = "        # 6. PACKAGE COUNT MATCH"
text = text.replace(target, parse_block + "        # 7. PACKAGE COUNT MATCH")

# Update parsed_data initialization
init_target = """        parsed_data = {
            'docket_number': None,
            'actual_weight': None,
            'total_packages': None,
            'dimensions': [],
            'rejection_reasons': '[]',
        }"""
init_new = """        parsed_data = {
            'docket_number': None,
            'actual_weight': None,
            'total_packages': None,
            'invoice_no': None,
            'invoice_value': None,
            'ai_original_invoice_no': None,
            'ai_original_invoice_value': None,
            'dimensions': [],
            'rejection_reasons': '[]',
        }"""
text = text.replace(init_target, init_new)

# Add import re at the top
if 'import re' not in text:
    text = "import re\n" + text

with open('validation_engine.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("validation_engine.py updated")
