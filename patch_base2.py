with open('templates/base.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix AI -> Doxera and 200 -> 50
text = text.replace("AI Quota Left Today", "Doxera Quota Left Today")
text = text.replace("notif_limit|default(200)", "notif_limit|default(50)")

# Fix Review Center for Viewer
old_review = """                    <a href="{{ url_for('ops.review_center') }}" class="sidebar-link {% if request.endpoint == 'ops.review_center' %}active{% endif %}">
                        <i data-lucide="inbox" class="sidebar-icon"></i> Review Center
                    </a>"""
new_review = """                    <a href="{{ url_for('ops.review_center') }}" class="sidebar-link {% if request.endpoint == 'ops.review_center' %}active{% endif %} {% if session.get('role') == 'VIEWER' %}opacity-50 cursor-not-allowed pointer-events-none{% endif %}">
                        <i data-lucide="inbox" class="sidebar-icon"></i> Review Center
                    </a>"""
text = text.replace(old_review, new_review)

with open('templates/base.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("base.html patched")
