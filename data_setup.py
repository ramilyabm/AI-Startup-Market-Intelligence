"""
AI Startup Market Intelligence — Data Setup & Cleaning
=======================================================
Author: Ramilya Bakiyeva | Portfolio Project #3

WHAT THIS SCRIPT DOES:
  1. Loads 4 CSV files (startups, taxonomy, funding history, investors)
  2. Cleans messy financial strings → numeric values (in $M)
  3. Normalizes investor names across tables
  4. Creates a bridge table linking funding rounds to individual investors
  5. Creates a SQLite database with 5 clean tables
  6. Prints a validation report

TABLES CREATED:
  startups        — 48 companies with cleaned financials
  taxonomy        — 19 AI categories with use cases and ROI drivers
  funding_history — 48 funding rounds with sortable dates
  investors       — 31 VC/investor profiles with tier and GTM signals
  round_investors — Bridge table: one row per investor per round
                    (splits "Accel, Meta, Amazon" into 3 rows)

RUN: python3 data_setup.py
"""

import pandas as pd
import sqlite3
import re
import os


# ── FILE PATHS ─────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

STARTUPS_FILE  = os.path.join(SCRIPT_DIR, "startups.csv")
TAXONOMY_FILE  = os.path.join(SCRIPT_DIR, "taxonomy.csv")
FUNDING_FILE   = os.path.join(SCRIPT_DIR, "funding_history.csv")
INVESTORS_FILE = os.path.join(SCRIPT_DIR, "investors.csv")
DB_PATH        = os.path.join(SCRIPT_DIR, "ai_startups.db")


# ── INVESTOR NAME NORMALIZATION ────────────────────────────────────────
# Maps how names appear in funding_history → canonical name in investors.csv.
# Only needed for genuine mismatches between the two files.

INVESTOR_ALIASES = {
    'Andreessen Horowitz':  'Andreessen Horowitz (a16z)',
    'Nvidia':               'NVIDIA',
}


# ── PARSING FUNCTIONS ──────────────────────────────────────────────────

def parse_money(value):
    """
    Convert financial strings to numeric (in millions USD).
    "$1B+" → 1000.0 | "$252.8M ARR" → 252.8 | "$0 (bootstrapped)" → 0.0
    """
    if pd.isna(value):
        return None

    s = str(value).strip().replace('"', '')

    if 'bootstrapped' in s.lower():
        return 0.0
    if 'seven figures' in s.lower():
        return 1.0
    if 'eight figures' in s.lower():
        return 10.0

    match = re.search(r'\$?([\d,]+\.?\d*)\s*(B|M|K)?', s, re.IGNORECASE)
    if not match:
        return None

    num = float(match.group(1).replace(',', ''))
    suffix = (match.group(2) or '').upper()

    if suffix == 'B':
        return num * 1000
    elif suffix == 'K':
        return num / 1000
    else:
        return num


def parse_valuation(value):
    """Parse valuation, preferring ESTIMATE annotations when present."""
    if pd.isna(value):
        return None

    s = str(value).strip()

    estimate = re.search(r'ESTIMATE[:\s]*\$?([\d,]+\.?\d*)\s*(B|M)?', s, re.IGNORECASE)
    if estimate:
        num = float(estimate.group(1).replace(',', ''))
        suffix = (estimate.group(2) or '').upper()
        return num * 1000 if suffix == 'B' else num

    return parse_money(s)


def parse_growth(value):
    """
    Extract growth percentage. "+130% YoY" → 130.0 | "2.5x growth" → 150.0
    Skips ambiguous entries like "2 years to $43M ARR" → None.
    """
    if pd.isna(value):
        return None

    s = str(value).strip()

    pct = re.search(r'[+]?([\d,]+\.?\d*)%', s)
    if pct:
        return float(pct.group(1).replace(',', ''))

    mult = re.search(r'([\d.]+)x\s*(growth|in)', s, re.IGNORECASE)
    if mult:
        return (float(mult.group(1)) - 1) * 100

    return None


def parse_funding_date(value):
    """Normalize dates to YYYY-MM for sorting. "01/2015" → "2015-01"."""
    if pd.isna(value):
        return None

    s = str(value).strip()

    match = re.match(r'^(\d{2})/(\d{4})$', s)
    if match:
        return f"{match.group(2)}-{match.group(1)}"

    match = re.match(r'^(\d{4})$', s)
    if match:
        return f"{match.group(1)}-01"

    return None


def normalize_investor_name(name):
    """Apply alias map: 'Andreessen Horowitz' → 'Andreessen Horowitz (a16z)'."""
    name = name.strip()
    return INVESTOR_ALIASES.get(name, name)


# ── STEP 1: LOAD RAW DATA ─────────────────────────────────────────────
print("=" * 60)
print("AI STARTUP MARKET INTELLIGENCE — DATA SETUP")
print("=" * 60)

print("\nLoading CSV files...")
df_startups  = pd.read_csv(STARTUPS_FILE)
df_taxonomy  = pd.read_csv(TAXONOMY_FILE)
df_funding   = pd.read_csv(FUNDING_FILE)
df_investors = pd.read_csv(INVESTORS_FILE)

print(f"  Startups:   {len(df_startups)} companies")
print(f"  Taxonomy:   {len(df_taxonomy)} categories")
print(f"  Funding:    {len(df_funding)} rounds")
print(f"  Investors:  {len(df_investors)} profiles")


# ── STEP 2: CLEAN STARTUPS ────────────────────────────────────────────
print("\nCleaning startups data...")

df_startups['funding_m']   = df_startups['Total Funding Raised (USD)'].apply(parse_money)
df_startups['valuation_m'] = df_startups['Valuation (USD)'].apply(parse_valuation)
df_startups['arr_m']       = df_startups['ARR (USD)'].apply(parse_money)
df_startups['growth_pct']  = df_startups['Growth Rate / Velocity'].apply(parse_growth)
df_startups['yc_backed']   = (df_startups['YCBacked'] == 'Yes').astype(int)
df_startups['company_age'] = 2026 - df_startups['Founding Year']

startups_clean = df_startups.rename(columns={
    'Company Name':                   'company_name',
    'Founding Year':                  'founding_year',
    'AI Category':                    'ai_category',
    'Use Case / Product Description': 'use_case',
    'Pricing Model':                  'pricing_model',
    'Latest Funding Round':           'latest_round',
    'Customer ROI Claim':             'roi_claim',
    'Growth Rate / Velocity':         'growth_raw',
})[['company_name', 'founding_year', 'company_age', 'ai_category', 'use_case',
    'funding_m', 'valuation_m', 'arr_m', 'growth_pct', 'growth_raw',
    'yc_backed', 'pricing_model', 'latest_round', 'roi_claim']]


# ── STEP 3: CLEAN TAXONOMY ────────────────────────────────────────────
taxonomy_clean = df_taxonomy.rename(columns={
    'AI Category':         'ai_category',
    'Common Use Cases':    'common_use_cases',
    'Target Industries':   'target_industries',
    'Typical ROI Drivers': 'roi_drivers',
})


# ── STEP 4: CLEAN FUNDING HISTORY ─────────────────────────────────────
print("Cleaning funding history...")

funding_clean = df_funding.rename(columns={
    'Company Name':         'company_name',
    'Round':                'round_name',
    'Amount ($M)':          'amount_m',
    'Date (MM/YYYY)':       'round_date_raw',
    'Lead Investor':        'lead_investor',
    'Post-Money Valuation': 'post_money_valuation',
})

funding_clean['round_date']   = df_funding['Date (MM/YYYY)'].apply(parse_funding_date)
funding_clean['post_money_m'] = funding_clean['post_money_valuation'].apply(parse_money)
funding_clean['round_id']     = range(1, len(funding_clean) + 1)

funding_clean = funding_clean[['round_id', 'company_name', 'round_name', 'amount_m',
                                'round_date', 'round_date_raw',
                                'lead_investor', 'post_money_m']]


# ── STEP 5: CLEAN INVESTORS ───────────────────────────────────────────
print("Cleaning investors...")

# Auto-detect the GTM column name (handles slight naming variations)
gtm_col = [c for c in df_investors.columns if 'GTM' in c or 'Signal' in c][0]

investors_clean = df_investors.rename(columns={
    'Investor Name':            'investor_name',
    'Investor Cohort (Tier)':   'investor_tier',
    'Typical Investment Stage': 'typical_stage',
    gtm_col:                    'gtm_signal',
})

investors_clean = investors_clean[['investor_name', 'investor_tier',
                                    'typical_stage', 'gtm_signal']]


# ── STEP 6: BUILD ROUND_INVESTORS BRIDGE TABLE ────────────────────────
print("Building composite round → investor bridge table...")

bridge_rows = []

# Part A: Harvest investors from detailed Funding History (the Big 10)
for _, row in funding_clean.iterrows():
    if pd.isna(row['lead_investor']):
        continue

    # Split multi-investor fields: "Accel, Meta, Amazon" → 3 rows
    raw_names = [n.strip() for n in str(row['lead_investor']).split(',')]
    for raw_name in raw_names:
        if raw_name:
            canonical = normalize_investor_name(raw_name)
            bridge_rows.append({
                'round_id':      row['round_id'],
                'company_name':  row['company_name'],
                'round_name':    row['round_name'],
                'investor_name': canonical,
            })

# Part B: Harvest supplemental investors from 'latest_round' in startups_clean
# This fixes the Higgsfield / Resolve AI missing backer issue!
existing_companies = {r['company_name'] for r in bridge_rows}

for _, row in startups_clean.iterrows():
    company = row['company_name']
    
    # Only harvest if we didn't already get them in Part A
    if company not in existing_companies:
        raw_text = str(row['latest_round'])
        if "Led by" in raw_text:
            try:
                # Snip everything after "Led by" and split by commas
                investor_part = raw_text.split("Led by")[-1].strip()
                raw_names = [n.strip() for n in investor_part.split(',')]
                
                for raw_name in raw_names:
                    if raw_name:
                        canonical = normalize_investor_name(raw_name)
                        bridge_rows.append({
                            'round_id':      None, # No explicit round_id from the summary text
                            'company_name':  company,
                            'round_name':    'Latest (Extracted)',
                            'investor_name': canonical,
                        })
            except Exception as e:
                continue

bridge_df = pd.DataFrame(bridge_rows)

# Coverage check (Helps you find spelling errors)
known = set(investors_clean['investor_name'].values)
matched   = bridge_df[bridge_df['investor_name'].isin(known)]
unmatched = bridge_df[~bridge_df['investor_name'].isin(known)]


# ── STEP 7: WRITE TO SQLITE ───────────────────────────────────────────
print(f"\nWriting to SQLite: ai_startups.db")

conn = sqlite3.connect(DB_PATH)
startups_clean.to_sql('startups',        conn, if_exists='replace', index=False)
taxonomy_clean.to_sql('taxonomy',        conn, if_exists='replace', index=False)
funding_clean.to_sql('funding_history',  conn, if_exists='replace', index=False)
investors_clean.to_sql('investors',      conn, if_exists='replace', index=False)
bridge_df.to_sql('round_investors',      conn, if_exists='replace', index=False)
conn.close()

print(f"  Table 'startups'        — {len(startups_clean)} rows")
print(f"  Table 'taxonomy'        — {len(taxonomy_clean)} rows")
print(f"  Table 'funding_history' — {len(funding_clean)} rows")
print(f"  Table 'investors'       — {len(investors_clean)} rows")
print(f"  Table 'round_investors' — {len(bridge_df)} rows (bridge)")


# ── STEP 8: VALIDATION REPORT ─────────────────────────────────────────
print("\n" + "=" * 60)
print("VALIDATION REPORT")
print("=" * 60)

total = len(startups_clean)
fields = {
    'funding_m':   'Total Funding',
    'valuation_m': 'Valuation',
    'arr_m':       'ARR',
    'growth_pct':  'Growth Rate',
}

for col, label in fields.items():
    parsed = startups_clean[col].notna().sum()
    missing = total - parsed
    pct = parsed / total * 100
    status = 'OK' if pct > 80 else f'{missing} missing'
    print(f"  {label:<16} {parsed:>2}/{total}  ({pct:.0f}%)  {status}")

# Investor coverage
print(f"\n  Investors: {len(investors_clean)} profiles across {investors_clean['investor_tier'].nunique()} tiers")
for tier, count in investors_clean['investor_tier'].value_counts().items():
    print(f"    {tier:<25} {count}")

print(f"\n  Bridge table: {len(bridge_df)} links, {len(matched)} matched, {len(unmatched)} unmatched")
if len(unmatched) > 0:
    print(f"  Unmatched: {', '.join(sorted(unmatched['investor_name'].unique()))}")

# ARR data
print(f"\n  Companies WITH ARR data ({startups_clean['arr_m'].notna().sum()}):")
arr_rows = startups_clean[startups_clean['arr_m'].notna()].sort_values('arr_m', ascending=False)
for _, row in arr_rows.iterrows():
    print(f"    ${row['arr_m']:>10,.1f}M  {row['company_name']}")

# Unparsed growth
unparsed = df_startups[
    df_startups['Growth Rate / Velocity'].notna() &
    df_startups['growth_pct'].isna()
]
if len(unparsed) > 0:
    print(f"\n  Growth rates skipped — ambiguous format ({len(unparsed)}):")
    for _, row in unparsed.iterrows():
        print(f"    {row['Company Name']}: \"{row['Growth Rate / Velocity']}\"")

print(f"\n{'=' * 60}")
print("DONE — 5 tables ready. Run 02_sql_analyses.py next.")
print(f"{'=' * 60}")