# DOXERA Executive Sales Export Engine
# =========================================================
# Generates minimalist, boardroom-ready PDF and PowerPoint (.PPTX)
# audit reports with embedded high-resolution visual charts.
# Security: Restricted strictly to ADMIN and AUDITOR roles.

import os
import io
import pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from config import Config


# ─────────────────────────────────────────────────────────────
# CURRENCY & NUMBER FORMATTING HELPERS
# ─────────────────────────────────────────────────────────────

def format_inr(val):
    if val is None or val == "":
        return "₹ 0.00"
    try:
        val = float(val)
        return "₹ " + f"{val:,.2f}"
    except (ValueError, TypeError):
        return str(val)

def format_plain_inr(val):
    if val is None or val == "":
        return "0.00"
    try:
        val = float(val)
        return f"{val:,.2f}"
    except (ValueError, TypeError):
        return str(val)


# ─────────────────────────────────────────────────────────────
# MINIMALIST EXECUTIVE CHART GENERATORS (Matplotlib Agg)
# ─────────────────────────────────────────────────────────────

def generate_trend_chart_img(daily_sales_list, width_in=5.8, height_in=2.6, dpi=160):
    """
    Renders Sale Graph by Date line chart matching the dashboard visual.
    """
    fig, ax = plt.subplots(figsize=(width_in, height_in), dpi=dpi)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')

    if not daily_sales_list:
        ax.text(0.5, 0.5, 'No Daily Sales Trend Data', ha='center', va='center', color='#94A3B8', fontsize=9)
        ax.axis('off')
    else:
        dates = []
        vals = []
        # Show recent 15 active billing dates
        for d in daily_sales_list[-15:]:
            raw_d = str(d.get("date", ""))
            parts = raw_d.split('-')
            label = f"{parts[0]}/{parts[1]}" if len(parts) >= 2 else raw_d
            dates.append(label)
            vals.append(float(d.get("sales", 0)))

        x_indices = list(range(len(dates)))
        ax.plot(x_indices, vals, color='#0284C7', lw=2.2, marker='o', markersize=4, zorder=3)

        if len(vals) > 1:
            max_val = max(vals)
            for idx, (x, v) in enumerate(zip(x_indices, vals)):
                is_peak = False
                if idx == 0 and len(vals) > 1 and v > vals[1]:
                    is_peak = True
                elif idx == len(vals) - 1 and v > vals[idx - 1]:
                    is_peak = True
                elif 0 < idx < len(vals) - 1 and v >= vals[idx - 1] and v >= vals[idx + 1]:
                    is_peak = True
                
                if is_peak or v == max_val:
                    ax.annotate(
                        f'{int(v):,}',
                        (x, v),
                        textcoords='offset points',
                        xytext=(0, 6),
                        ha='center',
                        fontsize=6.5,
                        fontweight='bold',
                        color='#0284C7'
                    )

        ax.set_xticks(x_indices)
        ax.set_xticklabels(dates, fontsize=6.5, fontweight='bold', color='#0F172A', rotation=0)
        ax.tick_params(axis='y', colors='#DC2626', labelsize=6.5)
        ax.tick_params(axis='x', length=2, color='#CBD5E1')
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#E2E8F0')
        ax.spines['bottom'].set_color('#CBD5E1')
        ax.grid(axis='y', linestyle='--', alpha=0.35, color='#94A3B8')

    plt.title('Sale Graph by Date', fontsize=8.5, fontweight='bold', loc='left', color='#0F172A', pad=8)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_sales_rep_chart_img(sales_reps_list, width_in=5.8, height_in=3.0, dpi=160):
    """
    Renders Total Sale by Sales Person horizontal bar chart matching the dashboard visual.
    """
    fig, ax = plt.subplots(figsize=(width_in, height_in), dpi=dpi)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')

    reps = sales_reps_list[:7] if sales_reps_list else []
    if not reps:
        ax.text(0.5, 0.5, 'No Sales Reps Data', ha='center', va='center', color='#94A3B8', fontsize=9)
        ax.axis('off')
    else:
        names = [str(r.get("name", "Unknown")) for r in reps]
        sales = [float(r.get("sales", 0)) for r in reps]
        
        names.reverse()
        sales.reverse()
        
        y_pos = list(range(len(names)))
        bars = ax.barh(y_pos, sales, color='#0F172A', height=0.52, edgecolor='none', zorder=3)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(names, fontsize=7.5, fontweight='bold', color='#1E3A8A')
        ax.tick_params(axis='x', colors='#DC2626', labelsize=6.5)
        ax.tick_params(axis='y', length=0)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))

        max_sale = max(sales) if sales else 1
        for bar, val in zip(bars, sales):
            ax.text(
                val + (max_sale * 0.02),
                bar.get_y() + bar.get_height() / 2,
                f'{val:,.0f}',
                va='center',
                fontsize=6.5,
                fontweight='bold',
                color='#0F172A'
            )

        ax.set_xlim(0, max_sale * 1.25)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['bottom'].set_color('#CBD5E1')
        ax.grid(axis='x', linestyle='--', alpha=0.35, color='#94A3B8')

    plt.title('Total Sale by Sales Person', fontsize=8.5, fontweight='bold', loc='left', color='#0F172A', pad=8)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_servicemode_pie_chart_img(mode_list, width_in=3.2, height_in=2.6, dpi=160):
    """
    Renders Total Sale by ServiceMode pie chart (Air, Surface, Train).
    """
    fig, ax = plt.subplots(figsize=(width_in, height_in), dpi=dpi)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')

    if not mode_list:
        ax.text(0.5, 0.5, 'No Mode Data', ha='center', va='center', color='#94A3B8', fontsize=9)
        ax.axis('off')
    else:
        labels = []
        vals = []
        color_map = {'Air': '#1D4ED8', 'Surface': '#0F172A', 'Train': '#991B1B'}
        pie_colors = []

        for m in mode_list:
            mode_name = str(m.get("mode", "Other"))
            sales_val = float(m.get("sales", 0))
            if sales_val > 0:
                labels.append(mode_name)
                vals.append(sales_val)
                pie_colors.append(color_map.get(mode_name, '#64748B'))

        if not vals:
            ax.text(0.5, 0.5, 'No Mode Data', ha='center', va='center', color='#94A3B8', fontsize=9)
            ax.axis('off')
        else:
            wedges, texts, autotexts = ax.pie(
                vals,
                labels=labels,
                colors=pie_colors,
                autopct='%1.1f%%',
                pctdistance=0.72,
                textprops={'fontsize': 7, 'color': '#0F172A', 'fontweight': 'bold'},
                startangle=130
            )
            for at in autotexts:
                at.set_color('#FFFFFF')
                at.set_fontsize(6.5)

    plt.title('Total Sale by ServiceMode', fontsize=8.5, fontweight='bold', color='#0F172A', pad=8)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_top_customer_chart_img(customers_list, width_in=3.2, height_in=2.6, dpi=160):
    """
    Renders TOP 5 Customer by Sale donut chart matching the dashboard.
    """
    fig, ax = plt.subplots(figsize=(width_in, height_in), dpi=dpi)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')

    top5 = customers_list[:5] if customers_list else []
    if not top5:
        ax.text(0.5, 0.5, 'No Customer Data', ha='center', va='center', color='#94A3B8', fontsize=9)
        ax.axis('off')
    else:
        labels = [str(c.get("name", "Unknown"))[:14] for c in top5]
        vals = [float(c.get("sales", 0)) for c in top5]
        colors = ['#0F172A', '#0284C7', '#1D4ED8', '#EA580C', '#7C3AED']

        if not any(vals):
            ax.text(0.5, 0.5, 'No Customer Sales', ha='center', va='center', color='#94A3B8', fontsize=9)
            ax.axis('off')
        else:
            wedges, texts, autotexts = ax.pie(
                vals,
                labels=labels,
                colors=colors[:len(vals)],
                autopct='%1.0f%%',
                pctdistance=0.74,
                textprops={'fontsize': 6.5, 'fontweight': 'bold', 'color': '#0F172A'},
                wedgeprops=dict(width=0.45, edgecolor='#FFFFFF'),
                startangle=140
            )
            for at in autotexts:
                at.set_color('#FFFFFF')
                at.set_fontsize(6)

    plt.title('TOP 5 Customer by Sale', fontsize=8.5, fontweight='bold', color='#0F172A', pad=8)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────
# 1. EXECUTIVE POWERPOINT PRESENTATION (.PPTX)
# ─────────────────────────────────────────────────────────────

def generate_sales_pptx(report_row, report_data):
    """
    Generates a minimalist, boardroom-ready 16:9 presentation.
    Slide 1: Executive Visual Dashboard (Power BI 1:1 Mirror with charts)
    Slide 2: Tri-Factor Financial Reconciliation & Risk Register
    Slide 3: Sales Team Accountability & Major Corporate Accounts
    Slide 4: Transport Modes, Strategic Corridors & Audit Attestation
    """
    prs = pptx.Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    logo_path = os.path.join(Config.BASE_DIR, "static", "doxera_logo.png")
    summary = report_data.get("summary", {})
    all_metrics = report_data.get("all", {})
    billed_metrics = report_data.get("billed", {})
    unbilled_metrics = report_data.get("unbilled", {})
    connectivity = report_data.get("connectivity", {})

    period_str = summary.get("period_label", "Monthly Audit Period")

    def add_minimalist_header(slide, title_text, category="NORTH EXPRESS LOGISTIC Pvt. Ltd."):
        # Title Textbox
        tx = slide.shapes.add_textbox(Inches(0.8), Inches(0.2), Inches(9.5), Inches(0.85))
        tf = tx.text_frame
        tf.word_wrap = True
        p1 = tf.paragraphs[0]
        p1.text = category
        p1.font.size = Pt(14)
        p1.font.bold = True
        p1.font.color.rgb = RGBColor(15, 23, 42) # Slate-900

        p2 = tf.add_paragraph()
        p2.text = f"{title_text}  •  Period: {period_str}  •  Note: Accurate Data."
        p2.font.size = Pt(10)
        p2.font.color.rgb = RGBColor(100, 116, 139) # Slate-500

        # Thin Hairline Divider
        line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.1), Inches(11.733), Inches(0.015))
        line.fill.solid()
        line.fill.fore_color.rgb = RGBColor(226, 232, 240)
        line.line.fill.background()

        # Doxera Logo
        if os.path.exists(logo_path):
            try:
                slide.shapes.add_picture(logo_path, Inches(10.8), Inches(0.25), width=Inches(1.6))
            except Exception:
                pass

    # ═════════════════════════════════════════════════════════════════
    # SLIDE 1: EXECUTIVE VISUAL DASHBOARD (1:1 Power BI Layout)
    # ═════════════════════════════════════════════════════════════════
    slide1 = prs.slides.add_slide(blank_layout)
    add_header_title = f"SALES REPORT (UNBILLED & CONSOLIDATED)"
    add_minimalist_header(slide1, add_header_title)

    # 1. Total Sale Black Card (Top-Left)
    kpi_card = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.3), Inches(3.2), Inches(1.6))
    kpi_card.fill.solid()
    kpi_card.fill.fore_color.rgb = RGBColor(0, 0, 0)
    kpi_card.line.fill.background()

    tx_kpi = slide1.shapes.add_textbox(Inches(0.9), Inches(1.38), Inches(3.0), Inches(1.4))
    tf_kpi = tx_kpi.text_frame
    tf_kpi.word_wrap = True
    
    # Amount
    p_kpi_amt = tf_kpi.paragraphs[0]
    unb_amt = summary.get("unbilled_sales", summary.get("total_sales", 0))
    p_kpi_amt.text = f"₹ {format_plain_inr(unb_amt)}"
    p_kpi_amt.font.size = Pt(19)
    p_kpi_amt.font.bold = True
    p_kpi_amt.font.color.rgb = RGBColor(56, 189, 248) # Cyan

    # Label
    p_kpi_lbl = tf_kpi.add_paragraph()
    p_kpi_lbl.text = "TOTAL SALE (UNBILLED)"
    p_kpi_lbl.font.size = Pt(10)
    p_kpi_lbl.font.bold = True
    p_kpi_lbl.font.color.rgb = RGBColor(226, 232, 240)

    # Subtext
    p_kpi_sub = tf_kpi.add_paragraph()
    unb_awbs = summary.get("unbilled_shipments", summary.get("total_shipments", 0))
    tot_wt = unbilled_metrics.get("summary", {}).get("total_weight", summary.get("total_weight", 0))
    p_kpi_sub.text = f"{unb_awbs:,} AWBs  •  {tot_wt:,.1f} Kg"
    p_kpi_sub.font.size = Pt(8.5)
    p_kpi_sub.font.color.rgb = RGBColor(148, 163, 184)

    # 2. Sale Graph by Date (Line Chart Image)
    daily_sales = unbilled_metrics.get("daily_sales", all_metrics.get("daily_sales", []))
    buf_trend = generate_trend_chart_img(daily_sales, width_in=4.8, height_in=2.4)
    slide1.shapes.add_picture(buf_trend, Inches(4.2), Inches(1.3), width=Inches(4.8), height=Inches(2.4))

    # 3. Total Sale by Sales Person (Horizontal Bar Chart Image)
    reps_list = unbilled_metrics.get("sales_reps", all_metrics.get("sales_reps", []))
    buf_rep = generate_sales_rep_chart_img(reps_list, width_in=8.2, height_in=3.4)
    slide1.shapes.add_picture(buf_rep, Inches(0.8), Inches(3.8), width=Inches(8.2), height=Inches(3.4))

    # 4. Total Sale by ServiceMode (Pie Chart Image - Right Top)
    modes_list = unbilled_metrics.get("modes", all_metrics.get("modes", []))
    buf_pie = generate_servicemode_pie_chart_img(modes_list, width_in=3.3, height_in=2.7)
    slide1.shapes.add_picture(buf_pie, Inches(9.2), Inches(1.3), width=Inches(3.3), height=Inches(2.7))

    # 5. TOP 5 Customer by Sale (Donut Chart Image - Right Bottom)
    custs_list = unbilled_metrics.get("customers", all_metrics.get("customers", []))
    buf_cust = generate_top_customer_chart_img(custs_list, width_in=3.3, height_in=2.7)
    slide1.shapes.add_picture(buf_cust, Inches(9.2), Inches(4.1), width=Inches(3.3), height=Inches(2.7))

    # ═════════════════════════════════════════════════════════════════
    # SLIDE 2: FINANCIAL RECONCILIATION & RISK AUDIT
    # ═════════════════════════════════════════════════════════════════
    slide2 = prs.slides.add_slide(blank_layout)
    add_minimalist_header(slide2, "SCHEDULE 01: TRI-FACTOR FINANCIAL RECONCILIATION & RISK REGISTER")

    # 3-Pillar Clean Metric Cards
    pillars = [
        ("BILLED INVOICED REVENUE", format_inr(summary.get("billed_sales", 0)), f"{summary.get('billed_shipments', 0):,} AWBs Invoiced", RGBColor(5, 150, 105)),
        ("UNBILLED EXPOSURE (RISK)", format_inr(summary.get("unbilled_sales", 0)), f"{summary.get('unbilled_shipments', 0):,} AWBs Pending", RGBColor(217, 119, 6)),
        ("CONSOLIDATED TOTAL", format_inr(summary.get("total_sales", 0)), f"{summary.get('total_shipments', 0):,} Dockets Reconciled", RGBColor(37, 99, 235))
    ]
    card_w = Inches(3.7)
    card_h = Inches(1.3)
    card_gap = Inches(0.3)
    start_x = Inches(0.8)

    for i, (label, val, sub, accent) in enumerate(pillars):
        x = start_x + (i * (card_w + card_gap))
        card = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, Inches(1.35), card_w, card_h)
        card.fill.solid()
        card.fill.fore_color.rgb = RGBColor(248, 250, 252)
        card.line.color.rgb = RGBColor(226, 232, 240)

        tx = slide2.shapes.add_textbox(x + Inches(0.2), Inches(1.45), card_w - Inches(0.4), card_h - Inches(0.2))
        tf = tx.text_frame
        p_lbl = tf.paragraphs[0]
        p_lbl.text = label
        p_lbl.font.size = Pt(9.5)
        p_lbl.font.bold = True
        p_lbl.font.color.rgb = RGBColor(100, 116, 139)

        p_val = tf.add_paragraph()
        p_val.text = val
        p_val.font.size = Pt(17)
        p_val.font.bold = True
        p_val.font.color.rgb = accent

        p_sub = tf.add_paragraph()
        p_sub.text = sub
        p_sub.font.size = Pt(8.5)
        p_sub.font.color.rgb = RGBColor(71, 85, 105)

    # Critical Revenue Leakage Alert Card
    alert_box = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(2.85), Inches(11.733), Inches(1.05))
    alert_box.fill.solid()
    alert_box.fill.fore_color.rgb = RGBColor(255, 241, 242)
    alert_box.line.color.rgb = RGBColor(244, 63, 94)

    tx_al = slide2.shapes.add_textbox(Inches(1.0), Inches(2.95), Inches(11.3), Inches(0.85))
    tf_al = tx_al.text_frame
    p_al = tf_al.paragraphs[0]
    p_al.text = "CRITICAL AUDIT FINDING: DELIVERED BUT UNBILLED REVENUE EXPOSURE"
    p_al.font.bold = True
    p_al.font.size = Pt(11)
    p_al.font.color.rgb = RGBColor(190, 18, 60)

    p_al2 = tf_al.add_paragraph()
    deliv_cnt = summary.get('delivered_unbilled_count', 0)
    deliv_val = format_inr(summary.get('delivered_unbilled_amt', 0))
    p_al2.text = f"{deliv_cnt:,} freight dockets valued at {deliv_val} have been successfully delivered to client locations without invoice generation. Immediate billing release required to avoid working capital loss."
    p_al2.font.size = Pt(9.5)
    p_al2.font.color.rgb = RGBColor(15, 23, 42)

    # Tri-Factor Schedule Table
    t_shape = slide2.shapes.add_table(4, 5, Inches(0.8), Inches(4.1), Inches(11.733), Inches(3.0))
    t = t_shape.table

    headers = ["Audit Category", "Reconciled Revenue (INR)", "Consignments", "Cargo Weight (Kg)", "Share %"]
    for col_idx, h in enumerate(headers):
        cell = t.cell(0, col_idx)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(15, 23, 42)
        for p in cell.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(11)
            p.font.color.rgb = RGBColor(255, 255, 255)

    tot_s = summary.get("total_sales", 1) or 1
    rows_data = [
        ["BILLED REVENUE (INVOICED)", format_inr(summary.get("billed_sales", 0)), f"{summary.get('billed_shipments', 0):,}", f"{billed_metrics.get('summary', {}).get('total_weight', 0):,.1f} Kg", f"{(summary.get('billed_sales', 0)/tot_s*100):.1f}%"],
        ["UNBILLED REVENUE (PENDING)", format_inr(summary.get("unbilled_sales", 0)), f"{summary.get('unbilled_shipments', 0):,}", f"{unbilled_metrics.get('summary', {}).get('total_weight', 0):,.1f} Kg", f"{(summary.get('unbilled_sales', 0)/tot_s*100):.1f}%"],
        ["CONSOLIDATED TOTAL", format_inr(tot_s), f"{summary.get('total_shipments', 0):,}", f"{summary.get('total_weight', 0):,.1f} Kg", "100.0%"]
    ]
    for row_idx, r in enumerate(rows_data, start=1):
        for col_idx, v in enumerate(r):
            cell = t.cell(row_idx, col_idx)
            cell.text = v
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(255, 255, 255) if row_idx < 3 else RGBColor(241, 245, 249)
            for p in cell.text_frame.paragraphs:
                p.font.bold = (row_idx == 3)
                p.font.size = Pt(10.5)
                p.font.color.rgb = RGBColor(15, 23, 42)

    # ═════════════════════════════════════════════════════════════════
    # SLIDE 3: SALES TEAM & CLIENT CONCENTRATION
    # ═════════════════════════════════════════════════════════════════
    slide3 = prs.slides.add_slide(blank_layout)
    add_minimalist_header(slide3, "SCHEDULE 02: SALES TEAM PERFORMANCE & MAJOR CLIENT ACCOUNTS")

    # Table 1 (Left): Sales Representatives
    reps = all_metrics.get("sales_reps", [])[:8]
    t_rep_shape = slide3.shapes.add_table(min(len(reps) + 1, 9), 4, Inches(0.8), Inches(1.4), Inches(5.6), Inches(5.6))
    t_rep = t_rep_shape.table

    rep_headers = ["Sales Representative", "AWBs", "Turnover (INR)", "Share"]
    for col_idx, h in enumerate(rep_headers):
        cell = t_rep.cell(0, col_idx)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(15, 23, 42)
        for p in cell.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(10)
            p.font.color.rgb = RGBColor(255, 255, 255)

    for row_idx, r in enumerate(reps, start=1):
        vals = [r["name"][:20], f"{r['shipments']:,}", format_inr(r["sales"]), f"{r['share_pct']}%"]
        for col_idx, v in enumerate(vals):
            cell = t_rep.cell(row_idx, col_idx)
            cell.text = v
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(255, 255, 255) if row_idx % 2 == 1 else RGBColor(248, 250, 252)
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(9.5)
                p.font.color.rgb = RGBColor(15, 23, 42)

    # Table 2 (Right): Top 8 Major Clients
    custs = all_metrics.get("customers", [])[:8]
    t_cust_shape = slide3.shapes.add_table(min(len(custs) + 1, 9), 4, Inches(6.8), Inches(1.4), Inches(5.7), Inches(5.6))
    t_cust = t_cust_shape.table

    cust_headers = ["Client Account Name", "Account Mgr", "Turnover (INR)", "Share"]
    for col_idx, h in enumerate(cust_headers):
        cell = t_cust.cell(0, col_idx)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(15, 23, 42)
        for p in cell.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(10)
            p.font.color.rgb = RGBColor(255, 255, 255)

    for row_idx, c in enumerate(custs, start=1):
        vals = [c["name"][:22], c["sales_person"][:12], format_inr(c["sales"]), f"{c['share_pct']}%"]
        for col_idx, v in enumerate(vals):
            cell = t_cust.cell(row_idx, col_idx)
            cell.text = v
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(255, 255, 255) if row_idx % 2 == 1 else RGBColor(248, 250, 252)
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(9.5)
                p.font.color.rgb = RGBColor(15, 23, 42)

    # ═════════════════════════════════════════════════════════════════
    # SLIDE 4: TRANSPORT MODES, DELIVERY HUBS & AUDIT SIGN-OFF
    # ═════════════════════════════════════════════════════════════════
    slide4 = prs.slides.add_slide(blank_layout)
    add_minimalist_header(slide4, "SCHEDULE 03: LOGISTICS MODES, HUBS & AUDITOR CERTIFICATION")

    # Mode Dynamics Table
    modes = all_metrics.get("modes", [])
    t_mode_shape = slide4.shapes.add_table(min(len(modes) + 1, 6), 4, Inches(0.8), Inches(1.4), Inches(5.6), Inches(3.2))
    t_mode = t_mode_shape.table

    mode_headers = ["Transport Mode", "Consignments", "Turnover (INR)", "Share"]
    for col_idx, h in enumerate(mode_headers):
        cell = t_mode.cell(0, col_idx)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(15, 23, 42)
        for p in cell.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(10)
            p.font.color.rgb = RGBColor(255, 255, 255)

    for row_idx, m in enumerate(modes, start=1):
        vals = [
            str(m.get("mode", "Other")),
            f"{m.get('shipments', 0):,} AWBs",
            format_inr(m.get("sales", 0)),
            f"{m.get('share_pct', 0)}%"
        ]
        for col_idx, v in enumerate(vals):
            cell = t_mode.cell(row_idx, col_idx)
            cell.text = v
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(255, 255, 255) if row_idx % 2 == 1 else RGBColor(248, 250, 252)
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(9.5)
                p.font.color.rgb = RGBColor(15, 23, 42)

    # Top Delivery Hubs Table
    dests = all_metrics.get("destinations", [])[:6]
    t_dest_shape = slide4.shapes.add_table(min(len(dests) + 1, 7), 3, Inches(6.8), Inches(1.4), Inches(5.7), Inches(3.2))
    t_dest = t_dest_shape.table

    dest_headers = ["Top Delivery Hub City", "Consignments", "Freight Turnover (INR)"]
    for col_idx, h in enumerate(dest_headers):
        cell = t_dest.cell(0, col_idx)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(15, 23, 42)
        for p in cell.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(10)
            p.font.color.rgb = RGBColor(255, 255, 255)

    for row_idx, d in enumerate(dests, start=1):
        vals = [str(d.get("city", "Unknown")), f"{d.get('shipments', 0):,} AWBs", format_inr(d.get("sales", 0))]
        for col_idx, v in enumerate(vals):
            cell = t_dest.cell(row_idx, col_idx)
            cell.text = v
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(255, 255, 255) if row_idx % 2 == 1 else RGBColor(248, 250, 252)
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(9.5)
                p.font.color.rgb = RGBColor(15, 23, 42)

    # Formal Attestation Card (Bottom)
    sign_box = slide4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(4.9), Inches(11.733), Inches(2.2))
    sign_box.fill.solid()
    sign_box.fill.fore_color.rgb = RGBColor(248, 250, 252)
    sign_box.line.color.rgb = RGBColor(203, 213, 225)

    tx_s = slide4.shapes.add_textbox(Inches(1.1), Inches(5.05), Inches(11.1), Inches(1.9))
    tf_s = tx_s.text_frame
    p_st = tf_s.paragraphs[0]
    p_st.text = "FORMAL AUDIT CERTIFICATION & MANAGEMENT ATTESTATION"
    p_st.font.bold = True
    p_st.font.size = Pt(11)
    p_st.font.color.rgb = RGBColor(15, 23, 42)

    p_sb = tf_s.add_paragraph()
    p_sb.text = ("This monthly sales and logistics audit report has been compiled through 100% automated three-way triangulation "
                 "across Billed MIS, Unbilled MIS, and Operations Booking Register. All dockets, weights, transport modes, and "
                 "sales attribution have been reconciled.")
    p_sb.font.size = Pt(9.5)
    p_sb.font.color.rgb = RGBColor(71, 85, 105)

    p_sig = tf_s.add_paragraph()
    p_sig.text = "Lead Internal Auditor: ___________________________          Audit Sign-Off Date: ___________________________"
    p_sig.font.bold = True
    p_sig.font.size = Pt(10)
    p_sig.font.color.rgb = RGBColor(15, 23, 42)
    p_sig.space_before = Pt(14)

    out = io.BytesIO()
    prs.save(out)
    out.seek(0)
    return out


# ─────────────────────────────────────────────────────────────
# 2. EXECUTIVE MULTI-PAGE AUDIT REPORT (.PDF)
# ─────────────────────────────────────────────────────────────

def generate_sales_pdf(report_row, report_data):
    """
    Generates a minimalist, Big-4 style PDF audit report with NumberedCanvas,
    Page 1 executive visual dashboard with embedded charts, and comprehensive schedules.
    """
    class NumberedCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super(NumberedCanvas, self).__init__(*args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            num_pages = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self.draw_page_decorations(num_pages)
                super(NumberedCanvas, self).showPage()
            super(NumberedCanvas, self).save()

        def draw_page_decorations(self, page_count):
            self.saveState()
            self.setFont("Helvetica-Bold", 7.5)
            self.setFillColor(colors.HexColor("#64748B"))
            # Running Header
            self.drawString(36, 808, "NORTH EXPRESS LOGISTICS LTD.  |  EXECUTIVE SALES AUDIT")
            self.drawRightString(559, 808, "STRICTLY CONFIDENTIAL")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(36, 802, 559, 802)
            
            # Running Footer
            self.line(36, 36, 559, 36)
            self.setFont("Helvetica", 7.5)
            self.drawString(36, 24, "Automated Tri-Factor Logistics Reconciliation Engine  |  Boardroom Copy")
            self.drawRightString(559, 24, f"Page {self._pageNumber} of {page_count}")
            self.restoreState()

    out = io.BytesIO()
    doc = SimpleDocTemplate(
        out,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=46,
        bottomMargin=46
    )

    styles = getSampleStyleSheet()

    doc_title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=17,
        leading=21,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=3
    )
    doc_sub_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#64748B')
    )
    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=6,
        spaceAfter=3
    )
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#1E293B')
    )
    card_label = ParagraphStyle(
        'CardLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=9,
        textColor=colors.HexColor('#64748B')
    )
    card_val = ParagraphStyle(
        'CardVal',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#0F172A')
    )
    table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=10,
        textColor=colors.white
    )
    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#1E293B')
    )
    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#0F172A')
    )
    table_cell_right = ParagraphStyle(
        'TableCellRight',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        alignment=2,
        textColor=colors.HexColor('#1E293B')
    )
    table_cell_right_bold = ParagraphStyle(
        'TableCellRightBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=10,
        alignment=2,
        textColor=colors.HexColor('#0F172A')
    )

    logo_path = os.path.join(Config.BASE_DIR, "static", "doxera_logo.png")
    summary = report_data.get("summary", {})
    all_metrics = report_data.get("all", {})
    billed_metrics = report_data.get("billed", {})
    unbilled_metrics = report_data.get("unbilled", {})
    connectivity = report_data.get("connectivity", {})

    period_str = summary.get("period_label", "Monthly Audit Period")

    story = []

    def make_section_banner(section_no, section_title, subtitle=""):
        banner_content = [
            Paragraph(f"<b>{section_no} | {section_title.upper()}</b>", h1_style)
        ]
        if subtitle:
            banner_content.append(Paragraph(subtitle, doc_sub_style))
        banner_content.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#CBD5E1"), spaceBefore=3, spaceAfter=6))
        return banner_content

    # ═════════════════════════════════════════════════════════════════
    # PAGE 1: EXECUTIVE VISUAL DASHBOARD (1:1 Power BI Layout)
    # ═════════════════════════════════════════════════════════════════
    
    # Header with Logo
    header_data = []
    if os.path.exists(logo_path):
        try:
            img = Image(logo_path, width=95, height=28)
            txt = Paragraph("<b>NORTH EXPRESS LOGISTICS LTD.</b><br/><font color='#64748B' size=7>EXECUTIVE LOGISTICS SALES AUDIT REPORT</font>", doc_sub_style)
            header_data = [[img, txt]]
        except Exception:
            header_data = [[Paragraph("<b>NORTH EXPRESS LOGISTICS LTD.</b>", doc_title_style)]]
    else:
        header_data = [[Paragraph("<b>NORTH EXPRESS LOGISTICS LTD.</b>", doc_title_style)]]
    
    t_head = Table(header_data, colWidths=[110, 413])
    t_head.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    story.append(t_head)
    story.append(Spacer(1, 2))

    story.append(Paragraph("SALES REPORT (UNBILLED & CONSOLIDATED)", doc_title_style))
    story.append(Paragraph(f"Audit Window: <b>{period_str}</b>  •  Correlated: <b>{summary.get('total_shipments', 0):,} AWBs</b>  •  <b>Note: Accurate Data.</b>", doc_sub_style))
    story.append(Spacer(1, 6))

    # Black High-Contrast KPI Card
    unb_amt = summary.get("unbilled_sales", summary.get("total_sales", 0))
    unb_awbs = summary.get("unbilled_shipments", summary.get("total_shipments", 0))
    tot_wt = unbilled_metrics.get("summary", {}).get("total_weight", summary.get("total_weight", 0))
    avg_ticket = unbilled_metrics.get("summary", {}).get("avg_ticket", summary.get("avg_ticket", 0))

    kpi_black_data = [
        [
            Paragraph(f"<font color='#38BDF8' size=14><b>₹ {format_plain_inr(unb_amt)}</b></font><br/>"
                      f"<font color='#FFFFFF' size=8><b>TOTAL SALE (UNBILLED)</b></font>", card_val),
            Paragraph(f"<font color='#FFFFFF' size=12><b>{unb_awbs:,}</b></font><br/>"
                      f"<font color='#94A3B8' size=7.5>CONSIGNMENTS</font>", card_val),
            Paragraph(f"<font color='#FFFFFF' size=12><b>{tot_wt:,.1f} Kg</b></font><br/>"
                      f"<font color='#94A3B8' size=7.5>GROSS WEIGHT</font>", card_val),
            Paragraph(f"<font color='#FFFFFF' size=12><b>₹ {format_plain_inr(avg_ticket)}</b></font><br/>"
                      f"<font color='#94A3B8' size=7.5>AVG FREIGHT TICKET</font>", card_val)
        ]
    ]
    t_kpi_black = Table(kpi_black_data, colWidths=[170, 115, 118, 120])
    t_kpi_black.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#000000')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_kpi_black)
    story.append(Spacer(1, 8))

    # 4 Visual Charts Grid (Matching Screen)
    daily_sales = unbilled_metrics.get("daily_sales", all_metrics.get("daily_sales", []))
    reps_list = unbilled_metrics.get("sales_reps", all_metrics.get("sales_reps", []))
    modes_list = unbilled_metrics.get("modes", all_metrics.get("modes", []))
    custs_list = unbilled_metrics.get("customers", all_metrics.get("customers", []))

    buf_trend = generate_trend_chart_img(daily_sales, width_in=4.4, height_in=2.0)
    buf_pie = generate_servicemode_pie_chart_img(modes_list, width_in=3.4, height_in=2.0)
    buf_rep = generate_sales_rep_chart_img(reps_list, width_in=4.4, height_in=2.2)
    buf_cust = generate_top_customer_chart_img(custs_list, width_in=3.4, height_in=2.2)

    img_trend = Image(buf_trend, width=285, height=135)
    img_pie = Image(buf_pie, width=230, height=135)
    img_rep = Image(buf_rep, width=285, height=145)
    img_cust = Image(buf_cust, width=230, height=145)

    charts_grid = [
        [img_trend, img_pie],
        [img_rep, img_cust]
    ]
    t_charts = Table(charts_grid, colWidths=[290, 233])
    t_charts.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(t_charts)

    # ═════════════════════════════════════════════════════════════════
    # PAGE 2: FINANCIAL RECONCILIATION & RISK REGISTER
    # ═════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.extend(make_section_banner("SCHEDULE 01", "Tri-Factor Financial Reconciliation & Risk Register", "Triangulation across Billed MIS, Unbilled MIS, and Booking Register."))

    # 3 Pillar Summary Cards
    tot_s = summary.get("total_sales", 1) or 1
    pillars_table = [
        [
            Paragraph("BILLED REVENUE (INVOICED)", card_label),
            Paragraph("UNBILLED EXPOSURE (PENDING)", card_label),
            Paragraph("CONSOLIDATED AUDIT TOTAL", card_label)
        ],
        [
            Paragraph(format_inr(summary.get("billed_sales", 0)), card_val),
            Paragraph(format_inr(summary.get("unbilled_sales", 0)), card_val),
            Paragraph(format_inr(tot_s), card_val)
        ],
        [
            Paragraph(f"{summary.get('billed_shipments', 0):,} AWBs  •  100% Invoiced", doc_sub_style),
            Paragraph(f"{summary.get('unbilled_shipments', 0):,} AWBs  •  Pending Billing", doc_sub_style),
            Paragraph(f"{summary.get('total_shipments', 0):,} AWBs  •  {summary.get('total_weight', 0):,.1f} Kg", doc_sub_style)
        ]
    ]
    t_pillars = Table(pillars_table, colWidths=[174, 174, 175])
    t_pillars.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 0.75, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_pillars)
    story.append(Spacer(1, 8))

    # Revenue Leakage Warning Box
    deliv_count = summary.get('delivered_unbilled_count', 0)
    deliv_amt = summary.get('delivered_unbilled_amt', 0)
    leakage_data = [
        [
            Paragraph("<b>CRITICAL REVENUE LEAKAGE FINDING (DELIVERED BUT UNBILLED)</b><br/>"
                      f"The audit engine reconciled <b>{deliv_count:,} consignments</b> totaling <b>{format_inr(deliv_amt)}</b> "
                      "where freight goods have been delivered to customer addresses without invoice generation. "
                      "Immediate billing action is required to avoid financial leakage.", body_style)
        ]
    ]
    t_leakage = Table(leakage_data, colWidths=[523])
    t_leakage.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FFF1F2')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#F43F5E')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_leakage)
    story.append(Spacer(1, 8))

    # Tri-Factor Reconciliation Table
    reconcil_data = [
        [
            Paragraph("<b>Audit Category</b>", table_header),
            Paragraph("<b>Dockets (AWB)</b>", table_header),
            Paragraph("<b>Weight (Kg)</b>", table_header),
            Paragraph("<b>Reconciled Freight (INR)</b>", table_header),
            Paragraph("<b>Average Ticket</b>", table_header),
            Paragraph("<b>Share %</b>", table_header)
        ],
        [
            Paragraph("<b>Billed MIS (Invoiced Revenue)</b>", table_cell_bold),
            Paragraph(f"{summary.get('billed_shipments', 0):,}", table_cell_right),
            Paragraph(f"{billed_metrics.get('summary', {}).get('total_weight', 0):,.1f}", table_cell_right),
            Paragraph(format_inr(summary.get("billed_sales", 0)), table_cell_right_bold),
            Paragraph(format_inr(billed_metrics.get("summary", {}).get("avg_ticket", 0)), table_cell_right),
            Paragraph(f"{(summary.get('billed_sales', 0)/tot_s*100):.1f}%", table_cell_right_bold)
        ],
        [
            Paragraph("<b>Unbilled MIS (Pending Exposure)</b>", table_cell_bold),
            Paragraph(f"{summary.get('unbilled_shipments', 0):,}", table_cell_right),
            Paragraph(f"{unbilled_metrics.get('summary', {}).get('total_weight', 0):,.1f}", table_cell_right),
            Paragraph(format_inr(summary.get("unbilled_sales", 0)), table_cell_right_bold),
            Paragraph(format_inr(unbilled_metrics.get("summary", {}).get("avg_ticket", 0)), table_cell_right),
            Paragraph(f"{(summary.get('unbilled_sales', 0)/tot_s*100):.1f}%", table_cell_right_bold)
        ],
        [
            Paragraph("<b>Total Reconciled Operations Base</b>", table_cell_bold),
            Paragraph(f"{summary.get('total_shipments', 0):,}", table_cell_right_bold),
            Paragraph(f"{summary.get('total_weight', 0):,.1f}", table_cell_right_bold),
            Paragraph(format_inr(tot_s), table_cell_right_bold),
            Paragraph(format_inr(summary.get("avg_ticket", 0)), table_cell_right_bold),
            Paragraph("100.0%", table_cell_right_bold)
        ]
    ]
    t_rec = Table(reconcil_data, colWidths=[163, 65, 75, 95, 75, 50])
    t_rec.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#FFFFFF')),
        ('BACKGROUND', (0,2), (-1,2), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,3), (-1,3), colors.HexColor('#F1F5F9')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_rec)

    # ═════════════════════════════════════════════════════════════════
    # PAGE 3: SALES TEAM & CLIENT CONCENTRATION
    # ═════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.extend(make_section_banner("SCHEDULE 02", "Sales Team Accountability & Corporate Client Concentration", "Portfolio allocation, sales representative turnover, and account concentration."))

    # Sales Reps Table
    reps = all_metrics.get("sales_reps", [])
    rep_table_data = [
        [
            Paragraph("<b>#</b>", table_header),
            Paragraph("<b>Sales Representative Name</b>", table_header),
            Paragraph("<b>Accounts</b>", table_header),
            Paragraph("<b>Dockets</b>", table_header),
            Paragraph("<b>Total Turnover (INR)</b>", table_header),
            Paragraph("<b>Share %</b>", table_header)
        ]
    ]
    for idx, r in enumerate(reps[:10], start=1):
        rep_table_data.append([
            Paragraph(str(idx), table_cell),
            Paragraph(str(r.get("name", "Unknown")), table_cell_bold),
            Paragraph(str(r.get("customer_count", 0)), table_cell_right),
            Paragraph(f"{r.get('shipments', 0):,}", table_cell_right),
            Paragraph(format_inr(r.get("sales", 0)), table_cell_right_bold),
            Paragraph(f"{r.get('share_pct', 0)}%", table_cell_right_bold)
        ])
    t_rep_audit = Table(rep_table_data, colWidths=[20, 195, 65, 65, 115, 63])
    t_rep_audit.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
        *([('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F8FAFC')) for i in range(2, len(rep_table_data), 2)])
    ]))
    story.append(t_rep_audit)
    story.append(Spacer(1, 10))

    # Top Clients Table
    story.append(Paragraph("<b>TOP CORPORATE CLIENT CONCENTRATION SCHEDULE</b>", h1_style))
    custs = all_metrics.get("customers", [])[:10]
    cust_table_data = [
        [
            Paragraph("<b>#</b>", table_header),
            Paragraph("<b>Customer Account Name</b>", table_header),
            Paragraph("<b>Code</b>", table_header),
            Paragraph("<b>Account Manager</b>", table_header),
            Paragraph("<b>Dockets</b>", table_header),
            Paragraph("<b>Total Turnover (INR)</b>", table_header),
            Paragraph("<b>Share %</b>", table_header)
        ]
    ]
    for idx, c in enumerate(custs, start=1):
        cust_name = str(c.get("name", "Unknown"))[:32]
        cust_code = str(c.get("code") or "---")
        cust_rep = str(c.get("sales_person", "NEL"))
        cust_table_data.append([
            Paragraph(str(idx), table_cell),
            Paragraph(cust_name, table_cell_bold),
            Paragraph(cust_code, table_cell),
            Paragraph(cust_rep, table_cell),
            Paragraph(f"{c.get('shipments', 0):,}", table_cell_right),
            Paragraph(format_inr(c.get("sales", 0)), table_cell_right_bold),
            Paragraph(f"{c.get('share_pct', 0)}%", table_cell_right)
        ])
    t_cust_audit = Table(cust_table_data, colWidths=[20, 185, 55, 95, 48, 75, 45])
    t_cust_audit.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
        *([('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F8FAFC')) for i in range(2, len(cust_table_data), 2)])
    ]))
    story.append(t_cust_audit)

    # ═════════════════════════════════════════════════════════════════
    # PAGE 4: LOGISTICS MODES, DELIVERY HUBS & AUDIT ATTESTATION
    # ═════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.extend(make_section_banner("SCHEDULE 03", "Transport Mode Dynamics, Hubs & Auditor Certification", "Air, Surface, and Train freight yields, destination hubs, and formal attestation."))

    # Mode Performance Table
    modes = all_metrics.get("modes", [])
    mode_table_data = [
        [
            Paragraph("<b>Transport Mode</b>", table_header),
            Paragraph("<b>Consignments</b>", table_header),
            Paragraph("<b>Total Weight (Kg)</b>", table_header),
            Paragraph("<b>Freight Yield (INR/Kg)</b>", table_header),
            Paragraph("<b>Reconciled Freight (INR)</b>", table_header),
            Paragraph("<b>Share %</b>", table_header)
        ]
    ]
    for m in modes:
        wt = m.get("weight", 0)
        wt_str = f"{wt:,.1f}" if wt else "---"
        yd = m.get("yield_per_kg", 0)
        yd_str = f"₹ {yd:.2f}/Kg" if yd else "---"
        mode_table_data.append([
            Paragraph(str(m.get("mode", "Other")), table_cell_bold),
            Paragraph(f"{m.get('shipments', 0):,}", table_cell_right),
            Paragraph(wt_str, table_cell_right),
            Paragraph(yd_str, table_cell_right),
            Paragraph(format_inr(m.get("sales", 0)), table_cell_right_bold),
            Paragraph(f"{m.get('share_pct', 0)}%", table_cell_right_bold)
        ])
    t_mode_audit = Table(mode_table_data, colWidths=[90, 75, 90, 95, 115, 58])
    t_mode_audit.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
    ]))
    story.append(t_mode_audit)
    story.append(Spacer(1, 10))

    # Top Delivery Hubs Table
    story.append(Paragraph("<b>TOP ALL-INDIA DESTINATION DELIVERY HUBS</b>", h1_style))
    dests = all_metrics.get("destinations", [])[:8]
    dest_table_data = [
        [
            Paragraph("<b>#</b>", table_header),
            Paragraph("<b>Delivery Destination Hub</b>", table_header),
            Paragraph("<b>Consignments (AWBs)</b>", table_header),
            Paragraph("<b>Freight Turnover (INR)</b>", table_header)
        ]
    ]
    for idx, d in enumerate(dests, start=1):
        dest_table_data.append([
            Paragraph(str(idx), table_cell),
            Paragraph(str(d.get("city", "Unknown")), table_cell_bold),
            Paragraph(f"{d.get('shipments', 0):,} AWBs", table_cell_right),
            Paragraph(format_inr(d.get("sales", 0)), table_cell_right_bold)
        ])
    t_dest_audit = Table(dest_table_data, colWidths=[25, 230, 115, 153])
    t_dest_audit.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
        *([('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F8FAFC')) for i in range(2, len(dest_table_data), 2)])
    ]))
    story.append(t_dest_audit)
    story.append(Spacer(1, 12))

    # Formal Attestation Block
    signoff_data = [
        [
            Paragraph("<b>FORMAL AUDIT CERTIFICATION & MANAGEMENT ATTESTATION</b><br/>"
                      "This monthly sales and logistics intelligence audit report has been compiled through 100% automated "
                      "three-way triangulation across Billed MIS, Unbilled MIS, and Operations Booking Register. "
                      "All docket numbers, cargo weights, transport modes, and sales allocations have been verified.<br/><br/>"
                      "<b>Lead Internal Auditor:</b> ___________________________ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; "
                      "<b>Audit Sign-Off Date:</b> ___________________________<br/>"
                      "<font size=7 color='#64748B'>North Express Logistics Internal Audit Committee | Doxera Intelligence Engine</font>", body_style)
        ]
    ]
    t_signoff = Table(signoff_data, colWidths=[523])
    t_signoff.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#0F172A')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_signoff)

    doc.build(story, canvasmaker=NumberedCanvas)
    out.seek(0)
    return out
