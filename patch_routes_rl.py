with open('routes_ops.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
old_check = r"rate_limited = any\('Rate limit' in str\(d\['rejection_reasons'\]\) or '429' in str\(d\['rejection_reasons'\]\) or '402' in str\(d\['rejection_reasons'\]\) for d in dockets if d\['status'\] == 'FAILED'\)"
new_check = "rate_limited = any('429' in str(d['rejection_reasons']) or '402' in str(d['rejection_reasons']) for d in dockets if d['status'] == 'FAILED')"

text = re.sub(old_check, new_check, text)

with open('routes_ops.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("routes_ops.py rate_limited check updated")
