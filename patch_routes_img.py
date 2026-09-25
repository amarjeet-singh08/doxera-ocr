with open('routes_ops.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update serve_image
old_serve_image = """@ops_bp.route('/uploads/<filename>')
@login_required
def serve_image(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)"""

new_serve_image = """@ops_bp.route('/uploads/<filename>')
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
        
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)"""

text = text.replace(old_serve_image, new_serve_image)

# 2. Update upload route to insert image base64
old_upload = """                if duplicate:
                    flash(f"Skipped: Image {filename} is a duplicate of Docket {duplicate['docket_number'] or 'ID '+str(duplicate['id'])}", "warning")
                    os.remove(filepath)  # Remove the duplicate file
                    continue  # SKIP IT ENTIRELY
                    
                docket_id = create_docket(job_id, saved_filename, image_hash, filename, session['username'])"""

new_upload = """                if duplicate:
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

                docket_id = create_docket(job_id, saved_filename, image_hash, filename, session['username'])"""

text = text.replace(old_upload, new_upload)

with open('routes_ops.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("routes_ops.py updated for image DB")
