with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

quota_logic = """
_quota_cache = {'remaining': 50, 'last_checked': 0}

def get_openrouter_quota():
    import time, requests
    from config import Config
    global _quota_cache
    
    # Cache for 60 seconds to avoid spamming OpenRouter API on every page load
    if time.time() - _quota_cache['last_checked'] > 60:
        try:
            headers = {'Authorization': f'Bearer {Config.ROUTER_API_KEY}'}
            res = requests.get('https://openrouter.ai/api/v1/auth/key', headers=headers, timeout=5)
            if res.status_code == 200:
                data = res.json().get('data', {})
                free_reqs = data.get('free_model_daily_requests')
                if free_reqs and 'remaining' in free_reqs:
                    _quota_cache['remaining'] = free_reqs['remaining']
            _quota_cache['last_checked'] = time.time()
        except Exception:
            pass
            
    return _quota_cache['remaining']
"""

if "_quota_cache = {" not in text:
    text = text.replace("def create_app():", quota_logic + "\ndef create_app():")

import re

old_logic = """        # Calculate rate limit remaining (assume 50 limit per day)
        today_count = conn.execute("SELECT COUNT(*) FROM audit_log WHERE action = 'UPLOADED' AND timestamp >= ?", (today_start,)).fetchone()[0]
        rate_limit_left = max(0, 50 - today_count)"""

new_logic = """        # Calculate rate limit remaining using OpenRouter actual API limit
        rate_limit_left = get_openrouter_quota()"""

if old_logic in text:
    text = text.replace(old_logic, new_logic)
else:
    print("WARNING: Could not replace logic")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("app.py live quota patched successfully")
