import pandas as pd
import sqlite3
import os
from datetime import datetime
from config import Config

def format_db_datetime(value):
    if not value:
        return ""
    try:
        from datetime import datetime, timedelta, timezone
        if hasattr(value, 'strftime'):
            dt = value
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            ist = timezone(timedelta(hours=5, minutes=30))
            return dt.astimezone(ist).strftime('%Y-%m-%d %I:%M %p')
            
        value_str = str(value)
        if len(value_str) >= 19 and value_str[10] in (' ', 'T'):
            clean_val = value_str[:19].replace('T', ' ')
            dt = datetime.strptime(clean_val, '%Y-%m-%d %H:%M:%S')
            dt = dt.replace(tzinfo=timezone.utc)
            ist = timezone(timedelta(hours=5, minutes=30))
            return dt.astimezone(ist).strftime('%Y-%m-%d %I:%M %p')
    except Exception:
        pass
    return str(value)[:19] if value else ""

def format_db_dateonly(value):
    dt_str = format_db_datetime(value)
    return dt_str[:10] if dt_str else ""


class ExcelExporter:

    @staticmethod
    def _get_db_connection():
        from database import get_db_connection
        return get_db_connection()

    @staticmethod
    def export_verified(start_date=None, end_date=None):
        """
        Exports only strictly VERIFIED dockets.
        Dynamically flattens dimension groups with strict column ordering.
        """
        conn = ExcelExporter._get_db_connection()
        
        query = "SELECT * FROM dockets WHERE status = 'VERIFIED' AND is_archived = 0"
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
            
        # Find maximum dimensions across all these dockets to fix column ordering
        max_dims = 0
        for d in dockets:
            count = conn.execute("SELECT COUNT(*) FROM dimension_groups WHERE docket_id = ?", (d['id'],)).fetchone()[0]
            if count > max_dims:
                max_dims = count
                
        export_data = []
        for i, d in enumerate(dockets, 1):
            date_only = format_db_dateonly(d['uploaded_at'])
            row = {
                'S.No': i,
                'Date': date_only,
                'Docket No': d['docket_number'],
                'Invoice No': d['invoice_no'],
                'Invoice Value': d['invoice_value'],
                'Actual Weight': d['actual_weight'],
                'Total Packages': d['total_packages']
            }
            
            dims = conn.execute("SELECT * FROM dimension_groups WHERE docket_id = ? ORDER BY group_index", (d['id'],)).fetchall()
            
            total_vol_weight = 0.0
            
            # Pad dimension columns to max_dims
            for idx in range(1, max_dims + 1):
                if idx <= len(dims):
                    dim = dims[idx - 1]
                    row[f'L{idx}'] = dim['length']
                    row[f'B{idx}'] = dim['breadth']
                    row[f'H{idx}'] = dim['height']
                    row[f'Boxes {idx}'] = dim['num_packages']
                    row[f'VolWeight {idx}'] = dim['dimension_weight']
                    if dim['dimension_weight']:
                        total_vol_weight += float(dim['dimension_weight'])
                else:
                    row[f'L{idx}'] = None
                    row[f'B{idx}'] = None
                    row[f'H{idx}'] = None
                    row[f'Boxes {idx}'] = None
                    row[f'VolWeight {idx}'] = None
            
            row['Total Volumetric Weight'] = round(total_vol_weight, 2)
            row['Status'] = d['status']
            row['Verified At'] = format_db_datetime(d['human_reviewed_at'])
            row['Verified By'] = d['human_reviewer']
            
            export_data.append(row)
            
        conn.close()
        
        # Use columns parameter to strictly enforce order
        all_cols = ['S.No', 'Date', 'Docket No', 'Invoice No', 'Invoice Value', 'Actual Weight', 'Total Packages']
        for idx in range(1, max_dims + 1):
            all_cols.extend([f'L{idx}', f'B{idx}', f'H{idx}', f'Boxes {idx}', f'VolWeight {idx}'])
        all_cols.extend(['Total Volumetric Weight', 'Status', 'Verified At', 'Verified By'])
        
        df = pd.DataFrame(export_data, columns=all_cols)
        
        if not os.path.exists(Config.EXPORT_FOLDER):
            os.makedirs(Config.EXPORT_FOLDER)
            
        filename = f"Verified_Dockets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = os.path.join(Config.EXPORT_FOLDER, filename)
        
        df.to_excel(filepath, index=False)
        return filename

    @staticmethod
    def export_rejected(start_date=None, end_date=None):
        """
        Exports strictly REJECTED dockets with strict column ordering.
        """
        conn = ExcelExporter._get_db_connection()
        query = "SELECT * FROM dockets WHERE status = 'REJECTED' AND is_archived = 0"
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
            
        # Find maximum dimensions across all these dockets to fix column ordering
        max_dims = 0
        for d in dockets:
            count = conn.execute("SELECT COUNT(*) FROM dimension_groups WHERE docket_id = ?", (d['id'],)).fetchone()[0]
            if count > max_dims:
                max_dims = count
                
        export_data = []
        for i, d in enumerate(dockets, 1):
            date_only = format_db_dateonly(d['uploaded_at'])
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
            
            # Pad dimension columns to max_dims
            for idx in range(1, max_dims + 1):
                if idx <= len(dims):
                    dim = dims[idx - 1]
                    row[f'L{idx}'] = dim['length']
                    row[f'B{idx}'] = dim['breadth']
                    row[f'H{idx}'] = dim['height']
                    row[f'Boxes {idx}'] = dim['num_packages']
                    row[f'VolWeight {idx}'] = dim['dimension_weight']
                    if dim['dimension_weight']:
                        total_vol_weight += float(dim['dimension_weight'])
                else:
                    row[f'L{idx}'] = None
                    row[f'B{idx}'] = None
                    row[f'H{idx}'] = None
                    row[f'Boxes {idx}'] = None
                    row[f'VolWeight {idx}'] = None
            
            row['Total Volumetric Weight'] = round(total_vol_weight, 2)
            row['Status'] = d['status']
            row['Rejection Reason'] = d['rejection_reasons']
            row['Original Filename'] = d['original_filename']
            row['Uploaded At'] = format_db_datetime(d['uploaded_at'])
            row['Uploaded By'] = d['uploaded_by']
            
            export_data.append(row)
            
        conn.close()
        
        # Use columns parameter to strictly enforce order
        all_cols = ['S.No', 'Date', 'Docket No', 'Invoice No', 'Invoice Value', 'Actual Weight', 'Total Packages']
        for idx in range(1, max_dims + 1):
            all_cols.extend([f'L{idx}', f'B{idx}', f'H{idx}', f'Boxes {idx}', f'VolWeight {idx}'])
        all_cols.extend(['Total Volumetric Weight', 'Status', 'Rejection Reason', 'Original Filename', 'Uploaded At', 'Uploaded By'])
        
        df = pd.DataFrame(export_data, columns=all_cols)
        
        if not os.path.exists(Config.EXPORT_FOLDER):
            os.makedirs(Config.EXPORT_FOLDER)
            
        filename = f"Rejected_Dockets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = os.path.join(Config.EXPORT_FOLDER, filename)
        
        df.to_excel(filepath, index=False)
        return filename

    @staticmethod
    def export_all(start_date=None, end_date=None):
        """
        Exports ALL dockets regardless of status.
        """
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
            date_only = format_db_dateonly(d['uploaded_at'])
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
                    row[f'B{idx}'] = dim['breadth']
                    row[f'H{idx}'] = dim['height']
                    row[f'Boxes {idx}'] = dim['num_packages']
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
