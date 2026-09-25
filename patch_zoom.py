with open('templates/docket_detail.html', 'r', encoding='utf-8') as f:
    text = f.read()

old_image_section = """        <div class="flex-1 bg-slate-100 p-2 overflow-auto relative flex items-center justify-center">
            <!-- In a real app, integrate a zoom/pan library like viewerjs -->
            <img src="{{ url_for('ops.serve_image', filename=docket.image_filename) }}" alt="Docket Image" class="max-w-full max-h-full object-contain rounded shadow-sm border border-slate-200 transition-transform origin-center" id="docketImage">
        </div>
        <div class="px-4 py-2 border-t border-slate-100 bg-slate-50 flex justify-center gap-2 flex-shrink-0">
            <button onclick="document.getElementById('docketImage').style.transform = 'scale(1.5)'" class="p-1.5 bg-white border border-slate-200 rounded text-slate-600 hover:bg-slate-50"><i data-lucide="zoom-in" class="h-4 w-4"></i></button>
            <button onclick="document.getElementById('docketImage').style.transform = 'scale(1)'" class="p-1.5 bg-white border border-slate-200 rounded text-slate-600 hover:bg-slate-50"><i data-lucide="minimize" class="h-4 w-4"></i></button>
            <button onclick="window.open('{{ url_for('ops.serve_image', filename=docket.image_filename) }}', '_blank')" class="p-1.5 bg-white border border-slate-200 rounded text-slate-600 hover:bg-slate-50"><i data-lucide="external-link" class="h-4 w-4"></i></button>
        </div>"""

new_image_section = """        <div class="flex-1 bg-slate-100 p-2 overflow-auto relative" id="imageContainer">
            <div class="flex items-center justify-center min-h-full">
                <img src="{{ url_for('ops.serve_image', filename=docket.image_filename) }}" alt="Docket Image" class="max-w-full object-contain rounded shadow-sm border border-slate-200 transition-all duration-200" id="docketImage" style="width: 100%; max-width: 100%;">
            </div>
        </div>
        <div class="px-4 py-2 border-t border-slate-100 bg-slate-50 flex justify-center gap-2 flex-shrink-0">
            <button type="button" onclick="zoomImage(0.2)" class="p-1.5 bg-white border border-slate-200 rounded text-slate-600 hover:bg-slate-50" title="Zoom In"><i data-lucide="zoom-in" class="h-4 w-4"></i></button>
            <button type="button" onclick="zoomImage(-0.2)" class="p-1.5 bg-white border border-slate-200 rounded text-slate-600 hover:bg-slate-50" title="Zoom Out"><i data-lucide="zoom-out" class="h-4 w-4"></i></button>
            <button type="button" onclick="resetZoom()" class="p-1.5 bg-white border border-slate-200 rounded text-slate-600 hover:bg-slate-50" title="Reset Zoom"><i data-lucide="minimize" class="h-4 w-4"></i></button>
            <button type="button" onclick="window.open('{{ url_for('ops.serve_image', filename=docket.image_filename) }}', '_blank')" class="p-1.5 bg-white border border-slate-200 rounded text-slate-600 hover:bg-slate-50" title="Open in new tab"><i data-lucide="external-link" class="h-4 w-4"></i></button>
        </div>"""

text = text.replace(old_image_section, new_image_section)

# Add the script for zooming
script = """
<script>
    let currentZoom = 1.0;
    
    function zoomImage(delta) {
        currentZoom += delta;
        if (currentZoom < 0.5) currentZoom = 0.5;
        if (currentZoom > 5.0) currentZoom = 5.0;
        
        const img = document.getElementById('docketImage');
        // By changing max-width and width based on percentage, the browser naturally triggers scrollbars!
        img.style.maxWidth = 'none';
        img.style.width = (currentZoom * 100) + '%';
    }
    
    function resetZoom() {
        currentZoom = 1.0;
        const img = document.getElementById('docketImage');
        img.style.maxWidth = '100%';
        img.style.width = '100%';
    }
</script>
{% endblock %}
"""

text = text.replace("{% endblock %}", script)

with open('templates/docket_detail.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("docket_detail.html updated for zoom")
