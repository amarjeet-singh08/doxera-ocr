with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    "# Calculate rate limit remaining (assume 200 free tier limit per day)\n        today_count = conn.execute(\"SELECT COUNT(*) FROM dockets WHERE uploaded_at >= ?\", (today_start,)).fetchone()[0]\n        rate_limit_left = max(0, 200 - today_count)",
    "# Calculate rate limit remaining (assume 50 limit per day)\n        today_count = conn.execute(\"SELECT COUNT(*) FROM dockets WHERE uploaded_at >= ?\", (today_start,)).fetchone()[0]\n        rate_limit_left = max(0, 50 - today_count)"
)
text = text.replace("max(0, 200 - today_count)", "max(0, 50 - today_count)")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("app.py patched for 50 limit")
