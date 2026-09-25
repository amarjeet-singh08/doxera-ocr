import re

with open('templates/base.html', 'r', encoding='utf-8') as f:
    text = f.read()

old_bell = """                <button class="text-slate-400 hover:text-slate-600 p-2">
                    <i data-lucide="bell" class="h-5 w-5"></i>
                </button>"""

new_bell = """                <div class="relative group">
                    <button type="button" class="text-slate-400 hover:text-slate-600 p-2 relative">
                        <i data-lucide="bell" class="h-5 w-5"></i>
                        {% if notif_total and notif_total > 0 %}
                        <span class="absolute top-1.5 right-1.5 block h-2 w-2 rounded-full bg-rose-500 ring-2 ring-white"></span>
                        {% endif %}
                    </button>
                    <!-- Notification Dropdown -->
                    <div class="absolute right-0 mt-2 w-72 bg-white rounded-md shadow-lg py-1 border border-slate-200 hidden group-hover:block z-50">
                        <div class="px-4 py-2 border-b border-slate-100 font-bold text-sm text-slate-700">Notifications</div>
                        <a href="{{ url_for('ops.dockets', status='REVIEW') }}" class="block px-4 py-2 text-sm text-amber-700 hover:bg-slate-50 flex items-center justify-between">
                            <span>Pending Review</span>
                            <span class="bg-amber-100 text-amber-800 text-xs font-bold px-2 py-0.5 rounded-full">{{ notif_pending|default(0) }}</span>
                        </a>
                        <a href="{{ url_for('ops.dockets', status='FAILED') }}" class="block px-4 py-2 text-sm text-rose-700 hover:bg-slate-50 flex items-center justify-between border-t border-slate-50">
                            <span>Failed AI Extraction</span>
                            <span class="bg-rose-100 text-rose-800 text-xs font-bold px-2 py-0.5 rounded-full">{{ notif_failed|default(0) }}</span>
                        </a>
                        <a href="{{ url_for('ops.dockets', status='REJECTED') }}" class="block px-4 py-2 text-sm text-rose-700 hover:bg-slate-50 flex items-center justify-between border-t border-slate-50">
                            <span>Rejected Dockets</span>
                            <span class="bg-rose-100 text-rose-800 text-xs font-bold px-2 py-0.5 rounded-full">{{ notif_rejected|default(0) }}</span>
                        </a>
                        <div class="block px-4 py-3 text-sm text-slate-600 border-t border-slate-100 bg-slate-50 flex items-center justify-between">
                            <span class="font-medium text-xs uppercase tracking-wider text-slate-400">AI Quota Left Today</span>
                            <span class="{% if notif_limit and notif_limit < 20 %}text-rose-600{% else %}text-emerald-600{% endif %} font-bold">{{ notif_limit|default(200) }} Dockets</span>
                        </div>
                    </div>
                </div>"""

text = text.replace(old_bell, new_bell)

with open('templates/base.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Notifications patched in base.html")
