with open('excel_exporter.py', 'r', encoding='utf-8') as f:
    text = f.read()

helper = """
def ist_to_utc_str(date_str, is_end_of_day=False):
    try:
        from datetime import datetime, timedelta, timezone
        time_str = "23:59:59" if is_end_of_day else "00:00:00"
        ist = timezone(timedelta(hours=5, minutes=30))
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
        dt = dt.replace(tzinfo=ist)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return f"{date_str} 23:59:59" if is_end_of_day else f"{date_str} 00:00:00"

class ExcelExporter:
"""

text = text.replace("class ExcelExporter:", helper)

import re

# We need to replace in all three functions
text = re.sub(
    r'params\.append\(f"\{start_date\} 00:00:00"\)',
    r'params.append(ist_to_utc_str(start_date, False))',
    text
)
text = re.sub(
    r'params\.append\(f"\{end_date\} 23:59:59"\)',
    r'params.append(ist_to_utc_str(end_date, True))',
    text
)

with open('excel_exporter.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("excel_exporter timezone queries patched")
