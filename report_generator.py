# ══════════════════════════════════════════════════════════════════════
# report_generator.py — PDF report generation for AI Startup Dashboard
# ══════════════════════════════════════════════════════════════════════

import io
import pandas as pd
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)

# ── Colors ───────────────────────────────────────────────────────────
NAVY       = HexColor('#0F172A')
BLUE       = HexColor('#2563EB')
DARK_BLUE  = HexColor('#1E40AF')
LIGHT_BLUE = HexColor('#DBEAFE')
GRAY       = HexColor('#64748B')
LIGHT_GRAY = HexColor('#F1F5F9')
MID_GRAY   = HexColor('#E2E8F0')
WHITE      = HexColor('#FFFFFF')
BLACK      = HexColor('#1E293B')
GREEN      = HexColor('#059669')
AMBER      = HexColor('#D97706')


# ── Styles ────────────────────────────────────────────────────────────
def _styles():
    base = getSampleStyleSheet()
    s = {}

    # Cover page
    s['cover_company'] = ParagraphStyle('CoverCompany',
        fontSize=28, textColor=WHITE, fontName='Helvetica-Bold',
        alignment=TA_LEFT, leading=34, spaceAfter=8)
    s['cover_sub'] = ParagraphStyle('CoverSub',
        fontSize=12, textColor=HexColor('#93C5FD'), fontName='Helvetica',
        alignment=TA_LEFT, leading=16, spaceAfter=6)
    s['cover_meta'] = ParagraphStyle('CoverMeta',
        fontSize=9, textColor=HexColor('#CBD5E1'), fontName='Helvetica',
        alignment=TA_LEFT, leading=13)
    s['cover_prepared'] = ParagraphStyle('CoverPrepared',
        fontSize=10, textColor=WHITE, fontName='Helvetica-Bold',
        alignment=TA_LEFT, spaceAfter=4)

    # Body
    s['title'] = ParagraphStyle('ReportTitle',
        fontSize=18, textColor=NAVY, spaceAfter=4, leading=22,
        fontName='Helvetica-Bold')
    s['subtitle'] = ParagraphStyle('Subtitle',
        fontSize=9, textColor=GRAY, spaceAfter=10, leading=13,
        fontName='Helvetica')
    s['h1'] = ParagraphStyle('H1',
        fontSize=13, textColor=DARK_BLUE, spaceBefore=16, spaceAfter=6,
        fontName='Helvetica-Bold')
    s['h2'] = ParagraphStyle('H2',
        fontSize=10, textColor=NAVY, spaceBefore=10, spaceAfter=4,
        fontName='Helvetica-Bold')
    s['body'] = ParagraphStyle('Body',
        fontSize=9, textColor=BLACK, leading=14, fontName='Helvetica',
        spaceAfter=3)
    s['body_gray'] = ParagraphStyle('BodyGray',
        fontSize=9, textColor=GRAY, leading=13, fontName='Helvetica',
        spaceAfter=3)
    s['kpi_label'] = ParagraphStyle('KPILabel',
        fontSize=7, textColor=GRAY, alignment=TA_CENTER,
        fontName='Helvetica', spaceAfter=2)
    s['kpi_value'] = ParagraphStyle('KPIValue',
        fontSize=15, textColor=NAVY, alignment=TA_CENTER,
        fontName='Helvetica-Bold', spaceAfter=1)
    s['kpi_delta'] = ParagraphStyle('KPIDelta',
        fontSize=7, textColor=BLUE, alignment=TA_CENTER,
        fontName='Helvetica')
    s['footer'] = ParagraphStyle('Footer',
        fontSize=7, textColor=GRAY, alignment=TA_CENTER,
        fontName='Helvetica')
    s['table_header'] = ParagraphStyle('TH',
        fontSize=8, textColor=WHITE, fontName='Helvetica-Bold')
    s['table_cell'] = ParagraphStyle('TD',
        fontSize=8, textColor=BLACK, fontName='Helvetica', leading=11)
    return s


# ── Helpers ──────────────────────────────────────────────────────────
def _fmt_money(val, decimals=1):
    if pd.isna(val) or val == 0:
        return 'N/A'
    if val >= 1000:
        return f'${val/1000:,.{decimals}f}B'
    return f'${val:,.0f}M'


def _fmt_pct(val):
    if pd.isna(val):
        return 'N/A'
    return f'{val:,.0f}%'


def _make_kpi_row(kpis, styles):
    s = styles
    cells = []
    for label, value, delta in kpis:
        cell = [Paragraph(value, s['kpi_value']), Paragraph(label, s['kpi_label'])]
        if delta:
            cell.append(Paragraph(delta, s['kpi_delta']))
        cells.append(cell)

    t = Table([cells], colWidths=[1.4 * inch] * len(kpis))
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), LIGHT_GRAY),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING',   (0, 0), (-1, -1), 6),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
        ('BOX',           (0, 0), (-1, -1), 0.5, MID_GRAY),
        ('INNERGRID',     (0, 0), (-1, -1), 0.5, MID_GRAY),
    ]))
    return t


def _make_table(headers, rows, col_widths=None):
    s = _styles()
    data = [[Paragraph(h, s['table_header']) for h in headers]]
    for row in rows:
        data.append([Paragraph(str(v), s['table_cell']) for v in row])

    if not col_widths:
        col_widths = [1.2 * inch] * len(headers)

    t = Table(data, colWidths=col_widths, repeatRows=1)
    cmds = [
        ('BACKGROUND',    (0, 0), (-1, 0),  DARK_BLUE),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  WHITE),
        ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, 0),  8),
        ('BOTTOMPADDING', (0, 0), (-1, 0),  7),
        ('TOPPADDING',    (0, 0), (-1, 0),  7),
        ('FONTNAME',      (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE',      (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ('TOPPADDING',    (0, 1), (-1, -1), 5),
        ('INNERGRID',     (0, 0), (-1, -1), 0.5, MID_GRAY),
        ('BOX',           (0, 0), (-1, -1), 0.5, HexColor('#CBD5E1')),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            cmds.append(('BACKGROUND', (0, i), (-1, i), LIGHT_GRAY))
    t.setStyle(TableStyle(cmds))
    return t


def _section_rule(story):
    """Thin blue rule used between sections."""
    story.append(HRFlowable(width="100%", thickness=1, color=LIGHT_BLUE,
                            spaceBefore=6, spaceAfter=10))


def _footer(canvas_obj, doc):
    canvas_obj.saveState()
    canvas_obj.setFont('Helvetica', 7)
    canvas_obj.setFillColor(GRAY)
    canvas_obj.drawString(
        0.75 * inch, 0.45 * inch,
        f"AI Startup Market Intelligence  |  {datetime.now().strftime('%B %d, %Y')}  |  Ramilya Bakiyeva Portfolio"
    )
    canvas_obj.drawRightString(
        7.75 * inch, 0.45 * inch,
        f"Page {doc.page}"
    )
    canvas_obj.restoreState()


def _cover_page(story, title_line1, title_line2, subtitle, prepared_for, styles):
    """
    Full navy cover page drawn as a single-cell table (full page background).
    """
    s = styles
    date_str = datetime.now().strftime("%B %d, %Y")

    inner = []
    inner.append(Spacer(1, 1.6 * inch))
    inner.append(Paragraph(title_line1, s['cover_company']))
    if title_line2:
        inner.append(Paragraph(title_line2, s['cover_sub']))
    inner.append(Spacer(1, 0.15 * inch))
    inner.append(HRFlowable(width="100%", thickness=1.5,
                             color=HexColor('#3B82F6'), spaceAfter=14))
    inner.append(Paragraph(subtitle, s['cover_meta']))
    inner.append(Spacer(1, 0.3 * inch))

    if prepared_for:
        inner.append(Paragraph("Prepared for", s['cover_meta']))
        inner.append(Paragraph(prepared_for, s['cover_prepared']))
        inner.append(Spacer(1, 0.15 * inch))

    inner.append(Paragraph(f"Generated: {date_str}", s['cover_meta']))
    inner.append(Paragraph("Ramilya Bakiyeva · Portfolio Project · San Jose, CA", s['cover_meta']))

    cover_table = Table([[inner]], colWidths=[7.0 * inch])
    cover_table.setStyle(TableStyle([
        ('BACKGROUND',  (0, 0), (-1, -1), NAVY),
        ('VALIGN',      (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0.6 * inch),
        ('RIGHTPADDING',(0, 0), (-1, -1), 0.6 * inch),
        ('TOPPADDING',  (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING',(0, 0),(-1, -1), 0),
    ]))
    story.append(cover_table)
    story.append(PageBreak())


# ════════════════════════════════════════════════════════════════════
# REPORT 1: SINGLE COMPANY BRIEF
# ════════════════════════════════════════════════════════════════════

def generate_company_report(company_name, startups_df, taxonomy_df,
                            investors_df, round_investors_df, funding_history_df,
                            prepared_for=""):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            topMargin=0.65 * inch, bottomMargin=0.75 * inch,
                            leftMargin=0.75 * inch, rightMargin=0.75 * inch)
    s = _styles()
    story = []

    c = startups_df[startups_df['company_name'] == company_name].iloc[0]
    tax_row = taxonomy_df[taxonomy_df['ai_category'] == c['ai_category']]

    # ── Cover ──
    _cover_page(
        story,
        title_line1=company_name,
        title_line2=f"{c['ai_category']}  ·  Founded {int(c['founding_year'])}",
        subtitle=f"Funding: {_fmt_money(c['funding_m'])}  |  Valuation: {_fmt_money(c.get('valuation_m'))}  |  ARR: {_fmt_money(c.get('arr_m'))}",
        prepared_for=prepared_for,
        styles=s,
    )

    # ── Page 2 Header ──
    story.append(Paragraph(f"{company_name} — Intelligence Brief", s['title']))
    story.append(Paragraph(
        f"{c['ai_category']}  ·  Founded {int(c['founding_year'])}  ·  "
        f"{'YC-Backed' if c.get('yc_backed') == 1 else 'Non-YC'}  ·  "
        f"GTM: {c.get('pricing_model', 'N/A')}",
        s['subtitle']
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=BLUE,
                            spaceAfter=14, spaceBefore=0))

    # ── KPIs ──
    val_mult_str = 'N/A'
    delta_str = ''
    if pd.notna(c.get('valuation_m')) and pd.notna(c.get('arr_m')) and c['arr_m'] > 0:
        mult = c['valuation_m'] / c['arr_m']
        val_mult_str = f'{mult:.1f}x'
        peers = startups_df[
            (startups_df['ai_category'] == c['ai_category']) &
            startups_df['valuation_m'].notna() &
            startups_df['arr_m'].notna() &
            (startups_df['arr_m'] > 0)
        ].copy()
        if len(peers) > 0:
            peers['_m'] = peers['valuation_m'] / peers['arr_m']
            med = peers['_m'].median()
            delta_str = f'{mult - med:+.1f}x vs category median'

    kpis = [
        ('Total Funding',  _fmt_money(c['funding_m']) if c['funding_m'] > 0 else 'Bootstrapped', ''),
        ('Valuation',      _fmt_money(c.get('valuation_m')), ''),
        ('ARR',            _fmt_money(c.get('arr_m')), ''),
        ('Val / ARR',      val_mult_str, delta_str),
        ('Growth',         _fmt_pct(c.get('growth_pct')), ''),
    ]
    story.append(_make_kpi_row(kpis, s))
    story.append(Spacer(1, 14))

    # ── Value Proposition ──
    if pd.notna(c.get('use_case')) or pd.notna(c.get('roi_claim')):
        story.append(Paragraph('Core Intelligence', s['h1']))
        _section_rule(story)
        if pd.notna(c.get('use_case')):
            story.append(Paragraph(f'<b>Value Proposition:</b> {c["use_case"]}', s['body']))
        if pd.notna(c.get('roi_claim')):
            story.append(Paragraph(f'<b>Market ROI Claim:</b> {c["roi_claim"]}', s['body']))
        story.append(Spacer(1, 10))

    # ── Two-column: Investors + GTM ──
    story.append(Paragraph('Capital & GTM Strategy', s['h1']))
    _section_rule(story)

    left_parts, right_parts = [], []

    # Left: Investors
    left_parts.append(Paragraph('<b>Capital Infrastructure</b>', s['h2']))
    backers = round_investors_df[
        round_investors_df['company_name'] == company_name
    ].merge(
        investors_df[['investor_name', 'investor_tier', 'gtm_signal']],
        on='investor_name', how='left'
    ).drop_duplicates(subset='investor_name')

    if len(backers) > 0:
        for _, b in backers.head(6).iterrows():
            tier = b['investor_tier'] if pd.notna(b['investor_tier']) else 'Unknown'
            left_parts.append(
                Paragraph(f'<b>{b["investor_name"]}</b> <font color="#64748B">({tier})</font>', s['body'])
            )
    else:
        left_parts.append(Paragraph('No investor data available.', s['body_gray']))

    # Right: GTM
    right_parts.append(Paragraph('<b>GTM Tactical Brief</b>', s['h2']))
    if len(tax_row) > 0:
        t = tax_row.iloc[0]
        right_parts.append(Paragraph(f'<b>The Hook:</b> {t["roi_drivers"]}', s['body']))
        right_parts.append(Spacer(1, 4))
        right_parts.append(Paragraph(f'<b>Target ICP:</b> {t["target_industries"]}', s['body']))
        right_parts.append(Spacer(1, 4))

    cat_peers = startups_df[startups_df['ai_category'] == c['ai_category']]
    bigger = cat_peers[
        (cat_peers['company_name'] != company_name) &
        (cat_peers['funding_m'] > c['funding_m'])
    ].sort_values('funding_m', ascending=False)

    if len(bigger) > 0:
        top = bigger.iloc[0]
        right_parts.append(Paragraph(
            f'<b>Peer Play:</b> {top["company_name"]} raised {_fmt_money(top["funding_m"])} — '
            f'frame competitive scale conversation.',
            s['body']
        ))
    else:
        right_parts.append(Paragraph(
            '<b>Peer Play:</b> Category leader by funding — position as market leader.',
            s['body']
        ))

    col_table = Table([[left_parts, right_parts]], colWidths=[3.3 * inch, 3.4 * inch])
    col_table.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',   (0, 0), (0, 0),   0),
        ('RIGHTPADDING',  (1, 0), (1, 0),   0),
        ('RIGHTPADDING',  (0, 0), (0, 0),   18),
    ]))
    story.append(col_table)
    story.append(Spacer(1, 14))

    # ── Competitive Landscape ──
    story.append(Paragraph(
        f'Competitive Landscape — {c["ai_category"]} ({len(cat_peers)} companies)',
        s['h1']
    ))
    _section_rule(story)

    peer_rows = []
    for _, p in cat_peers.sort_values('funding_m', ascending=False).head(10).iterrows():
        marker = ' ▶' if p['company_name'] == company_name else ''
        peer_rows.append([
            f'{p["company_name"]}{marker}',
            _fmt_money(p['funding_m']),
            _fmt_money(p.get('valuation_m')),
            _fmt_money(p.get('arr_m')),
            _fmt_pct(p.get('growth_pct')),
        ])

    story.append(_make_table(
        ['Company', 'Funding', 'Valuation', 'ARR', 'Growth'],
        peer_rows,
        col_widths=[2.0 * inch, 1.2 * inch, 1.2 * inch, 1.0 * inch, 0.8 * inch]
    ))
    story.append(Spacer(1, 14))

    # ── Funding History ──
    fh_rows = funding_history_df[
        funding_history_df['company_name'] == company_name
    ].sort_values('round_date', ascending=False)

    if len(fh_rows) > 0:
        story.append(Paragraph('Funding History', s['h1']))
        _section_rule(story)
        fh_data = []
        for _, r in fh_rows.head(6).iterrows():
            fh_data.append([
                str(r.get('round_name', 'N/A')),
                _fmt_money(r.get('amount_m')),
                str(r.get('round_date', 'N/A')),
                _fmt_money(r.get('post_money_m')),
                str(r.get('lead_investor', 'N/A'))[:32],
            ])
        story.append(_make_table(
            ['Round', 'Amount', 'Date', 'Post-Money', 'Lead Investor'],
            fh_data,
            col_widths=[1.2 * inch, 1.0 * inch, 0.9 * inch, 1.1 * inch, 2.0 * inch]
        ))

    # ── Notes ──
    if pd.notna(c.get('notes')) and str(c.get('notes', '')) not in ('', 'nan'):
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY,
                                spaceBefore=4, spaceAfter=6))
        story.append(Paragraph(f'<b>Notes:</b> {c["notes"]}', s['body_gray']))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    buf.seek(0)
    return buf.getvalue()


# ════════════════════════════════════════════════════════════════════
# REPORT 2: FULL PORTFOLIO OVERVIEW
# ════════════════════════════════════════════════════════════════════

def generate_portfolio_report(startups_df, taxonomy_df, investors_df,
                              round_investors_df, funding_history_df,
                              prepared_for=""):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            topMargin=0.65 * inch, bottomMargin=0.75 * inch,
                            leftMargin=0.65 * inch, rightMargin=0.65 * inch)
    s = _styles()
    story = []

    total_funding  = startups_df['funding_m'].sum()
    total_cos      = len(startups_df)
    categories     = startups_df['ai_category'].nunique()
    with_arr       = startups_df['arr_m'].notna().sum()
    median_val     = startups_df['valuation_m'].median()

    # ── Cover ──
    _cover_page(
        story,
        title_line1="AI Startup Market Intelligence",
        title_line2="Full Ecosystem Overview — 2026",
        subtitle=(
            f"{total_cos} Companies  ·  {categories} Categories  ·  "
            f"{_fmt_money(total_funding, 0)} Total Ecosystem Funding"
        ),
        prepared_for=prepared_for,
        styles=s,
    )

    # ── Page 2 Header ──
    story.append(Paragraph("AI Startup Market Intelligence", s['title']))
    story.append(Paragraph(
        f"{total_cos} Companies  ·  {categories} Categories  ·  "
        f"{_fmt_money(total_funding, 0)} Total Funding  ·  {datetime.now().strftime('%B %Y')}",
        s['subtitle']
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=BLUE,
                            spaceAfter=14, spaceBefore=0))

    # ── Portfolio KPIs ──
    kpis = [
        ('Total Companies',  str(total_cos),            ''),
        ('Categories',       str(categories),           ''),
        ('Total Funding',    _fmt_money(total_funding), ''),
        ('Median Valuation', _fmt_money(median_val),    ''),
        ('With ARR Data',    f'{with_arr} / {total_cos}', ''),
    ]
    story.append(_make_kpi_row(kpis, s))
    story.append(Spacer(1, 16))

    # ── Top 20 ──
    story.append(Paragraph('Top 20 Companies by Funding', s['h1']))
    _section_rule(story)
    top20 = startups_df.sort_values('funding_m', ascending=False).head(20)
    rows_top = []
    for _, r in top20.iterrows():
        rows_top.append([
            r['company_name'], r['ai_category'],
            _fmt_money(r['funding_m']),
            _fmt_money(r.get('valuation_m')),
            _fmt_money(r.get('arr_m')),
            _fmt_pct(r.get('growth_pct')),
        ])
    story.append(_make_table(
        ['Company', 'Category', 'Funding', 'Valuation', 'ARR', 'Growth'],
        rows_top,
        col_widths=[1.55 * inch, 1.3 * inch, 0.9 * inch, 0.9 * inch, 0.9 * inch, 0.65 * inch]
    ))
    story.append(Spacer(1, 16))

    # ── Category Breakdown ──
    story.append(Paragraph('Category Analysis', s['h1']))
    _section_rule(story)
    cat_stats = (
        startups_df.groupby('ai_category')
        .agg(count=('company_name', 'count'),
             total_funding=('funding_m', 'sum'),
             avg_valuation=('valuation_m', 'mean'),
             avg_arr=('arr_m', 'mean'))
        .sort_values('total_funding', ascending=False)
        .reset_index()
    )
    cat_rows = []
    for _, r in cat_stats.iterrows():
        cat_rows.append([
            r['ai_category'], str(int(r['count'])),
            _fmt_money(r['total_funding']),
            _fmt_money(r['avg_valuation']),
            _fmt_money(r['avg_arr']),
        ])
    story.append(_make_table(
        ['Category', 'Count', 'Total Funding', 'Avg Valuation', 'Avg ARR'],
        cat_rows,
        col_widths=[2.0 * inch, 0.6 * inch, 1.2 * inch, 1.2 * inch, 1.0 * inch]
    ))
    story.append(Spacer(1, 16))

    # ── Investor Landscape ──
    story.append(Paragraph('Top Investors by Portfolio Breadth', s['h1']))
    _section_rule(story)
    portfolio = (
        round_investors_df
        .drop_duplicates(subset=['investor_name', 'company_name'])
        .groupby('investor_name')['company_name']
        .agg(['nunique', lambda x: ', '.join(sorted(set(x)))])
        .reset_index()
    )
    portfolio.columns = ['Investor', 'Companies', 'Portfolio']
    portfolio = portfolio.sort_values('Companies', ascending=False).head(15)
    portfolio = portfolio.merge(
        investors_df[['investor_name', 'investor_tier']].rename(columns={'investor_name': 'Investor'}),
        on='Investor', how='left'
    )
    inv_rows = []
    for _, r in portfolio.iterrows():
        tier = r['investor_tier'] if pd.notna(r['investor_tier']) else 'Unknown'
        port = str(r['Portfolio'])
        port = port[:58] + '...' if len(port) > 58 else port
        inv_rows.append([r['Investor'], tier, str(int(r['Companies'])), port])
    story.append(_make_table(
        ['Investor', 'Tier', '#', 'Portfolio Companies'],
        inv_rows,
        col_widths=[1.6 * inch, 1.3 * inch, 0.4 * inch, 2.9 * inch]
    ))
    story.append(Spacer(1, 16))

    # ── Recent Mega-Rounds ──
    story.append(Paragraph('Recent Major Funding Rounds', s['h1']))
    _section_rule(story)
    recent = funding_history_df.sort_values('amount_m', ascending=False).head(12)
    round_rows = []
    for _, r in recent.iterrows():
        round_rows.append([
            str(r.get('company_name', 'N/A')),
            str(r.get('round_name', 'N/A')),
            _fmt_money(r.get('amount_m')),
            str(r.get('round_date', 'N/A')),
            str(r.get('lead_investor', 'N/A'))[:35],
        ])
    story.append(_make_table(
        ['Company', 'Round', 'Amount', 'Date', 'Lead Investor'],
        round_rows,
        col_widths=[1.4 * inch, 1.1 * inch, 1.0 * inch, 0.85 * inch, 1.85 * inch]
    ))
    story.append(Spacer(1, 16))

    # ── Full Company Index ──
    story.append(Paragraph('Full Company Index', s['h1']))
    _section_rule(story)
    all_rows = []
    for _, r in startups_df.sort_values('company_name').iterrows():
        all_rows.append([
            r['company_name'], r['ai_category'],
            _fmt_money(r['funding_m']),
            _fmt_money(r.get('valuation_m')),
            str(int(r.get('founding_year', 0))) if pd.notna(r.get('founding_year')) else 'N/A',
        ])
    story.append(_make_table(
        ['Company', 'Category', 'Funding', 'Valuation', 'Founded'],
        all_rows,
        col_widths=[1.7 * inch, 1.7 * inch, 1.0 * inch, 1.0 * inch, 0.7 * inch]
    ))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    buf.seek(0)
    return buf.getvalue()