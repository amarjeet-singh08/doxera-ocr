import json
from calculation_engine import CalculationEngine

class ValidationService:

    @staticmethod
    def _is_empty(val):
        return val is None or str(val).strip() == ""

    @staticmethod
    def validate_docket_record(conn, docket_id):
        """
        Validates a docket from the database.
        Returns (is_valid, reasons)
        Does NOT update the database status here, the caller handles status logic.
        """
        docket = conn.execute('SELECT * FROM dockets WHERE id = ?', (docket_id,)).fetchone()
        dims = conn.execute('SELECT * FROM dimension_groups WHERE docket_id = ?', (docket_id,)).fetchall()
        
        reasons = []
        
        # 1. Basic Fields Complete?
        if ValidationService._is_empty(docket['docket_number']):
            reasons.append("Missing Docket Number")
        if ValidationService._is_empty(docket['actual_weight']):
            reasons.append("Missing Actual Weight")
        if ValidationService._is_empty(docket['total_packages']):
            reasons.append("Missing Total Packages")
            
        # 2. Dimensions Complete?
        if not dims:
            reasons.append("No dimension groups added")
            
        total_dim_boxes = 0
        for dim in dims:
            if ValidationService._is_empty(dim['length']) or ValidationService._is_empty(dim['breadth']) or ValidationService._is_empty(dim['height']) or ValidationService._is_empty(dim['num_packages']):
                reasons.append(f"Missing values in Dimension Row {dim['group_index'] + 1}")
            else:
                total_dim_boxes += dim['num_packages']
                
        # 3. Package Count Match
        if not ValidationService._is_empty(docket['total_packages']):
            try:
                tp = float(docket['total_packages'])
                if total_dim_boxes != tp:
                    reasons.append(f"PACKAGE_COUNT_MISMATCH: Total ({tp}) != Sum of Rows ({total_dim_boxes})")
            except ValueError:
                reasons.append("Invalid Total Packages number format")

        is_valid = len(reasons) == 0
        
        # Update rejection reasons in DB
        conn.execute('UPDATE dockets SET rejection_reasons = ? WHERE id = ?', (json.dumps(reasons), docket_id))
        
        return is_valid, reasons

    @staticmethod
    def transition_status_on_edit(conn, docket_id):
        """
        Called after a user saves an edit.
        Determines the new status and recalculates weights.
        """
        docket = conn.execute('SELECT status FROM dockets WHERE id = ?', (docket_id,)).fetchone()
        current_status = docket['status']
        
        # Recalculate all dimension weights
        dims = conn.execute('SELECT * FROM dimension_groups WHERE docket_id = ?', (docket_id,)).fetchall()
        for dim in dims:
            if not ValidationService._is_empty(dim['length']) and not ValidationService._is_empty(dim['breadth']) and not ValidationService._is_empty(dim['height']) and not ValidationService._is_empty(dim['num_packages']):
                w = CalculationEngine.calculate_dimension_weight(dim['length'], dim['breadth'], dim['height'], dim['num_packages'])
                conn.execute('UPDATE dimension_groups SET dimension_weight = ? WHERE id = ?', (w, dim['id']))
            else:
                conn.execute('UPDATE dimension_groups SET dimension_weight = NULL WHERE id = ?', (dim['id'],))
        
        # Run validation
        is_valid, _ = ValidationService.validate_docket_record(conn, docket_id)
        
        # Status logic
        new_status = current_status
        if current_status == 'VERIFIED':
            new_status = 'MODIFIED_REVERIFICATION_REQUIRED'
        elif current_status in ('UPLOADED', 'PROCESSING', 'FAILED', 'REJECTED'):
            new_status = 'REVIEW_REQUIRED'
        
        if new_status != current_status:
            conn.execute('UPDATE dockets SET status = ? WHERE id = ?', (new_status, docket_id))
            
        return is_valid
