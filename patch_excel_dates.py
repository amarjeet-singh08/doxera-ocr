with open('excel_exporter.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_format = """def format_db_date(value):
    if not value:
        return value
    try:
        from datetime import timezone, timedelta
        # Check if the string matches SQLite timestamp format
        if len(value) == 19 and value[10] == ' ':
            dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            dt = dt.replace(tzinfo=timezone.utc)
            ist = timezone(timedelta(hours=5, minutes=30))
            return dt.astimezone(ist).strftime('%Y-%m-%d %I:%M %p')
        return value
    except Exception:
        return value"""

new_format_funcs = """def format_db_datetime(value):
    if not value:
        return ""
    try:
        from datetime import datetime, timedelta, timezone
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
    except Exception:
        pass
    return str(value)[:19] if value else ""

def format_db_dateonly(value):
    dt_str = format_db_datetime(value)
    return dt_str[:10] if dt_str else ""
"""

if old_format in text:
    text = text.replace(old_format, new_format_funcs)
else:
    print("WARNING: format_db_date not found!")

import re
text = re.sub(
    r"date_only = d\['uploaded_at'\].strftime\('%Y-%m-%d'\) if hasattr\(d\['uploaded_at'\], 'strftime'\) else str\(d\['uploaded_at'\]\)\[:10\] if d\['uploaded_at'\] else ''",
    r"date_only = format_db_dateonly(d['uploaded_at'])",
    text
)

text = text.replace('format_db_date(', 'format_db_datetime(')

with open('excel_exporter.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("excel_exporter dates patched!")
