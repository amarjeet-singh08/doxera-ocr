import re
with open('templates/exports.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Make all date inputs required
text = text.replace('<input type="date"', '<input type="date" required')

# To fix alignment, make the card body a flex column that stretches, and push the form down.
text = text.replace('<div class="p-6">', '<div class="p-6 flex flex-col h-full">')
text = text.replace('<form action', '<form class="space-y-4 mt-auto" action')

# Wait, if we change `<div class="p-6 flex flex-col h-full">`, we need the parent div to be h-full too
text = text.replace('<div class="bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden">', '<div class="bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden flex flex-col h-full">')

# Wait, the parent `grid` uses `gap-6`, which stretches children.
# But let me be careful.

# Let's also remove `class="space-y-4"` from `<form action="{{ url_for('ops.do_export_verified') }}" method="GET" class="space-y-4">` because we replace it.
text = re.sub(r'<form action="(.*?)" method="GET" class="space-y-4">', r'<form action="\1" method="GET" class="space-y-4 mt-auto">', text)

with open('templates/exports.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("exports.html UI patched")
