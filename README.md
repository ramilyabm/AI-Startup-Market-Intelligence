# AI Startup Market Intelligence Dashboard

A full-stack market intelligence tool tracking 48 AI startups across 19 categories — built as Portfolio Project #3 by Ramilya Bakiyeva.

**Live app:** [https://ai-startups-rami.streamlit.app/]

---

## What This Is

This dashboard was built to demonstrate market research, data engineering, and business analytics skills relevant to technical sales roles (Sales Engineer, Solutions Consultant, Technical CSM).

It answers the question a strategic account manager actually asks: *"Which AI companies are worth pursuing, why, and how do I sell to them?"*

---

## What It Does

- **Ecosystem Map** — Treemap of 48 companies colored by capital efficiency, sized by funding
- **Company Intelligence** — Per-company KPIs: funding, valuation, ARR, growth, val/ARR multiple vs. category median
- **Investor Intelligence** — 5-tier investor taxonomy (Big Tech Strategic → Angel), cascading filters, portfolio view
- **GTM Strategy** — Use case taxonomy with ROI drivers and target ICPs per category
- **PDF Report Generator** — Exportable intelligence briefs (company one-pager or full ecosystem overview) with cover page and custom context field

---

## Data

- **48 AI companies** — $78B+ total funding, 83% with confirmed valuations, 42% with 2026 ARR
- **160 funding rounds** — Seed through Series D, with lead investors and post-money valuations
- **86 investor profiles** — Structured into 5 tiers with GTM signals
- **19-category use case taxonomy** — Maps each AI category to industries, ROI drivers, and value propositions
- Sources: Sacra, TechCrunch, company blogs, Crunchbase (verified March 2026)

---

## Tech Stack

| Layer | Tools |
|---|---|
| Frontend | Streamlit |
| Data | Python, Pandas, SQLite |
| Visualization | Plotly |
| PDF Generation | ReportLab |
| Version Control | Git / GitHub |

---

## How to Run Locally

```bash
git clone https://github.com/ramilyabm/AI-Startup-Market-Intelligence.git
cd AI-Startup-Market-Intelligence
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python data_setup.py
streamlit run streamlit_app.py
```

---

## About

Built by **Ramilya Bakiyeva** — transitioning from elite B2B sales (top 1% at P&G, Eastern Europe) into AI-focused technical sales roles.

This is the third of three portfolio projects demonstrating business-technical fluency:
1. [Revenue Intelligence Dashboard](https://revenue-intelligence-dashboard-rami.streamlit.app)
2. [AI Transformation in 10 Years](https://ai-strategy-rami.streamlit.app/)
3. **AI Startup Market Intelligence** ← this project

📍 San Jose, CA · [LinkedIn](https://linkedin.com/in/ramilyabakiyeva)
