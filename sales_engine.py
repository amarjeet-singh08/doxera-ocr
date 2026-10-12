# DOXERA Sales Intelligence & Analytics Engine
# =========================================================
# Processes Billed and Unbilled MIS spreadsheets, correlates
# records via AWB numbers, matches customer codes with the
# sales representative master database, and generates
# executive-grade analytics, PDF reports, and PowerPoint presentations.

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
    """Normalize messy Excel column names to clean internal keys."""
    raw = str(col_str).strip().lower()
    clean = re.sub(r"[^a-z0-9]", "", raw)
    
    if "awb" in clean or "docket" in clean:
        return "awb_no"
    if "customercode" in clean or "custcode" in clean:
        return "customer_code"
    if "customer" in clean or "party" in clean:
        return "customer_name"
    if "servicemode" in clean or "transportmode" in clean or "mode" in clean:
        return "mode"
    if "totalamt" in clean or "amount" in clean or "totalamount" in clean or "freight" in clean:
        return "total_amt"
    if "weight" in clean or "wt" in clean:
        return "weight"
    if "origin" in clean:
        return "origin"
    if "destination" in clean or "dest" in clean:
        return "destination"
    if "shipper" in clean:
        return "shipper"
    if "consignee" in clean:
        return "consignee"
    if "appoint" in clean:
        return "appoint_date"
    if "date" in clean:
        return "date"
    return clean

def read_mis_file(file_storage_or_path, original_filename=""):
    """
    Universally parse .xlsx, .xls (binary or TSV-in-disguise), .csv, or .tsv.
    Returns a standardized pandas DataFrame.
    """
    if isinstance(file_storage_or_path, str):
        filepath = file_storage_or_path
        filename = os.path.basename(filepath)
    else:
        file_storage_or_path.seek(0)
        content_bytes = file_storage_or_path.read()
        filename = original_filename or getattr(file_storage_or_path, "filename", "upload.xlsx")
        filepath = io.BytesIO(content_bytes)

    df = None
    errors = []

    # 1. Try reading as text/CSV/TSV if file looks like text
    try:
        if isinstance(filepath, io.BytesIO):
            filepath.seek(0)
            sample = filepath.read(2048)
            filepath.seek(0)
        else:
            with open(filepath, "rb") as fp:
                sample = fp.read(2048)
                
        if b"\t" in sample or b"," in sample:
            try:
                if isinstance(filepath, io.BytesIO):
                    filepath.seek(0)
                    df = pd.read_csv(filepath, sep=None, engine="python", encoding="utf-8")
                else:
                    df = pd.read_csv(filepath, sep=None, engine="python", encoding="utf-8")
            except Exception:
                if isinstance(filepath, io.BytesIO):
                    filepath.seek(0)
                    df = pd.read_csv(filepath, sep=None, engine="python", encoding="latin1")
                else:
                    df = pd.read_csv(filepath, sep=None, engine="python", encoding="latin1")
    except Exception as e:
        errors.append(f"Text/CSV reader failed: {e}")

    # 2. Try openpyxl (standard XLSX)
    if df is None:
        try:
            if isinstance(filepath, io.BytesIO):
                filepath.seek(0)
            df = pd.read_excel(filepath, engine="openpyxl")
        except Exception as e:
            errors.append(f"openpyxl failed: {e}")

    # 3. Try xlrd (legacy binary XLS)
    if df is None:
        try:
            if isinstance(filepath, io.BytesIO):
                filepath.seek(0)
            df = pd.read_excel(filepath)
        except Exception as e:
            errors.append(f"Excel standard reader failed: {e}")

    # 4. Try HTML table (some systems export HTML inside .xls)
    if df is None:
        try:
            if isinstance(filepath, io.BytesIO):
                filepath.seek(0)
            dfs = pd.read_html(filepath)
            if dfs:
                df = dfs[0]
        except Exception as e:
            errors.append(f"HTML table reader failed: {e}")

    if df is None or df.empty:
        raise ValueError(f"Could not parse file '{filename}'. Details: {'; '.join(errors)}")

    # Standardize column headers
    col_mapping = {}
    for col in df.columns:
        norm = normalize_column_name(col)
        col_mapping[col] = norm
    df = df.rename(columns=col_mapping)

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

def parse_and_process_sales(billed_file, unbilled_file, billed_name, unbilled_name, created_by="admin", report_title=""):
    """
    Main ingestion and correlation workflow.
    Validates both sheets, correlates AWBs, assigns sales reps, and calculates analytics.
    """
    # 1. Parse both sheets
    try:
        billed_df = read_mis_file(billed_file, billed_name)
    except Exception as e:
        return None, f"Failed to read Billed Sheet ({billed_name}): {str(e)}"

    try:
        unbilled_df = read_mis_file(unbilled_file, unbilled_name)
    except Exception as e:
        return None, f"Failed to read Unbilled Sheet ({unbilled_name}): {str(e)}"

    # 2. Validate mandatory columns
    for df, label in [(billed_df, "Billed"), (unbilled_df, "Unbilled")]:
        missing = []
        if "awb_no" not in df.columns:
            missing.append("AWB / Docket Number")
        if "total_amt" not in df.columns:
            missing.append("Total Amount / Freight")
        if missing:
            return None, f"The {label} sheet is missing essential column(s): {', '.join(missing)}. Please verify the column headers."

    code_to_rep, name_to_rep = get_customer_sales_rep_map()

    # Helper function to extract and clean records
    def extract_records(df, source_label):
        records = []
        for _, row in df.iterrows():
            awb = str(row.get("awb_no", "")).strip()
            if not awb or awb.lower() in ("nan", "none", "0"):
                continue

            # Amount
            try:
                amt = float(row.get("total_amt", 0) or 0)
            except Exception:
                amt = 0.0

            # Weight
            try:
                wt = float(row.get("weight", 0) or 0)
            except Exception:
                wt = 0.0

            # Date formatting
            raw_date = str(row.get("date", "")).strip()
            clean_date = ""
            if raw_date and raw_date.lower() != "nan":
                clean_date = raw_date.split(" ")[0]

            code = str(row.get("customer_code", "")).strip().upper()
            if code == "NAN": code = ""
            name = str(row.get("customer_name", "")).strip()
            if name == "NAN": name = ""

            # Assign sales person
            rep = "NEL"
            if code in code_to_rep:
                rep = code_to_rep[code]
            elif name.upper() in name_to_rep:
                rep = name_to_rep[name.upper()]

            mode = str(row.get("mode", "")).strip().upper()
            if mode == "NAN": mode = "SURFACE"

            records.append({
                "awb_no": awb,
                "date": clean_date,
                "customer_code": code,
                "customer_name": name or code or "General Customer",
                "sales_person": rep,
                "shipper": str(row.get("shipper", "")).strip(),
                "consignee": str(row.get("consignee", "")).strip(),
                "origin": str(row.get("origin", "")).strip(),
                "destination": str(row.get("destination", "")).strip() or "Unknown",
                "service_mode": mode,
                "transport_mode": mode,
                "weight": wt,
                "appoint_date": str(row.get("appoint_date", "")).strip(),
                "total_amt": amt,
                "source": source_label
            })
        return records

    billed_records = extract_records(billed_df, "BILLED")
    unbilled_records = extract_records(unbilled_df, "UNBILLED")

    if not billed_records and not unbilled_records:
        return None, "Both uploaded files appear to have zero valid shipments. Please check the file contents."

    # 3. Merge by AWB Number
    merged_map = {}
    
    # Process Billed records first
    for rec in billed_records:
        merged_map[rec["awb_no"]] = {
            **rec,
            "billed_amt": rec["total_amt"],
            "unbilled_amt": 0.0,
            "source_type": "BILLED"
        }

    # Merge or Append Unbilled records
    for rec in unbilled_records:
        awb = rec["awb_no"]
        if awb in merged_map:
            # Common AWB in both sheets!
            merged_map[awb]["unbilled_amt"] = rec["total_amt"]
            # If billed didn't have customer details but unbilled does:
            if not merged_map[awb]["customer_name"] or merged_map[awb]["customer_name"] == "General Customer":
                merged_map[awb]["customer_name"] = rec["customer_name"]
                merged_map[awb]["customer_code"] = rec["customer_code"]
                merged_map[awb]["sales_person"] = rec["sales_person"]
            merged_map[awb]["source_type"] = "COMBINED"
        else:
            merged_map[awb] = {
                **rec,
                "billed_amt": 0.0,
                "unbilled_amt": rec["total_amt"],
                "source_type": "UNBILLED"
            }

    all_shipments = list(merged_map.values())

    # 4. Aggregations & Metrics
    total_sales = sum(s["total_amt"] for s in all_shipments)
    billed_sales = sum(s.get("billed_amt", 0.0) for s in all_shipments)
    unbilled_sales = sum(s.get("unbilled_amt", 0.0) for s in all_shipments)
    total_weight = sum(s["weight"] for s in all_shipments)
    total_count = len(all_shipments)
    avg_ticket = (total_sales / total_count) if total_count > 0 else 0.0

    # Sales by Sales Person
    rep_stats = {}
    for s in all_shipments:
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
    for s in all_shipments:
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

    # Sales by Date (Chronological)
    date_stats = {}
    for s in all_shipments:
        d = s["date"] or "Undated"
        if d not in date_stats:
            date_stats[d] = {"sales": 0.0, "shipments": 0}
        date_stats[d]["sales"] += s["total_amt"]
        date_stats[d]["shipments"] += 1

    # Attempt sorting dates
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

    # Service / Transport Mode breakdown
    mode_stats = {}
    for s in all_shipments:
        m = s["service_mode"] or "SURFACE"
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

    # Destination Breakdown (Top hubs)
    dest_stats = {}
    for s in all_shipments:
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

    # Determine period label from dates
    period_label = "Current Month"
    valid_dates = [parse_dt(d) for d in sorted_dates if parse_dt(d) != datetime.min]
    if valid_dates:
        earliest = min(valid_dates)
        period_label = earliest.strftime("%B %Y")

    if not report_title:
        report_title = f"North Express Logistics - Sales Report ({period_label})"

    # Consolidated JSON payload for instant dashboard rendering
    report_data = {
        "summary": {
            "total_sales": round(total_sales, 2),
            "billed_sales": round(billed_sales, 2),
            "unbilled_sales": round(unbilled_sales, 2),
            "total_shipments": total_count,
            "total_weight": round(total_weight, 2),
            "avg_ticket": round(avg_ticket, 2),
            "top_rep": top_rep,
            "top_customer": top_customer,
            "period_label": period_label
        },
        "sales_reps": sales_reps_list,
        "customers": customers_list,
        "daily_sales": daily_sales_list,
        "modes": mode_list,
        "destinations": dest_list[:20],
        "shipments_sample": all_shipments[:200]
    }

    # 5. Save to database
    report_id = f"SR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    conn = get_db_connection()
    c = conn.execute('''
        INSERT INTO sales_reports (
            report_id, title, period_label, billed_filename, unbilled_filename,
            total_sales, billed_sales, unbilled_sales, total_shipments, total_weight,
            avg_shipment_value, top_sales_person, top_customer, report_data_json, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        report_id, report_title, period_label, billed_name, unbilled_name,
        total_sales, billed_sales, unbilled_sales, total_count, total_weight,
        avg_ticket, top_rep, top_customer, json.dumps(report_data), created_by
    ))
    db_report_id = c.lastrowid

    # Batch insert shipments
    shipment_rows = []
    for s in all_shipments:
        shipment_rows.append((
            db_report_id, s["awb_no"], s["date"], s["customer_code"], s["customer_name"],
            s["sales_person"], s["shipper"], s["consignee"], s["origin"], s["destination"],
            s["service_mode"], s["transport_mode"], s["weight"], s["appoint_date"],
            s["total_amt"], s["source_type"]
        ))
    conn.executemany('''
        INSERT INTO sales_shipments (
            report_id, awb_no, booking_date, customer_code, customer_name,
            sales_person, shipper, consignee, origin, destination,
            service_mode, transport_mode, weight, appoint_date, total_amt, source_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', shipment_rows)

    conn.commit()
    conn.close()

    return db_report_id, None


# ═════════════════════════════════════════════════════════════════════
# EXECUTIVE EXPORT: POWERPOINT PRESENTATION (.PPTX)
# ═════════════════════════════════════════════════════════════════════

def generate_sales_pptx(report_row, report_data):
    """
    Generate an executive 16:9 PowerPoint presentation with 5 distinct slides:
    Slide 1: Title & Overall Executive Summary
    Slide 2: Sales Person Leaderboard & Performance Analysis
    Slide 3: Top Customer Accounts & Contribution
    Slide 4: Service & Transport Mode Breakdown
    Slide 5: Geographic Distribution & Lane Volumes
    """
    import pptx
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    from pptx.enum.shapes import MSO_SHAPE

    prs = pptx.Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Brand Colors
    C_NAVY = RGBColor(11, 19, 43)        # #0B132B
    C_BLUE = RGBColor(37, 99, 235)       # #2563EB
    C_LIGHT_BG = RGBColor(248, 250, 252) # #F8FAFC
    C_WHITE = RGBColor(255, 255, 255)
    C_SLATE = RGBColor(100, 116, 139)    # #64748B
    C_DARK = RGBColor(15, 23, 42)        # #0F172A

    logo_path = os.path.join(Config.BASE_DIR, "static", "doxera_logo.png")

    def add_header(slide, title_text, category="SALES INTELLIGENCE"):
        # Header background banner
        header_shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(1.1))
        header_shape.fill.solid()
        header_shape.fill.fore_color.rgb = C_NAVY
        header_shape.line.fill.background()

        # Title text
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

        # Add Logo if present
        if os.path.exists(logo_path):
            slide.shapes.add_picture(logo_path, Inches(11.2), Inches(0.2), width=Inches(1.5))

    summary = report_data.get("summary", {})

    # ─────────────────────────────────────────────────────────────
    # SLIDE 1: EXECUTIVE SUMMARY
    # ─────────────────────────────────────────────────────────────
    slide1 = prs.slides.add_slide(blank_layout)
    add_header(slide1, f"Executive Overview • {summary.get('period_label', 'Report')}")

    # Stat Card Helper
    cards_data = [
        ("TOTAL REVENUE", format_inr(summary.get("total_sales", 0)), RGBColor(37, 99, 235)),
        ("TOTAL SHIPMENTS", f"{summary.get('total_shipments', 0):,} AWBs", RGBColor(16, 185, 129)),
        ("TOTAL WEIGHT", f"{summary.get('total_weight', 0):,.1f} Kg", RGBColor(245, 158, 11)),
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

    # Summary Insights Box
    info_box = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(3.5), Inches(11.733), Inches(3.4))
    info_box.fill.solid()
    info_box.fill.fore_color.rgb = RGBColor(241, 245, 249)
    info_box.line.color.rgb = RGBColor(203, 213, 225)

    tx_info = slide1.shapes.add_textbox(Inches(1.2), Inches(3.8), Inches(10.9), Inches(2.8))
    tf_info = tx_info.text_frame
    tf_info.word_wrap = True

    h = tf_info.paragraphs[0]
    h.text = "Key Operational Highlights & Metrics"
    h.font.size = Pt(16)
    h.font.bold = True
    h.font.color.rgb = C_NAVY

    highlights = [
        f"• Grand Total Revenue: {format_inr(summary.get('total_sales', 0))} across {summary.get('total_shipments', 0):,} verified freight shipments.",
        f"• Average Revenue Per Docket: {format_inr(summary.get('avg_ticket', 0))} with {summary.get('total_weight', 0):,.1f} Kg cargo moved.",
        f"• Leading Account Contribution: {summary.get('top_customer', 'N/A')} represents the largest revenue driver.",
        f"• Sales Force Top Performer: {summary.get('top_rep', 'N/A')} generated the highest turnover during this billing period.",
        f"• Data Sources: Correlated from Billed ({report_row['billed_filename']}) & Unbilled ({report_row['unbilled_filename']}) MIS files."
    ]
    for bullet in highlights:
        p = tf_info.add_paragraph()
        p.text = bullet
        p.font.size = Pt(13)
        p.font.color.rgb = C_DARK
        p.space_before = Pt(8)

    # ─────────────────────────────────────────────────────────────
    # SLIDE 2: SALES PERSON LEADERBOARD
    # ─────────────────────────────────────────────────────────────
    slide2 = prs.slides.add_slide(blank_layout)
    add_header(slide2, "Sales Team Performance & Contribution Analysis")

    reps = report_data.get("sales_reps", [])
    table_shape = slide2.shapes.add_table(min(len(reps) + 1, 9), 5, Inches(0.8), Inches(1.5), Inches(11.733), Inches(5.2))
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

    # ─────────────────────────────────────────────────────────────
    # SLIDE 3: TOP CUSTOMER ACCOUNTS
    # ─────────────────────────────────────────────────────────────
    slide3 = prs.slides.add_slide(blank_layout)
    add_header(slide3, "Top Client Accounts & Volume Contribution")

    custs = report_data.get("customers", [])
    table_shape = slide3.shapes.add_table(min(len(custs) + 1, 11), 5, Inches(0.8), Inches(1.5), Inches(11.733), Inches(5.3))
    table = table_shape.table

    headers = ["Customer Account Name", "Account Code", "Account Manager", "Total Shipments", "Total Freight (INR)"]
    for col_idx, h in enumerate(headers):
        cell = table.cell(0, col_idx)
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
            cell = table.cell(row_idx, col_idx)
            cell.text = v
            cell.fill.solid()
            cell.fill.fore_color.rgb = C_WHITE if row_idx % 2 == 1 else RGBColor(248, 250, 252)
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(11)
                p.font.color.rgb = C_DARK

    # ─────────────────────────────────────────────────────────────
    # SLIDE 4: TRANSPORT & SERVICE MODES
    # ─────────────────────────────────────────────────────────────
    slide4 = prs.slides.add_slide(blank_layout)
    add_header(slide4, "Logistics Modes & Service Type Breakdown")

    modes = report_data.get("modes", [])
    table_shape = slide4.shapes.add_table(min(len(modes) + 1, 6), 4, Inches(0.8), Inches(1.5), Inches(11.733), Inches(3.5))
    table = table_shape.table

    headers = ["Service / Transport Mode", "Total Dockets", "Total Revenue (INR)", "Share of Total"]
    for col_idx, h in enumerate(headers):
        cell = table.cell(0, col_idx)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = C_NAVY
        for p in cell.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(13)
            p.font.color.rgb = C_WHITE

    for row_idx, m in enumerate(modes, start=1):
        vals = [m["mode"], f"{m['shipments']:,}", format_inr(m["sales"]), f"{m['share_pct']}%"]
        for col_idx, v in enumerate(vals):
            cell = table.cell(row_idx, col_idx)
            cell.text = v
            cell.fill.solid()
            cell.fill.fore_color.rgb = C_WHITE if row_idx % 2 == 1 else RGBColor(248, 250, 252)
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(12)
                p.font.color.rgb = C_DARK

    # ─────────────────────────────────────────────────────────────
    # SLIDE 5: TOP DESTINATIONS / LANES
    # ─────────────────────────────────────────────────────────────
    slide5 = prs.slides.add_slide(blank_layout)
    add_header(slide5, "Geographic Hubs & Destination Volumes")

    dests = report_data.get("destinations", [])
    table_shape = slide5.shapes.add_table(min(len(dests) + 1, 11), 3, Inches(0.8), Inches(1.5), Inches(11.733), Inches(5.3))
    table = table_shape.table

    headers = ["Destination Hub / City", "Shipments Delivered", "Total Freight Billed (INR)"]
    for col_idx, h in enumerate(headers):
        cell = table.cell(0, col_idx)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = C_NAVY
        for p in cell.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(13)
            p.font.color.rgb = C_WHITE

    for row_idx, d in enumerate(dests[:10], start=1):
        vals = [d["city"], f"{d['shipments']:,}", format_inr(d["sales"])]
        for col_idx, v in enumerate(vals):
            cell = table.cell(row_idx, col_idx)
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
    typography, distinct pages for executive summary, sales team,
    top customer accounts, and transit breakdown.
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

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0B132B')
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#2563EB')
    )
    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#0B132B'),
        spaceBefore=10,
        spaceAfter=8
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
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#0B132B')
    )

    logo_path = os.path.join(Config.BASE_DIR, "static", "doxera_logo.png")
    summary = report_data.get("summary", {})

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
        return [t, HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0B132B"), spaceBefore=8, spaceAfter=14), Paragraph(section_title, h2_style)]

    # ─────────────────────────────────────────────────────────────
    # PAGE 1: EXECUTIVE SUMMARY
    # ─────────────────────────────────────────────────────────────
    story.extend(make_header_block(f"Executive Sales Report: {summary.get('period_label', '')}"))

    # KPI 4-Card Table
    cards_table = [
        [
            Paragraph("TOTAL REVENUE", card_label),
            Paragraph("TOTAL SHIPMENTS", card_label),
            Paragraph("TOTAL WEIGHT", card_label),
            Paragraph("TOP SALES REP", card_label)
        ],
        [
            Paragraph(format_inr(summary.get("total_sales", 0)), card_val),
            Paragraph(f"{summary.get('total_shipments', 0):,} AWBs", card_val),
            Paragraph(f"{summary.get('total_weight', 0):,.1f} Kg", card_val),
            Paragraph(str(summary.get("top_rep", "NEL")), card_val)
        ]
    ]
    t_cards = Table(cards_table, colWidths=[130, 130, 130, 130])
    t_cards.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_cards)
    story.append(Spacer(1, 16))

    # Executive Summary Paragraphs
    story.append(Paragraph("<b>Executive Highlights</b>", h2_style))
    story.append(Paragraph(
        f"This report consolidates freight transactions from the Billed ({report_row['billed_filename']}) "
        f"and Unbilled ({report_row['unbilled_filename']}) MIS datasets. "
        f"A total of <b>{summary.get('total_shipments', 0):,} consignments</b> were moved, producing "
        f"<b>{format_inr(summary.get('total_sales', 0))}</b> in total freight revenue.",
        body_style
    ))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f"• Average freight value per consignment: <b>{format_inr(summary.get('avg_ticket', 0))}</b>.<br/>"
        f"• Highest grossing sales representative: <b>{summary.get('top_rep', 'NEL')}</b>.<br/>"
        f"• Key account leader: <b>{summary.get('top_customer', 'N/A')}</b>.",
        body_style
    ))
    story.append(Spacer(1, 16))

    # Service Mode Breakdown Table
    story.append(Paragraph("<b>Service / Transport Mode Breakdown</b>", h2_style))
    modes = report_data.get("modes", [])
    mode_table_data = [["Mode", "Shipments", "Revenue (INR)", "Share %"]]
    for m in modes:
        mode_table_data.append([m["mode"], f"{m['shipments']:,}", format_inr(m["sales"]), f"{m['share_pct']}%"])

    t_mode = Table(mode_table_data, colWidths=[150, 120, 150, 100])
    t_mode.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0B132B')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#F8FAFC')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
    ]))
    story.append(t_mode)

    # ─────────────────────────────────────────────────────────────
    # PAGE 2: SALES TEAM PERFORMANCE
    # ─────────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.extend(make_header_block("Sales Team Performance & Contribution"))

    reps = report_data.get("sales_reps", [])
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
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_rep)

    # ─────────────────────────────────────────────────────────────
    # PAGE 3: TOP CUSTOMERS
    # ─────────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.extend(make_header_block("Top Customer Accounts & Revenue Leaders"))

    custs = report_data.get("customers", [])
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
