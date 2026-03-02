"""
AI Startup Market Intelligence — Interactive Dashboard
=======================================================
Author: Ramilya Bakiyeva | Portfolio Project #3

WHAT THIS APP DOES:
  Interactive dashboard for exploring the AI startup ecosystem.
  Hero element: a treemap showing every company grouped by category,
  sized by funding, with high-density metrics. Plus filtered views for
  capital efficiency, funding progression, and company deep-dives.

RUN: streamlit run streamlit_app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import os
from report_generator import generate_company_report, generate_portfolio_report, _fmt_money

# ── 1. Page Config (MUST BE FIRST) ─────────────────────────────────────
st.set_page_config(
    page_title="AI Startup Market Intelligence",
    layout="wide",
)

# ── Configuration ──────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "ai_startups.db")

BLUE   = '#2563EB'
PURPLE = '#7C3AED'
GREEN  = '#059669'
AMBER  = '#D97706'
RED    = '#DC2626'
GRAY   = '#64748B'
BG     = '#FFFFFF'
GRID   = '#E2E8F0'
TEXT   = '#1E293B'


@st.cache_data
def load_data():
    conn = sqlite3.connect(DB_PATH)
    startups = pd.read_sql("SELECT * FROM startups", conn)
    taxonomy = pd.read_sql("SELECT * FROM taxonomy", conn)
    funding  = pd.read_sql("SELECT * FROM funding_history", conn)
    investors = pd.read_sql("SELECT * FROM investors", conn)
    round_investors = pd.read_sql("SELECT * FROM round_investors", conn)
    conn.close()
    return startups, taxonomy, funding, investors, round_investors

# Pull the raw tables from SQLite
startups_raw, taxonomy, funding, investors, round_investors = load_data()

# A. TIER ENRICHMENT: Logic to find the "Top Tier" for each company
def get_priority_tier(tiers):
    t_set = set(tiers)
    if 'Tier 1 Mega-VC' in t_set: return 'Tier 1 Mega-VC'
    if 'Big Tech Strategic' in t_set: return 'Big Tech Strategic'
    if 'Growth Equity / Pre-IPO' in t_set: return 'Growth Equity / Pre-IPO'
    if 'YC-Backed / Accelerator' in t_set: return 'YC-Backed / Accelerator'
    return 'Independent / Other'

enriched_bridge = round_investors.merge(investors[['investor_name', 'investor_tier']], on='investor_name', how='left')
company_tier_map = enriched_bridge.groupby('company_name')['investor_tier'].apply(get_priority_tier).reset_index()

# B. INVESTOR LIST ENRICHMENT: Create the "Lead Backers" string for the hover card
company_investor_list = round_investors.groupby('company_name')['investor_name'].apply(
    lambda x: ', '.join(sorted(set(x)))
).reset_index()
company_investor_list.columns = ['company_name', 'all_investors']

# C. FINAL MERGE: Combine everything into one 'startups' dataframe
# We start with the raw data and add the Tiers and the Investor Lists
startups = startups_raw.merge(company_tier_map, on='company_name', how='left')
startups = startups.merge(company_investor_list, on='company_name', how='left')

# D. SAFETY CLEANUP: Handle missing data for bootstrapped companies
startups['investor_tier'] = startups['investor_tier'].fillna('Unknown / Bootstrapped')
startups['all_investors'] = startups['all_investors'].fillna('Direct / Private')

# ── 4. Header & Global Control Panel ──────────────────────────────────
st.title("AI Startup Market Intelligence")
st.markdown("Executive Summary: 48 entities · $78B+ total funding · 19 AI categories | *Data as of Feb 2026, updated monthly*")
st.markdown("---")

st.markdown("### Market Filters")
f_col1, f_col2, f_col3, f_col4 = st.columns(4)

with f_col1:
    # UPGRADE: Changed from Multiselect to a clean Selectbox
    all_categories = ["All Categories"] + sorted(startups['ai_category'].unique().tolist())
    selected_category = st.selectbox("Category Segment", options=all_categories, index=0)

with f_col2:
    all_tiers = ["All Tiers"] + sorted(startups['investor_tier'].unique().tolist())
    if "Unknown / Bootstrapped" in all_tiers:
        all_tiers.remove("Unknown / Bootstrapped")
        all_tiers.append("Unknown / Bootstrapped")
    selected_tier = st.selectbox("Investor Pedigree", options=all_tiers, index=0)

with f_col3:
    yc_filter = st.selectbox("Accelerator Status", options=["All", "YC-Backed", "Non-YC"], index=0)

with f_col4:
    max_f = int(startups['funding_m'].max())
    funding_range = st.slider("Funding Range ($M)", min_value=0, max_value=max_f, value=(0, max_f))

# ── 5. Global Filtering Logic ─────────────────────────────────────────
# Start with a full copy
df = startups.copy()

# Apply Category Filter
if selected_category != "All Categories":
    df = df[df['ai_category'] == selected_category]

# Apply Tier Filter
if selected_tier != "All Tiers":
    df = df[df['investor_tier'] == selected_tier]

# Apply Accelerator Filter
if yc_filter == "YC-Backed":
    df = df[df['yc_backed'] == 1]
elif yc_filter == "Non-YC":
    df = df[df['yc_backed'] == 0]

# Apply Funding Range
df = df[
    (df['funding_m'] >= funding_range[0]) & 
    (df['funding_m'] <= funding_range[1])
]

st.markdown("<br>", unsafe_allow_html=True)

# ── Custom UI: Enterprise Tab Tiles ───────────────────────────────────
st.markdown("""
<style>
    /* Expand the tab list to full width and add a gap between tiles */
    div[data-testid="stTabs"] > div[data-baseweb="tab-list"] {
        display: flex;
        width: 100%;
        gap: 12px;
        border-bottom: none; /* Remove the default Streamlit line */
    }
    
    /* Style individual tabs as large, clickable tiles */
    div[data-testid="stTabs"] button[role="tab"] {
        flex: 1; /* This makes them stretch evenly across the screen! */
        background-color: #F8FAFC; /* Light gray background */
        border: 1px solid #E2E8F0;
        border-radius: 8px; /* Rounded corners */
        padding: 16px 10px; /* Taller height */
        font-size: 18px;
        font-weight: 600;
        color: #64748B;
        transition: all 0.2s ease;
    }
    
    /* Active Tab Styling (The "Selected Tile" look) */
    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        background-color: #2563EB; /* Deep Blue */
        color: white;
        border: 1px solid #2563EB;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2); /* Soft shadow */
    }
    
    /* Hover effect for unselected tabs */
    div[data-testid="stTabs"] button[role="tab"]:hover {
        background-color: #EFF6FF;
        color: #2563EB;
        border-color: #BFDBFE;
    }
    
    /* Hover effect for selected tab */
    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"]:hover {
        background-color: #1D4ED8;
        color: white;
    }
    
    /* Hide the default tiny blue underline that Streamlit uses */
    div[data-testid="stTabs"] div[data-baseweb="tab-highlight"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# ── 7. Analytical Views (Tabs) ────────────────────────────────────────
tab_map, tab_eff, tab_investor, tab_explore, tab_reports = st.tabs([
    "Market Landscape", 
    "Capital Efficiency", 
    "Investor Intelligence", 
    "Entity Deep Dive",
    "Reports"
])
# ══════════════════════════════════════════════════════════════════════
# TAB: ECOSYSTEM MAP (Treemap)
# ══════════════════════════════════════════════════════════════════════
with tab_map:
    st.markdown("#### Market Taxonomy & Capital Distribution")
    st.markdown("<span style='color:#64748B; font-size: 16px;'>Strategic view of the AI landscape. Size indicates total capital raised; colors denote efficiency.</span>", unsafe_allow_html=True)
    st.markdown("---")

    tree_df = df.copy()
    # 1. Create Efficiency Tiers for Coloring
    def get_efficiency_color(row):
        if pd.isna(row['arr_m']) or row['funding_m'] == 0:
            return "Unknown/Bootstrapped"
        ratio = row['arr_m'] / row['funding_m']
        if ratio >= 1.0: return "High Efficiency (>1.0x)"
        if ratio >= 0.5: return "Efficient (0.5x - 1.0x)"
        if ratio >= 0.1: return "Growth Mode (0.1x - 0.5x)"
        return "Capital Intensive (<0.1x)"

    tree_df['eff_tier'] = tree_df.apply(get_efficiency_color, axis=1)

    # Professional Financial Palette
    EFFICIENCY_COLORS = {
        "High Efficiency (>1.0x)": "#059669",
        "Efficient (0.5x - 1.0x)": "#0EA5E9",
        "Growth Mode (0.1x - 0.5x)": "#6366F1",
        "Capital Intensive (<0.1x)": "#64748B",
        "Unknown/Bootstrapped": "#94A3B8"
    }

    # 2. Enhanced Hover (Removed the <div> wrapper, kept the HTML formatting)
    def make_hover(row):
        multiple = "N/A"
        if pd.notna(row['valuation_m']) and pd.notna(row['arr_m']) and row['arr_m'] > 0:
            multiple = f"{(row['valuation_m']/row['arr_m']):.1f}x"
        
        # Determine status string
        accel_status = "YC-Backed" if row['yc_backed'] == 1 else "Non-YC"

        return (
            f"<span style='font-size:16px; font-weight:bold; color:white;'>{row['company_name']}</span><br>"
            f"<span style='color:#94A3B8; font-size:12px;'>{row['ai_category']} | {accel_status}</span><br><br>"
            f"<b style='color:#38BDF8;'>Core Thesis:</b><br>"
            f"<span style='color:#E2E8F0;'>{row['use_case']}</span><br><br>"
            f"<b style='color:#38BDF8;'>Key Metrics:</b><br>"
            f"<span style='color:#E2E8F0;'>• Total Funding: ${row['funding_m']:,.0f}M</span><br>"
            f"<span style='color:#E2E8F0;'>• Valuation: ${row['valuation_m']:,.0f}M ({multiple} ARR)</span><br>"
            f"<span style='color:#E2E8F0;'>• Efficiency Tier: {row['eff_tier']}</span><br><br>"
            f"<b style='color:#38BDF8;'>Lead Backers:</b><br>"
            f"<span style='color:#E2E8F0;'>{row['all_investors']}</span>"
        )

    tree_df['hover_html'] = tree_df.apply(make_hover, axis=1)

    # 3. Create a Dictionary for Tile Text to prevent the mismatch bug
    def make_tile_text(row):
        label = f"<span style='font-weight:700; font-size:14px;'>{row['company_name']}</span>"
        funding = f"${row['funding_m']:,.0f}M"
        arr = f"${row['arr_m']:,.0f}M ARR" if pd.notna(row['arr_m']) else "Undisclosed"
        return f"{label}<br><span style='font-size:11px; opacity:0.9;'>Raised: {funding}<br>{arr}</span>"

    tile_dict = {row['company_name']: make_tile_text(row) for _, row in tree_df.iterrows()}

    # 4. Initialize the Figure
    fig_tree = px.treemap(
        tree_df,
        path=[px.Constant("All Categories"), 'ai_category', 'company_name'],
        values='funding_m',
        color='eff_tier',
        color_discrete_map=EFFICIENCY_COLORS,
        custom_data=['hover_html']
    )

    # 5. FIX THE BUG: Map the text perfectly to Plotly's generated layout structure
    aligned_text = []
    for label, val in zip(fig_tree.data[0].labels, fig_tree.data[0].values):
        if label in tile_dict:
            # If it is a company, use our highly detailed ARR string
            aligned_text.append(tile_dict[label])
        else:
            # If it is a Category Parent Node, cleanly display the aggregate funding
            aligned_text.append(f"<span style='font-weight:700; font-size:16px;'>{label}</span><br><span style='font-size:12px; opacity:0.9;'>Total Raised: ${val:,.0f}M</span>")

    # 6. Apply traces with native Hover styling
    fig_tree.update_traces(
        root_color="#F1F5F9",
        hovertemplate='%{customdata[0]}<extra></extra>',
        text=aligned_text,            # Using our perfectly aligned array
        textinfo='text',
        texttemplate='%{text}',
        marker=dict(cornerradius=3, line=dict(width=2, color='#FFFFFF')),
        # This properly styles the background without causing <div> clipping errors
        hoverlabel=dict(bgcolor="#0F172A", bordercolor="#38BDF8", font_color="white", font_family="Inter")
    )

    fig_tree.update_layout(
        height=750,
        margin=dict(t=20, l=10, r=10, b=10),
        font=dict(family="Inter, sans-serif"),
        paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=None)
    )

    st.plotly_chart(fig_tree, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════
# TAB: CAPITAL EFFICIENCY
# ══════════════════════════════════════════════════════════════════════
with tab_eff:
    st.markdown("#### ARR vs. Capital Deployed")
    st.markdown("<span style='color:#64748B; font-size: 16px;'>Logarithmic scale. Assessing which entities generate the most revenue per dollar raised.</span>", unsafe_allow_html=True)
    st.markdown("---")

    scatter_df = df[
        (df['arr_m'].notna()) &
        (df['funding_m'].notna()) &
        (df['funding_m'] > 0)
    ].copy()

    if len(scatter_df) > 0:
        scatter_df['efficiency'] = (scatter_df['arr_m'] / scatter_df['funding_m']).round(2)
        scatter_df['eff_tier'] = scatter_df['efficiency'].apply(
            lambda x: 'High Efficiency (≥1.0x)' if x >= 1.0
            else 'Standard (0.5–1.0x)' if x >= 0.5
            else 'Capital Intensive (<0.5x)')

        eff_colors = {
            'High Efficiency (≥1.0x)': GREEN,
            'Standard (0.5–1.0x)': BLUE,
            'Capital Intensive (<0.5x)': AMBER,
        }

        fig_sc = px.scatter(
            scatter_df,
            x='funding_m', y='arr_m',
            color='eff_tier',
            color_discrete_map=eff_colors,
            text='company_name',
            hover_name='company_name', # <-- 1. ADDED: Puts the company name in bold at the top of the tooltip
            hover_data={
                'ai_category': True,
                'efficiency': ':.2f',
                'company_age': True,
                'funding_m': ':,.0f',
                'arr_m': ':,.0f',
                'eff_tier': False,
                'company_name': False,
            },
            labels={
                'funding_m': 'Total Funding ($M)',
                'arr_m': 'Annual Recurring Revenue (ARR) ($M)',
                'eff_tier': 'Efficiency Segment',
                'ai_category': 'Category',
                'efficiency': 'Efficiency Ratio',
                'company_age': 'Operating History (Yrs)',
            },
            log_x=True, log_y=True,
        )

        fig_sc.update_traces(
            textposition='top center', textfont_size=10,
            marker=dict(size=12, line=dict(width=1, color='white')),
        )

        # 1:1 Parity Line
        fig_sc.add_trace(go.Scatter(
            x=[5, 30000], y=[5, 30000],
            mode='lines',
            line=dict(dash='dash', color='#94A3B8', width=1.5),
            name='1:1 Parity (ARR = Funding)',
            hoverinfo='skip',
        ))

        fig_sc.update_layout(
            plot_bgcolor=BG, paper_bgcolor=BG,
            font=dict(size=12, color=TEXT),
            xaxis=dict(gridcolor=GRID),
            yaxis=dict(gridcolor=GRID),
            height=550,
            legend=dict(orientation='h', yanchor='bottom', y=-0.2, xanchor='center', x=0.5),
            margin=dict(t=20, b=100),
            # 2. ADDED: Forces the tooltip to match your Enterprise CSS (white background, professional font)
            hoverlabel=dict(
                bgcolor="#F8FAFC",
                bordercolor="#E2E8F0",
                font_size=14,
                font_family="Inter, sans-serif" 
            )
        )
        st.plotly_chart(fig_sc, use_container_width=True)

        st.subheader("Efficiency Index")
        rank_df = (scatter_df[['company_name', 'ai_category', 'arr_m',
                               'funding_m', 'efficiency', 'company_age']]
                   .sort_values('efficiency', ascending=False)
                   .rename(columns={
                       'company_name': 'Company',
                       'ai_category': 'Category',
                       'arr_m': 'ARR ($M)',
                       'funding_m': 'Funding ($M)',
                       'efficiency': 'Ratio (ARR/Funding)',
                       'company_age': 'Age (Yrs)',
                   }))
        st.dataframe(rank_df, use_container_width=True, hide_index=True)
    else:
        st.info("Insufficient data points containing both ARR and funding metrics in the current selection.")

# ══════════════════════════════════════════════════════════════════════
# TAB: INVESTOR INTELLIGENCE (Improved)
# ══════════════════════════════════════════════════════════════════════

with tab_investor:
    st.markdown("#### Investor Intelligence")
    st.markdown("<span style='color:#64748B; font-size: 16px;'>Strategic view of who funds the AI ecosystem — tier benchmarks, portfolio analysis, and co-investment networks.</span>", unsafe_allow_html=True)
    st.markdown("---")

    # ── SECTION 1: TIER OVERVIEW (always visible) ──────────────────────

    # Build tier-level stats from bridge table
    tier_bridge = round_investors.merge(
        investors[['investor_name', 'investor_tier']], on='investor_name', how='left'
    )
    tier_bridge = tier_bridge.merge(
        startups[['company_name', 'funding_m', 'valuation_m', 'arr_m']], on='company_name', how='left'
    )

    # Deduplicate: count each company once per tier (not once per round)
    tier_companies = tier_bridge.drop_duplicates(subset=['investor_tier', 'company_name'])

    tier_summary = tier_companies.groupby('investor_tier').agg(
        companies=('company_name', 'nunique'),
        investors=('investor_name', 'nunique'),
        total_funding=('funding_m', 'sum'),
        avg_valuation=('valuation_m', 'mean'),
    ).sort_values('total_funding', ascending=False).reset_index()

    # Tier KPI cards
    st.markdown("**Market Overview by Investor Tier**")
    tier_cols = st.columns(len(tier_summary) if len(tier_summary) <= 5 else 5)

    for i, (_, row) in enumerate(tier_summary.head(5).iterrows()):
        with tier_cols[i]:
            funding_str = (f"${row['total_funding']/1000:,.1f}B"
                          if row['total_funding'] >= 1000
                          else f"${row['total_funding']:,.0f}M")
            st.metric(row['investor_tier'], funding_str,
                     delta=f"{int(row['companies'])} companies · {int(row['investors'])} firms")

    st.markdown("")

    # Most active investors — horizontal bar
    portfolio_counts = (round_investors
                       .drop_duplicates(subset=['investor_name', 'company_name'])
                       .groupby('investor_name')['company_name']
                       .nunique()
                       .sort_values(ascending=False)
                       .head(15)
                       .reset_index())
    portfolio_counts.columns = ['Investor', 'Companies']

    # Add tier for color
    portfolio_counts = portfolio_counts.merge(
        investors[['investor_name', 'investor_tier']].rename(columns={'investor_name': 'Investor'}),
        on='Investor', how='left'
    )

    TIER_COLORS = {
        'Tier 1 Mega-VC': BLUE,
        'Big Tech Strategic': PURPLE,
        'Growth Equity': AMBER,
        'Accelerator': GREEN,
        'Angel / Individual': GRAY,
    }

    fig_active = px.bar(
        portfolio_counts.sort_values('Companies', ascending=True),
        x='Companies', y='Investor',
        orientation='h',
        color='investor_tier',
        color_discrete_map=TIER_COLORS,
        labels={'investor_tier': 'Tier', 'Companies': 'Portfolio Companies'},
    )
    fig_active.update_layout(
        title='Most Active AI Investors (by Portfolio Breadth)',
        height=max(350, len(portfolio_counts) * 30),
        margin=dict(t=40, b=20, l=200, r=20),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=True, gridcolor=GRID, title='', dtick=1),
        yaxis=dict(title=''),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, title=None),
        font=dict(size=12, color=TEXT),
    )
    st.plotly_chart(fig_active, use_container_width=True)

    st.markdown("---")

    # ── SECTION 2: INSTITUTION DEEP DIVE ───────────────────────────────

    st.markdown("**Institution Deep Dive**")

    filter_col1, filter_col2 = st.columns([1, 2])

    with filter_col1:
        available_tiers = ["All Tiers"] + sorted(investors['investor_tier'].unique().tolist())
        selected_tier_ui = st.selectbox("Filter by Tier", options=available_tiers)

    with filter_col2:
        if selected_tier_ui == "All Tiers":
            valid_investors = investors
        else:
            valid_investors = investors[investors['investor_tier'] == selected_tier_ui]

        active_investors_list = sorted(valid_investors['investor_name'].unique().tolist())

        if not active_investors_list:
            st.warning("No institutions found for the selected tier.")
            selected_vc = None
        else:
            selected_vc = st.selectbox("Select Institution", options=active_investors_list)

    if selected_vc:
        st.markdown("---")

        # Get VC data
        vc_portfolio_names = round_investors[
            round_investors['investor_name'] == selected_vc
        ]['company_name'].unique()
        vc_df = startups[startups['company_name'].isin(vc_portfolio_names)].copy()
        vc_info = investors[investors['investor_name'] == selected_vc].iloc[0]

        # Header + GTM signal
        st.markdown(f"### {selected_vc}")
        st.markdown(f"**{vc_info['investor_tier']}** · {vc_info['typical_stage']}")
        st.info(f"**GTM Signal:** {vc_info['gtm_signal']}")

        # KPI row
        v1, v2, v3, v4 = st.columns(4)

        v1.metric("Portfolio Companies", len(vc_df))

        total_f_vc = vc_df['funding_m'].sum()
        v2.metric("Total Capital Deployed",
                 f"${total_f_vc/1000:,.1f}B" if total_f_vc >= 1000 else f"${total_f_vc:,.0f}M")

        # Fix: avoid NaN in efficiency calc
        eff_df = vc_df[(vc_df['arr_m'].notna()) & (vc_df['funding_m'] > 0)]
        if len(eff_df) > 0:
            avg_eff = (eff_df['arr_m'] / eff_df['funding_m']).mean()
            v3.metric("Avg Capital Efficiency", f"{avg_eff:.2f}x")
        else:
            v3.metric("Avg Capital Efficiency", "No ARR data")

        total_val = vc_df['valuation_m'].sum()
        v4.metric("Portfolio Valuation",
                 f"${total_val/1000:,.1f}B" if pd.notna(total_val) and total_val >= 1000
                 else f"${total_val:,.0f}M" if pd.notna(total_val)
                 else "N/A")

        st.markdown("")

        # ── Two-column layout: Scatter + Table ─────────────────────────
        chart_col, table_col = st.columns([1.2, 1])

        with chart_col:
            st.markdown("**Portfolio Map** — Funding vs. Valuation")

            plot_df = vc_df[(vc_df['funding_m'] > 0) & (vc_df['valuation_m'].notna())].copy()

            if len(plot_df) > 0:
                # Size by ARR (or fixed if no ARR)
                plot_df['bubble_size'] = plot_df['arr_m'].fillna(10).clip(lower=10)

                fig_portfolio = px.scatter(
                    plot_df,
                    x='funding_m', y='valuation_m',
                    size='bubble_size',
                    text='company_name',
                    color='ai_category',
                    hover_data={
                        'funding_m': ':,.0f',
                        'valuation_m': ':,.0f',
                        'arr_m': ':,.0f',
                        'ai_category': True,
                        'bubble_size': False,
                        'company_name': False,
                    },
                    labels={
                        'funding_m': 'Total Funding ($M)',
                        'valuation_m': 'Valuation ($M)',
                        'arr_m': 'ARR ($M)',
                        'ai_category': 'Category',
                    },
                    color_discrete_sequence=px.colors.qualitative.Set2,
                )

                fig_portfolio.update_traces(
                    textposition='top center', textfont_size=10,
                )
                fig_portfolio.update_layout(
                    height=380,
                    margin=dict(t=10, b=40, l=60, r=20),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(gridcolor=GRID, title_font_size=11),
                    yaxis=dict(gridcolor=GRID, title_font_size=11),
                    showlegend=False,
                    font=dict(size=11, color=TEXT),
                )
                st.plotly_chart(fig_portfolio, use_container_width=True)
            else:
                st.caption("Insufficient valuation data for scatter plot.")

        with table_col:
            st.markdown("**Portfolio Entities**")

            display_df = (vc_df[['company_name', 'ai_category', 'funding_m',
                                 'valuation_m', 'arr_m', 'growth_pct']]
                         .sort_values('funding_m', ascending=False))

            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "company_name": "Entity",
                    "ai_category": "Category",
                    "funding_m": st.column_config.NumberColumn("Funding ($M)", format="$%d"),
                    "valuation_m": st.column_config.NumberColumn("Valuation ($M)", format="$%d"),
                    "arr_m": st.column_config.NumberColumn("ARR ($M)", format="$%d"),
                    "growth_pct": st.column_config.NumberColumn("Growth (%)", format="%d"),
                },
            )

        # ── Co-Investor Network ────────────────────────────────────────
        st.markdown("---")
        st.markdown("**Co-Investment Network** — Who invests alongside this firm?")
        st.caption("Firms that have co-invested in the same companies. Shared deal flow signals aligned thesis and potential co-selling opportunities.")

        # Find all investors who share portfolio companies with selected_vc
        vc_companies = set(vc_portfolio_names)
        co_investors = (round_investors[
            (round_investors['company_name'].isin(vc_companies)) &
            (round_investors['investor_name'] != selected_vc)
        ].drop_duplicates(subset=['investor_name', 'company_name']))

        if len(co_investors) > 0:
            co_summary = (co_investors
                         .groupby('investor_name')
                         .agg(
                             shared_companies=('company_name', 'nunique'),
                             companies_list=('company_name', lambda x: ', '.join(sorted(set(x)))),
                         )
                         .sort_values('shared_companies', ascending=False)
                         .reset_index())

            # Add tier info
            co_summary = co_summary.merge(
                investors[['investor_name', 'investor_tier']],
                on='investor_name', how='left'
            )
            co_summary['investor_tier'] = co_summary['investor_tier'].fillna('Unknown')

            # Display as styled table
            co_display = co_summary.rename(columns={
                'investor_name': 'Co-Investor',
                'investor_tier': 'Tier',
                'shared_companies': 'Shared Companies',
                'companies_list': 'Portfolio Overlap',
            })

            st.dataframe(
                co_display,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("No co-investment data available for this institution.")

        # ── Funding Round Detail ───────────────────────────────────────
        # Show specific rounds this VC participated in
        vc_rounds = round_investors[round_investors['investor_name'] == selected_vc].copy()

        if len(vc_rounds) > 0 and 'round_id' in vc_rounds.columns:
            # Merge with funding_history for full details
            from sqlite3 import connect
            conn = connect(DB_PATH)
            fh = pd.read_sql("SELECT * FROM funding_history", conn)
            conn.close()

            vc_round_detail = vc_rounds.merge(
                fh[['round_id', 'amount_m', 'round_date', 'post_money_m']],
                on='round_id', how='left'
            )

            # Only show if we have actual round data (not just "Latest (Extracted)")
            detailed = vc_round_detail[vc_round_detail['round_id'].notna()]
            if len(detailed) > 0:
                st.markdown("---")
                st.markdown("**Funding Round Participation**")

                rounds_display = (detailed[['company_name', 'round_name', 'round_date',
                                           'amount_m', 'post_money_m']]
                                 .sort_values('round_date', ascending=False)
                                 .rename(columns={
                                     'company_name': 'Company',
                                     'round_name': 'Round',
                                     'round_date': 'Date',
                                     'amount_m': 'Amount ($M)',
                                     'post_money_m': 'Post-Money ($M)',
                                 }))

                st.dataframe(rounds_display, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════
# TAB: ENTITY DEEP DIVE (Improved)
# ══════════════════════════════════════════════════════════════════════

with tab_explore:
    st.markdown("#### Entity Deep Dive")
    st.markdown("<span style='color:#64748B; font-size: 16px;'>Sales-ready intelligence brief. Select an account to generate a strategic profile with investor pedigree, valuation benchmarking, and competitive positioning.</span>", unsafe_allow_html=True)
    st.markdown("---")

    company_list = sorted(df['company_name'].tolist())
    if len(company_list) == 0:
        st.info("No matching entities found under current parameters.")
    else:
        selected = st.selectbox("Select Target Account", options=company_list)

        if selected:
            c = df[df['company_name'] == selected].iloc[0]
            tax_row = taxonomy[taxonomy['ai_category'] == c['ai_category']]

            # ── HEADER: Company + Context Line ─────────────────────────
            # Get investor tier for this company
            company_tier = c.get('investor_tier', 'Unknown')
            accel_status = "YC-Backed" if c['yc_backed'] == 1 else "Non-YC"

            st.markdown(f"### {c['company_name']}")
            st.markdown(
                f"**{c['ai_category']}** · Founded {int(c['founding_year'])} "
                f"({int(c['company_age'])}y) · {accel_status} · "
                f"Investor Pedigree: **{company_tier}** · GTM: {c['pricing_model']}"
            )

            # ── 1. KPI RIBBON: Unified Container ───────────────────────
            with st.container(border=True):
                m1, m2, m3, m4, m5 = st.columns(5)

                with m1:
                    if c['funding_m'] > 0:
                        st.metric("Total Funding", f"${c['funding_m']/1000:,.1f}B" if c['funding_m'] >= 1000 else f"${c['funding_m']:,.0f}M")
                    else:
                        st.metric("Total Funding", "Bootstrapped")

                with m2:
                    st.metric("Valuation", f"${c['valuation_m']/1000:,.1f}B" if pd.notna(c['valuation_m']) and c['valuation_m'] >= 1000 else f"${c['valuation_m']:,.0f}M" if pd.notna(c['valuation_m']) else "Undisclosed")

                with m3:
                    st.metric("Reported ARR", f"${c['arr_m']:,.0f}M" if pd.notna(c['arr_m']) else "Undisclosed")

                with m4:
                    if pd.notna(c['valuation_m']) and pd.notna(c['arr_m']) and c['arr_m'] > 0:
                        this_multiple = c['valuation_m'] / c['arr_m']
                        
                        cat_peers_mult = df[(df['ai_category'] == c['ai_category']) & (df['valuation_m'].notna()) & (df['arr_m'].notna()) & (df['arr_m'] > 0)].copy()
                        cat_peers_mult['_mult'] = cat_peers_mult['valuation_m'] / cat_peers_mult['arr_m']
                        cat_median = cat_peers_mult['_mult'].median()

                        delta = this_multiple - cat_median
                        st.metric("Implied Multiple", f"{this_multiple:.1f}x", delta=f"{delta:+.1f}x vs category median")
                    elif pd.notna(c['growth_pct']):
                        st.metric("YoY Growth", f"{c['growth_pct']:,.0f}%")
                    else:
                        st.metric("Implied Multiple", "N/A")

                with m5:
                    if pd.notna(c['growth_pct']):
                        st.metric("Growth Velocity", f"{c['growth_pct']:,.0f}%")
                    elif pd.notna(c['growth_raw']):
                        # Replaces the broken truncated text with a clean label
                        st.metric("Growth Velocity", "Qualitative")
                    else:
                        st.metric("Growth Velocity", "Undisclosed")

            # ── 2. CORE VALUE PROPOSITION ──────────────────────────────
            with st.container(border=True):
                # Core Value Proposition
                st.markdown(f"**Core Value Proposition:** {c['use_case']}")
                if pd.notna(c['roi_claim']):
                    st.markdown(f"**Market ROI Claim:** {c['roi_claim']}")
                
                st.markdown("---")

                # GTM Tactical Brief
                st.markdown("#### GTM Tactical Brief")
                st.caption("Pre-Meeting Account Intelligence & Positioning")
                
                if len(tax_row) > 0:
                    t = tax_row.iloc[0]
                    st.markdown("**The Hook:**")
                    st.markdown(f"<span style='color:#334155;'>Pitch focused on: *{t['roi_drivers']}*</span>", unsafe_allow_html=True)
                    
                    st.markdown("**Target ICP:**")
                    st.markdown(f"<span style='color:#334155;'>{t['target_industries']}</span>", unsafe_allow_html=True)

                cat_peers_all = df[df['ai_category'] == c['ai_category']]
                bigger_peers = cat_peers_all[(cat_peers_all['company_name'] != selected) & (cat_peers_all['funding_m'] > c['funding_m'])].sort_values('funding_m', ascending=False)
                smaller_peers = cat_peers_all[(cat_peers_all['company_name'] != selected) & (cat_peers_all['funding_m'] < c['funding_m'])].sort_values('funding_m', ascending=False)

                st.markdown("**Competitive Peer Play:**")
                if len(bigger_peers) > 0:
                    top = bigger_peers.iloc[0]
                    st.warning(f"Scale Play: {top['company_name']} has raised ${top['funding_m']:,.0f}M. Use this to frame a 'competitive parity & infrastructure scale' conversation.")
                elif len(smaller_peers) > 0:
                    st.success("Leader Play: This entity is leading category funding. Position your solution as the enterprise standard for market leaders.")
                else:
                    st.info("Category Pioneer: No direct funding peers identified in the current view. Focus the conversation on greenfield market capture and category creation.")

                st.markdown("---")

                # Capital Infrastructure
                st.markdown("#### Capital Infrastructure")
                st.caption("Lead Backers & Strategic Pedigree")

                company_backers = round_investors[
                    round_investors['company_name'] == selected
                ].merge(
                    investors[['investor_name', 'investor_tier', 'gtm_signal']],
                    on='investor_name', how='left'
                ).drop_duplicates(subset='investor_name')

                if len(company_backers) > 0:
                    html_grid = '<div style="display: flex; flex-wrap: wrap; gap: 15px;">'
                    
                    for _, backer in company_backers.iterrows():
                        tier = backer['investor_tier'] if pd.notna(backer['investor_tier']) else 'Unknown'
                        gtm = backer['gtm_signal'] if pd.notna(backer['gtm_signal']) else 'No distinct GTM signal tracked.'
                        
                        # Note: Indentation intentionally removed below to prevent markdown code block rendering
                        html_grid += f"""<div style="flex: 1 1 250px; background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 16px;">
<div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
<span style="font-weight: 600; font-size: 15px; color: #0F172A; display: block;">{backer['investor_name']}</span>
<span style="background-color: #DBEAFE; color: #1E40AF; padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: 500; white-space: nowrap;">{tier}</span>
</div>
<div style="font-size: 13px; color: #64748B; line-height: 1.4;">{gtm}</div>
</div>"""
                    
                    html_grid += '</div>'
                    st.markdown(html_grid, unsafe_allow_html=True)
                else:
                    st.info("No detailed investor infrastructure available.")

            # ── COMPETITIVE LANDSCAPE: Peer Scatter ────────────────────
            st.markdown("---")
            st.markdown(f"**Competitive Landscape** — {c['ai_category']} ({len(cat_peers_all)} entities)")

            scatter_col, table_col = st.columns([1.3, 1])

            with scatter_col:
                peer_plot = cat_peers_all[
                    (cat_peers_all['funding_m'] > 0) &
                    (cat_peers_all['valuation_m'].notna())
                ].copy()

                if len(peer_plot) >= 2:
                    peer_plot['is_target'] = (peer_plot['company_name'] == selected)
                    peer_plot['marker_color'] = peer_plot['is_target'].map(
                        {True: 'Target', False: 'Peer'}
                    )
                    peer_plot['bubble_size'] = peer_plot['arr_m'].fillna(10).clip(lower=10)

                    fig_peers = px.scatter(
                        peer_plot,
                        x='funding_m', y='valuation_m',
                        size='bubble_size',
                        color='marker_color',
                        color_discrete_map={'Target': '#DC2626', 'Peer': '#94A3B8'},
                        text='company_name',
                        hover_data={
                            'funding_m': ':,.0f',
                            'valuation_m': ':,.0f',
                            'arr_m': ':,.0f',
                            'bubble_size': False,
                            'is_target': False,
                            'marker_color': False,
                            'company_name': False,
                        },
                        labels={
                            'funding_m': 'Total Funding ($M)',
                            'valuation_m': 'Valuation ($M)',
                            'arr_m': 'ARR ($M)',
                            'marker_color': '',
                        },
                    )
                    fig_peers.update_traces(textposition='top center', textfont_size=10)
                    fig_peers.update_layout(
                        height=350,
                        margin=dict(t=10, b=40, l=60, r=20),
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        xaxis=dict(gridcolor=GRID, title_font_size=11),
                        yaxis=dict(gridcolor=GRID, title_font_size=11),
                        showlegend=True,
                        legend=dict(orientation='h', yanchor='bottom', y=1.02,
                                   xanchor='right', x=1, title=None),
                        font=dict(size=11, color=TEXT),
                    )
                    st.plotly_chart(fig_peers, use_container_width=True)
                else:
                    st.caption("Insufficient peer data for scatter plot.")

            with table_col:
                peer_table = (cat_peers_all[['company_name', 'funding_m', 'valuation_m',
                                             'arr_m', 'growth_pct']]
                             .sort_values('funding_m', ascending=False))

                st.dataframe(
                    peer_table,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "company_name": "Entity",
                        "funding_m": st.column_config.NumberColumn("Funding ($M)", format="$%d"),
                        "valuation_m": st.column_config.NumberColumn("Valuation ($M)", format="$%d"),
                        "arr_m": st.column_config.NumberColumn("ARR ($M)", format="$%d"),
                        "growth_pct": st.column_config.NumberColumn("Growth (%)", format="%d"),
                    },
                )

            # ── CATEGORY CONTEXT (expandable) ──────────────────────────
            if len(tax_row) > 0:
                t = tax_row.iloc[0]
                with st.expander(f"Category Reference — {c['ai_category']}"):
                    tx1, tx2, tx3 = st.columns(3)
                    with tx1:
                        st.markdown(f"**Target Industries**\n\n{t['target_industries']}")
                    with tx2:
                        st.markdown(f"**ROI Drivers**\n\n{t['roi_drivers']}")
                    with tx3:
                        st.markdown(f"**Common Use Cases**\n\n{t['common_use_cases']}")

            # ── LATEST ROUND + GROWTH CONTEXT (expandable) ─────────────
            has_round_info = pd.notna(c['latest_round']) or pd.notna(c['growth_raw'])
            if has_round_info:
                with st.expander("Funding & Growth Context"):
                    if pd.notna(c['latest_round']):
                        st.markdown(f"**Latest Capital Event:** {c['latest_round']}")
                    if pd.notna(c['growth_raw']):
                        st.markdown(f"**Growth Detail:** {c['growth_raw']}")

# ══════════════════════════════════════════════════════════════════════
# TAB: REPORT GENERATOR
# Replace your existing tab_reports block with this
# ══════════════════════════════════════════════════════════════════════

with tab_reports:
    st.markdown("#### Executive Report Generator")
    st.markdown(
        "<span style='color:#64748B; font-size: 14px;'>"
        "Export high-fidelity PDF intelligence briefs for internal strategy or executive meetings."
        "</span>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # ── Mode Toggle ──
    report_mode = st.radio(
        "Report Configuration",
        ["Company Intelligence Brief", "Full Ecosystem Overview"],
        horizontal=True,
    )

    # ══════════════════════════════════════════════════════════════════
    # COMPANY BRIEF
    # ══════════════════════════════════════════════════════════════════
    if report_mode == "Company Intelligence Brief":

        col_sel, col_meta = st.columns([2, 2])

        with col_sel:
            report_company = st.selectbox(
                "Select Target Account",
                options=sorted(startups['company_name'].tolist()),
                key="report_company_select",
            )

        with col_meta:
            prepared_for = st.text_input(
                "Prepared for (optional)",
                placeholder="e.g., Board Meeting — March 2026",
            )

        if report_company:
            # ── Visual Preview Card ──
            row = startups[startups['company_name'] == report_company].iloc[0]

            with st.container(border=True):
                st.markdown(f"**Preview — {report_company}**")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Category", row.get('ai_category', 'N/A'))
                c2.metric("Funding", _fmt_money(row.get('funding_m', 0)))
                c3.metric("Valuation", _fmt_money(row.get('valuation_m')))
                c4.metric("ARR", _fmt_money(row.get('arr_m')))

                if prepared_for:
                    st.caption(f"Prepared for: {prepared_for}")

                st.markdown("")  # spacing

                if st.button("Generate PDF Report", type="primary", use_container_width=True):
                    with st.spinner(f"Building brief for {report_company}..."):
                        _conn = sqlite3.connect(DB_PATH)
                        _fh = pd.read_sql("SELECT * FROM funding_history", _conn)
                        _conn.close()

                        pdf_bytes = generate_company_report(
                            report_company, startups, taxonomy,
                            investors, round_investors, _fh,
                            prepared_for=prepared_for,
                        )

                    st.success(f"Ready — {len(pdf_bytes)/1024:.0f} KB")
                    st.download_button(
                        label=f"⬇ Download {report_company} Brief",
                        data=pdf_bytes,
                        file_name=f"{report_company.replace(' ', '_')}_Brief.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )

    # ══════════════════════════════════════════════════════════════════
    # FULL PORTFOLIO OVERVIEW
    # ══════════════════════════════════════════════════════════════════
    else:
        prepared_for_port = st.text_input(
            "Prepared for (optional)",
            placeholder="e.g., Investor Deck Review — Q1 2026",
            key="port_prepared_for",
        )

        with st.container(border=True):
            st.markdown("**Full Ecosystem Portfolio Export**")

            c1, c2, c3 = st.columns(3)
            c1.metric("Companies", len(startups))
            c2.metric("Categories", startups['ai_category'].nunique())
            c3.metric("Total Funding", _fmt_money(startups['funding_m'].sum()))

            st.caption("Includes category benchmarks, top 20 rankings, and investor landscape analysis.")
            st.markdown("")

            if st.button("Generate Market Overview", type="primary", use_container_width=True):
                with st.spinner("Processing full database..."):
                    _conn = sqlite3.connect(DB_PATH)
                    _fh = pd.read_sql("SELECT * FROM funding_history", _conn)
                    _conn.close()

                    pdf_bytes = generate_portfolio_report(
                        startups, taxonomy, investors, round_investors, _fh,
                        prepared_for=prepared_for_port,
                    )

                st.success(f"Ecosystem Report Ready — {len(pdf_bytes)/1024:.0f} KB")
                st.download_button(
                    label="⬇ Download Full Portfolio Overview",
                    data=pdf_bytes,
                    file_name="AI_Startup_Market_Map_2026.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )