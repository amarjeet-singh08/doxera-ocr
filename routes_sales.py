# DOXERA Sales Intelligence & Analytics Blueprint
# =========================================================
# Standalone, isolated module for logistics business intelligence,
# report persistence, and executive exports.
# Security: Restricted strictly to ADMIN and AUDITOR roles.

import json
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, session, send_file, jsonify, abort
)
from decorators import login_required, role_required
from database import get_db_connection, log_audit
from sales_engine import (
    parse_and_process_sales_3way, format_inr,
    INDIA_CITY_COORDINATES, normalize_city_name,
    compute_segment_metrics
)
from sales_exports import (
    generate_sales_pptx, generate_sales_pdf
)

sales_bp = Blueprint('sales', __name__)


def _lookup_coords(city):
    """Return [lat, lon] only for cities we can geolocate with certainty, else None."""
    raw = str(city or '').strip()
    if not raw or raw.upper() in ('NAN', 'NONE', 'UNKNOWN', '0', '-'):
        return None
    norm = normalize_city_name(raw)
    coords = INDIA_CITY_COORDINATES.get(norm)
    return [coords[0], coords[1]] if coords else None


def _enrich_geo(report_data):
    """
    Attach verified coordinates to destination and lane records for the dashboard map.
    Older reports either lack coordinates or carry engine defaults (unknown city -> Delhi/Mumbai),
    which would plot misleading points. We recompute from the city name and mark unknowns as None.
    """
    if not isinstance(report_data, dict):
        return report_data

    def fix_segment(seg):
        if not isinstance(seg, dict):
            return
        for d in seg.get('destinations') or []:
            d['coords'] = _lookup_coords(d.get('city'))

    for key in ('all', 'billed', 'unbilled', 'for_update'):
        fix_segment(report_data.get(key))
    for month_block in (report_data.get('by_month') or {}).values():
        if isinstance(month_block, dict):
            for key in ('all', 'billed', 'unbilled', 'for_update'):
                fix_segment(month_block.get(key))

    conn_data = report_data.get('connectivity') or {}

    def fix_routes(routes):
        for r in routes or []:
            r['origin_coords'] = _lookup_coords(r.get('origin'))
            r['dest_coords'] = _lookup_coords(r.get('destination'))

    fix_routes(conn_data.get('all_routes'))
    for routes in (conn_data.get('by_month') or {}).values():
        fix_routes(routes)

    # Ensure complete shipment arrays exist
    if 'all_shipments' not in report_data:
        report_data['all_shipments'] = report_data.get('shipments_sample') or []
    if 'billed_shipments' not in report_data:
        report_data['billed_shipments'] = [s for s in report_data['all_shipments'] if s.get('source_type') in ('BILLED', 'COMBINED')]

    raw_unbilled = [s for s in report_data['all_shipments'] if s.get('source_type') in ('UNBILLED', 'COMBINED')]
    if 'for_update_shipments' not in report_data:
        report_data['for_update_shipments'] = [s for s in raw_unbilled if float(s.get('total_amt', 0) or 0) <= 10.0]
        report_data['unbilled_shipments'] = [s for s in raw_unbilled if float(s.get('total_amt', 0) or 0) > 10.0]
    else:
        # Guarantee unbilled_shipments does not contain dummy rates <= 10
        report_data['unbilled_shipments'] = [s for s in (report_data.get('unbilled_shipments') or raw_unbilled) if float(s.get('total_amt', 0) or 0) > 10.0]

    # Dynamically compute for_update metrics if absent (ensures older reports support For Update cleanly)
    if not report_data.get('for_update'):
        report_data['for_update'] = compute_segment_metrics(report_data['for_update_shipments'])

    return report_data

@sales_bp.route('/sales/dashboard')
@login_required
@role_required(['ADMIN', 'AUDITOR'])
def dashboard():
    """
    Main Sales Intelligence Dashboard.
    Loads the latest report or allows switching between previously saved reports.
    """
    conn = get_db_connection()
    reports = conn.execute('''
        SELECT id, report_id, title, period_label, total_sales, total_shipments, created_at, created_by
        FROM sales_reports
        ORDER BY created_at DESC
    ''').fetchall()

    if not reports:
        conn.close()
        return render_template('sales_empty.html')

    # Default to the most recent report or a requested report
    req_report_id = request.args.get('report_id')
    selected_report = None
    if req_report_id:
        selected_report = conn.execute('SELECT * FROM sales_reports WHERE id = ?', (req_report_id,)).fetchone()

    if not selected_report:
        selected_report = conn.execute('SELECT * FROM sales_reports ORDER BY created_at DESC LIMIT 1').fetchone()

    report_data = json.loads(selected_report['report_data_json']) if selected_report else {}
    report_data = _enrich_geo(report_data)
    conn.close()

    return render_template(
        'sales_dashboard.html',
        reports=reports,
        current_report=selected_report,
        report_data=report_data,
        format_inr=format_inr
    )

@sales_bp.route('/sales/report/<int:report_id>')
@login_required
@role_required(['ADMIN', 'AUDITOR'])
def view_report(report_id):
    """View a specific saved sales report by ID."""
    return redirect(url_for('sales.dashboard', report_id=report_id))

@sales_bp.route('/sales/upload', methods=['GET', 'POST'])
@login_required
@role_required(['ADMIN', 'AUDITOR'])
def upload_page():
    """Upload Billed MIS, Unbilled MIS, and Booking Master spreadsheets."""
    if request.method == 'POST':
        billed_file = request.files.get('billed_file')
        unbilled_file = request.files.get('unbilled_file')
        booking_file = request.files.get('booking_file')
        report_title = request.form.get('report_title', '').strip()

        if not billed_file or not billed_file.filename:
            flash("Validation Failed: Please upload the Billed MIS spreadsheet.", "error")
            return render_template('sales_upload.html')

        if not unbilled_file or not unbilled_file.filename:
            flash("Validation Failed: Please upload the Unbilled MIS spreadsheet.", "error")
            return render_template('sales_upload.html')

        if not booking_file or not booking_file.filename:
            flash("Validation Failed: Please upload the Operations Booking Master Register.", "error")
            return render_template('sales_upload.html')

        # Process and correlate all 3 sheets
        new_report_id, err = parse_and_process_sales_3way(
            billed_file=billed_file,
            unbilled_file=unbilled_file,
            booking_file=booking_file,
            billed_name=billed_file.filename,
            unbilled_name=unbilled_file.filename,
            booking_name=booking_file.filename,
            created_by=session.get('username', 'Admin'),
            report_title=report_title
        )

        if err:
            flash(f"Analysis Failed: {err}", "error")
            return render_template('sales_upload.html')

        log_audit(session.get('username', 'Admin'), 'SALES_REPORT_CREATED', details=f"Generated report ID {new_report_id}")
        flash("Sales report analyzed and saved successfully!", "success")
        return redirect(url_for('sales.dashboard', report_id=new_report_id))

    return render_template('sales_upload.html')

import re

def _get_export_filename(report, ext):
    title = ""
    period = ""
    if report:
        try:
            title = (report['title'] or '').strip()
            period = (report['period_label'] or '').strip()
        except Exception:
            title = (getattr(report, 'title', None) or '').strip()
            period = (getattr(report, 'period_label', None) or '').strip()
    if not title:
        title = f"Sales_Audit_{period}" if period else "Sales_Audit"
    
    # Clean characters illegal in filenames across Windows/macOS/iOS/Linux
    safe_name = re.sub(r'[\\/*?:"<>|]', '_', title).strip()
    safe_name = re.sub(r'[\s\-]+', '_', safe_name)
    safe_name = re.sub(r'_+', '_', safe_name).strip('_')
    
    # Guarantee official company name is always present in downloaded file
    if "North_Express_Logistics" not in safe_name:
        safe_name = f"North_Express_Logistics_Pvt_Ltd_{safe_name}"
    else:
        # Standardize company naming
        safe_name = re.sub(r'North_Express_Logistics(_Ltd)?', 'North_Express_Logistics_Pvt_Ltd', safe_name)
        safe_name = re.sub(r'_+', '_', safe_name).strip('_')

    if len(safe_name) > 110:
        safe_name = safe_name[:110].strip('_')
    return f"{safe_name}.{ext}"

@sales_bp.route('/sales/report/<int:report_id>/export/pdf')
@login_required
@role_required(['ADMIN', 'AUDITOR'])
def export_pdf(report_id):
    """Generate and stream an executive multi-page PDF report."""
    conn = get_db_connection()
    report = conn.execute('SELECT * FROM sales_reports WHERE id = ?', (report_id,)).fetchone()
    conn.close()

    if not report:
        abort(404)

    report_data = json.loads(report['report_data_json'])
    pdf_buffer = generate_sales_pdf(report, report_data)
    safe_filename = _get_export_filename(report, 'pdf')

    log_audit(session.get('username', 'Admin'), 'SALES_REPORT_EXPORT_PDF', details=f"Exported PDF for report {report_id} as {safe_filename}")
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=safe_filename,
        mimetype='application/pdf'
    )

@sales_bp.route('/sales/report/<int:report_id>/export/pptx')
@login_required
@role_required(['ADMIN', 'AUDITOR'])
def export_pptx(report_id):
    """Generate and stream an executive 16:9 widescreen PowerPoint presentation."""
    conn = get_db_connection()
    report = conn.execute('SELECT * FROM sales_reports WHERE id = ?', (report_id,)).fetchone()
    conn.close()

    if not report:
        abort(404)

    report_data = json.loads(report['report_data_json'])
    pptx_buffer = generate_sales_pptx(report, report_data)
    safe_filename = _get_export_filename(report, 'pptx')

    log_audit(session.get('username', 'Admin'), 'SALES_REPORT_EXPORT_PPTX', details=f"Exported PPTX for report {report_id} as {safe_filename}")
    return send_file(
        pptx_buffer,
        as_attachment=True,
        download_name=safe_filename,
        mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation'
    )

@sales_bp.route('/sales/report/<int:report_id>/delete', methods=['POST'])
@login_required
@role_required(['ADMIN', 'AUDITOR'])
def delete_report(report_id):
    """Delete a saved sales report (Admin or Auditor)."""
    conn = get_db_connection()
    rep = conn.execute('SELECT id, title FROM sales_reports WHERE id = ?', (report_id,)).fetchone()
    if not rep:
        conn.close()
        flash("Report not found or already deleted.", "error")
        return redirect(url_for('sales.dashboard'))

    conn.execute('DELETE FROM sales_shipments WHERE report_id = ?', (report_id,))
    conn.execute('DELETE FROM sales_reports WHERE id = ?', (report_id,))
    conn.commit()
    conn.close()

    title = rep['title'] or f"Report #{report_id}"
    log_audit(session.get('username', 'Admin'), 'SALES_REPORT_DELETED', details=f"Deleted report {report_id} ({title})")
    flash(f'Report "{title}" (Report #{report_id}) was permanently deleted. All other reports remain safe.', "success")
    return redirect(url_for('sales.dashboard'))

@sales_bp.route('/sales/customers', methods=['GET', 'POST'])
@login_required
@role_required(['ADMIN', 'AUDITOR'])
def customers_page():
    """Manage customer accounts and assigned sales representatives."""
    conn = get_db_connection()

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update':
            cust_id = request.form.get('customer_id')
            sales_rep = request.form.get('sales_person', '').strip() or 'NEL'
            conn.execute('''
                UPDATE sales_customers
                SET sales_person = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (sales_rep, cust_id))
            conn.commit()
            flash("Customer sales representative updated successfully.", "success")
        elif action == 'add':
            code = request.form.get('customer_code', '').strip().upper()
            name = request.form.get('customer_name', '').strip()
            sales_rep = request.form.get('sales_person', '').strip() or 'NEL'
            city = request.form.get('city', '').strip()
            state = request.form.get('state', '').strip()
            if code and name:
                try:
                    conn.execute('''
                        INSERT INTO sales_customers (customer_code, customer_name, sales_person, city, state)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (code, name, sales_rep, city, state))
                    conn.commit()
                    flash(f"Customer {name} added.", "success")
                except Exception as e:
                    flash(f"Could not add customer (code may already exist): {e}", "error")

    search_query = request.args.get('q', '').strip()
    rep_filter = request.args.get('rep', 'ALL')

    query = "SELECT * FROM sales_customers WHERE 1=1"
    params = []
    if search_query:
        query += " AND (customer_code LIKE ? OR customer_name LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])
    if rep_filter != 'ALL':
        query += " AND sales_person = ?"
        params.append(rep_filter)

    query += " ORDER BY customer_name ASC"
    customers = conn.execute(query, params).fetchall()

    reps = conn.execute('''
        SELECT DISTINCT sales_person FROM sales_customers
        WHERE sales_person IS NOT NULL AND sales_person != ''
        ORDER BY sales_person ASC
    ''').fetchall()

    conn.close()
    return render_template(
        'sales_customers.html',
        customers=customers,
        reps=[r['sales_person'] for r in reps],
        current_rep=rep_filter,
        search_query=search_query
    )
