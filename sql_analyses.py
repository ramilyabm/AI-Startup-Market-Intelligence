"""
AI Startup Market Intelligence — SQL Analysis
==============================================
Author: Ramilya Bakiyeva | Portfolio Project #3

WHAT THIS SCRIPT DOES:
  Runs 7 SQL queries against the SQLite database, each demonstrating
  a different SQL skill and answering a business question relevant
  to technical sales roles.

SQL SKILLS DEMONSTRATED:
  1. CASE expressions + calculated columns
  2. GROUP BY + conditional aggregation
  3. RANK() window function
  4. INNER JOIN across tables
  5. NTILE() window function
  6. Cumulative SUM() OVER (time-series)
  7. CTE (Common Table Expression) + multi-table JOIN + HAVING

SETUP: Run data_setup.py first to create ai_startups.db
RUN:   python3 sql_analyses.py
"""

import sqlite3
import pandas as pd
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "ai_startups.db")
conn = sqlite3.connect(DB_PATH)


def run_query(number, title, skill, why, sql):
    """Execute a query and print results with context."""
    print(f"\n{'=' * 65}")
    print(f"  QUERY {number}: {title}")
    print(f"  SQL SKILL: {skill}")
    print(f"  WHY IT MATTERS: {why}")
    print(f"{'=' * 65}")
    print(sql)

    df = pd.read_sql_query(sql, conn)
    print(df.to_string(index=False))
    print(f"({len(df)} rows)")
    return df


# ──────────────────────────────────────────────────────────────────────
# QUERY 1: Capital Efficiency — ARR per dollar raised, with age context
# ──────────────────────────────────────────────────────────────────────
run_query(
    1,
    "Capital Efficiency: Who generates the most ARR per dollar raised?",
    "CASE expression, calculated columns, WHERE, ORDER BY",
    "A Sales Engineer must understand unit economics to qualify prospects.",
    """
SELECT
    company_name,
    ai_category,
    company_age                                AS age_years,
    ROUND(arr_m, 1)                            AS arr_m,
    ROUND(funding_m, 1)                        AS funding_m,
    ROUND(arr_m / funding_m, 2)                AS efficiency_ratio,
    CASE
        WHEN arr_m / funding_m >= 1.0 THEN 'Excellent (>=1.0x)'
        WHEN arr_m / funding_m >= 0.5 THEN 'Good (0.5-1.0x)'
        WHEN arr_m / funding_m >= 0.1 THEN 'Building (0.1-0.5x)'
        ELSE 'Early (<0.1x)'
    END                                        AS efficiency_tier
FROM startups
WHERE arr_m IS NOT NULL
  AND funding_m IS NOT NULL
  AND funding_m > 0
ORDER BY efficiency_ratio DESC;
    """
)


# ──────────────────────────────────────────────────────────────────────
# QUERY 2: YC vs Non-YC Performance
# ──────────────────────────────────────────────────────────────────────
run_query(
    2,
    "YC-Backed vs Non-YC: Does Y Combinator affiliation matter?",
    "GROUP BY, conditional aggregation (CASE inside AVG), COUNT",
    "Selling to startups? Know if YC companies buy differently or scale faster.",
    """
SELECT
    CASE WHEN yc_backed = 1 THEN 'YC-Backed' ELSE 'Non-YC' END
                                               AS cohort,
    COUNT(*)                                   AS companies,
    ROUND(AVG(funding_m), 0)                   AS avg_funding_m,
    ROUND(AVG(valuation_m), 0)                 AS avg_valuation_m,
    ROUND(AVG(arr_m), 0)                       AS avg_arr_m,
    ROUND(AVG(growth_pct), 0)                  AS avg_growth_pct,
    ROUND(AVG(company_age), 1)                 AS avg_age_years,
    ROUND(AVG(CASE WHEN arr_m IS NOT NULL AND funding_m > 0
                   THEN arr_m / funding_m END), 2)
                                               AS avg_efficiency
FROM startups
GROUP BY yc_backed;
    """
)


# ──────────────────────────────────────────────────────────────────────
# QUERY 3: Category Leaders — #1 by ARR in each segment
# ──────────────────────────────────────────────────────────────────────
run_query(
    3,
    "Category Leaders: Top company by ARR in each AI segment",
    "RANK() window function, subquery, PARTITION BY",
    "Sales teams need to know who dominates each segment for competitive positioning.",
    """
SELECT
    ai_category,
    company_name,
    ROUND(arr_m, 1)       AS arr_m,
    ROUND(funding_m, 1)   AS funding_m,
    ROUND(valuation_m, 0) AS valuation_m,
    yc_backed
FROM (
    SELECT *,
        RANK() OVER (
            PARTITION BY ai_category
            ORDER BY arr_m DESC
        ) AS rank_in_category
    FROM startups
    WHERE arr_m IS NOT NULL
)
WHERE rank_in_category = 1
ORDER BY arr_m DESC;
    """
)


# ──────────────────────────────────────────────────────────────────────
# QUERY 4: ROI Benchmarking — Company claims vs category benchmarks
# ──────────────────────────────────────────────────────────────────────
run_query(
    4,
    "ROI Benchmarking: Company ROI claims vs. category-level benchmarks",
    "INNER JOIN, multi-table analysis",
    "Connecting product capabilities to measurable ROI closes deals — this is exactly what a Sales Engineer presents to prospects.",
    """
SELECT
    s.company_name,
    s.ai_category,
    s.roi_claim                        AS company_says,
    t.roi_drivers                      AS category_benchmark,
    t.target_industries                AS sells_to
FROM startups s
INNER JOIN taxonomy t ON s.ai_category = t.ai_category
WHERE s.roi_claim IS NOT NULL
ORDER BY s.company_name;
    """
)


# ──────────────────────────────────────────────────────────────────────
# QUERY 5: Growth Velocity Tiers
# ──────────────────────────────────────────────────────────────────────
run_query(
    5,
    "Growth Velocity: Segmenting companies into speed tiers",
    "NTILE() window function, CASE for labeling",
    "Account executives prioritize hypergrowth accounts — they buy faster and expand sooner.",
    """
SELECT
    company_name,
    ai_category,
    ROUND(growth_pct, 0)              AS growth_pct,
    growth_raw                        AS original_description,
    CASE growth_tier
        WHEN 1 THEN 'Hypergrowth (Top 25%)'
        WHEN 2 THEN 'Fast (25-50%)'
        WHEN 3 THEN 'Moderate (50-75%)'
        WHEN 4 THEN 'Steady (Bottom 25%)'
    END                               AS tier
FROM (
    SELECT *,
        NTILE(4) OVER (ORDER BY growth_pct DESC) AS growth_tier
    FROM startups
    WHERE growth_pct IS NOT NULL
)
ORDER BY growth_pct DESC;
    """
)


# ──────────────────────────────────────────────────────────────────────
# QUERY 6: Funding Progression — Time-series for top AI companies
# ──────────────────────────────────────────────────────────────────────
run_query(
    6,
    "Funding Progression: How top AI companies scaled their fundraising",
    "Cumulative SUM() OVER (window), JOIN, ORDER BY date",
    "A company that just raised $500M is about to spend — that's when a Sales Engineer wants to be in the room.",
    """
SELECT
    fh.company_name,
    fh.round_name,
    fh.round_date,
    ROUND(fh.amount_m, 0)             AS round_m,
    ROUND(SUM(fh.amount_m) OVER (
        PARTITION BY fh.company_name
        ORDER BY fh.round_date
    ), 0)                             AS cumulative_m,
    fh.lead_investor,
    ROUND(fh.post_money_m, 0)        AS post_money_m,
    s.ai_category
FROM funding_history fh
INNER JOIN startups s ON fh.company_name = s.company_name
WHERE fh.company_name IN ('OpenAI', 'Anthropic', 'Databricks')
ORDER BY fh.company_name, fh.round_date;
    """
)


# ──────────────────────────────────────────────────────────────────────
# QUERY 7: Market Landscape — CTE-based category summary
# ──────────────────────────────────────────────────────────────────────
run_query(
    7,
    "Market Landscape: Category-level investment and performance summary",
    "CTE (WITH clause), LEFT JOIN, HAVING, multi-aggregation",
    "The 30,000-foot view a Solutions Consultant needs: which categories attract the most capital and grow the fastest?",
    """
WITH category_stats AS (
    SELECT
        ai_category,
        COUNT(*)                       AS num_companies,
        ROUND(SUM(funding_m), 0)       AS total_funding_m,
        ROUND(AVG(arr_m), 0)           AS avg_arr_m,
        ROUND(AVG(growth_pct), 0)      AS avg_growth_pct,
        ROUND(AVG(company_age), 1)     AS avg_age,
        SUM(yc_backed)                 AS yc_count
    FROM startups
    GROUP BY ai_category
    HAVING num_companies >= 2
)
SELECT
    cs.*,
    t.target_industries,
    t.roi_drivers
FROM category_stats cs
LEFT JOIN taxonomy t ON cs.ai_category = t.ai_category
ORDER BY total_funding_m DESC;
    """
)


# ── SUMMARY ───────────────────────────────────────────────────────────
print(f"\n{'=' * 65}")
print("  7 QUERIES COMPLETE — SQL skills demonstrated:")
print(f"{'=' * 65}")
print("  1. Capital Efficiency   → CASE, calculated columns")
print("  2. YC vs Non-YC         → GROUP BY, conditional aggregation")
print("  3. Category Leaders     → RANK() window function")
print("  4. ROI Benchmarking     → INNER JOIN across tables")
print("  5. Growth Velocity      → NTILE() window function")
print("  6. Funding Progression  → Cumulative SUM() OVER, time-series")
print("  7. Market Landscape     → CTE, LEFT JOIN, HAVING")
print(f"{'=' * 65}")

conn.close()