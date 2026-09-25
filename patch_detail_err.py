with open('templates/docket_detail.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
old_html = """            <div class="p-4">
                <p class="text-sm text-red-700 font-mono break-all whitespace-pre-wrap">{{ docket.rejection_reasons }}</p>
            </div>"""

new_html = """            <div class="p-4">
                {% if docket.status == 'FAILED' and session.role != 'ADMIN' %}
                <p class="text-sm text-red-700 font-medium whitespace-pre-wrap">The system encountered an error while processing this docket. Please notify an administrator.</p>
                {% else %}
                <p class="text-sm text-red-700 font-mono break-all whitespace-pre-wrap">{{ docket.rejection_reasons }}</p>
                {% endif %}
            </div>"""

if old_html in text:
    text = text.replace(old_html, new_html)
else:
    print("WARNING: docket_detail.html error box not found!")

with open('templates/docket_detail.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("docket_detail.html patched")
