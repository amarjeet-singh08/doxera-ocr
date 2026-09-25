import re

with open('templates/dockets.html', 'r', encoding='utf-8') as f:
    text = f.read()

old_tr = '<tr class="hover:bg-slate-50 transition-colors">'
new_tr = '<tr class="hover:bg-slate-50 transition-colors {% if search_query and search_query == d.docket_number %}bg-amber-100 ring-2 ring-amber-300{% endif %}">'

text = text.replace(old_tr, new_tr)

with open('templates/dockets.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("dockets.html highlighted")
