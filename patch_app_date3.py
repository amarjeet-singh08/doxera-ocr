with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_block = """def format_datetime(value):
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
        return value
    except Exception:
        return value"""

new_block = """def format_datetime(value):
    if not value:
        return value
    try:
        from datetime import datetime, timedelta, timezone
        
        # Handle datetime objects directly
        if hasattr(value, 'strftime'):
            dt = value
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            ist = timezone(timedelta(hours=5, minutes=30))
            return dt.astimezone(ist).strftime('%Y-%m-%d %I:%M %p')
            
        value_str = str(value)
        if len(value_str) >= 19 and value_str[10] in (' ', 'T'):
            clean_val = value_str[:19].replace('T', ' ')
            dt = datetime.strptime(clean_val, '%Y-%m-%d %H:%M:%S')
            dt = dt.replace(tzinfo=timezone.utc)
            ist = timezone(timedelta(hours=5, minutes=30))
            return dt.astimezone(ist).strftime('%Y-%m-%d %I:%M %p')
        return value_str[:19] if value_str else value_str
    except Exception:
        return str(value)[:19] if value else value"""

if old_block in text:
    text = text.replace(old_block, new_block)
else:
    print("WARNING: Exact block not found!")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("app.py format_datetime cleanly patched")
