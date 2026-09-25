with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Add context processor before app.run()
context_processor = """
@app.context_processor
def inject_notifications():
    try:
        from database import get_db_connection
        from datetime import datetime
        conn = get_db_connection()
        today_start = datetime.now().strftime("%Y-%m-%d 00:00:00")
        
        pending = conn.execute("SELECT COUNT(*) FROM dockets WHERE is_archived = 0 AND status IN ('REVIEW_REQUIRED', 'MODIFIED_REVERIFICATION_REQUIRED')").fetchone()[0]
        failed = conn.execute("SELECT COUNT(*) FROM dockets WHERE is_archived = 0 AND status = 'FAILED'").fetchone()[0]
        rejected = conn.execute("SELECT COUNT(*) FROM dockets WHERE is_archived = 0 AND status = 'REJECTED'").fetchone()[0]
        
        # Calculate rate limit remaining (assume 200 free tier limit per day)
        today_count = conn.execute("SELECT COUNT(*) FROM dockets WHERE uploaded_at >= ?", (today_start,)).fetchone()[0]
        rate_limit_left = max(0, 200 - today_count)
        
        conn.close()
        return dict(
            notif_pending=pending,
            notif_failed=failed,
            notif_rejected=rejected,
            notif_limit=rate_limit_left,
            notif_total=pending + failed + rejected
        )
    except Exception as e:
        return dict(notif_total=0)
"""

if "@app.context_processor" not in text:
    text = text.replace("if __name__ == '__main__':", context_processor + "\nif __name__ == '__main__':")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("app.py patched")
