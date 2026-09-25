with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
text = re.sub(
    r'today_start = datetime\.now\(\)\.strftime\("%Y-%m-%d 00:00:00"\)',
    r'from datetime import timezone\n        today_start = datetime.now(timezone.utc).strftime("%Y-%m-%d 00:00:00")',
    text
)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("app.py UTC patched")
