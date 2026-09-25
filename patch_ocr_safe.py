with open('ocr_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re

# Fix 1: json parsing validation
old_json_parse = """            result = json.loads(content)
            
            # Safety: force all values to strings"""
new_json_parse = """            result = json.loads(content)
            if not isinstance(result, dict):
                return None, "API did not return a JSON object (dictionary)"
            
            # Safety: force all values to strings"""

if old_json_parse in text:
    text = text.replace(old_json_parse, new_json_parse)

# Fix 2: safe choices access
old_choices = """            # Check for upstream errors
            if 'error' in result_json:
                return None, f"API error: {result_json['error']}"
            
            content = result_json['choices'][0]['message'].get('content')
            if content is None:
                finish_reason = result_json['choices'][0].get('finish_reason', 'unknown')
                return None, f"API returned no content (finish_reason: {finish_reason})\""""

new_choices = """            # Check for upstream errors
            if 'error' in result_json:
                return None, f"API error: {result_json['error']}"
            
            choices = result_json.get('choices')
            if not choices or not isinstance(choices, list) or len(choices) == 0:
                return None, f"API returned no choices: {result_json}"
                
            message = choices[0].get('message', {})
            content = message.get('content')
            if content is None:
                finish_reason = choices[0].get('finish_reason', 'unknown')
                return None, f"API returned no content (finish_reason: {finish_reason})\""""

if old_choices in text:
    text = text.replace(old_choices, new_choices)

with open('ocr_engine.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("ocr_engine.py patched for AI anomalies")
