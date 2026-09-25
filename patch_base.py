with open('templates/base.html', 'r', encoding='utf-8') as f:
    text = f.read()

old_upload = """                    <a href="{{ url_for('ops.upload') }}" class="sidebar-link {% if request.endpoint == 'ops.upload' %}active{% endif %}">
                        <i data-lucide="upload-cloud" class="sidebar-icon"></i> Upload Dockets
                    </a>"""
new_upload = """                    <a href="{{ url_for('ops.upload') }}" class="sidebar-link {% if request.endpoint == 'ops.upload' %}active{% endif %} {% if session.get('role') == 'VIEWER' %}opacity-50 cursor-not-allowed pointer-events-none{% endif %}">
                        <i data-lucide="upload-cloud" class="sidebar-icon"></i> Upload Dockets
                    </a>"""
text = text.replace(old_upload, new_upload)

with open('templates/base.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("base.html patched")
