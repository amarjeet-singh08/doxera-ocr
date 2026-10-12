# DOXERA Sales Intelligence & Analytics Engine
# =========================================================
# Processes Billed MIS, Unbilled MIS, and Booking Master Register,
# cross-references consignments via foreign-key AWB numbers,
# extracts exact transport modes (Air, Surface, Train),
# correlates revenue against client sales managers, and
# generates executive boardroom reports, PDF, and PowerPoint presentations.

import os
import re
import json
import csv
import io
from datetime import datetime
import pandas as pd
from config import Config
from database import get_db_connection

def format_inr(number):
    """Format floating point amount into Indian numbering system (e.g. 1,19,24,625.02)"""
    try:
        val = float(number)
    except (ValueError, TypeError):
        return "0.00"
    
    is_negative = val < 0
    val = abs(val)
    parts = f"{val:.2f}".split(".")
    int_part = parts[0]
    dec_part = parts[1]
    
    if len(int_part) <= 3:
        formatted_int = int_part
    else:
        last3 = int_part[-3:]
        rest = int_part[:-3]
        formatted_rest = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", rest)
        formatted_int = formatted_rest + "," + last3
        
    return f"{'-' if is_negative else ''}₹ {formatted_int}.{dec_part}"

def normalize_column_name(col_str):
    """
    Intelligently map messy, variable logistics ERP column names
    to clean, unique internal dictionary keys without naming collisions.
    """
    raw = str(col_str).strip().lower()
    clean = re.sub(r"[^a-z0-9]", "", raw)
    
    # Coloader
    if "coloader" in clean:
        return "coloader_awb" if "awb" in clean else "coloader_name"
    # Booking & Service Modes
    if "bookingmode" in clean:
        return "booking_mode"
    if "servicemode" in clean:
        return "service_mode"
    # Handover
    if "handover" in clean:
        return "handover_weight" if ("wt" in clean or "weight" in clean) else "handover_date"
    # Entry
    if "entry" in clean:
        if "modified" in clean:
            return "entry_modified_by" if "by" in clean else "entry_modified_date"
        return "entry_done_by" if "by" in clean else "entry_date"
    # Billing & Invoices
    if "bill" in clean:
        return "bill_date" if "date" in clean else "bill_no"
    if "invoiceno" in clean:
        return "invoice_no"
    if "invoicevalue" in clean or "invval" in clean:
        return "invoice_value"
    # AWB / Docket number (Foreign Key)
    if "awb" in clean or "docket" in clean or "cnno" in clean or "consignment" in clean:
        return "awb_no"
    # Customer
    if "customercode" in clean or "custcode" in clean:
        return "customer_code"
    if "customer" in clean or "party" in clean or "client" in clean:
        return "customer_name"
    # Financial Freight Amount
    if "totalamt" in clean or "totalamount" in clean or "freight" in clean or clean == "amount" or "netamount" in clean:
        return "total_amt"
    # Weights & Packages
    if "chargabl" in clean or "chargable" in clean:
        return "chargeable_weight"
    if "volweight" in clean or "volumetric" in clean:
        return "vol_weight"
    if "boxes" in clean or "pkgs" in clean or "packages" in clean:
        return "boxes"
    if "weight" in clean or "wt" in clean:
        return "weight"
    # Geographics
    if "origin" in clean:
        return "origin_pincode" if "pin" in clean else "origin"
    if "destination" in clean or "dest" in clean:
        return "dest_pincode" if "pin" in clean else "destination"
    # Parties & Locations
    if "shipper" in clean:
        return "shipper"
    if "consignee" in clean or "cnee" in clean:
        return "consignee_address" if "address" in clean else "consignee"
    if "cnor" in clean or "consignor" in clean:
        return "consignor"
    # Operational Dates & Status
    if "appoint" in clean:
        return "appoint_date"
    if "status" in clean:
        return "status_date" if "date" in clean else "delivery_status"
    if "curlocation" in clean:
        return "current_location"
    if "date" in clean:
        return "date"
    return clean

def read_mis_file(file_storage_or_path, original_filename=""):
    """
    Intelligent ERP File Preprocessor:
    Handles raw files downloaded directly from logistics software
    without requiring manual Excel conversion, text-to-columns, or row adjustments.
    """
    if isinstance(file_storage_or_path, str):
        with open(file_storage_or_path, "rb") as fp:
            content_bytes = fp.read()
        filename = os.path.basename(file_storage_or_path)
    else:
        file_storage_or_path.seek(0)
        content_bytes = file_storage_or_path.read()
        filename = original_filename or getattr(file_storage_or_path, "filename", "upload.xlsx")

    df = None
    errors = []

    is_zip = content_bytes.startswith(b"PK\x03\x04")
    is_ole = content_bytes.startswith(b"\xd0\xcf\x11\xe0")

    # 1. Binary XLSX
    if is_zip:
        try:
            df = pd.read_excel(io.BytesIO(content_bytes), engine="openpyxl")
        except Exception as e:
            errors.append(f"openpyxl failed: {e}")

    # 2. Binary XLS
    elif is_ole:
        try:
            df = pd.read_excel(io.BytesIO(content_bytes))
        except Exception as e:
            errors.append(f"Legacy xls reader failed: {e}")

    # 3. Text / TSV / HTML disguised as XLS
    if df is None:
        sample_head = content_bytes[:2048].lower()
        if b"<html" in sample_head or b"<table" in sample_head:
            try:
                dfs = pd.read_html(io.BytesIO(content_bytes))
                if dfs:
                    df = dfs[0]
            except Exception as e:
                errors.append(f"HTML table reader failed: {e}")

        if df is None:
            text_content = ""
            for enc in ("utf-8-sig", "utf-8", "cp1252", "latin1", "iso-8859-1"):
                try:
                    text_content = content_bytes.decode(enc)
                    break
                except Exception:
                    continue

            if text_content:
                lines = text_content.splitlines()
                header_idx = -1
                detected_sep = '\t'
                
                # Sniff header row within first 35 lines
                for idx, line in enumerate(lines[:35]):
                    l_lower = line.lower()
                    if ("awb" in l_lower or "docket" in l_lower) and (
                        "cust" in l_lower or "party" in l_lower or "amt" in l_lower or
                        "amount" in l_lower or "weight" in l_lower or "dest" in l_lower or "mode" in l_lower
                    ):
                        header_idx = idx
                        if "\t" in line: detected_sep = "\t"
                        elif "," in line: detected_sep = ","
                        elif ";" in line: detected_sep = ";"
                        elif "|" in line: detected_sep = "|"
                        break

                try:
                    if header_idx != -1:
                        valid_text = "\n".join(lines[header_idx:])
                        df = pd.read_csv(io.StringIO(valid_text), sep=detected_sep, engine="python")
                    else:
                        df = pd.read_csv(io.StringIO(text_content), sep=None, engine="python")
                except Exception as e:
                    errors.append(f"Smart text parser failed: {e}")

    if df is None or df.empty:
        raise ValueError(f"Could not parse file '{filename}'. Details: {'; '.join(errors)}")

    # 4. Auto Row Adjustment (if header row is nested inside data rows)
    cols_str = " ".join(str(c).lower() for c in df.columns)
    if "awb" not in cols_str and "docket" not in cols_str:
        for idx in range(min(len(df), 25)):
            row_vals = [str(v).lower() for v in df.iloc[idx].values if pd.notna(v)]
            row_str = " ".join(row_vals)
            if ("awb" in row_str or "docket" in row_str) and (
                "cust" in row_str or "amount" in row_str or "amt" in row_str or "dest" in row_str or "weight" in row_str
            ):
                new_cols = df.iloc[idx].values
                df = df.iloc[idx + 1:].copy()
                df.columns = new_cols
                break

    # 5. Standardize column headers without name collisions
    col_mapping = {}
    for col in df.columns:
        norm = normalize_column_name(col)
        col_mapping[col] = norm
    df = df.rename(columns=col_mapping)

    # 6. Auto-Clean Footer Rows (totals, end-of-report markers)
    if "awb_no" in df.columns:
        # If duplicate awb_no columns exist, take the first one
        if isinstance(df["awb_no"], pd.DataFrame):
            df["awb_no"] = df["awb_no"].iloc[:, 0]

        def is_valid_awb(val):
            if pd.isna(val): return False
            s = str(val).strip().lower()
            if not s or s in ("nan", "none", "0"): return False
            if "total" in s or "subtotal" in s or "end of report" in s or "page" in s: return False
            return True

        df = df[df["awb_no"].apply(is_valid_awb)].copy()

    return df

def get_customer_sales_rep_map():
    """Fetch current customer to sales person mapping from SQLite."""
    conn = get_db_connection()
    c = conn.execute("SELECT customer_code, customer_name, sales_person FROM sales_customers").fetchall()
    conn.close()

    code_map = {}
    name_map = {}
    for row in c:
        rep = (row["sales_person"] or "NEL").strip()
        if not rep or rep.lower() in ("none", "null"):
            rep = "NEL"
        if row["customer_code"]:
            code_map[str(row["customer_code"]).strip().upper()] = rep
        if row["customer_name"]:
            name_map[str(row["customer_name"]).strip().upper()] = rep

    return code_map, name_map


# ═════════════════════════════════════════════════════════════════════
# 3-WAY CORRELATION & ANALYTICS PIPELINE
def extract_month_info(date_str):
    """
    Parses dates in formats like '01-09-2026 00:00', '2026-09-01', '01/09/2026', '01-Sep-2026'.
    Returns (clean_date, month_key, month_label)
    e.g. ('01-09-2026', '2026-09', 'September 2026')
    """
    if not date_str or str(date_str).strip().lower() in ('nan', 'none', '', 'nat'):
        return '', 'Undated', 'Undated'
    
    clean = str(date_str).strip().split(' ')[0]
    for fmt in ('%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%b-%Y', '%d-%B-%Y'):
        try:
            dt = datetime.strptime(clean, fmt)
            return dt.strftime('%d-%m-%Y'), dt.strftime('%Y-%m'), dt.strftime('%B %Y')
        except Exception:
            pass
            
    m = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', clean)
    if m:
        d, mon, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            dt = datetime(y, mon, d)
            return dt.strftime('%d-%m-%Y'), dt.strftime('%Y-%m'), dt.strftime('%B %Y')
        except Exception:
            pass
            
    return clean, 'Other', 'Other'

def compute_segment_metrics(shipment_list):
    """
    Computes all aggregates (summary, sales reps, customers, daily trend, modes, destinations)
    for a given list of shipments (used for All, Billed, and Unbilled segments).
    """
    total_sales = sum(s["total_amt"] for s in shipment_list)
    total_weight = sum(s["weight"] for s in shipment_list)
    total_count = len(shipment_list)
    avg_ticket = (total_sales / total_count) if total_count > 0 else 0.0

    # Sales by Sales Rep
    rep_stats = {}
    for s in shipment_list:
        rep = s["sales_person"]
        if rep not in rep_stats:
            rep_stats[rep] = {"sales": 0.0, "shipments": 0, "weight": 0.0, "customers": set()}
        rep_stats[rep]["sales"] += s["total_amt"]
        rep_stats[rep]["shipments"] += 1
        rep_stats[rep]["weight"] += s["weight"]
        rep_stats[rep]["customers"].add(s["customer_name"])

    sales_reps_list = []
    for rep, stat in rep_stats.items():
        share = (stat["sales"] / total_sales * 100) if total_sales > 0 else 0.0
        sales_reps_list.append({
            "name": rep,
            "sales": round(stat["sales"], 2),
            "shipments": stat["shipments"],
            "weight": round(stat["weight"], 2),
            "customer_count": len(stat["customers"]),
            "share_pct": round(share, 1)
        })
    sales_reps_list.sort(key=lambda x: x["sales"], reverse=True)
    top_rep = sales_reps_list[0]["name"] if sales_reps_list else "NEL"

    # Sales by Customer
    cust_stats = {}
    for s in shipment_list:
        cname = s["customer_name"]
        if cname not in cust_stats:
            cust_stats[cname] = {
                "sales": 0.0,
                "shipments": 0,
                "weight": 0.0,
                "sales_person": s["sales_person"],
                "customer_code": s["customer_code"]
            }
        cust_stats[cname]["sales"] += s["total_amt"]
        cust_stats[cname]["shipments"] += 1
        cust_stats[cname]["weight"] += s["weight"]

    customers_list = []
    for cname, stat in cust_stats.items():
        share = (stat["sales"] / total_sales * 100) if total_sales > 0 else 0.0
        customers_list.append({
            "name": cname,
            "code": stat["customer_code"],
            "sales": round(stat["sales"], 2),
            "shipments": stat["shipments"],
            "weight": round(stat["weight"], 2),
            "sales_person": stat["sales_person"],
            "share_pct": round(share, 1)
        })
    customers_list.sort(key=lambda x: x["sales"], reverse=True)
    top_customer = customers_list[0]["name"] if customers_list else "None"

    # Sales by Date
    date_stats = {}
    for s in shipment_list:
        d = s["date"] or "Undated"
        if d not in date_stats:
            date_stats[d] = {"sales": 0.0, "shipments": 0}
        date_stats[d]["sales"] += s["total_amt"]
        date_stats[d]["shipments"] += 1

    def parse_dt(d_str):
        for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
            try: return datetime.strptime(d_str, fmt)
            except: pass
        return datetime.min

    sorted_dates = sorted(date_stats.keys(), key=parse_dt)
    daily_sales_list = [{
        "date": d,
        "sales": round(date_stats[d]["sales"], 2),
        "shipments": date_stats[d]["shipments"]
    } for d in sorted_dates]

    # Service / Transport Mode breakdown (Air, Surface, Train)
    mode_stats = {}
    for s in shipment_list:
        m = s["transport_mode"] or s.get("service_mode") or "Surface"
        m = m.capitalize()
        if m not in mode_stats:
            mode_stats[m] = {"sales": 0.0, "shipments": 0}
        mode_stats[m]["sales"] += s["total_amt"]
        mode_stats[m]["shipments"] += 1

    mode_list = []
    for m, stat in mode_stats.items():
        share = (stat["sales"] / total_sales * 100) if total_sales > 0 else 0.0
        mode_list.append({
            "mode": m,
            "sales": round(stat["sales"], 2),
            "shipments": stat["shipments"],
            "share_pct": round(share, 1)
        })
    mode_list.sort(key=lambda x: x["sales"], reverse=True)

    # Destination Breakdown
    dest_stats = {}
    for s in shipment_list:
        dest = s["destination"] or "Unknown"
        if dest not in dest_stats:
            dest_stats[dest] = {"sales": 0.0, "shipments": 0}
        dest_stats[dest]["sales"] += s["total_amt"]
        dest_stats[dest]["shipments"] += 1

    dest_list = [{
        "city": dest,
        "sales": round(stat["sales"], 2),
        "shipments": stat["shipments"]
    } for dest, stat in sorted(dest_stats.items(), key=lambda x: x[1]["sales"], reverse=True)]

    return {
        "summary": {
            "total_sales": round(total_sales, 2),
            "total_shipments": total_count,
            "total_weight": round(total_weight, 2),
            "avg_ticket": round(avg_ticket, 2),
            "top_rep": top_rep,
            "top_customer": top_customer
        },
        "sales_reps": sales_reps_list,
        "customers": customers_list,
        "daily_sales": daily_sales_list,
        "modes": mode_list,
        "destinations": dest_list[:20]
    }

def parse_and_process_sales_3way(billed_file, unbilled_file, booking_file, billed_name, unbilled_name, booking_name, created_by="admin", report_title=""):
    """
    3-Way Ingestion and Correlation Pipeline:
    1. Billed MIS -> provides Billed amounts per AWB.
    2. Unbilled MIS -> provides Unbilled amounts per AWB.
    3. Booking Master Register -> provides BookingMode (Air, Surface, Train),
       BillNo, Delivery Status, Boxes, Origin, Destination for all shipments!
    """
    try:
        billed_df = read_mis_file(billed_file, billed_name)
    except Exception as e:
        return None, f"Could not parse Billed MIS Sheet ({billed_name}): {str(e)}"

    try:
        unbilled_df = read_mis_file(unbilled_file, unbilled_name)
    except Exception as e:
        return None, f"Could not parse Unbilled MIS Sheet ({unbilled_name}): {str(e)}"

    try:
        booking_df = read_mis_file(booking_file, booking_name)
    except Exception as e:
        return None, f"Could not parse Booking Master Register ({booking_name}): {str(e)}"

    # Validate AWB in all 3 sheets
    if "awb_no" not in billed_df.columns:
        return None, f"Billed sheet ({billed_name}) is missing the 'AWB / Docket Number' column."
    if "awb_no" not in unbilled_df.columns:
        return None, f"Unbilled sheet ({unbilled_name}) is missing the 'AWB / Docket Number' column."
    if "awb_no" not in booking_df.columns:
        return None, f"Booking Master Register ({booking_name}) is missing the 'AWB / Docket Number' column."

    code_to_rep, name_to_rep = get_customer_sales_rep_map()

    # 1. Build lookup dictionaries for Billed & Unbilled amounts
    def build_amt_map(df):
        m = {}
        for _, row in df.iterrows():
            awb = str(row.get("awb_no", "")).strip()
            if not awb or awb.lower() in ("nan", "none", "0"):
                continue
            try: amt = float(row.get("total_amt", 0) or 0)
            except: amt = 0.0
            m[awb] = amt
        return m

    billed_amt_map = build_amt_map(billed_df)
    unbilled_amt_map = build_amt_map(unbilled_df)

    # 2. Iterate through Booking Master Register as the source of truth
    all_shipments = []
    seen_awbs = set()

    for _, row in booking_df.iterrows():
        awb = str(row.get("awb_no", "")).strip()
        if not awb or awb.lower() in ("nan", "none", "0") or awb in seen_awbs:
            continue
        seen_awbs.add(awb)

        # Date & Month Detection
        raw_date = str(row.get("date", "")).strip()
        clean_date, month_key, month_label = extract_month_info(raw_date)

        # Customer Code & Name
        code = str(row.get("customer_code", "")).strip().upper()
        if code == "NAN": code = ""
        cname = str(row.get("customer_name", "")).strip()
        if cname == "NAN": cname = ""

        # Assign Sales Representative
        rep = "NEL"
        if code in code_to_rep:
            rep = code_to_rep[code]
        elif cname.upper() in name_to_rep:
            rep = name_to_rep[cname.upper()]

        # Mode of Transport (Air, Surface, Train)
        mode = str(row.get("booking_mode", "") or row.get("mode", "") or "Surface").strip()
        if mode.lower() in ("nan", "none", ""): mode = "Surface"
        mode = mode.capitalize()

        # Weight
        try: wt = float(row.get("weight", 0) or 0)
        except: wt = 0.0

        # Chargeable weight
        try: chg_wt = float(row.get("chargeable_weight", 0) or 0)
        except: chg_wt = wt

        # Boxes
        try: boxes = int(float(row.get("boxes", 1) or 1))
        except: boxes = 1

        # Bill Number & Delivery Status
        bill_no = str(row.get("bill_no", "")).strip()
        if bill_no.lower() in ("nan", "none", "0"): bill_no = ""
        delivery_status = str(row.get("delivery_status", "") or row.get("status", "")).strip()

        # Amounts from Billed and Unbilled sheets
        b_amt = billed_amt_map.get(awb, 0.0)
        u_amt = unbilled_amt_map.get(awb, 0.0)

        # Determine billing status
        if awb in billed_amt_map and awb in unbilled_amt_map:
            billing_tag = "COMBINED"
            total_amt = b_amt + u_amt
        elif awb in billed_amt_map:
            billing_tag = "BILLED"
            total_amt = b_amt
        elif awb in unbilled_amt_map:
            billing_tag = "UNBILLED"
            total_amt = u_amt
        else:
            # Fallback based on BillNo
            if bill_no:
                billing_tag = "BILLED"
                total_amt = 0.0
            else:
                billing_tag = "UNBILLED"
                total_amt = 0.0

        all_shipments.append({
            "awb_no": awb,
            "date": clean_date,
            "month_key": month_key,
            "month_label": month_label,
            "customer_code": code,
            "customer_name": cname or code or "General Customer",
            "sales_person": rep,
            "shipper": str(row.get("shipper", "")).strip(),
            "consignee": str(row.get("consignee", "")).strip(),
            "origin": str(row.get("origin", "")).strip(),
            "destination": str(row.get("destination", "")).strip() or "Unknown",
            "service_mode": str(row.get("service_mode", mode)),
            "transport_mode": mode,
            "weight": wt,
            "chargeable_weight": chg_wt,
            "boxes": boxes,
            "appoint_date": str(row.get("appoint_date", "")).strip(),
            "bill_no": bill_no,
            "delivery_status": delivery_status,
            "billed_amt": round(b_amt, 2),
            "unbilled_amt": round(u_amt, 2),
            "total_amt": round(total_amt, 2),
            "source_type": billing_tag
        })

    if not all_shipments:
        return None, "Zero valid shipments correlated. Please verify that AWB docket numbers match across sheets."

    # Separate segments for dashboard tabs
    billed_shipments = [s for s in all_shipments if s["source_type"] in ("BILLED", "COMBINED")]
    unbilled_shipments = [s for s in all_shipments if s["source_type"] in ("UNBILLED", "COMBINED")]

    # 3. Compute Metrics for All, Billed, and Unbilled Segments
    metrics_all = compute_segment_metrics(all_shipments)
    metrics_billed = compute_segment_metrics(billed_shipments)
    metrics_unbilled = compute_segment_metrics(unbilled_shipments)

    # Detect all unique months in the dataset
    months_dict = {}
    for s in all_shipments:
        mk = s["month_key"]
        ml = s["month_label"]
        if mk not in ("Undated", "Other"):
            if mk not in months_dict:
                months_dict[mk] = {"key": mk, "label": ml, "count": 0, "sales": 0.0}
            months_dict[mk]["count"] += 1
            months_dict[mk]["sales"] += s["total_amt"]

    sorted_months = sorted(months_dict.values(), key=lambda x: x["key"])
    for m in sorted_months:
        m["sales"] = round(m["sales"], 2)

    # Determine period label
    if len(sorted_months) == 1:
        period_label = sorted_months[0]["label"]
    elif len(sorted_months) > 1:
        period_label = f"{sorted_months[0]['label']} – {sorted_months[-1]['label']}"
    else:
        period_label = "Current Period"

    # Pre-compute metrics for each month separately (enables instant multi-month separation on dashboard)
    by_month_metrics = {}
    for m in sorted_months:
        mk = m["key"]
        m_shipments = [s for s in all_shipments if s["month_key"] == mk]
        m_billed = [s for s in m_shipments if s["source_type"] in ("BILLED", "COMBINED")]
        m_unbilled = [s for s in m_shipments if s["source_type"] in ("UNBILLED", "COMBINED")]
        by_month_metrics[mk] = {
            "summary": {
                "period_label": m["label"],
                "total_sales": round(sum(s["total_amt"] for s in m_shipments), 2),
                "billed_sales": round(sum(s["total_amt"] for s in m_billed), 2),
                "unbilled_sales": round(sum(s["total_amt"] for s in m_unbilled), 2),
                "total_shipments": len(m_shipments),
                "billed_shipments": len(m_billed),
                "unbilled_shipments": len(m_unbilled),
                "total_weight": round(sum(s["weight"] for s in m_shipments), 2),
                "avg_ticket": round((sum(s["total_amt"] for s in m_shipments) / len(m_shipments)) if m_shipments else 0.0, 2),
            },
            "all": compute_segment_metrics(m_shipments),
            "billed": compute_segment_metrics(m_billed),
            "unbilled": compute_segment_metrics(m_unbilled),
        }

    if not report_title:
        report_title = f"North Express Logistics - Executive Sales Intelligence ({period_label})"

    # Consolidated JSON bundle for instant client-side switching
    report_data = {
        "summary": {
            "period_label": period_label,
            "total_sales": metrics_all["summary"]["total_sales"],
            "billed_sales": metrics_billed["summary"]["total_sales"],
            "unbilled_sales": metrics_unbilled["summary"]["total_sales"],
            "total_shipments": metrics_all["summary"]["total_shipments"],
            "billed_shipments": metrics_billed["summary"]["total_shipments"],
            "unbilled_shipments": metrics_unbilled["summary"]["total_shipments"],
            "total_weight": metrics_all["summary"]["total_weight"],
            "avg_ticket": metrics_all["summary"]["avg_ticket"],
            "top_rep": metrics_all["summary"]["top_rep"],
            "top_customer": metrics_all["summary"]["top_customer"]
        },
        "months": sorted_months,
        "by_month": by_month_metrics,
        "all": metrics_all,
        "billed": metrics_billed,
        "unbilled": metrics_unbilled,
        "shipments_sample": all_shipments[:250]
    }

    # 4. Save to database (SQLite & PostgreSQL compatible)
    report_id = f"SR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    conn = get_db_connection()
    is_pg = getattr(conn, 'is_postgres', False)

    if is_pg:
        c = conn.execute('''
            INSERT INTO sales_reports (
                report_id, title, period_label, billed_filename, unbilled_filename, booking_filename,
                total_sales, billed_sales, unbilled_sales, total_shipments, total_weight,
                avg_shipment_value, top_sales_person, top_customer, report_data_json, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id
        ''', (
            report_id, report_title, period_label, billed_name, unbilled_name, booking_name,
            metrics_all["summary"]["total_sales"], metrics_billed["summary"]["total_sales"],
            metrics_unbilled["summary"]["total_sales"], metrics_all["summary"]["total_shipments"],
            metrics_all["summary"]["total_weight"], metrics_all["summary"]["avg_ticket"],
            metrics_all["summary"]["top_rep"], metrics_all["summary"]["top_customer"],
            json.dumps(report_data), created_by
        ))
        db_report_id = c.fetchone()[0]
    else:
        c = conn.execute('''
            INSERT INTO sales_reports (
                report_id, title, period_label, billed_filename, unbilled_filename, booking_filename,
                total_sales, billed_sales, unbilled_sales, total_shipments, total_weight,
                avg_shipment_value, top_sales_person, top_customer, report_data_json, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            report_id, report_title, period_label, billed_name, unbilled_name, booking_name,
            metrics_all["summary"]["total_sales"], metrics_billed["summary"]["total_sales"],
            metrics_unbilled["summary"]["total_sales"], metrics_all["summary"]["total_shipments"],
            metrics_all["summary"]["total_weight"], metrics_all["summary"]["avg_ticket"],
            metrics_all["summary"]["top_rep"], metrics_all["summary"]["top_customer"],
            json.dumps(report_data), created_by
        ))
        db_report_id = c.lastrowid

    # Batch insert shipments
    shipment_rows = []
    for s in all_shipments:
        shipment_rows.append((
            db_report_id, s["awb_no"], s["date"], s["customer_code"], s["customer_name"],
            s["sales_person"], s["shipper"], s["consignee"], s["origin"], s["destination"],
            s["service_mode"], s["transport_mode"], s["weight"], s["chargeable_weight"],
            s["boxes"], s["appoint_date"], s["bill_no"], s["delivery_status"],
            s["total_amt"], s["source_type"]
        ))

    conn.executemany('''
        INSERT INTO sales_shipments (
            report_id, awb_no, booking_date, customer_code, customer_name,
            sales_person, shipper, consignee, origin, destination,
            service_mode, transport_mode, weight, chargeable_weight, boxes,
            appoint_date, bill_no, delivery_status, total_amt, source_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', shipment_rows)

    conn.commit()
    conn.close()

    return db_report_id, None


# ═════════════════════════════════════════════════════════════════════
# EXECUTIVE EXPORT: POWERPOINT PRESENTATION (.PPTX)
# ═════════════════════════════════════════════════════════════════════

def generate_sales_pptx(report_row, report_data):
    """
    Generate an executive 16:9 PowerPoint presentation with 6 distinct slides:
    Slide 1: Executive Overview (Combined Turnovers)
    Slide 2: Billed vs Unbilled Comparative Analysis
    Slide 3: Transport Modes Breakdown (Air vs Surface vs Train)
    Slide 4: Sales Team Leaderboard & Contribution
    Slide 5: Top Client Accounts Ranking
    Slide 6: Major Delivery Hubs & Destination Volumes
    """
    import pptx
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE

    prs = pptx.Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Brand Colors
    C_NAVY = RGBColor(11, 19, 43)
    C_BLUE = RGBColor(37, 99, 235)
    C_WHITE = RGBColor(255, 255, 255)
    C_SLATE = RGBColor(100, 116, 139)
    C_DARK = RGBColor(15, 23, 42)

    logo_path = os.path.join(Config.BASE_DIR, "static", "doxera_logo.png")

    def add_header(slide, title_text, category="SALES INTELLIGENCE"):
        header_shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(1.1))
        header_shape.fill.solid()
        header_shape.fill.fore_color.rgb = C_NAVY
        header_shape.line.fill.background()

        tx = slide.shapes.add_textbox(Inches(0.8), Inches(0.18), Inches(9.5), Inches(0.8))
        tf = tx.text_frame
        tf.word_wrap = True
        p1 = tf.paragraphs[0]
        p1.text = category.upper()
        p1.font.size = Pt(10)
        p1.font.bold = True
        p1.font.color.rgb = RGBColor(96, 165, 250)
        
        p2 = tf.add_paragraph()
        p2.text = title_text
        p2.font.size = Pt(20)
        p2.font.bold = True
        p2.font.color.rgb = C_WHITE

        if os.path.exists(logo_path):
            slide.shapes.add_picture(logo_path, Inches(11.2), Inches(0.2), width=Inches(1.5))

    summary = report_data.get("summary", {})
    all_metrics = report_data.get("all", {})
    billed_metrics = report_data.get("billed", {})
    unbilled_metrics = report_data.get("unbilled", {})

    # SLIDE 1: EXECUTIVE OVERVIEW
    slide1 = prs.slides.add_slide(blank_layout)
    add_header(slide1, f"Executive Overview • {summary.get('period_label', 'Report')}")

    cards_data = [
        ("GRAND TOTAL REVENUE", format_inr(summary.get("total_sales", 0)), RGBColor(37, 99, 235)),
        ("TOTAL CONSIGNMENTS", f"{summary.get('total_shipments', 0):,} AWBs", RGBColor(16, 185, 129)),
        ("TOTAL CARGO MOVED", f"{summary.get('total_weight', 0):,.1f} Kg", RGBColor(245, 158, 11)),
        ("TOP SALES REP", str(summary.get("top_rep", "NEL")), RGBColor(139, 92, 246))
    ]

    card_w = Inches(2.7)
    card_h = Inches(1.6)
    card_gap = Inches(0.3)
    start_x = Inches(0.8)

    for i, (label, val, accent) in enumerate(cards_data):
        x = start_x + (i * (card_w + card_gap))
        y = Inches(1.5)
        card = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, card_w, card_h)
        card.fill.solid()
        card.fill.fore_color.rgb = C_WHITE
        card.line.color.rgb = RGBColor(226, 232, 240)

        tx = slide1.shapes.add_textbox(x + Inches(0.15), y + Inches(0.2), card_w - Inches(0.3), card_h - Inches(0.4))
        tf = tx.text_frame
        p = tf.paragraphs[0]
        p.text = label
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = C_SLATE
        
        p2 = tf.add_paragraph()
        p2.text = val
        p2.font.size = Pt(20)
        p2.font.bold = True
        p2.font.color.rgb = accent

    info_box = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(3.5), Inches(11.733), Inches(3.4))
    info_box.fill.solid()
    info_box.fill.fore_color.rgb = RGBColor(241, 245, 249)
    info_box.line.color.rgb = RGBColor(203, 213, 225)

    tx_info = slide1.shapes.add_textbox(Inches(1.2), Inches(3.8), Inches(10.9), Inches(2.8))
    tf_info = tx_info.text_frame
    tf_info.word_wrap = True

    h = tf_info.paragraphs[0]
    h.text = "Executive Highlights & Segment Breakdown"
    h.font.size = Pt(16)
    h.font.bold = True
    h.font.color.rgb = C_NAVY

    highlights = [
        f"• Grand Turnover: {format_inr(summary.get('total_sales', 0))} across {summary.get('total_shipments', 0):,} verified freight consignments.",
        f"• Billed Freight Revenue: {format_inr(summary.get('billed_sales', 0))} ({summary.get('billed_shipments', 0):,} dockets invoiced).",
        f"• Unbilled Freight Revenue: {format_inr(summary.get('unbilled_sales', 0))} ({summary.get('unbilled_shipments', 0):,} dockets pending billing).",
        f"• Leading Sales Rep: {summary.get('top_rep', 'NEL')} drove the primary turnover during this period.",
        f"• Tri-Factor Correlation: Synthesized across Billed MIS, Unbilled MIS, and Operations Booking Register."
    ]
    for bullet in highlights:
        p = tf_info.add_paragraph()
        p.text = bullet
        p.font.size = Pt(13)
        p.font.color.rgb = C_DARK
        p.space_before = Pt(7)

    # SLIDE 2: BILLED VS UNBILLED COMPARISON
    slide2 = prs.slides.add_slide(blank_layout)
    add_header(slide2, "Billed vs Unbilled Comparative Analysis")

    comp_table_shape = slide2.shapes.add_table(4, 5, Inches(0.8), Inches(1.8), Inches(11.733), Inches(4.5))
    comp_table = comp_table_shape.table

    comp_headers = ["Billing Classification", "Total Revenue (INR)", "Consignments", "Cargo Weight (Kg)", "Share %"]
    for col_idx, ch in enumerate(comp_headers):
        cell = comp_table.cell(0, col_idx)
        cell.text = ch
        cell.fill.solid()
        cell.fill.fore_color.rgb = C_NAVY
        for p in cell.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(13)
            p.font.color.rgb = C_WHITE

    tot_s = summary.get("total_sales", 1)
    comp_rows = [
        ["BILLED REVENUE", format_inr(summary.get("billed_sales", 0)), f"{summary.get('billed_shipments', 0):,}", f"{billed_metrics.get('summary', {}).get('total_weight', 0):,.1f} Kg", f"{(summary.get('billed_sales', 0)/tot_s*100):.1f}%"],
        ["UNBILLED REVENUE", format_inr(summary.get("unbilled_sales", 0)), f"{summary.get('unbilled_shipments', 0):,}", f"{unbilled_metrics.get('summary', {}).get('total_weight', 0):,.1f} Kg", f"{(summary.get('unbilled_sales', 0)/tot_s*100):.1f}%"],
        ["GRAND TOTAL", format_inr(tot_s), f"{summary.get('total_shipments', 0):,}", f"{summary.get('total_weight', 0):,.1f} Kg", "100.0%"]
    ]
    for row_idx, r in enumerate(comp_rows, start=1):
        for col_idx, v in enumerate(r):
            cell = comp_table.cell(row_idx, col_idx)
            cell.text = v
            cell.fill.solid()
            cell.fill.fore_color.rgb = C_WHITE if row_idx < 3 else RGBColor(241, 245, 249)
            for p in cell.text_frame.paragraphs:
                p.font.bold = (row_idx == 3)
                p.font.size = Pt(13)
                p.font.color.rgb = C_DARK

    # SLIDE 3: TRANSPORT MODES BREAKDOWN
    slide3 = prs.slides.add_slide(blank_layout)
    add_header(slide3, "Mode of Transport Breakdown (Air, Surface, Train)")

    modes = all_metrics.get("modes", [])
    mode_table_shape = slide3.shapes.add_table(min(len(modes) + 1, 6), 4, Inches(0.8), Inches(1.8), Inches(11.733), Inches(4.0))
    mode_table = mode_table_shape.table

    m_headers = ["Mode of Transport", "Consignments Moved", "Freight Turnover (INR)", "Revenue Share %"]
    for col_idx, mh in enumerate(m_headers):
        cell = mode_table.cell(0, col_idx)
        cell.text = mh
        cell.fill.solid()
        cell.fill.fore_color.rgb = C_NAVY
        for p in cell.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(13)
            p.font.color.rgb = C_WHITE

    for row_idx, m in enumerate(modes, start=1):
        vals = [m["mode"], f"{m['shipments']:,}", format_inr(m["sales"]), f"{m['share_pct']}%"]
        for col_idx, v in enumerate(vals):
            cell = mode_table.cell(row_idx, col_idx)
            cell.text = v
            cell.fill.solid()
            cell.fill.fore_color.rgb = C_WHITE if row_idx % 2 == 1 else RGBColor(248, 250, 252)
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(12)
                p.font.color.rgb = C_DARK

    # SLIDE 4: SALES TEAM LEADERBOARD
    slide4 = prs.slides.add_slide(blank_layout)
    add_header(slide4, "Sales Team Performance & Contribution Analysis")

    reps = all_metrics.get("sales_reps", [])
    table_shape = slide4.shapes.add_table(min(len(reps) + 1, 9), 5, Inches(0.8), Inches(1.5), Inches(11.733), Inches(5.2))
    table = table_shape.table

    headers = ["Sales Representative", "Assigned Accounts", "Total Shipments", "Total Freight (INR)", "Share of Total"]
    for col_idx, h in enumerate(headers):
        cell = table.cell(0, col_idx)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = C_NAVY
        for p in cell.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(13)
            p.font.color.rgb = C_WHITE

    for row_idx, r in enumerate(reps[:8], start=1):
        vals = [r["name"], str(r["customer_count"]), f"{r['shipments']:,}", format_inr(r["sales"]), f"{r['share_pct']}%"]
        for col_idx, v in enumerate(vals):
            cell = table.cell(row_idx, col_idx)
            cell.text = v
            cell.fill.solid()
            cell.fill.fore_color.rgb = C_WHITE if row_idx % 2 == 1 else RGBColor(248, 250, 252)
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(12)
                p.font.color.rgb = C_DARK

    # SLIDE 5: TOP CLIENT ACCOUNTS
    slide5 = prs.slides.add_slide(blank_layout)
    add_header(slide5, "Top Client Accounts & Volume Concentration")

    custs = all_metrics.get("customers", [])
    table_shape5 = slide5.shapes.add_table(min(len(custs) + 1, 11), 5, Inches(0.8), Inches(1.5), Inches(11.733), Inches(5.3))
    table5 = table_shape5.table

    cust_headers = ["Customer Account Name", "Account Code", "Account Manager", "Total Shipments", "Total Freight (INR)"]
    for col_idx, h in enumerate(cust_headers):
        cell = table5.cell(0, col_idx)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = C_NAVY
        for p in cell.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(13)
            p.font.color.rgb = C_WHITE

    for row_idx, c in enumerate(custs[:10], start=1):
        vals = [c["name"][:35], c["code"] or "---", c["sales_person"], f"{c['shipments']:,}", format_inr(c["sales"])]
        for col_idx, v in enumerate(vals):
            cell = table5.cell(row_idx, col_idx)
            cell.text = v
            cell.fill.solid()
            cell.fill.fore_color.rgb = C_WHITE if row_idx % 2 == 1 else RGBColor(248, 250, 252)
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(11)
                p.font.color.rgb = C_DARK

    out = io.BytesIO()
    prs.save(out)
    out.seek(0)
    return out


# ═════════════════════════════════════════════════════════════════════
# EXECUTIVE EXPORT: MULTI-PAGE PDF REPORT (.PDF)
# ═════════════════════════════════════════════════════════════════════

def generate_sales_pdf(report_row, report_data):
    """
    Generate an executive multi-page PDF report with Doxera branding,
    typography, and separate comparative pages for Billed and Unbilled.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, HRFlowable
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    out = io.BytesIO()
    doc = SimpleDocTemplate(
        out,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#0B132B'),
        spaceBefore=10,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155')
    )
    card_label = ParagraphStyle(
        'CardLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#64748B')
    )
    card_val = ParagraphStyle(
        'CardVal',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#0B132B')
    )

    logo_path = os.path.join(Config.BASE_DIR, "static", "doxera_logo.png")
    summary = report_data.get("summary", {})
    all_metrics = report_data.get("all", {})
    billed_metrics = report_data.get("billed", {})
    unbilled_metrics = report_data.get("unbilled", {})

    story = []

    def make_header_block(section_title):
        header_data = []
        if os.path.exists(logo_path):
            img = Image(logo_path, width=120, height=36)
            txt = Paragraph(f"<b>NORTH EXPRESS LOGISTICS</b><br/><font color='#64748B' size=8>DOXERA SALES INTELLIGENCE • {summary.get('period_label')}</font>", body_style)
            header_data = [[img, txt]]
        else:
            txt = Paragraph(f"<b>NORTH EXPRESS LOGISTICS</b><br/><font color='#64748B' size=8>DOXERA SALES INTELLIGENCE • {summary.get('period_label')}</font>", body_style)
            header_data = [[txt]]
        t = Table(header_data, colWidths=[140, 380])
        t.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (0,0), 'LEFT'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ]))
        return [t, HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0B132B"), spaceBefore=6, spaceAfter=10), Paragraph(section_title, h2_style)]

    # PAGE 1: EXECUTIVE SUMMARY
    story.extend(make_header_block(f"Executive Sales Report: {summary.get('period_label', '')}"))

    cards_table = [
        [
            Paragraph("TOTAL REVENUE", card_label),
            Paragraph("BILLED REVENUE", card_label),
            Paragraph("UNBILLED REVENUE", card_label),
            Paragraph("TOTAL CONSIGNMENTS", card_label)
        ],
        [
            Paragraph(format_inr(summary.get("total_sales", 0)), card_val),
            Paragraph(format_inr(summary.get("billed_sales", 0)), card_val),
            Paragraph(format_inr(summary.get("unbilled_sales", 0)), card_val),
            Paragraph(f"{summary.get('total_shipments', 0):,} AWBs", card_val)
        ]
    ]
    t_cards = Table(cards_table, colWidths=[130, 130, 130, 130])
    t_cards.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_cards)
    story.append(Spacer(1, 12))

    # Transport Modes Breakdown Table
    story.append(Paragraph("<b>Transport Mode Performance (Air vs Surface vs Train)</b>", h2_style))
    modes = all_metrics.get("modes", [])
    mode_table_data = [["Transport Mode", "Shipments Moved", "Freight Turnover (INR)", "Share %"]]
    for m in modes:
        mode_table_data.append([m["mode"], f"{m['shipments']:,}", format_inr(m["sales"]), f"{m['share_pct']}%"])

    t_mode = Table(mode_table_data, colWidths=[150, 120, 150, 100])
    t_mode.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0B132B')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 5),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#F8FAFC')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
    ]))
    story.append(t_mode)
    story.append(Spacer(1, 14))

    # Comparative Billed vs Unbilled Summary
    story.append(Paragraph("<b>Billed vs Unbilled Segmentation</b>", h2_style))
    tot_s = summary.get("total_sales", 1)
    comp_pdf_data = [
        ["Classification", "Freight Revenue (INR)", "Dockets", "Share %"],
        ["Billed Shipments", format_inr(summary.get("billed_sales", 0)), f"{summary.get('billed_shipments', 0):,}", f"{(summary.get('billed_sales', 0)/tot_s*100):.1f}%"],
        ["Unbilled Shipments", format_inr(summary.get("unbilled_sales", 0)), f"{summary.get('unbilled_shipments', 0):,}", f"{(summary.get('unbilled_sales', 0)/tot_s*100):.1f}%"],
        ["Grand Total", format_inr(tot_s), f"{summary.get('total_shipments', 0):,}", "100.0%"]
    ]
    t_comp = Table(comp_pdf_data, colWidths=[150, 160, 110, 100])
    t_comp.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0B132B')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#E2E8F0')),
    ]))
    story.append(t_comp)

    # PAGE 2: SALES TEAM PERFORMANCE
    story.append(PageBreak())
    story.extend(make_header_block("Sales Team Performance & Contribution Analysis"))

    reps = all_metrics.get("sales_reps", [])
    rep_table_data = [["Sales Representative", "Accounts", "Shipments", "Freight Revenue (INR)", "Share %"]]
    for r in reps:
        rep_table_data.append([
            r["name"],
            str(r["customer_count"]),
            f"{r['shipments']:,}",
            format_inr(r["sales"]),
            f"{r['share_pct']}%"
        ])

    t_rep = Table(rep_table_data, colWidths=[160, 70, 80, 140, 70])
    t_rep.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0B132B')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_rep)

    # PAGE 3: TOP CLIENT ACCOUNTS
    story.append(PageBreak())
    story.extend(make_header_block("Top Client Accounts & Volume Concentration"))

    custs = all_metrics.get("customers", [])
    cust_table_data = [["Customer Name", "Code", "Sales Rep", "Dockets", "Revenue (INR)"]]
    for c in custs[:18]:
        cust_table_data.append([
            c["name"][:32],
            c["code"] or "---",
            c["sales_person"],
            f"{c['shipments']:,}",
            format_inr(c["sales"])
        ])

    t_cust = Table(cust_table_data, colWidths=[180, 70, 110, 60, 100])
    t_cust.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0B132B')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_cust)

    doc.build(story)
    out.seek(0)
    return out
