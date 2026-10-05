# Mamaearth Returns & Growth Intelligence Pipeline

Capstone Project — Data Analytics with AI & Gen AI, E&ICT Academy IIT Roorkee.

This repository implements the capstone as one reproducible three-layer pipeline:

1. **SQL relational/reporting layer** — loads the exact raw CSV seed data into SQLite and produces the required reports.
2. **Python/Pandas analysis layer** — independently reads the same raw CSVs, cleans them, detects duplicates/outliers, performs EDA, creates visualizations, and writes the verified `narrator/findings.json`.
3. **GenAI narrative layer** — reads `findings.json` and generates a Situation–Complication–Resolution narrative with Gemini when a key is available, or a deterministic offline fallback when it is not.

The raw CSV files under `data/` are intentionally unchanged. Cleaning happens in Python.

## Repository structure

```text
mamaearth_returns_growth_intelligence/
├── README.md
├── sql/
│   ├── schema.sql
│   ├── seed_data.sql
│   └── reports.sql
├── data/
│   ├── customers.csv
│   ├── products.csv
│   └── orders.csv
├── analysis/
│   ├── clean_and_eda.py
│   └── visualize.py
├── visualizations/
│   ├── return_rate_by_payment.png
│   └── monthly_revenue_trend.png
└── narrator/
    ├── findings.json
    ├── generate_narrative.py
    └── sample_output.txt
```

## Requirements

- Python 3.10+
- SQLite 3.x
- Python packages:
  - `pandas`
  - `numpy`
  - `matplotlib`
  - `google-genai` (only required for the online Gemini path)

Install the Python dependencies:

```bash
pip install pandas numpy matplotlib google-genai
```

The analysis and offline narrator paths do not require a network connection.

---

# Exact run order

## 1. SQL layer

From the repository root, create a fresh SQLite database and load the schema:

```bash
sqlite3 mamaearth.db < sql/schema.sql
sqlite3 mamaearth.db < sql/seed_data.sql
```

Then run the report queries:

```bash
sqlite3 -header -column mamaearth.db < sql/reports.sql
```

`seed_data.sql` is generated from the exact CSV files and is re-runnable after `schema.sql`.

Expected source row counts after loading:

- customers: 45
- products: 16
- orders: 180

The SQL report comments contain the required expected outputs immediately above each query.

## 2. Python/Pandas analysis layer

Run:

```bash
python analysis/clean_and_eda.py
```

This script:

- loads the raw CSVs directly;
- verifies the raw order shape `(180, 9)`;
- standardizes payment-method casing;
- detects and removes the five intentional duplicate rows;
- imputes missing discount and rating values;
- merges orders, products, and customers;
- computes cleaned revenue and reconciles it to the SQL raw total;
- flags quantity outliers without deleting them;
- tests the COD return-rate hypothesis;
- performs payment-method × city-tier segmentation;
- labels all six correlation pairs;
- computes outlier-inclusive and outlier-corrected monthly revenue;
- writes `narrator/findings.json` **from values computed during this run**.

The generated findings are:

```json
{
  "cleaned_total_revenue_inr": 97358.3,
  "raw_total_revenue_inr": 99860.2,
  "duplicate_reconciliation_delta_inr": 2501.9,
  "return_rate_by_payment": {
    "COD": 44.4,
    "CARD": 14.7,
    "UPI": 18.9
  },
  "highest_risk_segment": {
    "payment_method": "COD",
    "city_tier": 2,
    "return_rate_pct": 54.5
  },
  "true_peak_month": {
    "month": "2026-03",
    "revenue_inr": 20318.9
  },
  "outlier_inflated_month": {
    "month": "2026-01",
    "apparent_revenue_inr": 29582.1,
    "corrected_revenue_inr": 11637.1
  }
}
```

## 3. Visualizations

After the analysis script completes, run:

```bash
python analysis/visualize.py
```

This regenerates:

- `visualizations/return_rate_by_payment.png`
- `visualizations/monthly_revenue_trend.png`

The monthly chart deliberately uses the outlier-corrected series, so March is the actual peak.

## 4. Narrator layer

The narrator must be run **after** `clean_and_eda.py`, because that script is the source of truth for `narrator/findings.json`.

### Online Gemini path

Google AI Studio provides a free Gemini usage tier. Use a free-tier API key; do not put the key in the repository.

Windows PowerShell:

```powershell
$env:GEMINI_API_KEY="YOUR_FREE_GOOGLE_AI_STUDIO_KEY"
python narrator/generate_narrative.py
```

macOS/Linux:

```bash
export GEMINI_API_KEY="YOUR_FREE_GOOGLE_AI_STUDIO_KEY"
python narrator/generate_narrative.py
```

The Gemini call uses:

- a separate system instruction;
- `temperature=0.0`;
- explicit `max_output_tokens`;
- a request timeout;
- structured success/error return dictionaries.

### Fully offline / keyless path

Simply run:

```bash
python narrator/generate_narrative.py
```

with no `GEMINI_API_KEY`.

The script automatically uses `generate_scr_narrative_offline(findings)` and makes no network call. If a Gemini key exists but the API call fails, the script also falls back to the same deterministic offline function.

The offline fallback contains the required verified numbers directly from the `findings` argument, rather than hardcoding those numbers into the online prompt.

## Data flow and anti-drift design

```text
data/*.csv
   │
   ├──► SQL schema.sql + seed_data.sql
   │          │
   │          └──► reports.sql
   │
   └──► analysis/clean_and_eda.py
              │
              ├──► visualizations/*.png
              │
              └──► narrator/findings.json
                         │
                         └──► narrator/generate_narrative.py
                                  ├──► Gemini narrative (if key works)
                                  └──► offline SCR fallback
```

The SQL and Pandas layers intentionally operate independently over the same raw source files. The narrator does **not** recompute analytics and does not receive numbers from an unrelated manually typed prompt. It receives the verified `findings` dictionary written by the analysis layer.

## Important verified results

- Raw SQL revenue: ₹99,860.20
- Cleaned revenue: ₹97,358.30
- Duplicate-driven reconciliation delta: ₹2,501.90
- COD return rate: 44.4%
- Highest-risk segment: COD + Tier-2 cities at 54.5%
- Apparent January revenue: ₹29,582.10
- Corrected January revenue: ₹11,637.10
- True peak: March 2026 at ₹20,318.90

The January peak is an outlier artifact caused by O0011 and O0098, whose quantities are 25 and 30 respectively. Once those two bulk orders are excluded from the monthly series, March becomes the true peak.

## Reproducibility

Do not edit anything under `data/` by hand.

A clean reproduction is:

```bash
sqlite3 mamaearth.db < sql/schema.sql
sqlite3 mamaearth.db < sql/seed_data.sql
sqlite3 -header -column mamaearth.db < sql/reports.sql

python analysis/clean_and_eda.py
python analysis/visualize.py
python narrator/generate_narrative.py
```

Running the sequence from the raw CSVs regenerates the verified analysis outputs and the two PNGs deterministically.
