import re

with open('templates/docket_detail.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Make the macro for field_editor respect readonly
old_macro = """                    {% macro field_editor(label, name, val, type='text') %}
                    <div class="space-y-1">
                        <label class="block text-[11px] uppercase tracking-wider text-slate-500 font-bold">{{ label }}</label>
                        <input type="{{ type }}" step="any" name="{{ name }}" value="{{ val or '' }}" {% if not val %}placeholder="Missing"{% endif %}
                               class="block w-full px-3 py-1.5 rounded-md border border-slate-300 text-sm focus:ring-1 focus:ring-nexpress-blue focus:border-nexpress-blue {% if not val %}bg-amber-50 border-amber-300 placeholder-amber-400{% endif %}">
                    </div>
                    {% endmacro %}"""

new_macro = """                    {% macro field_editor(label, name, val, type='text') %}
                    <div class="space-y-1">
                        <label class="block text-[11px] uppercase tracking-wider text-slate-500 font-bold">{{ label }}</label>
                        <input type="{{ type }}" step="any" name="{{ name }}" value="{{ val or '' }}" {% if not val %}placeholder="Missing"{% endif %}
                               class="block w-full px-3 py-1.5 rounded-md border border-slate-300 text-sm focus:ring-1 focus:ring-nexpress-blue focus:border-nexpress-blue {% if not val %}bg-amber-50 border-amber-300 placeholder-amber-400{% endif %}" {% if session.get('role') == 'VIEWER' %}readonly{% endif %}>
                    </div>
                    {% endmacro %}"""
text = text.replace(old_macro, new_macro)

# For dimensions fields, they are in a loop
text = re.sub(r'(<input type="number".*?name="dims\[.*?\]\[.*?\]".*?class=".*?")>', r'\1 {% if session.get("role") == "VIEWER" %}readonly{% endif %}>', text)

# Hide Add Group button
text = re.sub(r'(<button type="button" onclick="addDimRow\(\)".*?>.*?Add Group.*?<\/button>)', 
              r'{% if session.get("role") != "VIEWER" %}\1{% endif %}', text)

# Hide Remove button (lucide="trash-2")
text = re.sub(r'(<button type="button" onclick="this\.closest\(\'.dim-row\'\)\.remove\(\)".*?>.*?<i data-lucide="trash-2".*?>.*?<\/button>)', 
              r'{% if session.get("role") != "VIEWER" %}\1{% endif %}', text)

# Hide action buttons section
old_actions = """            <!-- Actions -->
            <div class="mt-6 flex items-center justify-between pt-5 border-t border-slate-200">
                <div class="flex gap-3">
                    <button type="submit" name="action" value="save" class="px-4 py-2 bg-white border border-slate-300 text-slate-700 text-sm font-medium rounded-md hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-nexpress-blue transition-colors">
                        <i data-lucide="save" class="h-4 w-4 inline-block mr-1.5 -mt-0.5"></i> Save Changes
                    </button>
                    {% if docket.status != 'REJECTED' %}
                    <button type="submit" name="action" value="reject" class="px-4 py-2 bg-white border border-rose-200 text-rose-600 text-sm font-medium rounded-md hover:bg-rose-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-rose-500 transition-colors">
                        <i data-lucide="x-circle" class="h-4 w-4 inline-block mr-1.5 -mt-0.5"></i> Reject Docket
                    </button>
                    {% endif %}
                </div>
                
                <div class="flex gap-3">
                    <button type="submit" name="action" value="archive" class="px-4 py-2 bg-slate-100 border border-slate-200 text-slate-600 text-sm font-medium rounded-md hover:bg-slate-200 focus:outline-none transition-colors">
                        <i data-lucide="archive" class="h-4 w-4 inline-block mr-1.5 -mt-0.5"></i> Archive
                    </button>
                    <button type="submit" name="action" value="verify" class="px-5 py-2 bg-nexpress-blue text-white text-sm font-medium rounded-md hover:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-nexpress-blue transition-colors shadow-sm flex items-center">
                        <i data-lucide="check-circle" class="h-4 w-4 mr-1.5"></i> Mark as Verified
                    </button>
                </div>
            </div>"""

new_actions = """            <!-- Actions -->
            {% if session.get('role') != 'VIEWER' %}
            <div class="mt-6 flex items-center justify-between pt-5 border-t border-slate-200">
                <div class="flex gap-3">
                    <button type="submit" name="action" value="save" class="px-4 py-2 bg-white border border-slate-300 text-slate-700 text-sm font-medium rounded-md hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-nexpress-blue transition-colors">
                        <i data-lucide="save" class="h-4 w-4 inline-block mr-1.5 -mt-0.5"></i> Save Changes
                    </button>
                    {% if docket.status != 'REJECTED' %}
                    <button type="submit" name="action" value="reject" class="px-4 py-2 bg-white border border-rose-200 text-rose-600 text-sm font-medium rounded-md hover:bg-rose-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-rose-500 transition-colors">
                        <i data-lucide="x-circle" class="h-4 w-4 inline-block mr-1.5 -mt-0.5"></i> Reject Docket
                    </button>
                    {% endif %}
                </div>
                
                <div class="flex gap-3">
                    <button type="submit" name="action" value="archive" class="px-4 py-2 bg-slate-100 border border-slate-200 text-slate-600 text-sm font-medium rounded-md hover:bg-slate-200 focus:outline-none transition-colors">
                        <i data-lucide="archive" class="h-4 w-4 inline-block mr-1.5 -mt-0.5"></i> Archive
                    </button>
                    <button type="submit" name="action" value="verify" class="px-5 py-2 bg-nexpress-blue text-white text-sm font-medium rounded-md hover:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-nexpress-blue transition-colors shadow-sm flex items-center">
                        <i data-lucide="check-circle" class="h-4 w-4 mr-1.5"></i> Mark as Verified
                    </button>
                </div>
            </div>
            {% endif %}"""

text = text.replace(old_actions, new_actions)

with open('templates/docket_detail.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("docket_detail.html patched for viewers")
