with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix format_datetime to handle microseconds from PostgreSQL
old_func = """def format_datetime(value):
    if not value:
        return value
    try:
        from datetime import datetime, timedelta, timezone
        # Check if the string matches SQLite timestamp format
        if len(value) == 19 and value[10] == ' ':
            dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            dt = dt.replace(tzinfo=timezone.utc)
            ist = timezone(timedelta(hours=5, minutes=30))
            return dt.astimezone(ist).strftime('%Y-%m-%d %I:%M %p')
    except:
        pass
    return value"""

new_func = """def format_datetime(value):
    if not value:
        return value
    try:
        from datetime import datetime, timedelta, timezone
        
        # Handle datetime objects directly (Postycopg2 often returns datetime objects)
        if hasattr(value, 'strftime'):
            dt = value
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            ist = timezone(timedelta(hours=5, minutes=30))
            return dt.astimezone(ist).strftime('%Y-%m-%d %I:%M %p')
            
        # Convert string to string without microseconds if present
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

if old_func in text:
    text = text.replace(old_func, new_func)
else:
    print("Could not find old format_datetime string exactly as expected. I will use regex.")
    import re
    text = re.sub(r'def format_datetime\(value\):.*?return value', new_func, text, flags=re.DOTALL)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("app.py format_datetime patched")
