with open('excel_exporter.py', 'r', encoding='utf-8') as f:
    text = f.read()

new_export_all = """
    @staticmethod
    def export_all(start_date=None, end_date=None):
        \"\"\"
        Exports ALL dockets regardless of status.
        \"\"\"
        conn = ExcelExporter._get_db_connection()
        query = "SELECT * FROM dockets WHERE is_archived = 0"
        params = []
        if start_date:
            query += " AND uploaded_at >= ?"
            params.append(f"{start_date} 00:00:00")
        if end_date:
            query += " AND uploaded_at <= ?"
            params.append(f"{end_date} 23:59:59")
            
        query += " ORDER BY uploaded_at DESC"
        dockets = conn.execute(query, params).fetchall()
        
        if not dockets:
            conn.close()
            return None
            
        max_dims = 0
        for d in dockets:
            count = conn.execute("SELECT COUNT(*) FROM dimension_groups WHERE docket_id = ?", (d['id'],)).fetchone()[0]
            if count > max_dims:
                max_dims = count
                
        export_data = []
        for i, d in enumerate(dockets, 1):
            date_only = d['uploaded_at'].strftime('%Y-%m-%d') if hasattr(d['uploaded_at'], 'strftime') else str(d['uploaded_at'])[:10] if d['uploaded_at'] else ''
            row = {
                'S.No': i,
                'Date': date_only,
                'Docket No': d['docket_number'] or '[Not Found]',
                'Invoice No': d['invoice_no'],
                'Invoice Value': d['invoice_value'],
                'Actual Weight': d['actual_weight'],
                'Total Packages': d['total_packages']
            }
            
            dims = conn.execute("SELECT * FROM dimension_groups WHERE docket_id = ? ORDER BY group_index", (d['id'],)).fetchall()
            
            total_vol_weight = 0.0
            for idx in range(1, max_dims + 1):
                if idx <= len(dims):
                    dim = dims[idx-1]
                    row[f'L{idx}'] = dim['length']
                    row[f'B{idx}'] = dim['width']
                    row[f'H{idx}'] = dim['height']
                    row[f'Boxes {idx}'] = dim['boxes_count']
                    row[f'VolWeight {idx}'] = dim['dimension_weight']
                    if dim['dimension_weight']:
                        total_vol_weight += float(dim['dimension_weight'])
                else:
                    row[f'L{idx}'] = ''
                    row[f'B{idx}'] = ''
                    row[f'H{idx}'] = ''
                    row[f'Boxes {idx}'] = ''
                    row[f'VolWeight {idx}'] = ''
                    
            row['Total Volumetric Weight'] = round(total_vol_weight, 2)
            row['Status'] = d['status']
            row['Uploaded By'] = d['uploaded_by']
            
            export_data.append(row)
            
        conn.close()
        
        all_cols = ['S.No', 'Date', 'Docket No', 'Invoice No', 'Invoice Value', 'Actual Weight', 'Total Packages']
        for idx in range(1, max_dims + 1):
            all_cols.extend([f'L{idx}', f'B{idx}', f'H{idx}', f'Boxes {idx}', f'VolWeight {idx}'])
        all_cols.extend(['Total Volumetric Weight', 'Status', 'Uploaded By'])
        
        import pandas as pd
        import os
        from datetime import datetime
        from config import Config
        df = pd.DataFrame(export_data, columns=all_cols)
        
        if not os.path.exists(Config.EXPORT_FOLDER):
            os.makedirs(Config.EXPORT_FOLDER)
            
        filename = f"All_Dockets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = os.path.join(Config.EXPORT_FOLDER, filename)
        
        df.to_excel(filepath, index=False)
        return filename
"""

# Append to file before the end
text += new_export_all

with open('excel_exporter.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("excel_exporter.py updated with export_all")
