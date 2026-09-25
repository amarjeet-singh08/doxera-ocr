with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re

new_func = """def format_datetime(value):
    if not value:
        return value
    try:
        from datetime import datetime, timedelta, timezone
        
        # Handle datetime objects directly (psycopg2 often returns datetime objects)
        if hasattr(value, 'strftime'):
            dt = value
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            ist = timezone(timedelta(hours=5, minutes=30))
            return dt.astimezone(ist).strftime('%Y-%m-%d %I:%M %p')
            
        # Convert string without microseconds if present
        value_str = str(value)
        if len(value_str) >= 19 and value_str[10] in (' ', 'T'):
            clean_val = value_str[:19].replace('T', ' ')
            dt = datetime.strptime(clean_val, '%Y-%m-%d %H:%M:%S')
            dt = dt.replace(tzinfo=timezone.utc)
            ist = timezone(timedelta(hours=5, minutes=30))
            return dt.astimezone(ist).strftime('%Y-%m-%d %I:%M %p')
    except Exception as e:
        pass
    return str(value)[:19] if value else value"""

# Replace the entire block
text = re.sub(r'def format_datetime\(value\):.*?    return value', new_func, text, flags=re.DOTALL)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("app.py format_datetime correctly patched")
