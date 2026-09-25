with open('excel_exporter.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix the datetime slicing issue
text = text.replace(
    "date_only = d['uploaded_at'][:10] if d['uploaded_at'] else ''",
    "date_only = d['uploaded_at'].strftime('%Y-%m-%d') if hasattr(d['uploaded_at'], 'strftime') else str(d['uploaded_at'])[:10] if d['uploaded_at'] else ''"
)

with open('excel_exporter.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Excel exporter patched for datetime issue")
