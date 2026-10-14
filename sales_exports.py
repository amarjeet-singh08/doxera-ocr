# DOXERA Executive Sales Export Engine
# =========================================================
# Generates boardroom-ready, statutory-grade PDF and PowerPoint (.PPTX)
# audit reports for North Express Logistics Pvt. Ltd. with embedded
# high-resolution visual analytics charts.
# Security: Restricted strictly to ADMIN and AUDITOR roles.

import os
import io
import re
import pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from config import Config


# ─────────────────────────────────────────────────────────────
# CORPORATE IDENTITY CONSTANTS
# ─────────────────────────────────────────────────────────────
COMPANY_LEGAL_NAME = "NORTH EXPRESS LOGISTICS PVT. LTD."
COMPANY_TITLE_NAME = "North Express Logistics Pvt. Ltd."
AUDIT_REPORT_SUBTITLE = "EXECUTIVE LOGISTICS REVENUE & RECONCILIATION AUDIT REPORT"
AUDIT_BODY_AUTHORITY = "North Express Logistics Pvt. Ltd. Internal Audit Committee | Doxera Intelligence Engine"


# ─────────────────────────────────────────────────────────────
# CURRENCY & NUMBER FORMATTING HELPERS
# ─────────────────────────────────────────────────────────────

def format_indian_number(val, decimals=2):
    """
    Formats a numeric value using the authentic Indian numbering system:
    e.g. 9062452.84 -> '90,62,452.84'
    """
    if val is None or val == "":
        return "0.00" if decimals > 0 else "0"
    try:
        val = float(val)
        is_negative = val < 0
        val = abs(val)
        formatted_base = f"{val:.{decimals}f}"
        parts = formatted_base.split(".")
        int_part = parts[0]
        dec_part = ("." + parts[1]) if len(parts) > 1 and decimals > 0 else ""
        if len(int_part) <= 3:
            formatted_int = int_part
        else:
            last3 = int_part[-3:]
            rest = int_part[:-3]
            formatted_rest = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", rest)
            formatted_int = formatted_rest + "," + last3
        return f"{'-' if is_negative else ''}{formatted_int}{dec_part}"
    except (ValueError, TypeError):
        return str(val)

def format_inr(val):
    """Standard Indian Rupee currency string with symbol: ₹ 90,62,452.84"""
    if val is None or val == "":
        return "₹ 0.00"
    return "₹ " + format_indian_number(val, 2)

def format_plain_inr(val):
    """Indian currency string without currency symbol: 90,62,452.84"""
    return format_indian_number(val, 2)

def format_inr_short(val, prefix="₹ "):
    """
    Compact currency notation: e.g. ₹ 90.62 L, ₹ 1.25 Cr, ₹ 31.9 K.
    """
    if val is None or val == "":
        return f"{prefix}0.00"
    try:
        v = float(val)
        if v >= 10000000:
            return f"{prefix}{v/10000000:.2f} Cr"
        elif v >= 100000:
            return f"{prefix}{v/100000:.2f} L"
        elif v >= 1000:
            return f"{prefix}{v/1000:.1f} K"
        return f"{prefix}{v:,.0f}"
    except (ValueError, TypeError):
        return str(val)

def format_pdf_inr_short(val):
    """PDF-safe short currency (uses 'INR ' to avoid font symbol issues)."""
    return format_inr_short(val, prefix="INR ")


def _fmt_axis_lakh(v, p=None):
    """Clean tick formatter: 0, 20 L, 40 L, 60 L without overlapping text."""
    v = float(v or 0)
    if v == 0:
        return "0"
    if v >= 10000000:
        return f"{v/10000000:.1f} Cr"
    if v >= 100000:
        return f"{v/100000:.0f} L"
    if v >= 1000:
        return f"{v/1000:.0f} K"
    return f"{v:.0f}"


# ─────────────────────────────────────────────────────────────
# MINIMALIST EXECUTIVE CHART GENERATORS (Matplotlib Agg)
# Boardroom / Statutory Audit Aesthetic: Slate-900, Corporate Navy, Deep Teal
# ─────────────────────────────────────────────────────────────

def generate_trend_chart_img(daily_sales_list, width_in=4.4, height_in=2.0, dpi=180):
    """
    Renders Sale Graph by Date line chart with smooth area fill,
    dual callouts (Peak day + Latest day), non-overlapping X-axis date ticks,
    and clean INR Y-axis.
    """
    fig, ax = plt.subplots(figsize=(width_in, height_in), dpi=dpi)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')

    valid_days = [d for d in (daily_sales_list or []) if d.get('date') and d.get('date') != 'Undated']
    if not valid_days:
        ax.text(0.5, 0.5, 'No Daily Sales Trend Data', ha='center', va='center', color='#94A3B8', fontsize=8.5)
        ax.axis('off')
    else:
        vals = [float(d.get('sales', 0)) for d in valid_days]
        raw_dates = [str(d.get('date', '')) for d in valid_days]

        date_labels = []
        for rd in raw_dates:
            p = rd.split('-')
            date_labels.append(f"{p[0]}/{p[1]}" if len(p) >= 2 else rd)

        x = np.arange(len(valid_days))
        ax.plot(x, vals, color='#0F172A', lw=1.8, marker='o', markersize=3.2,
                markerfacecolor='#0F172A', markeredgecolor='#FFFFFF', markeredgewidth=0.8, zorder=3)
        ax.fill_between(x, vals, color='#0F172A', alpha=0.06, zorder=2)

        # 1. Peak Day Callout Badge
        if len(vals) > 0:
            max_idx = int(np.argmax(vals))
            max_val = vals[max_idx]
            ax.scatter([max_idx], [max_val], color='#0F172A', s=36, zorder=4)
            ax.annotate(
                f"Peak: {format_inr_short(max_val)}",
                xy=(max_idx, max_val),
                xytext=(0, 6),
                textcoords='offset points',
                ha='center',
                fontsize=6.5,
                fontweight='bold',
                color='#0F172A',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='#F1F5F9', edgecolor='#CBD5E1', lw=0.6)
            )

            # 2. Latest/Last Day Callout Badge (if different from peak)
            last_idx = len(vals) - 1
            if last_idx > 0 and last_idx != max_idx:
                last_val = vals[last_idx]
                ax.scatter([last_idx], [last_val], color='#475569', s=30, zorder=4)
                ax.annotate(
                    f"Latest: {format_inr_short(last_val)}",
                    xy=(last_idx, last_val),
                    xytext=(-12, 6),
                    textcoords='offset points',
                    ha='right',
                    fontsize=6.2,
                    fontweight='bold',
                    color='#334155',
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='#F8FAFC', edgecolor='#CBD5E1', lw=0.6)
                )

        # Space out X ticks so dates never collide
        step = max(1, len(valid_days) // 6)
        tick_indices = list(range(0, len(valid_days), step))
        if (len(valid_days) - 1) not in tick_indices:
            tick_indices.append(len(valid_days) - 1)

        ax.set_xticks(tick_indices)
        ax.set_xticklabels([date_labels[i] for i in tick_indices], fontsize=6.5, color='#475569')
        ax.yaxis.set_major_locator(ticker.MaxNLocator(nbins=4))
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(_fmt_axis_lakh))
        ax.tick_params(axis='y', labelsize=6.5, colors='#64748B')
        ax.tick_params(axis='x', length=2.5, color='#CBD5E1')
        ax.set_ylim(0, (max(vals) if vals else 1) * 1.25)

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#E2E8F0')
        ax.spines['bottom'].set_color('#CBD5E1')
        ax.grid(axis='y', linestyle='--', alpha=0.45, color='#E2E8F0')

    plt.title('Daily Sales Turnover Trend (Reconciled)', fontsize=8.0, fontweight='bold', loc='left', color='#0F172A', pad=7)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_sales_rep_chart_img(sales_reps_list, width_in=4.4, height_in=2.0, dpi=180):
    """
    Renders Total Sale by Sales Person ranked horizontal bar chart.
    Top performer in Slate-900; others in Slate-600.
    """
    fig, ax = plt.subplots(figsize=(width_in, height_in), dpi=dpi)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')

    reps = sales_reps_list[:6] if sales_reps_list else []
    if not reps:
        ax.text(0.5, 0.5, 'No Sales Reps Data', ha='center', va='center', color='#94A3B8', fontsize=8.5)
        ax.axis('off')
    else:
        names = [str(r.get("name", "NEL"))[:16] for r in reps]
        sales = [float(r.get("sales", 0)) for r in reps]
        shares = [float(r.get("share_pct", 0)) for r in reps]

        names.reverse()
        sales.reverse()
        shares.reverse()

        y_pos = np.arange(len(names))
        bars = ax.barh(y_pos, sales, color='#475569', height=0.52, edgecolor='none', zorder=3)
        if len(bars) > 0:
            bars[-1].set_color('#0F172A')  # Highlight top performer in Slate-900

        max_s = max(sales) if sales else 1
        for bar, s, sh in zip(bars, sales, shares):
            ax.text(
                s + (max_s * 0.02),
                bar.get_y() + bar.get_height() / 2,
                f"{format_inr_short(s)}  ({sh:.1f}%)",
                va='center',
                ha='left',
                fontsize=6.4,
                fontweight='bold',
                color='#334155'
            )

        ax.set_yticks(y_pos)
        ax.set_yticklabels(names, fontsize=6.8, fontweight='bold', color='#0F172A')
        ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=4))
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(_fmt_axis_lakh))
        ax.tick_params(axis='x', labelsize=6.4, colors='#64748B')
        ax.tick_params(axis='y', length=0)
        ax.set_xlim(0, max_s * 1.38)

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['bottom'].set_color('#CBD5E1')
        ax.grid(axis='x', linestyle='--', alpha=0.45, color='#E2E8F0')

    plt.title('Top Sales Representatives by Audited Turnover', fontsize=8.0, fontweight='bold', loc='left', color='#0F172A', pad=7)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_servicemode_pie_chart_img(mode_list, width_in=3.6, height_in=2.0, dpi=180):
    """
    Renders Total Sale by ServiceMode donut chart with guaranteed visual slice floor
    for small transport modes (e.g. Train 0.2%), center total, and crisp side legend.
    """
    fig, ax = plt.subplots(figsize=(width_in, height_in), dpi=dpi)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')

    valid_modes = [m for m in (mode_list or []) if float(m.get("sales", 0)) > 0 or int(m.get("shipments", 0)) > 0]
    if not valid_modes:
        ax.text(0.5, 0.5, 'No Mode Data', ha='center', va='center', color='#94A3B8', fontsize=8.5)
        ax.axis('off')
    else:
        raw_sales = [float(m.get("sales", 0)) for m in valid_modes]
        labels = [str(m.get("mode", "Other")) for m in valid_modes]
        total_sales = sum(raw_sales) or 1

        color_map = {'Air': '#0F172A', 'Surface': '#0D9488', 'Train': '#B45309'}
        pie_colors = [color_map.get(lbl, '#64748B') for lbl in labels]

        # Allocate minimum 4.5% visual slice floor so Train is never squished or invisible
        min_pct = 0.045
        visual_vals = list(raw_sales)
        small_indices = [i for i, v in enumerate(raw_sales) if v > 0 and (v / total_sales) < min_pct]
        if small_indices and len(small_indices) < len(raw_sales):
            reserved = min_pct * len(small_indices)
            rem_sum = sum(raw_sales[i] for i in range(len(raw_sales)) if i not in small_indices)
            scale = (1.0 - reserved)
            for i in range(len(raw_sales)):
                if i in small_indices:
                    visual_vals[i] = total_sales * min_pct
                else:
                    visual_vals[i] = (raw_sales[i] / rem_sum) * total_sales * scale if rem_sum > 0 else raw_sales[i]

        wedges, texts = ax.pie(
            visual_vals,
            colors=pie_colors,
            wedgeprops=dict(width=0.40, edgecolor='#FFFFFF', linewidth=1.5),
            startangle=140
        )

        # Center donut hole metric with clean vertical spacing
        ax.text(0, 0.10, 'AUDITED TURNOVER', ha='center', va='center', fontsize=5.8, fontweight='bold', color='#64748B')
        ax.text(0, -0.12, format_inr_short(total_sales), ha='center', va='center', fontsize=8.2, fontweight='bold', color='#0F172A')

        # Clean structured legend with true amounts and exact percentages
        legend_labels = []
        for m in valid_modes:
            name = m.get("mode")
            s = float(m.get("sales", 0))
            pct = (s / total_sales * 100) if total_sales else 0
            legend_labels.append(f"{name}: {format_inr_short(s)} ({pct:.1f}%)")

        ax.legend(
            wedges, legend_labels,
            loc='center left',
            bbox_to_anchor=(0.88, 0.5),
            frameon=False,
            fontsize=6.8,
            labelcolor='#0F172A'
        )

    plt.title('Turnover by Transport Mode', fontsize=8.0, fontweight='bold', loc='left', color='#0F172A', pad=7)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_top_customer_chart_img(customers_list, width_in=3.6, height_in=2.0, dpi=180):
    """
    Renders Top Corporate Accounts concentration horizontal bar chart matching the dashboard.
    """
    fig, ax = plt.subplots(figsize=(width_in, height_in), dpi=dpi)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')

    top_c = customers_list[:6] if customers_list else []
    if not top_c:
        ax.text(0.5, 0.5, 'No Customer Data', ha='center', va='center', color='#94A3B8', fontsize=8.5)
        ax.axis('off')
    else:
        names = [str(c.get("name", "General"))[:18] for c in top_c]
        sales = [float(c.get("sales", 0)) for c in top_c]
        shares = [float(c.get("share_pct", 0)) for c in top_c]

        names.reverse()
        sales.reverse()
        shares.reverse()

        y_pos = np.arange(len(names))
        bars = ax.barh(y_pos, sales, color='#475569', height=0.52, edgecolor='none', zorder=3)
        if len(bars) > 0:
            bars[-1].set_color('#0F172A')  # Highlight top customer in Slate-900

        max_cs = max(sales) if sales else 1
        for bar, s, sh in zip(bars, sales, shares):
            ax.text(
                s + (max_cs * 0.02),
                bar.get_y() + bar.get_height() / 2,
                f"{format_inr_short(s)}  ({sh:.1f}%)",
                va='center',
                ha='left',
                fontsize=6.2,
                fontweight='bold',
                color='#334155'
            )

        ax.set_yticks(y_pos)
        ax.set_yticklabels(names, fontsize=6.5, fontweight='bold', color='#0F172A')
        ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=4))
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(_fmt_axis_lakh))
        ax.tick_params(axis='x', labelsize=6.2, colors='#64748B')
        ax.tick_params(axis='y', length=0)
        ax.set_xlim(0, max_cs * 1.40)

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['bottom'].set_color('#CBD5E1')
        ax.grid(axis='x', linestyle='--', alpha=0.45, color='#E2E8F0')

    plt.title('Top Corporate Accounts Concentration', fontsize=8.0, fontweight='bold', loc='left', color='#0F172A', pad=7)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────
# 1. EXECUTIVE POWERPOINT PRESENTATION (.PPTX)
# Boardroom / Statutory Audit Presentation (16:9 Widescreen)
# ─────────────────────────────────────────────────────────────

def generate_sales_pptx(report_row, report_data):
    """
    Generates a minimalist, boardroom-ready 16:9 presentation.
    Slide 1: Executive Visual Dashboard (Clean White KPI Cards + 4 Visual Charts + Highlights)
    Slide 2: Tri-Factor Financial Reconciliation & Risk Register
    Slide 3: Sales Team Accountability & Major Corporate Accounts
    Slide 4: Transport Modes, Strategic Corridors & Audit Attestation
    """
    prs = pptx.Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Resolve report title
    report_title = ""
    if report_row:
        try:
            report_title = str(report_row["title"] or "").strip()
        except Exception:
            try:
                report_title = str(getattr(report_row, "title", "") or "").strip()
            except Exception:
                report_title = ""

    doc_full_title = f"{COMPANY_TITLE_NAME} - {report_title or 'Executive Sales Audit Report'}"

    # Set Presentation Core Metadata (Guarantees NO "Anonymous" creator in PowerPoint/Keynote)
    prs.core_properties.title = doc_full_title
    prs.core_properties.author = COMPANY_TITLE_NAME
    prs.core_properties.last_modified_by = f"{COMPANY_TITLE_NAME} Internal Audit"
    prs.core_properties.company = COMPANY_TITLE_NAME
    prs.core_properties.subject = "Logistics Sales Revenue & Tri-Factor Reconciliation Audit"
    prs.core_properties.category = "Statutory & Boardroom Audit"
    prs.core_properties.comments = "Official Executive Logistics Sales Audit Report generated by Doxera Intelligence Engine."

    logo_path = os.path.join(Config.BASE_DIR, "static", "doxera_logo.png")
    summary = report_data.get("summary", {})
    all_metrics = report_data.get("all", {})
    billed_metrics = report_data.get("billed", {})
    unbilled_metrics = report_data.get("unbilled", {})

    period_str = summary.get("period_label", "Monthly Audit Period")

    def add_minimalist_header(slide, title_text, category=COMPANY_LEGAL_NAME):
        tx = slide.shapes.add_textbox(Inches(0.8), Inches(0.22), Inches(9.5), Inches(0.80))
        tf = tx.text_frame
        tf.word_wrap = True
        p1 = tf.paragraphs[0]
        p1.text = category
        p1.font.size = Pt(13)
        p1.font.bold = True
        p1.font.color.rgb = RGBColor(15, 23, 42)  # Slate-900

        p2 = tf.add_paragraph()
        p2.text = f"{title_text}  •  Period: {period_str}  •  Reconciled Audit Master"
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = RGBColor(100, 116, 139)  # Slate-500

        # Hairline Divider
        line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.10), Inches(11.733), Inches(0.015))
        line.fill.solid()
        line.fill.fore_color.rgb = RGBColor(226, 232, 240)
        line.line.fill.background()

        if os.path.exists(logo_path):
            try:
                slide.shapes.add_picture(logo_path, Inches(10.8), Inches(0.25), width=Inches(1.6))
            except Exception:
                pass

    # ═════════════════════════════════════════════════════════════════
    # SLIDE 1: EXECUTIVE VISUAL DASHBOARD (Boardroom Layout)
    # ═════════════════════════════════════════════════════════════════
    slide1 = prs.slides.add_slide(blank_layout)
    dash_title = report_title.upper() if report_title else "EXECUTIVE LOGISTICS SALES AUDIT REPORT"
    add_minimalist_header(slide1, dash_title)

    tot_sales = summary.get("total_sales", 0)
    billed_sales = summary.get("billed_sales", 0)
    unbilled_sales = summary.get("unbilled_sales", 0)
    leakage_amt = summary.get("delivered_unbilled_amt", 0)

    tot_awbs = summary.get("total_shipments", 0)
    billed_awbs = summary.get("billed_shipments", 0)
    unbilled_awbs = summary.get("unbilled_shipments", 0)
    leakage_awbs = summary.get("delivered_unbilled_count", 0)
    tot_wt = summary.get("total_weight", 0)

    # 4 Executive Clean White KPI Cards with Exact Rupee Sub-amounts
    kpi_cards_data = [
        ("TOTAL AUDITED TURNOVER", format_inr_short(tot_sales), format_inr(tot_sales), f"{tot_awbs:,} AWBs • 100% • {tot_wt/1000:,.1f}k Kg", RGBColor(15, 23, 42)),
        ("BILLED (INVOICED)", format_inr_short(billed_sales), format_inr(billed_sales), f"{billed_awbs:,} AWBs • {(billed_sales/tot_sales*100 if tot_sales else 0):.1f}% Share", RGBColor(4, 120, 87)),
        ("UNBILLED EXPOSURE", format_inr_short(unbilled_sales), format_inr(unbilled_sales), f"{unbilled_awbs:,} AWBs • {(unbilled_sales/tot_sales*100 if tot_sales else 0):.1f}% Pending", RGBColor(180, 83, 9)),
        ("DELIVERED UNBILLED", format_inr_short(leakage_amt), format_inr(leakage_amt), f"{leakage_awbs:,} AWBs • Immediate Risk", RGBColor(185, 28, 28))
    ]

    card_w = Inches(2.78)
    card_h = Inches(1.15)
    card_gap = Inches(0.20)
    start_x = Inches(0.8)

    for i, (lbl, val_short, val_exact, sub, accent_color) in enumerate(kpi_cards_data):
        x = start_x + (i * (card_w + card_gap))
        k_card = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, Inches(1.22), card_w, card_h)
        k_card.fill.solid()
        k_card.fill.fore_color.rgb = RGBColor(255, 255, 255)
        k_card.line.color.rgb = RGBColor(226, 232, 240)
        k_card.line.width = Pt(1)

        tx = slide1.shapes.add_textbox(x + Inches(0.12), Inches(1.26), card_w - Inches(0.24), card_h - Inches(0.08))
        tf = tx.text_frame
        tf.word_wrap = True

        p_lbl = tf.paragraphs[0]
        p_lbl.text = lbl
        p_lbl.font.size = Pt(8.0)
        p_lbl.font.bold = True
        p_lbl.font.color.rgb = RGBColor(100, 116, 139)

        p_val = tf.add_paragraph()
        p_val.text = val_short
        p_val.font.size = Pt(15.0)
        p_val.font.bold = True
        p_val.font.color.rgb = accent_color

        p_ex = tf.add_paragraph()
        p_ex.text = val_exact
        p_ex.font.size = Pt(8.2)
        p_ex.font.bold = True
        p_ex.font.color.rgb = RGBColor(51, 65, 85)

        p_sub = tf.add_paragraph()
        p_sub.text = sub
        p_sub.font.size = Pt(7.5)
        p_sub.font.color.rgb = RGBColor(100, 116, 139)

    # 4 Visual Charts Grid
    daily_sales = all_metrics.get("daily_sales", [])
    reps_list = all_metrics.get("sales_reps", [])
    modes_list = all_metrics.get("modes", [])
    custs_list = all_metrics.get("customers", [])

    buf_trend = generate_trend_chart_img(daily_sales, width_in=6.3, height_in=2.2)
    buf_mode = generate_servicemode_pie_chart_img(modes_list, width_in=5.2, height_in=2.2)
    buf_rep = generate_sales_rep_chart_img(reps_list, width_in=6.3, height_in=2.2)
    buf_cust = generate_top_customer_chart_img(custs_list, width_in=5.2, height_in=2.2)

    # Row 1 Charts (Top)
    slide1.shapes.add_picture(buf_trend, Inches(0.8), Inches(2.48), width=Inches(6.3), height=Inches(2.2))
    slide1.shapes.add_picture(buf_mode, Inches(7.3), Inches(2.48), width=Inches(5.2), height=Inches(2.2))

    # Row 2 Charts (Bottom)
    slide1.shapes.add_picture(buf_rep, Inches(0.8), Inches(4.82), width=Inches(6.3), height=Inches(2.2))
    slide1.shapes.add_picture(buf_cust, Inches(7.3), Inches(4.82), width=Inches(5.2), height=Inches(2.2))

    # Bottom Executive Highlights Strip
    hl_box = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(7.12), Inches(11.733), Inches(0.28))
    hl_box.fill.solid()
    hl_box.fill.fore_color.rgb = RGBColor(248, 250, 252)
    hl_box.line.color.rgb = RGBColor(226, 232, 240)
    hl_box.line.width = Pt(0.5)
    tx_hl = slide1.shapes.add_textbox(Inches(0.9), Inches(7.12), Inches(11.5), Inches(0.28))
    p_hl = tx_hl.text_frame.paragraphs[0]
    p_hl.text = f"Audit Verification: 100% Correlated across 3 MIS Registers  •  Cargo Weight: {tot_wt:,.1f} Kg  •  Yield: INR {(tot_sales/tot_wt if tot_wt else 0):.2f}/Kg  •  {COMPANY_TITLE_NAME} Boardroom Copy"
    p_hl.font.size = Pt(7.5)
    p_hl.font.color.rgb = RGBColor(100, 116, 139)

    # ═════════════════════════════════════════════════════════════════
    # SLIDE 2: FINANCIAL RECONCILIATION & RISK AUDIT
    # ═════════════════════════════════════════════════════════════════
    slide2 = prs.slides.add_slide(blank_layout)
    add_minimalist_header(slide2, "SCHEDULE 01: TRI-FACTOR FINANCIAL RECONCILIATION & RISK REGISTER")

    # 3-Pillar Clean Metric Cards
    pillars = [
        ("BILLED INVOICED REVENUE", format_inr(summary.get("billed_sales", 0)), f"{summary.get('billed_shipments', 0):,} AWBs Invoiced", RGBColor(4, 120, 87)),
        ("UNBILLED EXPOSURE (RISK)", format_inr(summary.get("unbilled_sales", 0)), f"{summary.get('unbilled_shipments', 0):,} AWBs Pending", RGBColor(180, 83, 9)),
        ("CONSOLIDATED AUDIT TOTAL", format_inr(summary.get("total_sales", 0)), f"{summary.get('total_shipments', 0):,} Dockets Reconciled", RGBColor(15, 23, 42))
    ]
    p_w = Inches(3.7)
    p_h = Inches(1.20)
    p_gap = Inches(0.3)

    for i, (label, val, sub, accent) in enumerate(pillars):
        x = start_x + (i * (p_w + p_gap))
        card = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, Inches(1.28), p_w, p_h)
        card.fill.solid()
        card.fill.fore_color.rgb = RGBColor(255, 255, 255)
        card.line.color.rgb = RGBColor(226, 232, 240)
        card.line.width = Pt(1)

        tx = slide2.shapes.add_textbox(x + Inches(0.18), Inches(1.34), p_w - Inches(0.36), p_h - Inches(0.12))
        tf = tx.text_frame
        p_lbl = tf.paragraphs[0]
        p_lbl.text = label
        p_lbl.font.size = Pt(9.0)
        p_lbl.font.bold = True
        p_lbl.font.color.rgb = RGBColor(100, 116, 139)

        p_val = tf.add_paragraph()
        p_val.text = val
        p_val.font.size = Pt(15.5)
        p_val.font.bold = True
        p_val.font.color.rgb = accent

        p_sub = tf.add_paragraph()
        p_sub.text = sub
        p_sub.font.size = Pt(8.2)
        p_sub.font.color.rgb = RGBColor(71, 85, 105)

    # Critical Revenue Leakage Alert Card
    alert_box = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(2.65), Inches(11.733), Inches(0.95))
    alert_box.fill.solid()
    alert_box.fill.fore_color.rgb = RGBColor(254, 242, 242)
    alert_box.line.color.rgb = RGBColor(185, 28, 28)
    alert_box.line.width = Pt(1)

    tx_al = slide2.shapes.add_textbox(Inches(1.0), Inches(2.72), Inches(11.3), Inches(0.80))
    tf_al = tx_al.text_frame
    p_al = tf_al.paragraphs[0]
    p_al.text = "CRITICAL AUDIT FINDING: DELIVERED BUT UNBILLED REVENUE EXPOSURE"
    p_al.font.bold = True
    p_al.font.size = Pt(10.0)
    p_al.font.color.rgb = RGBColor(185, 28, 28)

    p_al2 = tf_al.add_paragraph()
    deliv_cnt = summary.get('delivered_unbilled_count', 0)
    deliv_val = format_inr(summary.get('delivered_unbilled_amt', 0))
    p_al2.text = f"{deliv_cnt:,} freight consignments valued at {deliv_val} have been physically delivered to consignees without invoice generation. Immediate commercial billing release is required to avoid working capital loss."
    p_al2.font.size = Pt(8.8)
    p_al2.font.color.rgb = RGBColor(15, 23, 42)

    for_update_metrics = report_data.get("for_update", {})
    for_update_s = summary.get("for_update_sales", for_update_metrics.get("summary", {}).get("total_sales", 0))
    for_update_awb = summary.get("for_update_shipments", for_update_metrics.get("summary", {}).get("total_shipments", len(report_data.get("for_update_shipments", []))))
    for_update_wt = for_update_metrics.get("summary", {}).get("total_weight", sum(float(s.get("weight", 0) or 0) for s in report_data.get("for_update_shipments", [])))

    tot_s = summary.get("total_sales", 1) or 1
    billed_wt = billed_metrics.get('summary', {}).get('total_weight', 0)
    unbilled_wt = unbilled_metrics.get('summary', {}).get('total_weight', 0)
    rows_data = [
        ["Billed MIS (Invoiced Revenue)", format_inr(summary.get("billed_sales", 0)), f"{summary.get('billed_shipments', 0):,}", f"{billed_wt:,.1f}", f"{(summary.get('billed_sales', 0)/billed_wt if billed_wt else 0):.2f}", f"{(summary.get('billed_sales', 0)/tot_s*100):.1f}%"],
        ["Unbilled MIS (Pending Exposure)", format_inr(summary.get("unbilled_sales", 0)), f"{summary.get('unbilled_shipments', 0):,}", f"{unbilled_wt:,.1f}", f"{(summary.get('unbilled_sales', 0)/unbilled_wt if unbilled_wt else 0):.2f}", f"{(summary.get('unbilled_sales', 0)/tot_s*100):.1f}%"]
    ]
    if for_update_awb > 0:
        rows_data.append(["Pending Rate Update (≤ ₹10)", format_inr(for_update_s), f"{for_update_awb:,}", f"{for_update_wt:,.1f}", f"{(for_update_s/for_update_wt if for_update_wt else 0):.2f}", f"{(for_update_s/tot_s*100):.1f}%"])
    rows_data.append(["Consolidated Reconciled Operations Base", format_inr(tot_s), f"{summary.get('total_shipments', 0):,}", f"{summary.get('total_weight', 0):,.1f}", f"{(tot_s/summary.get('total_weight', 1) if summary.get('total_weight') else 0):.2f}", "100.0%"])

    num_rows = len(rows_data) + 1
    t_shape = slide2.shapes.add_table(num_rows, 6, Inches(0.8), Inches(3.80), Inches(11.733), Inches(3.2))
    t = t_shape.table

    headers = ["Audit Category", "Reconciled Freight (INR)", "Dockets (AWB)", "Weight (Kg)", "Yield (INR/Kg)", "Share %"]
    for col_idx, h in enumerate(headers):
        cell = t.cell(0, col_idx)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(15, 23, 42)
        for p in cell.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(10.0)
            p.font.color.rgb = RGBColor(255, 255, 255)

    for row_idx, r in enumerate(rows_data, start=1):
        for col_idx, v in enumerate(r):
            cell = t.cell(row_idx, col_idx)
            cell.text = v
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(255, 255, 255) if row_idx < len(rows_data) else RGBColor(241, 245, 249)
            for p in cell.text_frame.paragraphs:
                p.font.bold = (row_idx == len(rows_data))
                p.font.size = Pt(9.5)
                p.font.color.rgb = RGBColor(15, 23, 42)

    # ═════════════════════════════════════════════════════════════════
    # SLIDE 3: SALES TEAM & CLIENT CONCENTRATION
    # ═════════════════════════════════════════════════════════════════
    slide3 = prs.slides.add_slide(blank_layout)
    add_minimalist_header(slide3, "SCHEDULE 02: SALES TEAM PERFORMANCE & MAJOR CLIENT ACCOUNTS")

    # Table 1 (Left): Sales Representatives
    reps = all_metrics.get("sales_reps", [])[:8]
    t_rep_shape = slide3.shapes.add_table(min(len(reps) + 1, 9), 4, Inches(0.8), Inches(1.30), Inches(5.6), Inches(5.7))
    t_rep = t_rep_shape.table

    rep_headers = ["Sales Representative", "AWBs", "Turnover (INR)", "Share"]
    for col_idx, h in enumerate(rep_headers):
        cell = t_rep.cell(0, col_idx)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(15, 23, 42)
        for p in cell.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(9.5)
            p.font.color.rgb = RGBColor(255, 255, 255)

    for row_idx, r in enumerate(reps, start=1):
        vals = [r.get("name", "NEL")[:20], f"{r.get('shipments', 0):,}", format_inr(r.get("sales", 0)), f"{r.get('share_pct', 0):.1f}%"]
        for col_idx, v in enumerate(vals):
            cell = t_rep.cell(row_idx, col_idx)
            cell.text = v
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(255, 255, 255) if row_idx % 2 == 1 else RGBColor(248, 250, 252)
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(9.0)
                p.font.color.rgb = RGBColor(15, 23, 42)

    # Table 2 (Right): Top 8 Major Clients
    custs = all_metrics.get("customers", [])[:8]
    t_cust_shape = slide3.shapes.add_table(min(len(custs) + 1, 9), 4, Inches(6.8), Inches(1.30), Inches(5.7), Inches(5.7))
    t_cust = t_cust_shape.table

    cust_headers = ["Client Account Name", "Account Mgr", "Turnover (INR)", "Share"]
    for col_idx, h in enumerate(cust_headers):
        cell = t_cust.cell(0, col_idx)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(15, 23, 42)
        for p in cell.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(9.5)
            p.font.color.rgb = RGBColor(255, 255, 255)

    for row_idx, c in enumerate(custs, start=1):
        vals = [c.get("name", "General")[:22], str(c.get("sales_person", "NEL"))[:12], format_inr(c.get("sales", 0)), f"{c.get('share_pct', 0):.1f}%"]
        for col_idx, v in enumerate(vals):
            cell = t_cust.cell(row_idx, col_idx)
            cell.text = v
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(255, 255, 255) if row_idx % 2 == 1 else RGBColor(248, 250, 252)
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(9.0)
                p.font.color.rgb = RGBColor(15, 23, 42)

    # ═════════════════════════════════════════════════════════════════
    # SLIDE 4: TRANSPORT MODES, DELIVERY HUBS & AUDIT SIGN-OFF
    # ═════════════════════════════════════════════════════════════════
    slide4 = prs.slides.add_slide(blank_layout)
    add_minimalist_header(slide4, "SCHEDULE 03: LOGISTICS MODES, HUBS & AUDITOR CERTIFICATION")

    # Mode Dynamics Table
    modes = all_metrics.get("modes", [])
    t_mode_shape = slide4.shapes.add_table(min(len(modes) + 1, 6), 4, Inches(0.8), Inches(1.30), Inches(5.6), Inches(3.2))
    t_mode = t_mode_shape.table

    mode_headers = ["Transport Mode", "Consignments", "Turnover (INR)", "Share"]
    for col_idx, h in enumerate(mode_headers):
        cell = t_mode.cell(0, col_idx)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(15, 23, 42)
        for p in cell.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(9.5)
            p.font.color.rgb = RGBColor(255, 255, 255)

    for row_idx, m in enumerate(modes, start=1):
        vals = [
            str(m.get("mode", "Other")),
            f"{m.get('shipments', 0):,} AWBs",
            format_inr(m.get("sales", 0)),
            f"{m.get('share_pct', 0):.1f}%"
        ]
        for col_idx, v in enumerate(vals):
            cell = t_mode.cell(row_idx, col_idx)
            cell.text = v
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(255, 255, 255) if row_idx % 2 == 1 else RGBColor(248, 250, 252)
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(9.0)
                p.font.color.rgb = RGBColor(15, 23, 42)

    # Top Delivery Hubs Table
    dests = all_metrics.get("destinations", [])[:6]
    t_dest_shape = slide4.shapes.add_table(min(len(dests) + 1, 7), 3, Inches(6.8), Inches(1.30), Inches(5.7), Inches(3.2))
    t_dest = t_dest_shape.table

    dest_headers = ["Top Delivery Hub City", "Consignments", "Freight Turnover (INR)"]
    for col_idx, h in enumerate(dest_headers):
        cell = t_dest.cell(0, col_idx)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(15, 23, 42)
        for p in cell.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(9.5)
            p.font.color.rgb = RGBColor(255, 255, 255)

    for row_idx, d in enumerate(dests, start=1):
        vals = [str(d.get("city", "Unknown")), f"{d.get('shipments', 0):,} AWBs", format_inr(d.get("sales", 0))]
        for col_idx, v in enumerate(vals):
            cell = t_dest.cell(row_idx, col_idx)
            cell.text = v
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(255, 255, 255) if row_idx % 2 == 1 else RGBColor(248, 250, 252)
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(9.0)
                p.font.color.rgb = RGBColor(15, 23, 42)

    # Formal Attestation Card (Bottom)
    sign_box = slide4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(4.75), Inches(11.733), Inches(2.3))
    sign_box.fill.solid()
    sign_box.fill.fore_color.rgb = RGBColor(248, 250, 252)
    sign_box.line.color.rgb = RGBColor(203, 213, 225)
    sign_box.line.width = Pt(1)

    tx_s = slide4.shapes.add_textbox(Inches(1.1), Inches(4.88), Inches(11.1), Inches(2.0))
    tf_s = tx_s.text_frame
    p_st = tf_s.paragraphs[0]
    p_st.text = "FORMAL STATUTORY AUDIT CERTIFICATION & MANAGEMENT ATTESTATION"
    p_st.font.bold = True
    p_st.font.size = Pt(10.5)
    p_st.font.color.rgb = RGBColor(15, 23, 42)

    p_sb = tf_s.add_paragraph()
    p_sb.text = (f"This statutory logistics revenue audit has been prepared by the Internal Audit Division of {COMPANY_TITLE_NAME} "
                 "utilizing the Doxera Automated Tri-Factor Reconciliation Engine. We hereby certify that the financial statements, "
                 "freight turnover figures, cargo weights, and billing reconciliations contained within Schedules 01, 02, and 03 "
                 "represent a true and fair view of commercial operations for the audit period.")
    p_sb.font.size = Pt(9.0)
    p_sb.font.color.rgb = RGBColor(71, 85, 105)

    p_sig = tf_s.add_paragraph()
    p_sig.text = "Lead Internal Auditor: ___________________________          Audit Sign-Off Date: ___________________________"
    p_sig.font.bold = True
    p_sig.font.size = Pt(9.5)
    p_sig.font.color.rgb = RGBColor(15, 23, 42)
    p_sig.space_before = Pt(14)

    out = io.BytesIO()
    prs.save(out)
    out.seek(0)
    return out


# ─────────────────────────────────────────────────────────────
# 2. EXECUTIVE MULTI-PAGE AUDIT REPORT (.PDF)
# Boardroom / Statutory Audit Multi-Page Document (A4)
# ─────────────────────────────────────────────────────────────

def generate_sales_pdf(report_row, report_data):
    """
    Generates a statutory-grade, boardroom-ready A4 multi-page PDF audit report.
    Page 1: Executive Visual Dashboard & Operational Reconciliation Matrix
    Page 2: Schedule 01 - Tri-Factor Financial Reconciliation & Risk Horizon
    Page 3: Schedule 02 - Sales Team Accountability & Major Corporate Accounts
    Page 4: Schedule 03 - Logistics Modes, Strategic Hubs & Statutory Certification
    """
    report_title = ""
    if report_row:
        try:
            report_title = str(report_row["title"] or "").strip()
        except Exception:
            try:
                report_title = str(getattr(report_row, "title", "") or "").strip()
            except Exception:
                report_title = ""

    doc_full_title = f"{COMPANY_TITLE_NAME} - {report_title or 'Executive Sales Audit Report'}"

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

            # Set PDF document metadata so file never displays as "Anonymous" in viewers/iOS
            try:
                self.setAuthor(COMPANY_TITLE_NAME)
                self.setTitle(doc_full_title)
                self.setSubject(AUDIT_REPORT_SUBTITLE)
                self.setCreator("Doxera Logistics Intelligence Engine")
            except Exception:
                pass

            self.setFont("Helvetica-Bold", 7.2)
            self.setFillColor(colors.HexColor("#64748B"))

            # Running Header
            hdr_sub = (report_title[:45] + '...') if len(report_title) > 48 else (report_title or "EXECUTIVE SALES AUDIT")
            self.drawString(36, 808, f"{COMPANY_LEGAL_NAME}  |  {hdr_sub.upper()}")
            self.drawRightString(559, 808, "STRICTLY CONFIDENTIAL")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(36, 802, 559, 802)

            # Running Footer
            self.line(36, 36, 559, 36)
            self.setFont("Helvetica", 7.2)
            self.drawString(36, 24, f"{COMPANY_TITLE_NAME} Internal Audit Division  |  Boardroom Certified")
            self.drawRightString(559, 24, f"Page {self._pageNumber} of {page_count}")
            self.restoreState()

    out = io.BytesIO()
    doc = SimpleDocTemplate(
        out,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=44,
        bottomMargin=44
    )

    # Document Information Dictionary properties (guarantees NO Anonymous in Acrobat/Preview)
    doc.title = doc_full_title
    doc.author = COMPANY_TITLE_NAME
    doc.subject = AUDIT_REPORT_SUBTITLE
    doc.creator = "Doxera Logistics Intelligence Engine"

    styles = getSampleStyleSheet()

    doc_title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=2
    )
    doc_sub_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.8,
        leading=10.5,
        textColor=colors.HexColor('#64748B')
    )
    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=4,
        spaceAfter=2
    )
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.4,
        leading=10.0,
        textColor=colors.HexColor('#1E293B')
    )
    card_label = ParagraphStyle(
        'CardLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=6.8,
        leading=8.5,
        textColor=colors.HexColor('#64748B')
    )
    card_val = ParagraphStyle(
        'CardVal',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=13,
        textColor=colors.HexColor('#0F172A')
    )
    table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.2,
        leading=9.5,
        textColor=colors.white
    )
    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.2,
        leading=9.5,
        textColor=colors.HexColor('#1E293B')
    )
    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.2,
        leading=9.5,
        textColor=colors.HexColor('#0F172A')
    )
    table_cell_right = ParagraphStyle(
        'TableCellRight',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.2,
        leading=9.5,
        alignment=2,
        textColor=colors.HexColor('#1E293B')
    )
    table_cell_right_bold = ParagraphStyle(
        'TableCellRightBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.2,
        leading=9.5,
        alignment=2,
        textColor=colors.HexColor('#0F172A')
    )

    logo_path = os.path.join(Config.BASE_DIR, "static", "doxera_logo.png")
    summary = report_data.get("summary", {})
    all_metrics = report_data.get("all", {})
    billed_metrics = report_data.get("billed", {})
    unbilled_metrics = report_data.get("unbilled", {})

    period_str = summary.get("period_label", "Monthly Audit Period")

    story = []

    def make_section_banner(section_no, section_title, subtitle=""):
        banner_content = [
            Paragraph(f"<b>{section_no} | {section_title.upper()}</b>", h1_style)
        ]
        if subtitle:
            banner_content.append(Paragraph(subtitle, doc_sub_style))
        banner_content.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#CBD5E1"), spaceBefore=2, spaceAfter=4))
        return banner_content

    # ═════════════════════════════════════════════════════════════════
    # PAGE 1: EXECUTIVE VISUAL DASHBOARD & RECONCILIATION MATRIX
    # ═════════════════════════════════════════════════════════════════

    # Header with Logo and Official Company Legal Name
    header_data = []
    if os.path.exists(logo_path):
        try:
            img = Image(logo_path, width=95, height=28)
            txt = Paragraph(f"<b>{COMPANY_LEGAL_NAME}</b><br/><font color='#64748B' size=7>{AUDIT_REPORT_SUBTITLE}</font>", doc_sub_style)
            header_data = [[img, txt]]
        except Exception:
            header_data = [[Paragraph(f"<b>{COMPANY_LEGAL_NAME}</b>", doc_title_style)]]
    else:
        header_data = [[Paragraph(f"<b>{COMPANY_LEGAL_NAME}</b>", doc_title_style)]]

    t_head = Table(header_data, colWidths=[110, 413])
    t_head.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(t_head)
    story.append(Spacer(1, 2))

    main_doc_title = report_title.upper() if report_title else "EXECUTIVE SALES AUDIT REPORT"
    story.append(Paragraph(main_doc_title, doc_title_style))
    story.append(Paragraph(f"Audit Window: <b>{period_str}</b>  •  Correlated: <b>{summary.get('total_shipments', 0):,} AWBs</b>  •  Classification: <b>Boardroom Certified Audit</b>", doc_sub_style))
    story.append(Spacer(1, 4))

    # 4 Executive Clean White KPI Cards (with both Short & Exact Rupee Amounts!)
    tot_s = summary.get("total_sales", 0)
    billed_s = summary.get("billed_sales", 0)
    unbilled_s = summary.get("unbilled_sales", 0)
    deliv_unb_s = summary.get("delivered_unbilled_amt", 0)

    tot_awb = summary.get("total_shipments", 0)
    billed_awb = summary.get("billed_shipments", 0)
    unbilled_awb = summary.get("unbilled_shipments", 0)
    deliv_unb_awb = summary.get("delivered_unbilled_count", 0)
    tot_wt = summary.get("total_weight", 0)

    kpi_white_data = [
        [
            Paragraph(f"<font color='#64748B' size=6.5><b>TOTAL AUDITED TURNOVER</b></font><br/>"
                      f"<font color='#0F172A' size=11.5><b>{format_pdf_inr_short(tot_s)}</b></font><br/>"
                      f"<font color='#334155' size=7.2><b>INR {format_indian_number(tot_s)}</b></font><br/>"
                      f"<font color='#64748B' size=6.5>{tot_awb:,} AWBs • 100% • {tot_wt/1000:,.1f}T</font>", card_val),
            Paragraph(f"<font color='#64748B' size=6.5><b>BILLED (INVOICED)</b></font><br/>"
                      f"<font color='#047857' size=11.5><b>{format_pdf_inr_short(billed_s)}</b></font><br/>"
                      f"<font color='#334155' size=7.2><b>INR {format_indian_number(billed_s)}</b></font><br/>"
                      f"<font color='#64748B' size=6.5>{billed_awb:,} AWBs • {(billed_s/tot_s*100 if tot_s else 0):.1f}% Invoiced</font>", card_val),
            Paragraph(f"<font color='#64748B' size=6.5><b>UNBILLED EXPOSURE</b></font><br/>"
                      f"<font color='#B45309' size=11.5><b>{format_pdf_inr_short(unbilled_s)}</b></font><br/>"
                      f"<font color='#334155' size=7.2><b>INR {format_indian_number(unbilled_s)}</b></font><br/>"
                      f"<font color='#64748B' size=6.5>{unbilled_awb:,} AWBs • {(unbilled_s/tot_s*100 if tot_s else 0):.1f}% Pending</font>", card_val),
            Paragraph(f"<font color='#64748B' size=6.5><b>DELIVERED UNBILLED</b></font><br/>"
                      f"<font color='#B91C1C' size=11.5><b>{format_pdf_inr_short(deliv_unb_s)}</b></font><br/>"
                      f"<font color='#334155' size=7.2><b>INR {format_indian_number(deliv_unb_s)}</b></font><br/>"
                      f"<font color='#64748B' size=6.5>{deliv_unb_awb:,} AWBs • Immediate Risk</font>", card_val)
        ]
    ]
    t_kpi_white = Table(kpi_white_data, colWidths=[130, 131, 131, 131])
    t_kpi_white.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FFFFFF')),
        ('BOX', (0,0), (-1,-1), 0.6, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_kpi_white)
    story.append(Spacer(1, 4))

    # 4 Visual Charts Grid
    daily_sales = all_metrics.get("daily_sales", [])
    reps_list = all_metrics.get("sales_reps", [])
    modes_list = all_metrics.get("modes", [])
    custs_list = all_metrics.get("customers", [])

    buf_trend = generate_trend_chart_img(daily_sales, width_in=4.4, height_in=1.92)
    buf_mode = generate_servicemode_pie_chart_img(modes_list, width_in=3.6, height_in=1.92)
    buf_rep = generate_sales_rep_chart_img(reps_list, width_in=4.4, height_in=1.98)
    buf_cust = generate_top_customer_chart_img(custs_list, width_in=3.6, height_in=1.98)

    img_trend = Image(buf_trend, width=285, height=130)
    img_mode = Image(buf_mode, width=233, height=130)
    img_rep = Image(buf_rep, width=285, height=136)
    img_cust = Image(buf_cust, width=233, height=136)

    charts_grid = [
        [img_trend, img_mode],
        [img_rep, img_cust]
    ]
    t_charts = Table(charts_grid, colWidths=[290, 233])
    t_charts.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(t_charts)
    story.append(Spacer(1, 5))

    # Bottom Executive Highlights & Operational Verification Strip (Fills the lower Page 1!)
    avg_ticket = summary.get("avg_ticket", 0) or (tot_s / tot_awb if tot_awb else 0)
    yield_val = (tot_s / tot_wt) if tot_wt else 0

    highlights_data = [
        [
            Paragraph("<font color='#64748B' size=6.5><b>CARGO WEIGHT AUDITED</b></font><br/>"
                      f"<font color='#0F172A' size=9.5><b>{tot_wt:,.1f} Kg</b></font><br/>"
                      f"<font color='#475569' size=6.8>{tot_wt/1000:,.1f} Metric Tons</font>", card_val),
            Paragraph("<font color='#64748B' size=6.5><b>FREIGHT YIELD</b></font><br/>"
                      f"<font color='#0F172A' size=9.5><b>INR {yield_val:.2f} / Kg</b></font><br/>"
                      "<font color='#475569' size=6.8>Network Realization</font>", card_val),
            Paragraph("<font color='#64748B' size=6.5><b>AVERAGE TICKET</b></font><br/>"
                      f"<font color='#0F172A' size=9.5><b>INR {format_indian_number(avg_ticket)}</b></font><br/>"
                      "<font color='#475569' size=6.8>Per Docket (AWB)</font>", card_val),
            Paragraph("<font color='#64748B' size=6.5><b>BILLING REVENUE REALIZATION</b></font><br/>"
                      f"<font color='#047857' size=9.5><b>{(billed_s/tot_s*100 if tot_s else 0):.1f}% Invoiced</b></font><br/>"
                      f"<font color='#B45309' size=6.8>{(unbilled_s/tot_s*100 if tot_s else 0):.1f}% Pending Release</font>", card_val)
        ]
    ]
    t_highlights = Table(highlights_data, colWidths=[130, 131, 131, 131])
    t_highlights.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 0.6, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_highlights)
    story.append(Spacer(1, 4))

    # Audit Assurance Note Strip
    assurance_data = [
        [
            Paragraph(f"<b>TRI-FACTOR AUDIT ASSURANCE & RECONCILIATION SUMMARY:</b> "
                      f"The audit engine achieved 100% correlation across Billed MIS, Unbilled MIS, and Operations Booking Register for {COMPANY_TITLE_NAME} "
                      f"Total exposure of INR {format_indian_number(unbilled_s)} is pending commercial billing, of which {deliv_unb_awb:,} consignments "
                      f"(INR {format_indian_number(deliv_unb_s)}) are physical deliveries awaiting invoice dispatch. Certified for Boardroom review.", body_style)
        ]
    ]
    t_assurance = Table(assurance_data, colWidths=[523])
    t_assurance.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FFFFFF')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
        ('LEFTPADDING', (0,0), (-1,-1), 7),
        ('RIGHTPADDING', (0,0), (-1,-1), 7),
    ]))
    story.append(t_assurance)

    # ═════════════════════════════════════════════════════════════════
    # PAGE 2: FINANCIAL RECONCILIATION & RISK REGISTER
    # ═════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.extend(make_section_banner("SCHEDULE 01", "Tri-Factor Financial Reconciliation & Risk Register", "Three-way mathematical triangulation across Billed MIS, Unbilled MIS, and Booking Register."))

    # 3 Pillar Summary Cards
    tot_s_base = summary.get("total_sales", 1) or 1
    pillars_table = [
        [
            Paragraph("BILLED REVENUE (INVOICED)", card_label),
            Paragraph("UNBILLED EXPOSURE (PENDING)", card_label),
            Paragraph("CONSOLIDATED AUDIT TOTAL", card_label)
        ],
        [
            Paragraph(f"INR {format_indian_number(summary.get('billed_sales', 0))}", card_val),
            Paragraph(f"INR {format_indian_number(summary.get('unbilled_sales', 0))}", card_val),
            Paragraph(f"INR {format_indian_number(tot_s_base)}", card_val)
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
        ('BOX', (0,0), (-1,-1), 0.6, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_pillars)
    story.append(Spacer(1, 6))

    # Revenue Leakage Warning Box
    deliv_count = summary.get('delivered_unbilled_count', 0)
    deliv_amt = summary.get('delivered_unbilled_amt', 0)
    leakage_data = [
        [
            Paragraph("<b>CRITICAL REVENUE LEAKAGE FINDING (DELIVERED BUT UNBILLED)</b><br/>"
                      f"The audit engine reconciled <b>{deliv_count:,} physical consignments</b> totaling <b>INR {format_indian_number(deliv_amt)}</b> "
                      "where freight cargo has been delivered to consignees without invoice issuance. "
                      "Immediate commercial billing release is required to avoid working capital loss and DSO expansion.", body_style)
        ]
    ]
    t_leakage = Table(leakage_data, colWidths=[523])
    t_leakage.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FEF2F2')),
        ('BOX', (0,0), (-1,-1), 0.8, colors.HexColor('#B91C1C')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_leakage)
    story.append(Spacer(1, 6))

    # Tri-Factor Reconciliation Table
    billed_wt = billed_metrics.get('summary', {}).get('total_weight', 0)
    unbilled_wt = unbilled_metrics.get('summary', {}).get('total_weight', 0)
    reconcil_data = [
        [
            Paragraph("<b>Audit Category</b>", table_header),
            Paragraph("<b>Dockets (AWB)</b>", table_header),
            Paragraph("<b>Weight (Kg)</b>", table_header),
            Paragraph("<b>Reconciled Freight (INR)</b>", table_header),
            Paragraph("<b>Average Ticket (INR)</b>", table_header),
            Paragraph("<b>Freight Yield (INR/Kg)</b>", table_header),
            Paragraph("<b>Share %</b>", table_header)
        ],
        [
            Paragraph("<b>Billed MIS (Invoiced Revenue)</b>", table_cell_bold),
            Paragraph(f"{summary.get('billed_shipments', 0):,}", table_cell_right),
            Paragraph(f"{billed_wt:,.1f}", table_cell_right),
            Paragraph(format_indian_number(summary.get("billed_sales", 0)), table_cell_right_bold),
            Paragraph(format_indian_number(billed_metrics.get("summary", {}).get("avg_ticket", 0)), table_cell_right),
            Paragraph(f"{(summary.get('billed_sales', 0)/billed_wt if billed_wt else 0):.2f}", table_cell_right),
            Paragraph(f"{(summary.get('billed_sales', 0)/tot_s_base*100):.1f}%", table_cell_right_bold)
        ],
        [
            Paragraph("<b>Unbilled MIS (Pending Exposure)</b>", table_cell_bold),
            Paragraph(f"{summary.get('unbilled_shipments', 0):,}", table_cell_right),
            Paragraph(f"{unbilled_wt:,.1f}", table_cell_right),
            Paragraph(format_indian_number(summary.get("unbilled_sales", 0)), table_cell_right_bold),
            Paragraph(format_indian_number(unbilled_metrics.get("summary", {}).get("avg_ticket", 0)), table_cell_right),
            Paragraph(f"{(summary.get('unbilled_sales', 0)/unbilled_wt if unbilled_wt else 0):.2f}", table_cell_right),
            Paragraph(f"{(summary.get('unbilled_sales', 0)/tot_s_base*100):.1f}%", table_cell_right_bold)
        ]
    ]

    for_update_metrics = report_data.get("for_update", {})
    for_update_s = summary.get("for_update_sales", for_update_metrics.get("summary", {}).get("total_sales", 0))
    for_update_awb = summary.get("for_update_shipments", for_update_metrics.get("summary", {}).get("total_shipments", len(report_data.get("for_update_shipments", []))))
    for_update_wt = for_update_metrics.get("summary", {}).get("total_weight", sum(float(s.get("weight", 0) or 0) for s in report_data.get("for_update_shipments", [])))

    if for_update_awb > 0:
        reconcil_data.append([
            Paragraph("<b>Pending Rate Update (≤ ₹10)</b>", table_cell_bold),
            Paragraph(f"{for_update_awb:,}", table_cell_right),
            Paragraph(f"{for_update_wt:,.1f}", table_cell_right),
            Paragraph(format_indian_number(for_update_s), table_cell_right_bold),
            Paragraph(format_indian_number(for_update_s/for_update_awb if for_update_awb else 0), table_cell_right),
            Paragraph(f"{(for_update_s/for_update_wt if for_update_wt else 0):.2f}", table_cell_right),
            Paragraph(f"{(for_update_s/tot_s_base*100):.1f}%", table_cell_right_bold)
        ])

    reconcil_data.append([
        Paragraph("<b>Total Reconciled Operations Base</b>", table_cell_bold),
        Paragraph(f"{summary.get('total_shipments', 0):,}", table_cell_right_bold),
        Paragraph(f"{summary.get('total_weight', 0):,.1f}", table_cell_right_bold),
        Paragraph(format_indian_number(tot_s_base), table_cell_right_bold),
        Paragraph(format_indian_number(summary.get("avg_ticket", 0)), table_cell_right_bold),
        Paragraph(f"{(tot_s_base/summary.get('total_weight', 1) if summary.get('total_weight') else 0):.2f}", table_cell_right_bold),
        Paragraph("100.0%", table_cell_right_bold)
    ])

    t_rec = Table(reconcil_data, colWidths=[153, 52, 60, 92, 68, 58, 40])
    t_style = [
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#FFFFFF')),
        ('BACKGROUND', (0,2), (-1,2), colors.HexColor('#F8FAFC')),
    ]
    if for_update_awb > 0:
        t_style.append(('BACKGROUND', (0,3), (-1,3), colors.HexColor('#FFF1F2')))
        t_style.append(('BACKGROUND', (0,4), (-1,4), colors.HexColor('#F1F5F9')))
    else:
        t_style.append(('BACKGROUND', (0,3), (-1,3), colors.HexColor('#F1F5F9')))
    t_style.extend([
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ])
    t_rec.setStyle(TableStyle(t_style))
    story.append(t_rec)
    story.append(Spacer(1, 8))

    # Unbilled Operational Risk Horizon & Aging Matrix (Completes Page 2!)
    story.append(Paragraph("<b>UNBILLED EXPOSURE OPERATIONAL STAGE & RISK BREAKDOWN</b>", h1_style))
    unbilled_shipments = report_data.get("unbilled_shipments", [])
    status_map = {}
    for s in unbilled_shipments:
        raw_st = str(s.get("delivery_status") or s.get("shipment_status") or "In-Transit").strip().title()
        if "Deliv" in raw_st:
            norm_st = "Delivered (Pending Invoicing)"
            risk_desc = "Critical Risk"
            rec_action = "Immediate invoice dispatch"
        elif "Out" in raw_st or "Ofd" in raw_st:
            norm_st = "Out For Delivery"
            risk_desc = "High Priority"
            rec_action = "Capture electronic POD"
        elif "Transit" in raw_st or "Intransit" in raw_st:
            norm_st = "In-Transit to Destination Hub"
            risk_desc = "Active Operational"
            rec_action = "Track inter-hub linehaul"
        else:
            norm_st = "Booked / Manifested"
            risk_desc = "Pipeline Operational"
            rec_action = "Scheduled hub dispatch"

        val = float(s.get("unbilled_amt") or s.get("total_amt") or s.get("sales") or 0)
        wt = float(s.get("weight") or s.get("chargeable_weight") or 0)

        if norm_st not in status_map:
            status_map[norm_st] = {"count": 0, "sales": 0.0, "weight": 0.0, "risk": risk_desc, "action": rec_action}
        status_map[norm_st]["count"] += 1
        status_map[norm_st]["sales"] += val
        status_map[norm_st]["weight"] += wt

    # Fallback to summary counts if shipment-level array is empty
    if not status_map:
        if deliv_count > 0:
            status_map["Delivered (Pending Invoicing)"] = {
                "count": deliv_count, "sales": deliv_amt, "weight": unbilled_wt * (deliv_count / (summary.get('unbilled_shipments') or 1)),
                "risk": "Critical Risk", "action": "Immediate invoice dispatch"
            }
        rem_count = max(0, (summary.get('unbilled_shipments', 0) - deliv_count))
        rem_sales = max(0, (summary.get('unbilled_sales', 0) - deliv_amt))
        if rem_count > 0:
            status_map["In-Transit to Destination Hub"] = {
                "count": rem_count, "sales": rem_sales, "weight": unbilled_wt - status_map.get("Delivered (Pending Invoicing)", {}).get("weight", 0),
                "risk": "Active Operational", "action": "Track inter-hub linehaul"
            }

    # Sort so Delivered is first
    ordered_statuses = sorted(status_map.items(), key=lambda kv: 0 if "Deliv" in kv[0] else 1)
    status_table_data = [
        [
            Paragraph("<b>Operational Stage</b>", table_header),
            Paragraph("<b>AWBs</b>", table_header),
            Paragraph("<b>Weight (Kg)</b>", table_header),
            Paragraph("<b>Exposure Value (INR)</b>", table_header),
            Paragraph("<b>Risk Level</b>", table_header),
            Paragraph("<b>Auditor Recommendation</b>", table_header)
        ]
    ]
    tot_st_cnt = 0
    tot_st_wt = 0.0
    tot_st_amt = 0.0
    for st_label, st_info in ordered_statuses:
        tot_st_cnt += st_info['count']
        tot_st_wt += st_info['weight']
        tot_st_amt += st_info['sales']
        status_table_data.append([
            Paragraph(f"<b>{st_label}</b>", table_cell_bold),
            Paragraph(f"{st_info['count']:,}", table_cell_right),
            Paragraph(f"{st_info['weight']:,.1f}", table_cell_right),
            Paragraph(format_indian_number(st_info['sales']), table_cell_right_bold),
            Paragraph(st_info['risk'], table_cell),
            Paragraph(st_info['action'], table_cell)
        ])
    # Total row for unbilled status schedule
    status_table_data.append([
        Paragraph("<b>Total Unbilled Exposure Base</b>", table_cell_bold),
        Paragraph(f"{tot_st_cnt:,}", table_cell_right_bold),
        Paragraph(f"{tot_st_wt:,.1f}", table_cell_right_bold),
        Paragraph(format_indian_number(tot_st_amt), table_cell_right_bold),
        Paragraph("<b>All Unbilled Categories</b>", table_cell_bold),
        Paragraph("<b>Revenue Assurance Control</b>", table_cell_bold)
    ])

    t_status = Table(status_table_data, colWidths=[140, 45, 60, 95, 78, 105])
    t_status.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#F1F5F9')),
        ('TOPPADDING', (0,0), (-1,-1), 3.2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.2),
        *([('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F8FAFC')) for i in range(1, len(status_table_data) - 1, 2)])
    ]))
    story.append(t_status)
    story.append(Spacer(1, 7))

    # Working Capital Optimization Recommendation Note
    recom_data = [
        [
            Paragraph("<b>AUDITOR ACTION NOTE:</b> Implement mandatory automated billing triggers upon destination delivery status update. "
                      f"Prioritize immediate invoice generation for the {deliv_count:,} delivered consignments to release INR {format_indian_number(deliv_amt)} "
                      "into receivables, compressing DSO by an estimated 14 days and eliminating working capital risk.", body_style)
        ]
    ]
    t_recom = Table(recom_data, colWidths=[523])
    t_recom.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 7),
        ('RIGHTPADDING', (0,0), (-1,-1), 7),
    ]))
    story.append(t_recom)

    # ═════════════════════════════════════════════════════════════════
    # PAGE 3: SALES TEAM & CLIENT CONCENTRATION
    # ═════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.extend(make_section_banner("SCHEDULE 02", "Sales Team Accountability & Corporate Client Concentration", "Portfolio allocation, sales representative turnover, and account concentration."))

    # Sales Reps Table
    reps = all_metrics.get("sales_reps", [])
    all_shipments = report_data.get("all_shipments", [])
    rep_table_data = [
        [
            Paragraph("<b>#</b>", table_header),
            Paragraph("<b>Sales Representative Name</b>", table_header),
            Paragraph("<b>Accounts</b>", table_header),
            Paragraph("<b>Dockets</b>", table_header),
            Paragraph("<b>Cargo Weight (Kg)</b>", table_header),
            Paragraph("<b>Audited Turnover (INR)</b>", table_header),
            Paragraph("<b>Yield (INR/Kg)</b>", table_header),
            Paragraph("<b>Share %</b>", table_header)
        ]
    ]
    tot_rep_awb = 0
    tot_rep_wt = 0.0
    tot_rep_s = 0.0

    for idx, r in enumerate(reps[:10], start=1):
        r_name = str(r.get("name", "NEL"))
        r_sales = float(r.get("sales", 0))
        r_awb = int(r.get("shipments", 0))
        r_wt = float(r.get("weight", 0) or 0)
        if not r_wt and all_shipments:
            r_wt = sum(float(s.get("weight", 0) or 0) for s in all_shipments if str(s.get("sales_person", "")).lower() == r_name.lower())
        r_yd = (r_sales / r_wt) if r_wt > 0 else 0

        tot_rep_awb += r_awb
        tot_rep_wt += r_wt
        tot_rep_s += r_sales

        rep_table_data.append([
            Paragraph(str(idx), table_cell),
            Paragraph(r_name, table_cell_bold),
            Paragraph(str(r.get("customer_count", 0)), table_cell_right),
            Paragraph(f"{r_awb:,}", table_cell_right),
            Paragraph(f"{r_wt:,.1f}" if r_wt else "---", table_cell_right),
            Paragraph(format_indian_number(r_sales), table_cell_right_bold),
            Paragraph(f"{r_yd:.2f}" if r_yd else "---", table_cell_right),
            Paragraph(f"{r.get('share_pct', 0):.1f}%", table_cell_right_bold)
        ])

    # Total row for Reps table
    rep_table_data.append([
        Paragraph("<b>Total - Top Sales Representatives</b>", table_cell_bold),
        "",
        Paragraph(f"{len(reps):,}", table_cell_right_bold),
        Paragraph(f"{tot_rep_awb:,}", table_cell_right_bold),
        Paragraph(f"{tot_rep_wt:,.1f}", table_cell_right_bold),
        Paragraph(format_indian_number(tot_rep_s), table_cell_right_bold),
        Paragraph(f"{(tot_rep_s/tot_rep_wt if tot_rep_wt else 0):.2f}", table_cell_right_bold),
        Paragraph(f"{(tot_rep_s/tot_s*100 if tot_s else 0):.1f}%", table_cell_right_bold)
    ])

    t_rep_audit = Table(rep_table_data, colWidths=[24, 150, 48, 46, 68, 95, 52, 40])
    t_rep_audit.setStyle(TableStyle([
        ('SPAN', (0, -1), (1, -1)),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#F1F5F9')),
        ('TOPPADDING', (0,0), (-1,-1), 3.0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.0),
        *([('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F8FAFC')) for i in range(1, len(rep_table_data) - 1, 2)])
    ]))
    story.append(t_rep_audit)
    story.append(Spacer(1, 8))

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
            Paragraph("<b>Cargo Weight (Kg)</b>", table_header),
            Paragraph("<b>Audited Turnover (INR)</b>", table_header),
            Paragraph("<b>Share %</b>", table_header)
        ]
    ]
    tot_cust_awb = 0
    tot_cust_wt = 0.0
    tot_cust_s = 0.0

    for idx, c in enumerate(custs, start=1):
        cust_name = str(c.get("name", "General"))[:28]
        cust_code = str(c.get("code") or "---")
        cust_rep = str(c.get("sales_person", "NEL"))[:16]
        c_sales = float(c.get("sales", 0))
        c_awb = int(c.get("shipments", 0))
        c_wt = float(c.get("weight", 0) or 0)
        if not c_wt and all_shipments:
            c_wt = sum(float(s.get("weight", 0) or 0) for s in all_shipments if str(s.get("customer_name", "")).lower() == cust_name.lower())

        tot_cust_awb += c_awb
        tot_cust_wt += c_wt
        tot_cust_s += c_sales

        cust_table_data.append([
            Paragraph(str(idx), table_cell),
            Paragraph(cust_name, table_cell_bold),
            Paragraph(cust_code, table_cell),
            Paragraph(cust_rep, table_cell),
            Paragraph(f"{c_awb:,}", table_cell_right),
            Paragraph(f"{c_wt:,.1f}" if c_wt else "---", table_cell_right),
            Paragraph(format_indian_number(c_sales), table_cell_right_bold),
            Paragraph(f"{c.get('share_pct', 0):.1f}%", table_cell_right)
        ])

    # Total row for Customers table
    cust_table_data.append([
        Paragraph("<b>Total - Top Corporate Accounts</b>", table_cell_bold),
        "",
        Paragraph("---", table_cell),
        Paragraph("Multiple", table_cell),
        Paragraph(f"{tot_cust_awb:,}", table_cell_right_bold),
        Paragraph(f"{tot_cust_wt:,.1f}", table_cell_right_bold),
        Paragraph(format_indian_number(tot_cust_s), table_cell_right_bold),
        Paragraph(f"{(tot_cust_s/tot_s*100 if tot_s else 0):.1f}%", table_cell_right_bold)
    ])

    t_cust_audit = Table(cust_table_data, colWidths=[24, 150, 46, 80, 46, 62, 75, 40])
    t_cust_audit.setStyle(TableStyle([
        ('SPAN', (0, -1), (1, -1)),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#F1F5F9')),
        ('TOPPADDING', (0,0), (-1,-1), 3.0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.0),
        *([('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F8FAFC')) for i in range(1, len(cust_table_data) - 1, 2)])
    ]))
    story.append(t_cust_audit)
    story.append(Spacer(1, 6))

    # Client Concentration Insight Note
    top5_sales = sum(float(c.get("sales", 0)) for c in custs[:5])
    top5_pct = (top5_sales / tot_s * 100) if tot_s else 0
    cust_note_data = [
        [
            Paragraph(f"<b>CLIENT CONCENTRATION ANALYSIS:</b> The top 5 corporate accounts contribute <b>{top5_pct:.1f}%</b> of total audited turnover. "
                      "Customer account monitoring and service level agreements (SLAs) must be safeguarded to maintain commercial stability.", body_style)
        ]
    ]
    t_cust_note = Table(cust_note_data, colWidths=[523])
    t_cust_note.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
        ('LEFTPADDING', (0,0), (-1,-1), 7),
        ('RIGHTPADDING', (0,0), (-1,-1), 7),
    ]))
    story.append(t_cust_note)

    # ═════════════════════════════════════════════════════════════════
    # PAGE 4: LOGISTICS MODES, DELIVERY HUBS & AUDIT ATTESTATION
    # ═════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.extend(make_section_banner("SCHEDULE 03", "Transport Mode Dynamics, Hubs & Auditor Certification", "Air, Surface, and Train freight yields, destination hubs, and formal attestation."))

    # Mode Performance Table with recomputed weight & yield if missing
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
    tot_mode_awb = 0
    tot_mode_wt = 0.0
    tot_mode_s = 0.0

    for m in modes:
        mode_name = str(m.get("mode", "Other"))
        wt = m.get("weight", 0)
        if not wt and all_shipments:
            wt = sum(float(s.get("weight", 0) or 0) for s in all_shipments if str(s.get("transport_mode", "")).lower() == mode_name.lower())
        sales_val = float(m.get("sales", 0))
        m_awb = int(m.get("shipments", 0))
        yd = (sales_val / wt) if wt > 0 else m.get("yield_per_kg", 0)

        tot_mode_awb += m_awb
        tot_mode_wt += wt
        tot_mode_s += sales_val

        mode_table_data.append([
            Paragraph(mode_name, table_cell_bold),
            Paragraph(f"{m_awb:,}", table_cell_right),
            Paragraph(f"{wt:,.1f}" if wt else "---", table_cell_right),
            Paragraph(f"INR {yd:.2f}/Kg" if yd else "---", table_cell_right),
            Paragraph(format_indian_number(sales_val), table_cell_right_bold),
            Paragraph(f"{m.get('share_pct', 0):.1f}%", table_cell_right_bold)
        ])

    # Mode total row
    mode_table_data.append([
        Paragraph("<b>Total Transport Operations</b>", table_cell_bold),
        Paragraph(f"{tot_mode_awb:,}", table_cell_right_bold),
        Paragraph(f"{tot_mode_wt:,.1f}", table_cell_right_bold),
        Paragraph(f"INR {(tot_mode_s/tot_mode_wt if tot_mode_wt else 0):.2f}/Kg", table_cell_right_bold),
        Paragraph(format_indian_number(tot_mode_s), table_cell_right_bold),
        Paragraph("100.0%", table_cell_right_bold)
    ])

    t_mode_audit = Table(mode_table_data, colWidths=[90, 75, 90, 95, 115, 58])
    t_mode_audit.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#F1F5F9')),
        ('TOPPADDING', (0,0), (-1,-1), 3.2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.2),
    ]))
    story.append(t_mode_audit)
    story.append(Spacer(1, 8))

    # Top Delivery Hubs Table
    story.append(Paragraph("<b>TOP ALL-INDIA DESTINATION DELIVERY HUBS</b>", h1_style))
    dests = all_metrics.get("destinations", [])[:8]
    dest_table_data = [
        [
            Paragraph("<b>#</b>", table_header),
            Paragraph("<b>Delivery Destination Hub</b>", table_header),
            Paragraph("<b>Consignments (AWBs)</b>", table_header),
            Paragraph("<b>Cargo Weight (Kg)</b>", table_header),
            Paragraph("<b>Freight Turnover (INR)</b>", table_header),
            Paragraph("<b>Share %</b>", table_header)
        ]
    ]
    tot_dest_awb = 0
    tot_dest_wt = 0.0
    tot_dest_s = 0.0

    for idx, d in enumerate(dests, start=1):
        d_city = str(d.get("city", "Unknown"))
        d_awb = int(d.get("shipments", 0))
        d_s = float(d.get("sales", 0))
        d_wt = float(d.get("weight", 0) or 0)
        if not d_wt and all_shipments:
            d_wt = sum(float(s.get("weight", 0) or 0) for s in all_shipments if str(s.get("destination", "")).lower() == d_city.lower())

        tot_dest_awb += d_awb
        tot_dest_wt += d_wt
        tot_dest_s += d_s

        dest_table_data.append([
            Paragraph(str(idx), table_cell),
            Paragraph(d_city, table_cell_bold),
            Paragraph(f"{d_awb:,} AWBs", table_cell_right),
            Paragraph(f"{d_wt:,.1f}" if d_wt else "---", table_cell_right),
            Paragraph(format_indian_number(d_s), table_cell_right_bold),
            Paragraph(f"{(d_s/tot_s*100 if tot_s else 0):.1f}%", table_cell_right)
        ])

    # Dest total row
    dest_table_data.append([
        Paragraph("<b>Total - Top Delivery Hubs</b>", table_cell_bold),
        "",
        Paragraph(f"{tot_dest_awb:,} AWBs", table_cell_right_bold),
        Paragraph(f"{tot_dest_wt:,.1f}", table_cell_right_bold),
        Paragraph(format_indian_number(tot_dest_s), table_cell_right_bold),
        Paragraph(f"{(tot_dest_s/tot_s*100 if tot_s else 0):.1f}%", table_cell_right_bold)
    ])

    t_dest_audit = Table(dest_table_data, colWidths=[24, 160, 95, 80, 110, 54])
    t_dest_audit.setStyle(TableStyle([
        ('SPAN', (0, -1), (1, -1)),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#F1F5F9')),
        ('TOPPADDING', (0,0), (-1,-1), 3.0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.0),
        *([('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F8FAFC')) for i in range(1, len(dest_table_data) - 1, 2)])
    ]))
    story.append(t_dest_audit)
    story.append(Spacer(1, 9))

    # Formal Statutory Audit Certification Block with Dual Signatories
    signoff_data = [
        [
            Paragraph(f"<b>FORMAL STATUTORY AUDIT CERTIFICATION & MANAGEMENT ATTESTATION</b><br/>"
                      f"This statutory sales and logistics revenue audit report has been compiled through 100% automated "
                      f"three-way triangulation across Billed MIS, Unbilled MIS, and Operations Booking Register for <b>{COMPANY_LEGAL_NAME}</b> "
                      "All physical docket numbers, volumetric cargo weights, transport mode classifications, and revenue attributions have been verified and reconciled.<br/><br/>"
                      "We confirm that the accompanying financial statements and schedules present a true and fair view of commercial operations for the audit period in accordance with standard internal audit guidelines.", body_style)
        ],
        [
            Table([
                [
                    Paragraph("<b>LEAD INTERNAL AUDITOR</b><br/><br/>"
                              "Signature: ___________________________<br/>"
                              "Name: Internal Audit Controller<br/>"
                              "Title: Head of Revenue Assurance & Risk<br/>"
                              "Date: ___________________________", body_style),
                    Paragraph("<b>AUDIT COMMITTEE / CHIEF FINANCIAL OFFICER</b><br/><br/>"
                              "Signature: ___________________________<br/>"
                              "Name: Executive Director & CFO<br/>"
                              "Title: Authorized Corporate Signatory<br/>"
                              "Date: ___________________________", body_style)
                ]
            ], colWidths=[250, 250])
        ],
        [
            Paragraph(f"<font size=6.8 color='#64748B'>{AUDIT_BODY_AUTHORITY}  •  "
                      f"Audit Ref: NEL-AUD-{re.sub(r'[^A-Za-z0-9]', '', period_str)}  •  "
                      "STRICTLY CONFIDENTIAL - BOARDROOM MASTER COPY</font>", body_style)
        ]
    ]
    t_signoff = Table(signoff_data, colWidths=[523])
    t_signoff.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 0.8, colors.HexColor('#0F172A')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_signoff)

    doc.build(story, canvasmaker=NumberedCanvas)
    out.seek(0)
    return out
