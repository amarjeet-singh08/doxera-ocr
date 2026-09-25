with open('routes_ops.py', 'r', encoding='utf-8') as f:
    text = f.read()

new_route = """
@ops_bp.route('/export/all')
@login_required
@role_required(['ADMIN', 'REVIEWER', 'VIEWER'])
def do_export_all():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    from excel_exporter import ExcelExporter
    filename = ExcelExporter.export_all(start_date, end_date)
    if not filename:
        flash("No records found for this date range.", "error")
        return redirect(url_for('ops.exports_page'))
    log_audit('EXPORTED', details=f"Generated All Dockets Excel: {filename}")
    return send_from_directory(current_app.config['EXPORT_FOLDER'], filename, as_attachment=True)
"""

text += new_route

with open('routes_ops.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("routes_ops.py updated with export_all")
