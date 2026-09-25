import re

# 1. Update ocr_engine.py
with open('ocr_engine.py', 'r', encoding='utf-8') as f:
    ocr_text = f.read()

old_step5 = """    - Invoice numbers can be strictly alphanumeric (contain both letters and numbers, e.g., "INV12345A").
    - Do NOT confuse this with the Docket Number."""

new_step5 = """    - Invoice numbers can contain letters, numbers, and symbols like '/', '-', '+'. Extract them exactly as written.
    - WARNING: Do NOT assume or guess characters! If a slash '/' looks somewhat like a '1' or 'l' but you are not 100% sure, DO NOT GUESS. If it is ambiguous, just set confidence to "UNREADABLE" and leave the section completely blank "".
    - Do NOT confuse this with the Docket Number."""

ocr_text = ocr_text.replace(old_step5, new_step5)

old_step6 = """    - Look for fields labeled "Invoice Value", "Value", "Declared Value", or currency amounts.
    - This is often a large number (e.g., 50000, 1500.50)."""

new_step6 = """    - Look for fields labeled "Invoice Value", "Value", "Declared Value", or currency amounts.
    - This is often a large number but can also contain letters and symbols like '/', '-', '+'. Extract them exactly as written.
    - WARNING: Do NOT assume or guess characters! If ambiguous, set confidence to "UNREADABLE" and leave it blank."""

ocr_text = ocr_text.replace(old_step6, new_step6)

with open('ocr_engine.py', 'w', encoding='utf-8') as f:
    f.write(ocr_text)

# 2. Update validation_engine.py
with open('validation_engine.py', 'r', encoding='utf-8') as f:
    val_text = f.read()

# Update _clean_alphanumeric to allow symbols
val_text = re.sub(r"cleaned = re\.sub\(r'\[\^a-zA-Z0-9\]', '', val_str\)", 
                  r"cleaned = re.sub(r'[^a-zA-Z0-9/\-\+ ]', '', val_str)", val_text)

# Update _clean_currency to allow symbols and return string instead of float
old_clean_curr = """    def _clean_currency(val_str):
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
            return None"""

new_clean_curr = """    def _clean_currency(val_str):
        if val_str is None or str(val_str).strip() == "":
            return None
        val_str = str(val_str).strip()
        if 'extracted_' in val_str or 'here' in val_str or '...' in val_str:
            return None
        # Allow symbols since user requested /, -, + for invoice values
        cleaned = re.sub(r'[^a-zA-Z0-9.\/\-\+ ]', '', val_str)
        return cleaned if cleaned else None"""

val_text = val_text.replace(old_clean_curr, new_clean_curr)

with open('validation_engine.py', 'w', encoding='utf-8') as f:
    f.write(val_text)

# 3. Update docket_detail.html
with open('templates/docket_detail.html', 'r', encoding='utf-8') as f:
    html_text = f.read()

html_text = html_text.replace("field_editor('Invoice Value', 'invoice_value', docket.invoice_value, 'number')", 
                              "field_editor('Invoice Value', 'invoice_value', docket.invoice_value, 'text')")

with open('templates/docket_detail.html', 'w', encoding='utf-8') as f:
    f.write(html_text)

print("AI logic patched")
