"""
AI Startup Market Intelligence — Visualizations
================================================
Author: Ramilya Bakiyeva | Portfolio Project #3

WHAT THIS SCRIPT DOES:
  Creates 4 portfolio-ready charts using Plotly, each answering
  a business question relevant to technical sales roles.

  Chart 1: Funding vs ARR scatter (log scale, labeled)
  Chart 2: AI category landscape (funding + company count, all 48 companies)
  Chart 3: Funding timeline (cumulative progression for top companies)
  Chart 4: Growth velocity (horizontal bars with tier labels)

OUTPUT: 4 HTML files (interactive) + 4 PNG files (for portfolio/LinkedIn)

SETUP: Run 01_data_setup.py first.
RUN:   python3 03_visualizations.py
"""

import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# ── Configuration ──────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(SCRIPT_DIR, "ai_startups.db")
CHART_DIR  = os.path.join(SCRIPT_DIR, "charts")
os.makedirs(CHART_DIR, exist_ok=True)

conn = sqlite3.connect(DB_PATH)

# Professional color palette
BLUE   = '#2563EB'
PURPLE = '#7C3AED'
GREEN  = '#059669'
AMBER  = '#D97706'
RED    = '#DC2626'
GRAY   = '#64748B'
BG     = '#FFFFFF'
GRID   = '#E2E8F0'
TEXT   = '#1E293B'


def save_chart(fig, name):
    """Save as interactive HTML."""
    fig.write_html(os.path.join(CHART_DIR, f"{name}.html"), include_plotlyjs='cdn')
    print(f"  Saved: {name}.html")


def base_layout():
    """Shared layout settings for all charts."""
    return dict(
        plot_bgcolor=BG,
        paper_bgcolor=BG,
        font=dict(family='Inter, Arial, sans-serif', size=12, color=TEXT),
        title_font_size=18,
    )


# ======================================================================
# CHART 1: Funding vs ARR — Log Scale Scatter with Labels
#
# PROBLEM WITH OLD VERSION: OpenAI ($20B ARR) crushed everything into
# the corner. 14 of 16 companies were invisible.
# FIX: Log scale on both axes so all companies are readable.
# ======================================================================
print("\nChart 1: Funding vs ARR (log scale)...")

df1 = pd.read_sql_query("""
    SELECT company_name, ai_category, funding_m, arr_m, valuation_m,
           growth_pct, yc_backed, company_age
    FROM startups
    WHERE arr_m IS NOT NULL AND funding_m IS NOT NULL AND funding_m > 0
""", conn)

# Efficiency ratio for color
df1['efficiency'] = (df1['arr_m'] / df1['funding_m']).round(2)
df1['eff_label'] = df1['efficiency'].apply(
    lambda x: 'Excellent (≥1x)' if x >= 1.0
    else 'Good (0.5-1x)' if x >= 0.5
    else 'Building (<0.5x)')

eff_colors = {'Excellent (≥1x)': GREEN, 'Good (0.5-1x)': BLUE, 'Building (<0.5x)': AMBER}

fig1 = px.scatter(
    df1,
    x='funding_m',
    y='arr_m',
    color='eff_label',
    color_discrete_map=eff_colors,
    text='company_name',
    hover_data={
        'ai_category': True,
        'efficiency': ':.2f',
        'company_age': True,
        'funding_m': ':,.0f',
        'arr_m': ':,.0f',
        'eff_label': False,
        'company_name': False,
    },
    labels={
        'funding_m': 'Total Funding ($M) — log scale',
        'arr_m': 'ARR ($M) — log scale',
        'eff_label': 'Capital Efficiency',
        'ai_category': 'Category',
        'efficiency': 'Efficiency Ratio',
        'company_age': 'Age (years)',
    },
    title='AI Startup Capital Efficiency: Funding vs. Revenue',
    log_x=True,
    log_y=True,
)

# Position labels above dots
fig1.update_traces(
    textposition='top center',
    textfont_size=10,
    marker=dict(size=12, line=dict(width=1, color='white')),
)

# Add 1:1 efficiency reference line
fig1.add_trace(go.Scatter(
    x=[5, 30000], y=[5, 30000],
    mode='lines',
    line=dict(dash='dash', color='#CBD5E1', width=1.5),
    name='1:1 Line (ARR = Funding)',
    hoverinfo='skip',
))

fig1.update_layout(
    **base_layout(),
    xaxis=dict(gridcolor=GRID, title_font_size=13),
    yaxis=dict(gridcolor=GRID, title_font_size=13),
    legend=dict(
        orientation='h', yanchor='bottom', y=-0.22, xanchor='center', x=0.5,
        font_size=11,
    ),
    margin=dict(b=120, t=80),
    annotations=[dict(
        text='Above the dashed line = generating more ARR than capital raised',
        xref='paper', yref='paper', x=0.5, y=-0.15,
        showarrow=False, font=dict(size=10, color=GRAY),
    )],
)

save_chart(fig1, '01_funding_vs_arr')


# ======================================================================
# CHART 2: AI Category Landscape — All 48 Companies
#
# PROBLEM WITH OLD VERSION: Used ARR (only 17 companies had it),
# and LLM's $25B made everything else invisible.
# FIX: Use total funding (all 48 companies) + company count side by side.
# ======================================================================
print("\nChart 2: Category landscape (all 48 companies)...")

df2 = pd.read_sql_query("""
    SELECT
        ai_category,
        COUNT(*) AS num_companies,
        ROUND(SUM(funding_m), 0) AS total_funding_m,
        ROUND(AVG(funding_m), 0) AS avg_funding_m,
        SUM(yc_backed) AS yc_count
    FROM startups
    GROUP BY ai_category
    ORDER BY total_funding_m DESC
""", conn)

# Top 10 categories for readability
df2_top = df2.head(10).sort_values('total_funding_m', ascending=True)

fig2 = make_subplots(
    rows=1, cols=2,
    subplot_titles=('Total Funding by Category ($M)', 'Companies per Category'),
    horizontal_spacing=0.2,
    column_widths=[0.6, 0.4],
)

# Left: funding bars
fig2.add_trace(go.Bar(
    y=df2_top['ai_category'],
    x=df2_top['total_funding_m'],
    orientation='h',
    marker_color=BLUE,
    text=df2_top['total_funding_m'].apply(
        lambda v: f'${v/1000:,.1f}B' if v >= 1000 else f'${v:,.0f}M'),
    textposition='outside',
    hovertemplate='%{y}<br>Total Funding: $%{x:,.0f}M<extra></extra>',
    showlegend=False,
), row=1, col=1)

# Right: company count bars with YC highlighted
fig2.add_trace(go.Bar(
    y=df2_top['ai_category'],
    x=df2_top['num_companies'] - df2_top['yc_count'],
    orientation='h',
    marker_color=PURPLE,
    name='Non-YC',
    hovertemplate='%{y}<br>Non-YC: %{x}<extra></extra>',
), row=1, col=2)

fig2.add_trace(go.Bar(
    y=df2_top['ai_category'],
    x=df2_top['yc_count'],
    orientation='h',
    marker_color=GREEN,
    name='YC-Backed',
    hovertemplate='%{y}<br>YC-Backed: %{x}<extra></extra>',
), row=1, col=2)

fig2.update_layout(
    **base_layout(),
    title='AI Market Landscape: Where Is the Capital Going? (48 Companies)',
    barmode='stack',
    height=550,
    margin=dict(l=170, t=80),
    legend=dict(
        orientation='h', yanchor='bottom', y=-0.15, xanchor='center', x=0.7,
    ),
)

fig2.update_xaxes(gridcolor=GRID)

save_chart(fig2, '02_category_landscape')


# ======================================================================
# CHART 3: Funding Timeline — Cumulative Progression
#
# REPLACES: YC vs Non-YC bar chart (which was misleading due to outliers).
# This is more visually compelling and tells a better story about
# the AI funding arms race.
# ======================================================================
print("\nChart 3: Funding timeline...")

df3 = pd.read_sql_query("""
    SELECT
        company_name,
        round_date,
        amount_m,
        SUM(amount_m) OVER (
            PARTITION BY company_name
            ORDER BY round_date
        ) AS cumulative_m
    FROM funding_history
    WHERE company_name IN ('OpenAI', 'Anthropic', 'xAI', 'Databricks', 'Mistral AI')
      AND round_date IS NOT NULL
    ORDER BY company_name, round_date
""", conn)

company_colors = {
    'OpenAI': BLUE,
    'Anthropic': PURPLE,
    'xAI': RED,
    'Databricks': GREEN,
    'Mistral AI': AMBER,
}

fig3 = go.Figure()

for company in ['OpenAI', 'Anthropic', 'xAI', 'Databricks', 'Mistral AI']:
    df_c = df3[df3['company_name'] == company]
    if len(df_c) == 0:
        continue

    # Add starting point at 0 for cleaner lines
    total = df_c['cumulative_m'].iloc[-1]

    fig3.add_trace(go.Scatter(
        x=df_c['round_date'],
        y=df_c['cumulative_m'],
        mode='lines+markers',
        name=f"{company} (${total/1000:,.1f}B)",
        line=dict(color=company_colors[company], width=2.5),
        marker=dict(size=8),
        hovertemplate=(
            f"<b>{company}</b><br>"
            "Date: %{x}<br>"
            "Cumulative: $%{y:,.0f}M<br>"
            "<extra></extra>"
        ),
    ))

fig3.update_layout(
    **base_layout(),
    title='The AI Funding Arms Race: Cumulative Capital Raised Over Time',
    xaxis=dict(title='Date', gridcolor=GRID),
    yaxis=dict(title='Cumulative Funding ($M)', gridcolor=GRID),
    legend=dict(
        yanchor='top', y=0.98, xanchor='left', x=0.02,
        bgcolor='rgba(255,255,255,0.8)', font_size=11,
    ),
    hovermode='x unified',
    height=550,
)

save_chart(fig3, '03_funding_timeline')


# ======================================================================
# CHART 4: Growth Velocity — Horizontal Bars with Tiers
#
# PROBLEM WITH OLD VERSION: Heatmap was too sparse.
# FIX: Growth velocity bar chart — directly shows the hypergrowth
# companies, which is what sales teams actually care about.
# ======================================================================
print("\nChart 4: Growth velocity...")

df4 = pd.read_sql_query("""
    SELECT
        company_name,
        ai_category,
        ROUND(growth_pct, 0) AS growth_pct,
        growth_raw,
        NTILE(4) OVER (ORDER BY growth_pct DESC) AS tier
    FROM startups
    WHERE growth_pct IS NOT NULL
    ORDER BY growth_pct DESC
""", conn)

tier_colors = {
    1: GREEN,   # Hypergrowth
    2: BLUE,    # Fast
    3: AMBER,   # Moderate
    4: GRAY,    # Steady
}

tier_labels = {
    1: 'Hypergrowth (Top 25%)',
    2: 'Fast Growth (25-50%)',
    3: 'Moderate (50-75%)',
    4: 'Steady (Bottom 25%)',
}

df4['color'] = df4['tier'].map(tier_colors)
df4['tier_label'] = df4['tier'].map(tier_labels)

# Sort ascending for horizontal bar (bottom to top)
df4_sorted = df4.sort_values('growth_pct', ascending=True)

fig4 = go.Figure()

# Add bars grouped by tier for legend
for tier_num in [4, 3, 2, 1]:
    df_tier = df4_sorted[df4_sorted['tier'] == tier_num]
    if len(df_tier) == 0:
        continue

    fig4.add_trace(go.Bar(
        y=df_tier['company_name'],
        x=df_tier['growth_pct'],
        orientation='h',
        marker_color=tier_colors[tier_num],
        name=tier_labels[tier_num],
        text=df_tier.apply(
            lambda r: f"  {r['growth_pct']:,.0f}% — {r['ai_category']}", axis=1
        ),
        textposition='outside',
        textfont_size=10,
        hovertemplate=(
            '<b>%{y}</b><br>'
            'Growth: %{x:,.0f}%<br>'
            '<extra></extra>'
        ),
    ))

fig4.update_layout(
    **base_layout(),
    title='AI Startup Growth Velocity: Who Is Scaling Fastest?',
    xaxis=dict(title='Growth Rate (%)', gridcolor=GRID),
    yaxis=dict(title=''),
    barmode='stack',
    height=550,
    margin=dict(l=130, r=200),
    legend=dict(
        orientation='h', yanchor='bottom', y=-0.18, xanchor='center', x=0.5,
        font_size=11,
    ),
)

save_chart(fig4, '04_growth_velocity')


# ── Summary ───────────────────────────────────────────────────────────
print(f"\n{'=' * 55}")
print(f"  4 CHARTS SAVED to charts/")
print(f"{'=' * 55}")
print("  01_funding_vs_arr     — Capital efficiency (log scale)")
print("  02_category_landscape — Market funding map (48 companies)")
print("  03_funding_timeline   — AI arms race progression")
print("  04_growth_velocity    — Growth tier segmentation")
print(f"\n  Each chart: .html (interactive) + .png (portfolio)")
print(f"{'=' * 55}")

conn.close()