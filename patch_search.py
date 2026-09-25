import re

# 1. Update routes_ops.py for /dockets search
with open('routes_ops.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_dockets = """@ops_bp.route('/dockets')
@login_required
def dockets():
    status_filter = request.args.get('status', 'ALL')
    conn = get_db_connection()
    
    query = "SELECT * FROM dockets WHERE is_archived = 0 "
    params = [session['username']]
    if status_filter != 'ALL':
        if status_filter == 'REVIEW':
            query += " AND (status = 'REVIEW_REQUIRED' OR status = 'MODIFIED_REVERIFICATION_REQUIRED')"
        else:
            query += " AND status = ?"
            params.append(status_filter)
            
    query += " ORDER BY uploaded_at DESC LIMIT 100"
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return render_template('dockets.html', dockets=rows, current_filter=status_filter)"""

new_dockets = """@ops_bp.route('/dockets')
@login_required
def dockets():
    status_filter = request.args.get('status', 'ALL')
    search_query = request.args.get('search', '').strip()
    conn = get_db_connection()
    
    query = "SELECT * FROM dockets WHERE is_archived = 0"
    params = []
    
    if search_query:
        # Match exactly or partially? User said "when user type docket no, so user will go directly to that docket"
        # Since docket numbers are exact, let's do exact match or LIKE
        query += " AND docket_number = ?"
        params.append(search_query)
        
    if status_filter != 'ALL':
        if status_filter == 'REVIEW':
            query += " AND (status = 'REVIEW_REQUIRED' OR status = 'MODIFIED_REVERIFICATION_REQUIRED')"
        else:
            query += " AND status = ?"
            params.append(status_filter)
            
    query += " ORDER BY uploaded_at DESC LIMIT 100"
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return render_template('dockets.html', dockets=rows, current_filter=status_filter, search_query=search_query)"""

text = text.replace(old_dockets, new_dockets)

with open('routes_ops.py', 'w', encoding='utf-8') as f:
    f.write(text)

# 2. Update base.html to wrap global search in a form
with open('templates/base.html', 'r', encoding='utf-8') as f:
    base_text = f.read()

old_search = """                <div class="relative hidden sm:block">
                    <i data-lucide="search" class="h-4 w-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400"></i>
                    <input type="text" placeholder="Global search..." class="pl-9 pr-4 py-1.5 text-sm border border-slate-300 rounded-md bg-slate-50 focus:bg-white focus:ring-1 focus:ring-nexpress-blue focus:border-nexpress-blue transition-colors w-40 lg:w-64">
                </div>"""

new_search = """                <div class="relative hidden sm:block">
                    <form action="{{ url_for('ops.dockets') }}" method="GET">
                        <i data-lucide="search" class="h-4 w-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400"></i>
                        <input type="text" name="search" placeholder="Global search..." class="pl-9 pr-4 py-1.5 text-sm border border-slate-300 rounded-md bg-slate-50 focus:bg-white focus:ring-1 focus:ring-nexpress-blue focus:border-nexpress-blue transition-colors w-40 lg:w-64" required>
                    </form>
                </div>"""

base_text = base_text.replace(old_search, new_search)

# 3. Update notification bell in base.html
# The user wants "notify about pending dockets, failed dockets and rejected dockets, or how much left rate limit for today."
# We need to pass these values to base.html context, but `base.html` is extended by everything.
# Best way is a context_processor in app.py! Or just hardcode a dropdown that fetches via AJAX?
# I'll leave base.html writing for now and handle notifications later.
with open('templates/base.html', 'w', encoding='utf-8') as f:
    f.write(base_text)

print("Search patched")
