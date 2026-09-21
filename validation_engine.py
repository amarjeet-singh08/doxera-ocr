import re
import json
from calculation_engine import CalculationEngine

class ValidationEngine:
    """
    Validates OCR output and determines docket status:
    - VERIFIED: All fields present and parseable with HIGH confidence
    - REVIEW_REQUIRED: Some fields are present but have LOW/MEDIUM confidence or parse issues
    - REJECTED: Critical fields are completely missing or UNREADABLE (except docket_number)
    """

    @staticmethod
    def _clean_number(val_str):
        """Clean a string value to extract a float. Fails if there are non-numeric chars."""
        if val_str is None or str(val_str).strip() == "":
            return None
        val_str = str(val_str).strip()
        # Reject AI placeholder echoes
        if 'extracted_' in val_str or 'here' in val_str or '...' in val_str:
            return None
        try:
            return float(val_str)
        except ValueError:
            return None

    @staticmethod
    def _parse_box_count(val_str):
        """Parse box count, handling the '0.1' = 1 box convention and '01' = 1."""
        if val_str is None or str(val_str).strip() == "":
            return None
        
        val_str = str(val_str).strip()
        
        # Handle "0.1" which means 1 box in NorthExpress dockets
        if val_str == '0.1':
            return 1.0
        # Handle "01", "02" etc. (but only if it's strictly digits to avoid aggressive cleaning)
        if re.match(r'^0\d+$', val_str):
            return float(val_str.lstrip('0') or '0')
            
        return ValidationEngine._clean_number(val_str)

    @staticmethod
    def _is_field_unreadable(field_data):
        """Check if a field's confidence is UNREADABLE or the value is empty/missing."""
        if not isinstance(field_data, dict):
            return True
        conf = field_data.get('confidence', 'UNREADABLE')
        val = field_data.get('value', '')
        return conf == 'UNREADABLE' or val is None or str(val).strip() == ''

    @staticmethod
    def _is_field_uncertain(field_data):
        """Check if a field has LOW or MEDIUM confidence (readable but uncertain)."""
        if not isinstance(field_data, dict):
            return False
        conf = field_data.get('confidence', 'UNREADABLE')
        return conf in ('LOW', 'MEDIUM')

    @staticmethod
    def validate_docket(ocr_data):
        """
        Validates the raw OCR JSON from the AI.
        
        Returns (status: str, reasons: list, parsed_data: dict)
        
        Status determination:
        - 'REJECTED': Any required field (except docket_number) is completely missing/UNREADABLE
        - 'REVIEW_REQUIRED': AI extraction was successful (even if perfect). Human verification is mandatory.
        """
        reasons = []
        review_reasons = []  # Soft issues
        reject_reasons = []  # Hard issues
        
        parsed_data = {
            'docket_number': None,
            'actual_weight': None,
            'total_packages': None,
            'dimensions': [],
            'ai_raw_response': json.dumps(ocr_data) if isinstance(ocr_data, dict) else ocr_data,
            'ai_confidence_notes': json.dumps(ocr_data.get('warnings', [])) if isinstance(ocr_data, dict) else '[]'
        }

        # 1. Check if OCR returned an error
        if isinstance(ocr_data, str):
            return 'REVIEW_REQUIRED', [ocr_data], parsed_data
        if 'error' in ocr_data:
            return 'REVIEW_REQUIRED', [f"{ocr_data['error']}"], parsed_data

        # ═══════════════════════════════════════════════════════
        # 2. DOCKET NUMBER — always accepted if present (clearly printed)
        # ═══════════════════════════════════════════════════════
        dkt_field = ocr_data.get('docket_number', {})
        dkt_str = dkt_field.get('value') if isinstance(dkt_field, dict) else None
        if isinstance(dkt_str, str) and ('extracted_' in dkt_str or 'here' in dkt_str or '...' in dkt_str):
            dkt_str = None
        if dkt_str is not None:
            dkt_str = str(dkt_str).strip()
        parsed_data['docket_number'] = dkt_str if dkt_str else None
        
        if not parsed_data['docket_number']:
            review_reasons.append("Docket number could not be extracted")

        # ═══════════════════════════════════════════════════════
        # 3. ACTUAL WEIGHT — required field
        # ═══════════════════════════════════════════════════════
        wt_field = ocr_data.get('actual_weight', {})
        if ValidationEngine._is_field_unreadable(wt_field):
            review_reasons.append("Actual weight is UNREADABLE or missing")
        elif ValidationEngine._is_field_uncertain(wt_field):
            review_reasons.append(f"Actual weight has uncertain confidence ({wt_field.get('confidence')})")
        
        wt_str = wt_field.get('value') if isinstance(wt_field, dict) else None
        if isinstance(wt_str, str) and ('extracted_' in wt_str or 'here' in wt_str):
            wt_str = None
        parsed_data['actual_weight'] = ValidationEngine._clean_number(wt_str)
        if wt_str and parsed_data['actual_weight'] is None:
            review_reasons.append(f"Actual weight '{wt_str}' could not be parsed as a number")

        # 3. Total Packages
        pkgs_field = ocr_data.get('total_packages', {})
        if ValidationEngine._is_field_unreadable(pkgs_field):
            review_reasons.append("Total packages is UNREADABLE or missing")
        elif ValidationEngine._is_field_uncertain(pkgs_field):
            review_reasons.append(f"Total packages has uncertain confidence ({pkgs_field.get('confidence')})")
        
        pkgs_str = pkgs_field.get('value') if isinstance(pkgs_field, dict) else None
        parsed_data['total_packages'] = ValidationEngine._clean_number(pkgs_str)
        if pkgs_str and parsed_data['total_packages'] is None:
            review_reasons.append(f"Total packages '{pkgs_str}' could not be parsed as a number")

        # 4. Dimension Groups
        dim_groups = ocr_data.get('dimension_groups', [])
        if not dim_groups:
            review_reasons.append("No dimension groups found in the docket")
        
        total_dim_boxes = 0
        
        for row_num, dim in enumerate(dim_groups, 1):
            if not isinstance(dim, dict):
                review_reasons.append(f"Row {row_num} has invalid format")
                continue
            
            # Check confidence for each key
            row_has_reject = False
            row_has_review = False
            for k, label in [('length', 'Length'), ('breadth', 'Breadth'), ('height', 'Height'), ('num_packages', 'Boxes')]:
                field = dim.get(k, {})
                if ValidationEngine._is_field_unreadable(field):
                    review_reasons.append(f"Row {row_num}: {label} is UNREADABLE or missing")
                    row_has_reject = True
                elif ValidationEngine._is_field_uncertain(field):
                    review_reasons.append(f"Row {row_num}: {label} has uncertain confidence ({field.get('confidence')})")
                    row_has_review = True
            
            # Parse values
            l_str = dim.get('length', {}).get('value', '') if isinstance(dim.get('length'), dict) else ''
            b_str = dim.get('breadth', {}).get('value', '') if isinstance(dim.get('breadth'), dict) else ''
            h_str = dim.get('height', {}).get('value', '') if isinstance(dim.get('height'), dict) else ''
            box_str = dim.get('num_packages', {}).get('value', '') if isinstance(dim.get('num_packages'), dict) else ''

            l_val = ValidationEngine._clean_number(l_str)
            b_val = ValidationEngine._clean_number(b_str)
            h_val = ValidationEngine._clean_number(h_str)
            box_val = ValidationEngine._parse_box_count(box_str)
            
            if None in [l_val, b_val, h_val, box_val]:
                if not row_has_reject:
                    review_reasons.append(f"Row {row_num}: Could not parse all dimension values as strict numbers")
                # Keep the unparseable row so user can edit it
                
            if box_val is not None:
                total_dim_boxes += box_val
            
            # Calculate dimension weight
            dim_weight = None
            if None not in [l_val, b_val, h_val, box_val]:
                dim_weight = CalculationEngine.calculate_dimension_weight(l_val, b_val, h_val, box_val)
            
            parsed_data['dimensions'].append({
                'length': l_val,
                'breadth': b_val,
                'height': h_val,
                'num_packages': int(box_val) if box_val is not None else None,
                'dimension_weight': dim_weight,
                'ai_original_length': l_str,
                'ai_original_breadth': b_str,
                'ai_original_height': h_str,
                'ai_original_num_packages': box_str
            })

        # ═══════════════════════════════════════════════════════
        # 6. PACKAGE COUNT MATCH — only if both total and rows are available
        # ═══════════════════════════════════════════════════════
        if parsed_data['total_packages'] is not None and parsed_data['dimensions'] and not reject_reasons:
            if int(total_dim_boxes) != int(parsed_data['total_packages']):
                review_reasons.append(f"PACKAGE_COUNT_MISMATCH: Total ({int(parsed_data['total_packages'])}) != Sum of Rows ({int(total_dim_boxes)})")

        # ═══════════════════════════════════════════════════════
        # 7. DETERMINE FINAL STATUS
        # ═══════════════════════════════════════════════════════
        all_reasons = reject_reasons + review_reasons
        
        # NEVER set to VERIFIED automatically. Human review is mandatory.
        if reject_reasons:
            status = 'REJECTED'
        else:
            status = 'REVIEW_REQUIRED'
        
        parsed_data['rejection_reasons'] = json.dumps(all_reasons)
        
        return status, all_reasons, parsed_data
