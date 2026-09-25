with open('templates/exports.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Change grid layout to 3 cols
text = text.replace('grid-cols-1 md:grid-cols-2 max-w-4xl', 'grid-cols-1 md:grid-cols-3 max-w-6xl')
text = text.replace('grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl', 'grid-cols-1 md:grid-cols-3 gap-6 max-w-6xl')

# Add the new All Dockets box before Verified Dockets
all_dockets_html = """    <!-- All Dockets Export -->
    <div class="bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden">
        <div class="px-6 py-4 border-b border-blue-100 bg-blue-50">
            <h2 class="text-base font-bold text-blue-900 flex items-center">
                <i data-lucide="layers" class="h-5 w-5 mr-2 text-blue-600"></i> All Dockets Export
            </h2>
        </div>
        <div class="p-6">
            <p class="text-sm text-slate-600 mb-6">Generates an Excel spreadsheet containing <strong>ALL</strong> dockets, regardless of status (including those Pending Review, Verified, and Rejected).</p>
            
            <form action="{{ url_for('ops.do_export_all') }}" method="GET" class="space-y-4">
                <div class="flex gap-4">
                    <div class="flex-1">
                        <label class="block text-xs font-medium text-slate-700 mb-1">Start Date</label>
                        <input type="date" name="start_date" class="w-full text-sm border-slate-300 rounded-md shadow-sm">
                    </div>
                    <div class="flex-1">
                        <label class="block text-xs font-medium text-slate-700 mb-1">End Date</label>
                        <input type="date" name="end_date" class="w-full text-sm border-slate-300 rounded-md shadow-sm">
                    </div>
                </div>
                <button type="submit" class="inline-flex items-center justify-center w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium shadow-sm transition-colors">
                    <i data-lucide="download" class="h-4 w-4 mr-2"></i> Download All Excel
                </button>
            </form>
        </div>
    </div>
"""

text = text.replace('<!-- Verified Export -->', all_dockets_html + '\n    <!-- Verified Export -->')

with open('templates/exports.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("exports.html updated")
