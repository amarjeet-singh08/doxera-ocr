with open('templates/docket_detail.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Update tabs section
old_tabs = """            <div class="flex border-b border-slate-100 bg-slate-50 text-xs font-bold text-slate-500 uppercase tracking-wide">
                <button class="px-4 py-3 text-nexpress-blue border-b-2 border-nexpress-blue" id="tabAudit" onclick="switchTab('audit')">Audit Log</button>
                <button class="px-4 py-3 hover:text-slate-700" id="tabCorr" onclick="switchTab('corr')">Corrections</button>
            </div>
            
            <div id="contentAudit" class="p-4 max-h-64 overflow-y-auto space-y-3">
                {% for log in audit %}
                <div class="flex gap-3 text-sm">
                    <div class="flex-shrink-0 mt-0.5">
                        <div class="h-2 w-2 rounded-full bg-slate-300 mt-1.5"></div>
                    </div>
                    <div>
                        <p class="text-slate-800"><span class="font-medium">{{ log.user }}</span> {{ log.action|replace('_', ' ')|lower }}</p>
                        <p class="text-xs text-slate-500">{{ log.details }}</p>
                        <p class="text-[10px] text-slate-400 mt-0.5">{{ log.timestamp|localdt }}</p>
                    </div>
                </div>
                {% else %}
                <p class="text-sm text-slate-500">No history available.</p>
                {% endfor %}
            </div>
            
            <div id="contentCorr" class="p-4 max-h-64 overflow-y-auto space-y-3 hidden">"""

new_tabs = """            <div class="flex border-b border-slate-100 bg-slate-50 text-xs font-bold text-slate-500 uppercase tracking-wide">
                {% if session.get('role') == 'ADMIN' %}
                <button class="px-4 py-3 text-nexpress-blue border-b-2 border-nexpress-blue" id="tabAudit" onclick="switchTab('audit')">Audit Log</button>
                <button class="px-4 py-3 hover:text-slate-700" id="tabCorr" onclick="switchTab('corr')">Corrections</button>
                {% else %}
                <button class="px-4 py-3 text-nexpress-blue border-b-2 border-nexpress-blue" id="tabCorr" onclick="switchTab('corr')">Corrections</button>
                {% endif %}
            </div>
            
            {% if session.get('role') == 'ADMIN' %}
            <div id="contentAudit" class="p-4 max-h-64 overflow-y-auto space-y-3">
                {% for log in audit %}
                <div class="flex gap-3 text-sm">
                    <div class="flex-shrink-0 mt-0.5">
                        <div class="h-2 w-2 rounded-full bg-slate-300 mt-1.5"></div>
                    </div>
                    <div>
                        <p class="text-slate-800"><span class="font-medium">{{ log.user }}</span> {{ log.action|replace('_', ' ')|lower }}</p>
                        <p class="text-xs text-slate-500">{{ log.details }}</p>
                        <p class="text-[10px] text-slate-400 mt-0.5">{{ log.timestamp|localdt }}</p>
                    </div>
                </div>
                {% else %}
                <p class="text-sm text-slate-500">No history available.</p>
                {% endfor %}
            </div>
            {% endif %}
            
            <div id="contentCorr" class="p-4 max-h-64 overflow-y-auto space-y-3 {% if session.get('role') == 'ADMIN' %}hidden{% endif %}">"""

text = text.replace(old_tabs, new_tabs)

# Also update the JS so it doesn't crash if tabAudit is missing
old_js = """        document.getElementById('contentAudit').classList.add('hidden');
        document.getElementById('contentCorr').classList.add('hidden');
        document.getElementById('tabAudit').classList.remove('text-nexpress-blue', 'border-b-2', 'border-nexpress-blue');
        document.getElementById('tabCorr').classList.remove('text-nexpress-blue', 'border-b-2', 'border-nexpress-blue');
        document.getElementById('tabAudit').classList.add('hover:text-slate-700');
        document.getElementById('tabCorr').classList.add('hover:text-slate-700');
        
        if(tab === 'audit') {
            document.getElementById('contentAudit').classList.remove('hidden');
            document.getElementById('tabAudit').classList.add('text-nexpress-blue', 'border-b-2', 'border-nexpress-blue');
            document.getElementById('tabAudit').classList.remove('hover:text-slate-700');
        } else {"""

new_js = """        if(document.getElementById('contentAudit')) document.getElementById('contentAudit').classList.add('hidden');
        if(document.getElementById('contentCorr')) document.getElementById('contentCorr').classList.add('hidden');
        if(document.getElementById('tabAudit')) document.getElementById('tabAudit').classList.remove('text-nexpress-blue', 'border-b-2', 'border-nexpress-blue');
        if(document.getElementById('tabCorr')) document.getElementById('tabCorr').classList.remove('text-nexpress-blue', 'border-b-2', 'border-nexpress-blue');
        if(document.getElementById('tabAudit')) document.getElementById('tabAudit').classList.add('hover:text-slate-700');
        if(document.getElementById('tabCorr')) document.getElementById('tabCorr').classList.add('hover:text-slate-700');
        
        if(tab === 'audit' && document.getElementById('contentAudit')) {
            document.getElementById('contentAudit').classList.remove('hidden');
            document.getElementById('tabAudit').classList.add('text-nexpress-blue', 'border-b-2', 'border-nexpress-blue');
            document.getElementById('tabAudit').classList.remove('hover:text-slate-700');
        } else {"""
text = text.replace(old_js, new_js)

with open('templates/docket_detail.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("docket_detail.html patched for audit log")
