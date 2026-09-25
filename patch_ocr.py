with open('ocr_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

target_json = """{
  "docket_number": {"value": "...", "confidence": "HIGH|MEDIUM|LOW|UNREADABLE"},
  "actual_weight": {"value": "...", "confidence": "HIGH|MEDIUM|LOW|UNREADABLE"},
  "total_packages": {"value": "...", "confidence": "HIGH|MEDIUM|LOW|UNREADABLE"},
  "dimension_groups": ["""

new_json = """{
  "docket_number": {"value": "...", "confidence": "HIGH|MEDIUM|LOW|UNREADABLE"},
  "actual_weight": {"value": "...", "confidence": "HIGH|MEDIUM|LOW|UNREADABLE"},
  "total_packages": {"value": "...", "confidence": "HIGH|MEDIUM|LOW|UNREADABLE"},
  "invoice_no": {"value": "...", "confidence": "HIGH|MEDIUM|LOW|UNREADABLE"},
  "invoice_value": {"value": "...", "confidence": "HIGH|MEDIUM|LOW|UNREADABLE"},
  "dimension_groups": ["""

if target_json in text:
    text = text.replace(target_json, new_json)
    print("JSON replaced successfully!")
else:
    print("Failed to find target JSON")

with open('ocr_engine.py', 'w', encoding='utf-8') as f:
    f.write(text)
