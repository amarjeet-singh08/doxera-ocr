from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_from_directory, current_app
from database import get_db_connection, log_audit, create_job, create_docket, check_duplicate_image
from decorators import login_required, role_required
from validation_service import ValidationService
from ocr_engine import OCREngine
from validation_engine import ValidationEngine
from image_processor import ImageProcessor
from datetime import datetime
from werkzeug.utils import secure_filename
import os
import threading
import json

ops_bp = Blueprint('ops', __name__)

def process_docket_async(docket_id, filepath, app_context):
    with app_context:
        try:
            conn = get_db_connection()
            conn.execute("UPDATE dockets SET status = 'PROCESSING' WHERE id = ?", (docket_id,))
            conn.commit()
            conn.close()
            
            # 1. Image checks & formatting
            processed_path = filepath + "_processed.jpg"
            processed_path = ImageProcessor.preprocess_image(filepath, processed_path)
            
            # 2. OCR
            engine = OCREngine()
            raw_response = engine.extract_docket_data(processed_path)
            
            # 3. AI Parsing — returns (status, reasons, parsed_data)
            ai_status, reasons, parsed_data = ValidationEngine.validate_docket(raw_response)
            
            conn = get_db_connection()
            try:
                docket_info = conn.execute("SELECT original_filename FROM dockets WHERE id = ?", (docket_id,)).fetchone()
                fallback_name = f"Unknown ({docket_info['original_filename']})" if docket_info and docket_info['original_filename'] else f"Unknown ({docket_id})"
                
                docket_num = parsed_data.get('docket_number')
                if not docket_num or str(docket_num).strip() == '':
                    docket_num = fallback_name

                # Update docket with AI parsed data
                conn.execute('''
                    UPDATE dockets 
                    SET docket_number = ?, actual_weight = ?, total_packages = ?, invoice_no = ?, invoice_value = ?,
                        ai_original_docket_number = ?, ai_original_actual_weight = ?, ai_original_total_packages = ?, ai_original_invoice_no = ?, ai_original_invoice_value = ?,
                        ai_raw_response = ?, ai_confidence_notes = ?, rejection_reasons = ?,
                        processed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (
                    docket_num, 
                    parsed_data.get('actual_weight'), 
                    parsed_data.get('total_packages'),
                    parsed_data.get('invoice_no'),
                    parsed_data.get('invoice_value'),
                    str(parsed_data.get('docket_number')) if parsed_data.get('docket_number') is not None else None,
                    str(parsed_data.get('actual_weight')) if parsed_data.get('actual_weight') is not None else None,
                    str(parsed_data.get('total_packages')) if parsed_data.get('total_packages') is not None else None,
                    str(parsed_data.get('ai_original_invoice_no')) if parsed_data.get('ai_original_invoice_no') is not None else None,
                    str(parsed_data.get('ai_original_invoice_value')) if parsed_data.get('ai_original_invoice_value') is not None else None,
                    parsed_data.get('ai_raw_response'), 
                    parsed_data.get('ai_confidence_notes'), 
                    json.dumps(reasons), 
                    docket_id
                ))
                
                # Insert dimensions
                if parsed_data.get('dimensions'):
                    for idx, dim in enumerate(parsed_data['dimensions']):
                        conn.execute('''
                            INSERT INTO dimension_groups (
                                docket_id, group_index, length, breadth, height, num_packages,
                                dimension_weight, ai_original_length, ai_original_breadth,
                                ai_original_height, ai_original_num_packages
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            docket_id, idx,
                            dim.get('length'), dim.get('breadth'), dim.get('height'), dim.get('num_packages'),
                            dim.get('dimension_weight'),
                            dim.get('ai_original_length'), dim.get('ai_original_breadth'),
                            dim.get('ai_original_height'), dim.get('ai_original_num_packages')
                        ))
                
                # 4. DOXERA Final Validation logic
                # AI must only extract data. Never automatically mark a docket VERIFIED.
                if ai_status == 'FAILED':
                    final_status = 'FAILED'
                elif ai_status == 'REJECTED':
                    final_status = 'REJECTED'
                else:
                    # Even if validation is perfect, it MUST be verified by a human
                    is_valid, final_reasons = ValidationService.validate_docket_record(conn, docket_id)
                    if not is_valid:
                        # Append any backend validation failures to the AI reasons
                        reasons.extend(final_reasons)
                        conn.execute('UPDATE dockets SET rejection_reasons = ? WHERE id = ?', (json.dumps(reasons), docket_id))
                    
                    final_status = 'REVIEW_REQUIRED'
                
                conn.execute("UPDATE dockets SET status = ? WHERE id = ?", (final_status, docket_id))
                
                # Update job counts
                docket = conn.execute("SELECT job_id FROM dockets WHERE id = ?", (docket_id,)).fetchone()
                job_id = docket['job_id']
                
                conn.execute('''
                    UPDATE processing_jobs SET 
                    processed_count = processed_count + 1,
                    verified_count = verified_count + ?,
                    review_count = review_count + ?,
                    rejected_count = rejected_count + ?,
                    failed_count = failed_count + ?
                    WHERE id = ?
                ''', (
                    1 if final_status == 'VERIFIED' else 0,
                    1 if final_status == 'REVIEW_REQUIRED' else 0,
                    1 if final_status == 'REJECTED' else 0,
                    1 if final_status == 'FAILED' else 0,
                    job_id
                ))
                
                log_audit('SYSTEM', 'OCR_PROCESSED', docket_id, f"OCR completed with status {final_status}", conn=conn)
                conn.commit()
            finally:
                conn.close()
                
            # Cleanup temp file
            if os.path.exists(processed_path) and processed_path != filepath:
                os.remove(processed_path)
                
        except Exception as e:
            try:
                conn = get_db_connection()
                conn.execute("UPDATE dockets SET status = 'FAILED', rejection_reasons = ? WHERE id = ?", (json.dumps([str(e)]), docket_id))
                docket = conn.execute("SELECT job_id FROM dockets WHERE id = ?", (docket_id,)).fetchone()
                if docket:
                    conn.execute('UPDATE processing_jobs SET processed_count = processed_count + 1, failed_count = failed_count + 1 WHERE id = ?', (docket['job_id'],))
                log_audit('SYSTEM', 'OCR_FAILED', docket_id, f"Error: {str(e)}", conn=conn)
                conn.commit()
            finally:
                conn.close()


@ops_bp.route('/')
@ops_bp.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    today_start = datetime.utcnow().strftime('%Y-%m-%d 00:00:00')
    
    # Stats
    today = conn.execute("SELECT COUNT(*) FROM dockets WHERE uploaded_at >= ?", (today_start,)).fetchone()[0]
    processing = conn.execute("SELECT COUNT(*) FROM dockets WHERE status IN ('PROCESSING', 'UPLOADED')").fetchone()[0]
    verified = conn.execute("SELECT COUNT(*) FROM dockets WHERE status = 'VERIFIED'").fetchone()[0]
    review = conn.execute("SELECT COUNT(*) FROM dockets WHERE (status = 'REVIEW_REQUIRED' OR status = 'MODIFIED_REVERIFICATION_REQUIRED')").fetchone()[0]
    rejected = conn.execute("SELECT COUNT(*) FROM dockets WHERE status = 'REJECTED'").fetchone()[0]
    failed = conn.execute("SELECT COUNT(*) FROM dockets WHERE status = 'FAILED'").fetchone()[0]
    
    # Pipeline Jobs
    # Pipeline Jobs: Admin sees all, others see only their own
    if session.get('role') == 'ADMIN':
        jobs = conn.execute("SELECT * FROM processing_jobs ORDER BY created_at DESC LIMIT 5").fetchall()
    else:
        jobs = conn.execute("SELECT * FROM processing_jobs WHERE created_by = ? ORDER BY created_at DESC LIMIT 5", (session['username'],)).fetchall()
    
    # Recent dockets
    dockets = conn.execute("SELECT * FROM dockets WHERE is_archived = 0 ORDER BY uploaded_at DESC LIMIT 10").fetchall()
    
    conn.close()
    
    return render_template('dashboard.html', 
                           stats={'today': today, 'processing': processing, 'verified': verified, 'review': review, 'rejected': rejected, 'failed': failed},
                           jobs=jobs, dockets=dockets)

@ops_bp.route('/upload', methods=['GET', 'POST'])
@login_required
@role_required(['ADMIN', 'REVIEWER'])
def upload():
    if request.method == 'POST':
        files = request.files.getlist('files[]')
        if not files or files[0].filename == '':
            flash('No selected file', 'error')
            return redirect(url_for('ops.upload'))
            
        batch_id = f"NX-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        job_id = create_job(batch_id, len(files), session['username'])
        
        app_context = current_app.app_context()
        
        # We will collect dockets to process in a single background thread
        dockets_to_process = []
        
        for file in files:
            if file:
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
                saved_filename = f"{timestamp}_{filename}"
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], saved_filename)
                file.save(filepath)
                
                image_hash = ImageProcessor.get_image_hash(filepath)
                duplicate = check_duplicate_image(image_hash)
                
                if duplicate:
                    flash(f"Skipped: Image {filename} is a duplicate of Docket {duplicate['docket_number'] or 'ID '+str(duplicate['id'])}", "warning")
                    os.remove(filepath)  # Remove the duplicate file
                    continue  # SKIP IT ENTIRELY
                    
                # Save to database for persistent storage on Render
                import base64
                import mimetypes
                with open(filepath, 'rb') as img_f:
                    encoded = base64.b64encode(img_f.read()).decode('utf-8')
                    mime = mimetypes.guess_type(filepath)[0] or 'image/jpeg'
                    conn = get_db_connection()
                    try:
                        conn.execute("INSERT INTO docket_images (filename, image_base64, mimetype) VALUES (?, ?, ?)", 
                                     (saved_filename, encoded, mime))
                        conn.commit()
                    except Exception as e:
                        print("Failed to save image to DB:", e)
                    finally:
                        conn.close()

                docket_id = create_docket(job_id, saved_filename, image_hash, filename, session['username'])
                log_audit(session['username'], 'UPLOADED', docket_id, f"Uploaded {filename}")
                dockets_to_process.append((docket_id, filepath))
                
        if dockets_to_process:
            # Process with limited concurrency to balance speed and OpenRouter rate limits
            def process_batch(dockets, ctx):
                from concurrent.futures import ThreadPoolExecutor
                import time
                
                def process_single(d_data):
                    d_id, f_path = d_data
                    process_docket_async(d_id, f_path, ctx)
                    
                # Free models usually allow ~10-20 requests per minute
                # Using 3 workers will process about 10-15 images per minute, staying under the radar
                with ThreadPoolExecutor(max_workers=3) as executor:
                    executor.map(process_single, dockets)
            
            thread = threading.Thread(target=process_batch, args=(dockets_to_process, app_context))
            thread.start()
            flash(f'Started processing batch {batch_id} with {len(dockets_to_process)} new files.', 'success')
        else:
            flash('No new files to process (all were duplicates or invalid).', 'warning')
            
        if request.headers.get('Accept') == 'application/json':
            return {"job_id": job_id, "batch_id": batch_id, "count": len(dockets_to_process)}
        return redirect(url_for('ops.review_center'))
        
    return render_template('upload.html')

@ops_bp.route('/api/job_status/<int:job_id>')
@login_required
def api_job_status(job_id):
    conn = get_db_connection()
    job = conn.execute("SELECT * FROM processing_jobs WHERE id = ?", (job_id,)).fetchone()
    if not job:
        conn.close()
        return {"error": "not found"}, 404
        
    dockets = conn.execute("SELECT status, rejection_reasons FROM dockets WHERE job_id = ?", (job_id,)).fetchall()
    conn.close()
    
    total = len(dockets)
    processed = sum(1 for d in dockets if d['status'] not in ('UPLOADED', 'PROCESSING'))
    rate_limited = any('Rate limit' in str(d['rejection_reasons']) or '429' in str(d['rejection_reasons']) or '402' in str(d['rejection_reasons']) for d in dockets if d['status'] == 'FAILED')
    
    return {
        "status": job['status'],
        "total": total,
        "processed": processed,
        "complete": processed >= total if total > 0 else True,
        "rate_limited": rate_limited
    }

@ops_bp.route('/processing')
@login_required
def processing():
    conn = get_db_connection()
    jobs = conn.execute("SELECT * FROM processing_jobs ORDER BY created_at DESC LIMIT 20").fetchall()
    conn.close()
    return render_template('processing.html', jobs=jobs)

@ops_bp.route('/dockets')
@login_required
def dockets():
    status_filter = request.args.get('status', 'ALL')
    search_query = request.args.get('search', '').strip()
    conn = get_db_connection()
    
    query = "SELECT * FROM dockets WHERE is_archived = 0"
    params = []
    
    if search_query:
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
    return render_template('dockets.html', dockets=rows, current_filter=status_filter, search_query=search_query)

@ops_bp.route('/review_center')
@login_required
@role_required(['ADMIN', 'REVIEWER'])
def review_center():
    conn = get_db_connection()
    # Fetch ones needing review
    rows = conn.execute("SELECT * FROM dockets WHERE is_archived = 0 AND (status = 'REVIEW_REQUIRED' OR status = 'MODIFIED_REVERIFICATION_REQUIRED') ORDER BY uploaded_at ASC").fetchall()
    conn.close()
    return render_template('review_center.html', dockets=rows)

@ops_bp.route('/docket/<int:docket_id>', methods=['GET', 'POST'])
@login_required
def docket_detail(docket_id):
    conn = get_db_connection()
    try:
        if request.method == 'POST':
            if session.get('role') == 'VIEWER':
                from flask import abort
                abort(403)
                
            action = request.form.get('action')
            if action == 'verify':
                # Must pass validation to verify
                is_valid, _ = ValidationService.validate_docket_record(conn, docket_id)
                if is_valid:
                    conn.execute("UPDATE dockets SET status = 'VERIFIED', human_reviewed = 1, human_reviewer = ?, human_reviewed_at = CURRENT_TIMESTAMP WHERE id = ?", (session['username'], docket_id))
                    log_audit(session['username'], 'VERIFIED', docket_id, "Marked as Verified", conn=conn)
                    flash("Docket Verified successfully.", "success")
                else:
                    flash("Cannot verify. Validation failed.", "error")
                    
            elif action == 'reject':
                reason = request.form.get('rejection_reason', 'Manual rejection')
                conn.execute("UPDATE dockets SET status = 'REJECTED' WHERE id = ?", (docket_id,))
                log_audit(session['username'], 'REJECTED', docket_id, f"Rejected: {reason}", conn=conn)
                flash("Docket Rejected.", "success")
                
            elif action == 'archive':
                conn.execute("UPDATE dockets SET is_archived = 1 WHERE id = ?", (docket_id,))
                log_audit(session['username'], 'ARCHIVED', docket_id, "Archived docket", conn=conn)
                flash("Docket Archived.", "success")
                
            elif action == 'reopen':
                reason = request.form.get('reopen_reason', 'Reopened for review')
                conn.execute("UPDATE dockets SET status = 'REVIEW_REQUIRED', reopen_reason = ? WHERE id = ?", (reason, docket_id))
                log_audit(session['username'], 'REOPENED', docket_id, f"Reopened: {reason}", conn=conn)
                flash("Docket Reopened.", "success")
                
            elif action == 'permanent_delete':
                if session.get('role') != 'ADMIN':
                    from flask import abort
                    abort(403)
                
                # Delete related records first
                conn.execute("DELETE FROM dimension_groups WHERE docket_id = ?", (docket_id,))
                conn.execute("DELETE FROM corrections WHERE docket_id = ?", (docket_id,))
                
                # Cannot delete audit_log rows if we want a permanent log, but let's keep one final log before deleting the docket itself
                log_audit(session['username'], 'PERMANENT_DELETE', docket_id, "PERMANENTLY DELETED DOCKET RECORD", conn=conn)
                
                # We could keep the docket image file around, but we'll delete the DB record
                conn.execute("DELETE FROM dockets WHERE id = ?", (docket_id,))
                
                flash("Docket Permanently Deleted.", "success")
                conn.commit()
                return redirect(url_for('ops.dockets'))
                
            conn.commit()
            return redirect(url_for('ops.docket_detail', docket_id=docket_id))
            
        docket = conn.execute('SELECT * FROM dockets WHERE id = ?', (docket_id,)).fetchone()
        if not docket:
            return "Not found", 404
            
        dims = conn.execute('SELECT * FROM dimension_groups WHERE docket_id = ? ORDER BY group_index', (docket_id,)).fetchall()
        corrections = conn.execute('SELECT * FROM corrections WHERE docket_id = ? ORDER BY corrected_at DESC', (docket_id,)).fetchall()
        audit = conn.execute('SELECT * FROM audit_log WHERE docket_id = ? ORDER BY timestamp DESC', (docket_id,)).fetchall()
        
        is_valid, reasons = ValidationService.validate_docket_record(conn, docket_id)
        
        return render_template('docket_detail.html', docket=docket, dims=dims, corrections=corrections, audit=audit, is_valid=is_valid, validation_reasons=reasons)
    finally:
        conn.close()

@ops_bp.route('/docket/<int:docket_id>/edit_all', methods=['POST'])
@login_required
@role_required(['ADMIN', 'REVIEWER'])
def edit_all(docket_id):
    conn = get_db_connection()
    try:
        docket = conn.execute('SELECT * FROM dockets WHERE id = ?', (docket_id,)).fetchone()
        if not docket:
            abort(404)
            
        # 1. Update basic fields
        changes_made = False
        for field in ['docket_number', 'actual_weight', 'total_packages', 'invoice_no', 'invoice_value']:
            new_val = request.form.get(field, '').strip()
            if not new_val: new_val = None
            old_val = docket[field]
            
            if str(old_val) != str(new_val):
                conn.execute('INSERT INTO corrections (docket_id, field_name, original_value, corrected_value, corrected_by) VALUES (?, ?, ?, ?, ?)',
                             (docket_id, field, str(old_val) if old_val is not None else '', str(new_val) if new_val is not None else '', session['username']))
                conn.execute(f'UPDATE dockets SET {field} = ? WHERE id = ?', (new_val, docket_id))
                changes_made = True
                
        # 2. Update dimensions (we receive arrays of dimension values)
        dim_ids = request.form.getlist('dim_id[]')
        lengths = request.form.getlist('length[]')
        breadths = request.form.getlist('breadth[]')
        heights = request.form.getlist('height[]')
        packages = request.form.getlist('num_packages[]')
        
        # Get existing dimensions
        existing_dims = {str(d['id']): d for d in conn.execute('SELECT * FROM dimension_groups WHERE docket_id = ?', (docket_id,)).fetchall()}
        
        # Keep track of which dims we kept
        kept_dim_ids = set()
        
        for idx in range(len(lengths)):
            dim_id = dim_ids[idx] if idx < len(dim_ids) else 'new'
            l_val = lengths[idx].strip() or None
            b_val = breadths[idx].strip() or None
            h_val = heights[idx].strip() or None
            p_val = packages[idx].strip() or None
            
            if dim_id == 'new':
                # Insert new dimension
                conn.execute('''
                    INSERT INTO dimension_groups (docket_id, group_index, length, breadth, height, num_packages)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (docket_id, idx, l_val, b_val, h_val, p_val))
                changes_made = True
                conn.execute('INSERT INTO corrections (docket_id, field_name, original_value, corrected_value, corrected_by) VALUES (?, ?, ?, ?, ?)',
                             (docket_id, f"Dim {idx+1}", "", "Added", session['username']))
            else:
                kept_dim_ids.add(dim_id)
                old_dim = existing_dims.get(dim_id)
                if old_dim:
                    dim_changed = False
                    for f_name, n_val in [('length', l_val), ('breadth', b_val), ('height', h_val), ('num_packages', p_val)]:
                        o_val = old_dim[f_name]
                        if str(o_val) != str(n_val):
                            conn.execute(f'UPDATE dimension_groups SET {f_name} = ? WHERE id = ?', (n_val, dim_id))
                            dim_changed = True
                            conn.execute('INSERT INTO corrections (docket_id, field_name, original_value, corrected_value, corrected_by) VALUES (?, ?, ?, ?, ?)',
                                         (docket_id, f"Dim {idx+1} {f_name}", str(o_val) if o_val is not None else '', str(n_val) if n_val is not None else '', session['username']))
                    if dim_changed:
                        changes_made = True
                        
        # Remove deleted dimensions
        for old_dim_id in existing_dims.keys():
            if old_dim_id not in kept_dim_ids:
                conn.execute('DELETE FROM dimension_groups WHERE id = ?', (old_dim_id,))
                changes_made = True
                conn.execute('INSERT INTO corrections (docket_id, field_name, original_value, corrected_value, corrected_by) VALUES (?, ?, ?, ?, ?)',
                             (docket_id, f"Dim Removed", "Exists", "Deleted", session['username']))
                             
        # Re-index dimensions and calculate weights
        from calculation_engine import CalculationEngine
        current_dims = conn.execute('SELECT * FROM dimension_groups WHERE docket_id = ? ORDER BY id', (docket_id,)).fetchall()
        for i, d in enumerate(current_dims):
            l = float(d['length']) if d['length'] else None
            b = float(d['breadth']) if d['breadth'] else None
            h = float(d['height']) if d['height'] else None
            p = float(d['num_packages']) if d['num_packages'] else None
            
            weight = None
            if None not in [l, b, h, p]:
                weight = CalculationEngine.calculate_dimension_weight(l, b, h, p)
                
            conn.execute('UPDATE dimension_groups SET group_index = ?, dimension_weight = ? WHERE id = ?', (i, weight, d['id']))
            
        if changes_made:
            ValidationService.transition_status_on_edit(conn, docket_id)
            log_audit(session['username'], 'EDITED_DOCKET', docket_id, "Updated docket fields and/or dimensions", conn=conn)
            flash("Docket updated successfully.", "success")
        else:
            flash("No changes detected.", "info")
            
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for('ops.docket_detail', docket_id=docket_id))

@ops_bp.route('/dockets/<int:docket_id>/delete', methods=['POST'])
@login_required
def delete_docket(docket_id):
    if session.get('role') != 'ADMIN':
        from flask import abort
        abort(403)
        
    conn = get_db_connection()
    conn.execute('DELETE FROM dimension_groups WHERE docket_id = ?', (docket_id,))
    conn.execute('DELETE FROM corrections WHERE docket_id = ?', (docket_id,))
    log_audit(session['username'], 'PERMANENT_DELETE', docket_id, 'PERMANENTLY DELETED DOCKET RECORD', conn=conn)
    conn.execute('DELETE FROM dockets WHERE id = ?', (docket_id,))
    conn.commit()
    conn.close()
    
    flash('Docket deleted.', 'success')
    return redirect(url_for('ops.dockets'))

@ops_bp.route('/dockets/delete_all', methods=['POST'])
@login_required
def delete_all_dockets():
    if session.get('role') != 'ADMIN':
        from flask import abort
        abort(403)
        
    conn = get_db_connection()
    status = request.form.get('status', 'ALL')
    
    if status == 'ALL':
        dockets = conn.execute('SELECT id FROM dockets').fetchall()
    elif status == 'REVIEW':
        dockets = conn.execute("SELECT id FROM dockets WHERE status IN ('REVIEW_REQUIRED', 'MODIFIED_REVERIFICATION_REQUIRED')").fetchall()
    else:
        dockets = conn.execute('SELECT id FROM dockets WHERE status = ?', (status,)).fetchall()
        
    for d in dockets:
        conn.execute('DELETE FROM dimension_groups WHERE docket_id = ?', (d['id'],))
        conn.execute('DELETE FROM corrections WHERE docket_id = ?', (d['id'],))
        conn.execute('DELETE FROM dockets WHERE id = ?', (d['id'],))
        
    log_audit(session['username'], 'PERMANENT_DELETE_ALL', details=f'Deleted all dockets in status {status}', conn=conn)
    conn.commit()
    conn.close()
    
    flash(f'Deleted all {status} dockets.', 'success')
    return redirect(url_for('ops.dockets'))

@ops_bp.route('/uploads/<filename>')
@login_required
def serve_image(filename):
    conn = get_db_connection()
    img_row = conn.execute("SELECT image_base64, mimetype FROM docket_images WHERE filename = ?", (filename,)).fetchone()
    conn.close()
    if img_row and img_row['image_base64']:
        import base64
        import io
        from flask import send_file
        img_data = base64.b64decode(img_row['image_base64'])
        return send_file(io.BytesIO(img_data), mimetype=img_row['mimetype'] or 'image/jpeg')
        
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@ops_bp.route('/exports')
@login_required
@role_required(['ADMIN', 'REVIEWER', 'VIEWER'])
def exports_page():
    return render_template('exports.html')

@ops_bp.route('/export/verified')
@login_required
@role_required(['ADMIN', 'REVIEWER', 'VIEWER'])
def do_export_verified():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    from excel_exporter import ExcelExporter
    filename = ExcelExporter.export_verified(start_date, end_date)
    if not filename:
        flash("No verified records found for this date range.", "error")
        return redirect(url_for('ops.exports_page'))
    log_audit(session['username'], 'EXPORTED', details=f"Generated Verified Excel: {filename}")
    return send_from_directory(current_app.config['EXPORT_FOLDER'], filename, as_attachment=True)

@ops_bp.route('/export/rejected')
@login_required
@role_required(['ADMIN', 'REVIEWER', 'VIEWER'])
def do_export_rejected():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    from excel_exporter import ExcelExporter
    filename = ExcelExporter.export_rejected(start_date, end_date)
    if not filename:
        flash("No rejected records found for this date range.", "error")
        return redirect(url_for('ops.exports_page'))
    log_audit(session['username'], 'EXPORTED', details=f"Generated Rejected Excel: {filename}")
    return send_from_directory(current_app.config['EXPORT_FOLDER'], filename, as_attachment=True)
