# DOXERA Executive Sales Export Engine
# =========================================================
# Generates minimalist, boardroom-ready PDF and PowerPoint (.PPTX)
# audit reports with embedded high-resolution visual charts.
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
    """PDF-safe short currency (uses 'INR ' to avoid glyph issues)."""
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
# Boardroom / Big-4 Audit Aesthetic: Slate, Navy, Teal, Amber
# ─────────────────────────────────────────────────────────────

def generate_trend_chart_img(daily_sales_list, width_in=5.8, height_in=2.7, dpi=180):
    """
    Renders Sale Graph by Date line chart with smooth area fill,
    non-overlapping X-axis date ticks, peak callout, and clean INR Y-axis.
    """
    fig, ax = plt.subplots(figsize=(width_in, height_in), dpi=dpi)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')

    valid_days = [d for d in (daily_sales_list or []) if d.get('date') and d.get('date') != 'Undated']
    if not valid_days:
        ax.text(0.5, 0.5, 'No Daily Sales Trend Data', ha='center', va='center', color='#94A3B8', fontsize=9)
        ax.axis('off')
    else:
        vals = [float(d.get('sales', 0)) for d in valid_days]
        raw_dates = [str(d.get('date', '')) for d in valid_days]

        date_labels = []
        for rd in raw_dates:
            p = rd.split('-')
            date_labels.append(f"{p[0]}/{p[1]}" if len(p) >= 2 else rd)

        x = np.arange(len(valid_days))
        ax.plot(x, vals, color='#1E3A8A', lw=2.0, marker='o', markersize=3.5,
                markerfacecolor='#1E3A8A', markeredgecolor='#FFFFFF', markeredgewidth=1.0, zorder=3)
        ax.fill_between(x, vals, color='#1E3A8A', alpha=0.08, zorder=2)

        # Highlight single peak day with sleek badge
        if len(vals) > 0:
            max_idx = int(np.argmax(vals))
            max_val = vals[max_idx]
            ax.scatter([max_idx], [max_val], color='#1E3A8A', s=45, zorder=4)
            ax.annotate(
                f"Peak: {format_inr_short(max_val)}",
                xy=(max_idx, max_val),
                xytext=(0, 7),
                textcoords='offset points',
                ha='center',
                fontsize=6.8,
                fontweight='bold',
                color='#1E3A8A',
                bbox=dict(boxstyle='round,pad=0.25', facecolor='#EFF6FF', edgecolor='#BFDBFE', lw=0.75)
            )

        # Space out X ticks so dates never collide
        step = max(1, len(valid_days) // 7)
        tick_indices = list(range(0, len(valid_days), step))
        if (len(valid_days) - 1) not in tick_indices:
            tick_indices.append(len(valid_days) - 1)

        ax.set_xticks(tick_indices)
        ax.set_xticklabels([date_labels[i] for i in tick_indices], fontsize=6.8, color='#475569')
        ax.yaxis.set_major_locator(ticker.MaxNLocator(nbins=5))
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(_fmt_axis_lakh))
        ax.tick_params(axis='y', labelsize=6.8, colors='#64748B')
        ax.tick_params(axis='x', length=3, color='#CBD5E1')
        ax.set_ylim(0, (max(vals) if vals else 1) * 1.25)

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#E2E8F0')
        ax.spines['bottom'].set_color('#CBD5E1')
        ax.grid(axis='y', linestyle='--', alpha=0.5, color='#E2E8F0')

    plt.title('Daily Sales Turnover Trend (Reconciled)', fontsize=8.5, fontweight='bold', loc='left', color='#0F172A', pad=9)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_sales_rep_chart_img(sales_reps_list, width_in=5.8, height_in=3.0, dpi=180):
    """
    Renders Total Sale by Sales Person ranked horizontal bar chart.
    Top performer highlighted in Corporate Navy; others in Slate-800.
    """
    fig, ax = plt.subplots(figsize=(width_in, height_in), dpi=dpi)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')

    reps = sales_reps_list[:7] if sales_reps_list else []
    if not reps:
        ax.text(0.5, 0.5, 'No Sales Reps Data', ha='center', va='center', color='#94A3B8', fontsize=9)
        ax.axis('off')
    else:
        names = [str(r.get("name", "NEL"))[:18] for r in reps]
        sales = [float(r.get("sales", 0)) for r in reps]
        shares = [float(r.get("share_pct", 0)) for r in reps]

        names.reverse()
        sales.reverse()
        shares.reverse()

        y_pos = np.arange(len(names))
        bars = ax.barh(y_pos, sales, color='#1E293B', height=0.54, edgecolor='none', zorder=3)
        if len(bars) > 0:
            bars[-1].set_color('#1E3A8A')  # Highlight top performer

        max_s = max(sales) if sales else 1
        for bar, s, sh in zip(bars, sales, shares):
            ax.text(
                s + (max_s * 0.02),
                bar.get_y() + bar.get_height() / 2,
                f"{format_inr_short(s)}  ({sh:.1f}%)",
                va='center',
                ha='left',
                fontsize=6.8,
                fontweight='bold',
                color='#334155'
            )

        ax.set_yticks(y_pos)
        ax.set_yticklabels(names, fontsize=7.2, fontweight='bold', color='#0F172A')
        ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=5))
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(_fmt_axis_lakh))
        ax.tick_params(axis='x', labelsize=6.8, colors='#64748B')
        ax.tick_params(axis='y', length=0)
        ax.set_xlim(0, max_s * 1.35)

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['bottom'].set_color('#CBD5E1')
        ax.grid(axis='x', linestyle='--', alpha=0.5, color='#E2E8F0')

    plt.title('Top Sales Representatives by Audited Turnover', fontsize=8.5, fontweight='bold', loc='left', color='#0F172A', pad=9)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_servicemode_pie_chart_img(mode_list, width_in=4.8, height_in=3.0, dpi=180):
    """
    Renders Total Sale by ServiceMode donut chart with guaranteed visual slice floor
    for small transport modes (e.g. Train 0.2%), center total, and crisp side legend.
    """
    fig, ax = plt.subplots(figsize=(width_in, height_in), dpi=dpi)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')

    valid_modes = [m for m in (mode_list or []) if float(m.get("sales", 0)) > 0 or int(m.get("shipments", 0)) > 0]
    if not valid_modes:
        ax.text(0.5, 0.5, 'No Mode Data', ha='center', va='center', color='#94A3B8', fontsize=9)
        ax.axis('off')
    else:
        raw_sales = [float(m.get("sales", 0)) for m in valid_modes]
        labels = [str(m.get("mode", "Other")) for m in valid_modes]
        total_sales = sum(raw_sales) or 1

        color_map = {'Air': '#1E3A8A', 'Surface': '#0D9488', 'Train': '#D97706'}
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
            wedgeprops=dict(width=0.40, edgecolor='#FFFFFF', linewidth=2.0),
            startangle=140
        )

        # Center donut hole metric with clean vertical spacing
        ax.text(0, 0.12, 'TOTAL TURNOVER', ha='center', va='center', fontsize=6.2, fontweight='bold', color='#64748B')
        ax.text(0, -0.12, format_inr_short(total_sales), ha='center', va='center', fontsize=8.6, fontweight='bold', color='#0F172A')

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
            fontsize=7.2,
            labelcolor='#0F172A'
        )

    plt.title('Turnover by Transport Mode', fontsize=8.5, fontweight='bold', loc='left', color='#0F172A', pad=9)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_top_customer_chart_img(customers_list, width_in=4.8, height_in=3.0, dpi=180):
    """
    Renders Top Corporate Accounts concentration horizontal bar chart matching the dashboard.
    """
    fig, ax = plt.subplots(figsize=(width_in, height_in), dpi=dpi)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')

    top_c = customers_list[:6] if customers_list else []
    if not top_c:
        ax.text(0.5, 0.5, 'No Customer Data', ha='center', va='center', color='#94A3B8', fontsize=9)
        ax.axis('off')
    else:
        names = [str(c.get("name", "General"))[:22] for c in top_c]
        sales = [float(c.get("sales", 0)) for c in top_c]
        shares = [float(c.get("share_pct", 0)) for c in top_c]

        names.reverse()
        sales.reverse()
        shares.reverse()

        y_pos = np.arange(len(names))
        bars = ax.barh(y_pos, sales, color='#334155', height=0.52, edgecolor='none', zorder=3)
        if len(bars) > 0:
            bars[-1].set_color('#0D9488')  # Highlight top customer in Teal

        max_cs = max(sales) if sales else 1
        for bar, s, sh in zip(bars, sales, shares):
            ax.text(
                s + (max_cs * 0.02),
                bar.get_y() + bar.get_height() / 2,
                f"{format_inr_short(s)}  ({sh:.1f}%)",
                va='center',
                ha='left',
                fontsize=6.5,
                fontweight='bold',
                color='#334155'
            )

        ax.set_yticks(y_pos)
        ax.set_yticklabels(names, fontsize=6.8, fontweight='bold', color='#0F172A')
        ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=5))
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(_fmt_axis_lakh))
        ax.tick_params(axis='x', labelsize=6.5, colors='#64748B')
        ax.tick_params(axis='y', length=0)
        ax.set_xlim(0, max_cs * 1.38)

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['bottom'].set_color('#CBD5E1')
        ax.grid(axis='x', linestyle='--', alpha=0.5, color='#E2E8F0')

    plt.title('Top Corporate Accounts Concentration', fontsize=8.5, fontweight='bold', loc='left', color='#0F172A', pad=9)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────
# 1. EXECUTIVE POWERPOINT PRESENTATION (.PPTX)
# Boardroom / Statutory Audit Presentation
# ─────────────────────────────────────────────────────────────

def generate_sales_pptx(report_row, report_data):
    """
    Generates a minimalist, boardroom-ready 16:9 presentation.
    Slide 1: Executive Visual Dashboard (Clean White KPI Cards + 4 Visual Charts)
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

    period_str = summary.get("period_label", "Monthly Audit Period")

    def add_minimalist_header(slide, title_text, category="NORTH EXPRESS LOGISTICS PVT. LTD."):
        tx = slide.shapes.add_textbox(Inches(0.8), Inches(0.25), Inches(9.5), Inches(0.80))
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
        line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.15), Inches(11.733), Inches(0.015))
        line.fill.solid()
        line.fill.fore_color.rgb = RGBColor(226, 232, 240)
        line.line.fill.background()

        if os.path.exists(logo_path):
            try:
                slide.shapes.add_picture(logo_path, Inches(10.8), Inches(0.28), width=Inches(1.6))
            except Exception:
                pass

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

    # ═════════════════════════════════════════════════════════════════
    # SLIDE 1: EXECUTIVE VISUAL DASHBOARD (Boardroom Layout)
    # ═════════════════════════════════════════════════════════════════
    slide1 = prs.slides.add_slide(blank_layout)
    dash_title = report_title.upper() if report_title else "EXECUTIVE LOGISTICS SALES AUDIT REPORT"
    add_minimalist_header(slide1, dash_title)

    # 4 Executive White KPI Cards (Replacing old black box!)
    tot_sales = summary.get("total_sales", 0)
    billed_sales = summary.get("billed_sales", 0)
    unbilled_sales = summary.get("unbilled_sales", 0)
    leakage_amt = summary.get("delivered_unbilled_amt", 0)

    tot_awbs = summary.get("total_shipments", 0)
    billed_awbs = summary.get("billed_shipments", 0)
    unbilled_awbs = summary.get("unbilled_shipments", 0)
    leakage_awbs = summary.get("delivered_unbilled_count", 0)
    tot_wt = summary.get("total_weight", 0)

    kpi_cards_data = [
        ("TOTAL AUDITED TURNOVER", format_inr_short(tot_sales), f"{tot_awbs:,} AWBs  •  {tot_wt/1000:,.1f}k Kg", RGBColor(30, 58, 138)),
        ("BILLED (INVOICED)", format_inr_short(billed_sales), f"{billed_awbs:,} AWBs  •  {(billed_sales/tot_sales*100 if tot_sales else 0):.1f}% Share", RGBColor(5, 150, 105)),
        ("UNBILLED EXPOSURE", format_inr_short(unbilled_sales), f"{unbilled_awbs:,} AWBs  •  {(unbilled_sales/tot_sales*100 if tot_sales else 0):.1f}% Share", RGBColor(217, 119, 6)),
        ("DELIVERED UNBILLED", format_inr_short(leakage_amt), f"{leakage_awbs:,} AWBs  •  Immediate Risk", RGBColor(190, 18, 60))
    ]

    card_w = Inches(2.78)
    card_h = Inches(1.05)
    card_gap = Inches(0.20)
    start_x = Inches(0.8)

    for i, (lbl, val, sub, accent_color) in enumerate(kpi_cards_data):
        x = start_x + (i * (card_w + card_gap))
        k_card = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, Inches(1.28), card_w, card_h)
        k_card.fill.solid()
        k_card.fill.fore_color.rgb = RGBColor(255, 255, 255)
        k_card.line.color.rgb = RGBColor(226, 232, 240)
        k_card.line.width = Pt(1)

        tx = slide1.shapes.add_textbox(x + Inches(0.12), Inches(1.34), card_w - Inches(0.24), card_h - Inches(0.12))
        tf = tx.text_frame
        tf.word_wrap = True

        p_lbl = tf.paragraphs[0]
        p_lbl.text = lbl
        p_lbl.font.size = Pt(8.5)
        p_lbl.font.bold = True
        p_lbl.font.color.rgb = RGBColor(100, 116, 139)

        p_val = tf.add_paragraph()
        p_val.text = val
        p_val.font.size = Pt(16)
        p_val.font.bold = True
        p_val.font.color.rgb = accent_color

        p_sub = tf.add_paragraph()
        p_sub.text = sub
        p_sub.font.size = Pt(8)
        p_sub.font.color.rgb = RGBColor(71, 85, 105)

    # 4 Visual Charts Grid (Using all_metrics for complete audited dataset)
    daily_sales = all_metrics.get("daily_sales", [])
    reps_list = all_metrics.get("sales_reps", [])
    modes_list = all_metrics.get("modes", [])
    custs_list = all_metrics.get("customers", [])

    buf_trend = generate_trend_chart_img(daily_sales, width_in=6.3, height_in=2.3)
    buf_mode = generate_servicemode_pie_chart_img(modes_list, width_in=5.2, height_in=2.3)
    buf_rep = generate_sales_rep_chart_img(reps_list, width_in=6.3, height_in=2.3)
    buf_cust = generate_top_customer_chart_img(custs_list, width_in=5.2, height_in=2.3)

    # Row 1 Charts (Top)
    slide1.shapes.add_picture(buf_trend, Inches(0.8), Inches(2.48), width=Inches(6.3), height=Inches(2.3))
    slide1.shapes.add_picture(buf_mode, Inches(7.3), Inches(2.48), width=Inches(5.2), height=Inches(2.3))

    # Row 2 Charts (Bottom)
    slide1.shapes.add_picture(buf_rep, Inches(0.8), Inches(4.90), width=Inches(6.3), height=Inches(2.3))
    slide1.shapes.add_picture(buf_cust, Inches(7.3), Inches(4.90), width=Inches(5.2), height=Inches(2.3))

    # ═════════════════════════════════════════════════════════════════
    # SLIDE 2: FINANCIAL RECONCILIATION & RISK AUDIT
    # ═════════════════════════════════════════════════════════════════
    slide2 = prs.slides.add_slide(blank_layout)
    add_minimalist_header(slide2, "SCHEDULE 01: TRI-FACTOR FINANCIAL RECONCILIATION & RISK REGISTER")

    # 3-Pillar Clean Metric Cards
    pillars = [
        ("BILLED INVOICED REVENUE", format_inr(summary.get("billed_sales", 0)), f"{summary.get('billed_shipments', 0):,} AWBs Invoiced", RGBColor(5, 150, 105)),
        ("UNBILLED EXPOSURE (RISK)", format_inr(summary.get("unbilled_sales", 0)), f"{summary.get('unbilled_shipments', 0):,} AWBs Pending", RGBColor(217, 119, 6)),
        ("CONSOLIDATED AUDIT TOTAL", format_inr(summary.get("total_sales", 0)), f"{summary.get('total_shipments', 0):,} Dockets Reconciled", RGBColor(30, 58, 138))
    ]
    p_w = Inches(3.7)
    p_h = Inches(1.25)
    p_gap = Inches(0.3)

    for i, (label, val, sub, accent) in enumerate(pillars):
        x = start_x + (i * (p_w + p_gap))
        card = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, Inches(1.35), p_w, p_h)
        card.fill.solid()
        card.fill.fore_color.rgb = RGBColor(255, 255, 255)
        card.line.color.rgb = RGBColor(226, 232, 240)
        card.line.width = Pt(1)

        tx = slide2.shapes.add_textbox(x + Inches(0.18), Inches(1.42), p_w - Inches(0.36), p_h - Inches(0.14))
        tf = tx.text_frame
        p_lbl = tf.paragraphs[0]
        p_lbl.text = label
        p_lbl.font.size = Pt(9.5)
        p_lbl.font.bold = True
        p_lbl.font.color.rgb = RGBColor(100, 116, 139)

        p_val = tf.add_paragraph()
        p_val.text = val
        p_val.font.size = Pt(16.5)
        p_val.font.bold = True
        p_val.font.color.rgb = accent

        p_sub = tf.add_paragraph()
        p_sub.text = sub
        p_sub.font.size = Pt(8.5)
        p_sub.font.color.rgb = RGBColor(71, 85, 105)

    # Critical Revenue Leakage Alert Card
    alert_box = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(2.80), Inches(11.733), Inches(1.05))
    alert_box.fill.solid()
    alert_box.fill.fore_color.rgb = RGBColor(255, 241, 242)
    alert_box.line.color.rgb = RGBColor(244, 63, 94)
    alert_box.line.width = Pt(1)

    tx_al = slide2.shapes.add_textbox(Inches(1.0), Inches(2.88), Inches(11.3), Inches(0.85))
    tf_al = tx_al.text_frame
    p_al = tf_al.paragraphs[0]
    p_al.text = "CRITICAL AUDIT FINDING: DELIVERED BUT UNBILLED REVENUE EXPOSURE"
    p_al.font.bold = True
    p_al.font.size = Pt(10.5)
    p_al.font.color.rgb = RGBColor(190, 18, 60)

    p_al2 = tf_al.add_paragraph()
    deliv_cnt = summary.get('delivered_unbilled_count', 0)
    deliv_val = format_inr(summary.get('delivered_unbilled_amt', 0))
    p_al2.text = f"{deliv_cnt:,} freight consignments valued at {deliv_val} have been successfully delivered to client addresses without invoice generation. Immediate billing release required to avoid working capital loss."
    p_al2.font.size = Pt(9.2)
    p_al2.font.color.rgb = RGBColor(15, 23, 42)

    # Tri-Factor Schedule Table
    t_shape = slide2.shapes.add_table(4, 5, Inches(0.8), Inches(4.05), Inches(11.733), Inches(3.0))
    t = t_shape.table

    headers = ["Audit Category", "Reconciled Revenue (INR)", "Consignments", "Cargo Weight (Kg)", "Share %"]
    for col_idx, h in enumerate(headers):
        cell = t.cell(0, col_idx)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(15, 23, 42)
        for p in cell.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(10.5)
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
                p.font.size = Pt(10)
                p.font.color.rgb = RGBColor(15, 23, 42)

    # ═════════════════════════════════════════════════════════════════
    # SLIDE 3: SALES TEAM & CLIENT CONCENTRATION
    # ═════════════════════════════════════════════════════════════════
    slide3 = prs.slides.add_slide(blank_layout)
    add_minimalist_header(slide3, "SCHEDULE 02: SALES TEAM PERFORMANCE & MAJOR CLIENT ACCOUNTS")

    # Table 1 (Left): Sales Representatives
    reps = all_metrics.get("sales_reps", [])[:8]
    t_rep_shape = slide3.shapes.add_table(min(len(reps) + 1, 9), 4, Inches(0.8), Inches(1.35), Inches(5.6), Inches(5.6))
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
        vals = [r.get("name", "NEL")[:20], f"{r.get('shipments', 0):,}", format_inr(r.get("sales", 0)), f"{r.get('share_pct', 0):.1f}%"]
        for col_idx, v in enumerate(vals):
            cell = t_rep.cell(row_idx, col_idx)
            cell.text = v
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(255, 255, 255) if row_idx % 2 == 1 else RGBColor(248, 250, 252)
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(9.2)
                p.font.color.rgb = RGBColor(15, 23, 42)

    # Table 2 (Right): Top 8 Major Clients
    custs = all_metrics.get("customers", [])[:8]
    t_cust_shape = slide3.shapes.add_table(min(len(custs) + 1, 9), 4, Inches(6.8), Inches(1.35), Inches(5.7), Inches(5.6))
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
        vals = [c.get("name", "General")[:22], str(c.get("sales_person", "NEL"))[:12], format_inr(c.get("sales", 0)), f"{c.get('share_pct', 0):.1f}%"]
        for col_idx, v in enumerate(vals):
            cell = t_cust.cell(row_idx, col_idx)
            cell.text = v
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(255, 255, 255) if row_idx % 2 == 1 else RGBColor(248, 250, 252)
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(9.2)
                p.font.color.rgb = RGBColor(15, 23, 42)

    # ═════════════════════════════════════════════════════════════════
    # SLIDE 4: TRANSPORT MODES, DELIVERY HUBS & AUDIT SIGN-OFF
    # ═════════════════════════════════════════════════════════════════
    slide4 = prs.slides.add_slide(blank_layout)
    add_minimalist_header(slide4, "SCHEDULE 03: LOGISTICS MODES, HUBS & AUDITOR CERTIFICATION")

    # Mode Dynamics Table
    modes = all_metrics.get("modes", [])
    t_mode_shape = slide4.shapes.add_table(min(len(modes) + 1, 6), 4, Inches(0.8), Inches(1.35), Inches(5.6), Inches(3.2))
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
            f"{m.get('share_pct', 0):.1f}%"
        ]
        for col_idx, v in enumerate(vals):
            cell = t_mode.cell(row_idx, col_idx)
            cell.text = v
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(255, 255, 255) if row_idx % 2 == 1 else RGBColor(248, 250, 252)
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(9.2)
                p.font.color.rgb = RGBColor(15, 23, 42)

    # Top Delivery Hubs Table
    dests = all_metrics.get("destinations", [])[:6]
    t_dest_shape = slide4.shapes.add_table(min(len(dests) + 1, 7), 3, Inches(6.8), Inches(1.35), Inches(5.7), Inches(3.2))
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
                p.font.size = Pt(9.2)
                p.font.color.rgb = RGBColor(15, 23, 42)

    # Formal Attestation Card (Bottom)
    sign_box = slide4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(4.85), Inches(11.733), Inches(2.2))
    sign_box.fill.solid()
    sign_box.fill.fore_color.rgb = RGBColor(248, 250, 252)
    sign_box.line.color.rgb = RGBColor(203, 213, 225)
    sign_box.line.width = Pt(1)

    tx_s = slide4.shapes.add_textbox(Inches(1.1), Inches(5.0), Inches(11.1), Inches(1.9))
    tf_s = tx_s.text_frame
    p_st = tf_s.paragraphs[0]
    p_st.text = "FORMAL AUDIT CERTIFICATION & MANAGEMENT ATTESTATION"
    p_st.font.bold = True
    p_st.font.size = Pt(11)
    p_st.font.color.rgb = RGBColor(15, 23, 42)

    p_sb = tf_s.add_paragraph()
    p_sb.text = ("This monthly sales and logistics audit report has been compiled through 100% automated three-way triangulation "
                 "across Billed MIS, Unbilled MIS, and Operations Booking Register. All dockets, cargo weights, transport modes, and "
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
# Big-4 / Institutional Audit Style (Pure White, Crisp Typography)
# ─────────────────────────────────────────────────────────────

def generate_sales_pdf(report_row, report_data):
    """
    Generates a minimalist, Big-4 style PDF audit report with NumberedCanvas,
    Page 1 executive visual dashboard with embedded charts, and comprehensive schedules.
    """
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
            hdr_sub = (report_title[:45] + '...') if len(report_title) > 48 else (report_title or "EXECUTIVE SALES AUDIT")
            self.drawString(36, 808, f"NORTH EXPRESS LOGISTICS LTD.  |  {hdr_sub.upper()}")
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
        fontSize=16,
        leading=20,
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
        fontSize=10.5,
        leading=13,
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
    # PAGE 1: EXECUTIVE VISUAL DASHBOARD
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

    main_doc_title = report_title.upper() if report_title else "EXECUTIVE SALES AUDIT REPORT"
    story.append(Paragraph(main_doc_title, doc_title_style))
    story.append(Paragraph(f"Audit Window: <b>{period_str}</b>  •  Correlated: <b>{summary.get('total_shipments', 0):,} AWBs</b>  •  Status: <b>Verified & Audited</b>", doc_sub_style))
    story.append(Spacer(1, 6))

    # 4 Executive Clean White KPI Cards (Replacing old black box!)
    tot_s = summary.get("total_sales", 0)
    billed_s = summary.get("billed_sales", 0)
    unbilled_s = summary.get("unbilled_sales", 0)
    deliv_unb_s = summary.get("delivered_unbilled_amt", 0)

    tot_awb = summary.get("total_shipments", 0)
    billed_awb = summary.get("billed_shipments", 0)
    unbilled_awb = summary.get("unbilled_shipments", 0)
    deliv_unb_awb = summary.get("delivered_unbilled_count", 0)

    kpi_white_data = [
        [
            Paragraph(f"<font color='#64748B' size=7><b>TOTAL AUDITED TURNOVER</b></font><br/>"
                      f"<font color='#1E3A8A' size=12><b>{format_pdf_inr_short(tot_s)}</b></font><br/>"
                      f"<font color='#475569' size=7>{tot_awb:,} AWBs  •  100%</font>", card_val),
            Paragraph(f"<font color='#64748B' size=7><b>BILLED (INVOICED)</b></font><br/>"
                      f"<font color='#059669' size=12><b>{format_pdf_inr_short(billed_s)}</b></font><br/>"
                      f"<font color='#475569' size=7>{billed_awb:,} AWBs  •  {(billed_s/tot_s*100 if tot_s else 0):.1f}%</font>", card_val),
            Paragraph(f"<font color='#64748B' size=7><b>UNBILLED EXPOSURE</b></font><br/>"
                      f"<font color='#D97706' size=12><b>{format_pdf_inr_short(unbilled_s)}</b></font><br/>"
                      f"<font color='#475569' size=7>{unbilled_awb:,} AWBs  •  {(unbilled_s/tot_s*100 if tot_s else 0):.1f}%</font>", card_val),
            Paragraph(f"<font color='#64748B' size=7><b>DELIVERED UNBILLED</b></font><br/>"
                      f"<font color='#BE123C' size=12><b>{format_pdf_inr_short(deliv_unb_s)}</b></font><br/>"
                      f"<font color='#475569' size=7>{deliv_unb_awb:,} AWBs  •  Risk</font>", card_val)
        ]
    ]
    t_kpi_white = Table(kpi_white_data, colWidths=[130, 131, 131, 131])
    t_kpi_white.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 0.75, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_kpi_white)
    story.append(Spacer(1, 8))

    # 4 Visual Charts Grid (Using all_metrics for complete audited dataset)
    daily_sales = all_metrics.get("daily_sales", [])
    reps_list = all_metrics.get("sales_reps", [])
    modes_list = all_metrics.get("modes", [])
    custs_list = all_metrics.get("customers", [])

    buf_trend = generate_trend_chart_img(daily_sales, width_in=4.4, height_in=2.1)
    buf_mode = generate_servicemode_pie_chart_img(modes_list, width_in=3.6, height_in=2.1)
    buf_rep = generate_sales_rep_chart_img(reps_list, width_in=4.4, height_in=2.2)
    buf_cust = generate_top_customer_chart_img(custs_list, width_in=3.6, height_in=2.2)

    img_trend = Image(buf_trend, width=285, height=140)
    img_mode = Image(buf_mode, width=233, height=140)
    img_rep = Image(buf_rep, width=285, height=148)
    img_cust = Image(buf_cust, width=233, height=148)

    charts_grid = [
        [img_trend, img_mode],
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
                      f"The audit engine reconciled <b>{deliv_count:,} consignments</b> totaling <b>INR {format_indian_number(deliv_amt)}</b> "
                      "where freight goods have been physically delivered to client addresses without invoice generation. "
                      "Immediate billing release is required to avoid working capital loss.", body_style)
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
            Paragraph("<b>Average Ticket (INR)</b>", table_header),
            Paragraph("<b>Share %</b>", table_header)
        ],
        [
            Paragraph("<b>Billed MIS (Invoiced Revenue)</b>", table_cell_bold),
            Paragraph(f"{summary.get('billed_shipments', 0):,}", table_cell_right),
            Paragraph(f"{billed_metrics.get('summary', {}).get('total_weight', 0):,.1f}", table_cell_right),
            Paragraph(format_indian_number(summary.get("billed_sales", 0)), table_cell_right_bold),
            Paragraph(format_indian_number(billed_metrics.get("summary", {}).get("avg_ticket", 0)), table_cell_right),
            Paragraph(f"{(summary.get('billed_sales', 0)/tot_s_base*100):.1f}%", table_cell_right_bold)
        ],
        [
            Paragraph("<b>Unbilled MIS (Pending Exposure)</b>", table_cell_bold),
            Paragraph(f"{summary.get('unbilled_shipments', 0):,}", table_cell_right),
            Paragraph(f"{unbilled_metrics.get('summary', {}).get('total_weight', 0):,.1f}", table_cell_right),
            Paragraph(format_indian_number(summary.get("unbilled_sales", 0)), table_cell_right_bold),
            Paragraph(format_indian_number(unbilled_metrics.get("summary", {}).get("avg_ticket", 0)), table_cell_right),
            Paragraph(f"{(summary.get('unbilled_sales', 0)/tot_s_base*100):.1f}%", table_cell_right_bold)
        ],
        [
            Paragraph("<b>Total Reconciled Operations Base</b>", table_cell_bold),
            Paragraph(f"{summary.get('total_shipments', 0):,}", table_cell_right_bold),
            Paragraph(f"{summary.get('total_weight', 0):,.1f}", table_cell_right_bold),
            Paragraph(format_indian_number(tot_s_base), table_cell_right_bold),
            Paragraph(format_indian_number(summary.get("avg_ticket", 0)), table_cell_right_bold),
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
            Paragraph("<b>Audited Turnover (INR)</b>", table_header),
            Paragraph("<b>Share %</b>", table_header)
        ]
    ]
    for idx, r in enumerate(reps[:10], start=1):
        rep_table_data.append([
            Paragraph(str(idx), table_cell),
            Paragraph(str(r.get("name", "NEL")), table_cell_bold),
            Paragraph(str(r.get("customer_count", 0)), table_cell_right),
            Paragraph(f"{r.get('shipments', 0):,}", table_cell_right),
            Paragraph(format_indian_number(r.get("sales", 0)), table_cell_right_bold),
            Paragraph(f"{r.get('share_pct', 0):.1f}%", table_cell_right_bold)
        ])
    t_rep_audit = Table(rep_table_data, colWidths=[28, 187, 65, 65, 115, 63])
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
            Paragraph("<b>Audited Turnover (INR)</b>", table_header),
            Paragraph("<b>Share %</b>", table_header)
        ]
    ]
    for idx, c in enumerate(custs, start=1):
        cust_name = str(c.get("name", "General"))[:30]
        cust_code = str(c.get("code") or "---")
        cust_rep = str(c.get("sales_person", "NEL"))
        cust_table_data.append([
            Paragraph(str(idx), table_cell),
            Paragraph(cust_name, table_cell_bold),
            Paragraph(cust_code, table_cell),
            Paragraph(cust_rep, table_cell),
            Paragraph(f"{c.get('shipments', 0):,}", table_cell_right),
            Paragraph(format_indian_number(c.get("sales", 0)), table_cell_right_bold),
            Paragraph(f"{c.get('share_pct', 0):.1f}%", table_cell_right)
        ])
    t_cust_audit = Table(cust_table_data, colWidths=[28, 177, 55, 95, 48, 75, 45])
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

    # Mode Performance Table with recomputed weight & yield if missing
    modes = all_metrics.get("modes", [])
    all_shipments = report_data.get("all_shipments", [])
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
        mode_name = str(m.get("mode", "Other"))
        wt = m.get("weight", 0)
        # Compute from shipments if missing
        if not wt and all_shipments:
            wt = sum(float(s.get("weight", 0) or 0) for s in all_shipments if str(s.get("transport_mode", "")).lower() == mode_name.lower())
        wt_str = f"{wt:,.1f}" if wt else "---"
        sales_val = float(m.get("sales", 0))
        yd = (sales_val / wt) if wt > 0 else m.get("yield_per_kg", 0)
        yd_str = f"INR {yd:.2f}/Kg" if yd else "---"

        mode_table_data.append([
            Paragraph(mode_name, table_cell_bold),
            Paragraph(f"{m.get('shipments', 0):,}", table_cell_right),
            Paragraph(wt_str, table_cell_right),
            Paragraph(yd_str, table_cell_right),
            Paragraph(format_indian_number(sales_val), table_cell_right_bold),
            Paragraph(f"{m.get('share_pct', 0):.1f}%", table_cell_right_bold)
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
            Paragraph(format_indian_number(d.get("sales", 0)), table_cell_right_bold)
        ])
    t_dest_audit = Table(dest_table_data, colWidths=[28, 227, 115, 153])
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
