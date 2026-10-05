"""
Mamaearth Returns & Growth Intelligence — Part 3 narrator.

Online path:
    Windows PowerShell:
        $env:GEMINI_API_KEY="your_free_google_ai_studio_key"
        python narrator/generate_narrative.py

    macOS/Linux:
        export GEMINI_API_KEY="your_free_google_ai_studio_key"
        python narrator/generate_narrative.py

Offline path:
    python narrator/generate_narrative.py
    (works with no API key and no network)
"""
from __future__ import annotations
from pathlib import Path
import json
import os
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FINDINGS_PATH = ROOT / "narrator" / "findings.json"
SAMPLE_PATH = ROOT / "narrator" / "sample_output.txt"

SYSTEM_INSTRUCTION = """
You are a senior data analyst writing for Mamaearth's regional ops and finance heads.

Write a concise business narrative using exactly three labeled sections:
Situation
Complication
Resolution

Every number in the narrative must come only from the supplied findings and must appear
with the same value (equivalent comma formatting and decimal formatting are acceptable).
Do not invent statistics, percentages, dates, savings, costs, causes, or forecasts.
Explain what the verified findings mean operationally and financially, but do not create
unsupported numerical claims.
""".strip()

def _user_prompt(findings: dict[str, Any]) -> str:
    return f"""
Create the SCR narrative from these verified findings. Use the values below as the sole
source of numerical facts. Keep the three sections labeled Situation, Complication,
Resolution.

Verified findings:
{json.dumps(findings, indent=2, sort_keys=True)}
""".strip()

def generate_scr_narrative(findings: dict) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return generate_scr_narrative_offline(findings)

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        # temperature=0.0 is intentional: this is a factual business report, not creative writing.
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.0,
            max_output_tokens=500,
            http_options=types.HttpOptions(timeout=30000),
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=_user_prompt(findings),
            config=config,
        )
        narrative = response.text.strip() if response.text else ""
        if not narrative:
            raise RuntimeError("Gemini returned an empty narrative.")

        tokens = None
        usage = getattr(response, "usage_metadata", None)
        if usage is not None:
            tokens = getattr(usage, "total_token_count", None)

        return {
            "status": "success",
            "narrative": narrative,
            "tokens": tokens,
        }
    except Exception as err:
        return {
            "status": "error",
            "narrative": None,
            "message": str(err),
        }

def generate_scr_narrative_offline(findings: dict) -> dict:
    rr = findings["return_rate_by_payment"]
    hs = findings["highest_risk_segment"]
    peak = findings["true_peak_month"]
    inflated = findings["outlier_inflated_month"]

    narrative = f"""Situation

Cleaned revenue is ₹{findings["cleaned_total_revenue_inr"]:,.2f}, compared with raw revenue of ₹{findings["raw_total_revenue_inr"]:,.2f}. Payment-method analysis shows COD at {rr["COD"]:.1f}% returns, versus CARD at {rr["CARD"]:.1f}% and UPI at {rr["UPI"]:.1f}%.

Complication

The highest-risk segment is COD in Tier-{hs["city_tier"]} cities at {hs["return_rate_pct"]:.1f}%. The raw-to-cleaned reconciliation has a ₹{findings["duplicate_reconciliation_delta_inr"]:,.2f} duplicate-driven delta. January appears to lead at ₹{inflated["apparent_revenue_inr"]:,.2f}, but that view is distorted by the two bulk-order outliers.

Resolution

Use the cleaned pipeline as the reporting baseline, investigate COD returns in Tier-{hs["city_tier"]} cities first, and keep duplicate detection in the operational data-quality workflow. After removing the two quantity outliers, the true revenue peak is {peak["month"]} at ₹{peak["revenue_inr"]:,.2f}, while January falls to ₹{inflated["corrected_revenue_inr"]:,.2f}."""
    return {
        "status": "success",
        "narrative": narrative,
        "tokens": None,
    }

def check_required_figures(narrative: str) -> list[tuple[str, bool]]:
    normalized = narrative.replace(",", "")
    checks = [
        ("cleaned revenue 97358.30", "97358.30" in normalized or "97358.3" in normalized),
        ("COD return rate 44.4", "44.4" in normalized),
        ("COD Tier-2 return rate 54.5", "54.5" in normalized),
        ("duplicate delta 2501.90", "2501.90" in normalized or "2501.9" in normalized),
        ("March and 20318.90", ("March" in narrative or "2026-03" in narrative) and
         ("20318.90" in normalized or "20318.9" in normalized)),
    ]
    for label, passed in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {label}")
    return checks

def main() -> int:
    if not FINDINGS_PATH.exists():
        raise FileNotFoundError(
            "narrator/findings.json not found. Run python analysis/clean_and_eda.py first."
        )

    findings = json.loads(FINDINGS_PATH.read_text(encoding="utf-8"))
    result = generate_scr_narrative(findings)

    if result["status"] == "error":
        print("Gemini path failed; switching to deterministic offline fallback.")
        result = generate_scr_narrative_offline(findings)

    narrative = result["narrative"]
    print("\n" + "=" * 80)
    print("SCR NARRATIVE")
    print("=" * 80)
    print(narrative)

    print("\n" + "=" * 80)
    print("NUMERIC ACCURACY CHECK")
    print("=" * 80)
    checks = check_required_figures(narrative)
    assert all(ok for _, ok in checks), "Numeric accuracy checklist failed."

    SAMPLE_PATH.write_text(narrative + "\n", encoding="utf-8")
    print(f"\nSaved sample output to: {SAMPLE_PATH}")
    print(f"Path used: {'Gemini API' if result.get('tokens') is not None else 'offline fallback'}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
