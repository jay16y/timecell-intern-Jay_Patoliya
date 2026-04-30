"""
Task 01 — Portfolio Risk Calculator
Timecell.AI Summer Internship 2025

Computes crash-survival metrics for a portfolio of assets.
AI Tools Used: Claude (edge-case enumeration), Copilot (autocomplete)
"""

import math
import json
import sys

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ── Validation ───────────────────────────────────────────

def validate_portfolio(portfolio):
    """Check that portfolio has correct structure and valid values."""

    # Required keys
    assert "total_value_inr" in portfolio, "Missing 'total_value_inr'"
    assert "monthly_expenses_inr" in portfolio, "Missing 'monthly_expenses_inr'"
    assert "assets" in portfolio and len(portfolio["assets"]) > 0, "Missing or empty 'assets'"

    # Value constraints
    assert portfolio["total_value_inr"] >= 0, "total_value_inr cannot be negative"
    assert portfolio["monthly_expenses_inr"] >= 0, "monthly_expenses_inr cannot be negative"

    # Asset-level checks
    total_allocation = 0
    for asset in portfolio["assets"]:
        assert all(k in asset for k in ("name", "allocation_pct", "expected_crash_pct")), \
            f"Asset missing required keys: {asset}"
        assert asset["allocation_pct"] >= 0, f"{asset['name']}: allocation cannot be negative"
        assert -100 <= asset["expected_crash_pct"] <= 0, \
            f"{asset['name']}: crash_pct must be between -100 and 0"
        total_allocation += asset["allocation_pct"]

    # Allocations must sum to 100%
    assert math.isclose(total_allocation, 100, abs_tol=0.01), \
        f"Allocations sum to {total_allocation}%, expected 100%"


def load_portfolio_from_file(filepath: str) -> dict:
    """Load portfolio from a JSON file."""
    with open(filepath, 'r') as f:
        portfolio = json.load(f)
    return portfolio


# ── Core Calculation ─────────────────────────────────────

def compute_risk_metrics(portfolio):
    """
    Compute 5 key risk metrics for a portfolio.

    Math:
      post_crash_value = total_value × Σ(weight_i × (1 + crash_i))
      runway_months    = post_crash_value / monthly_expenses
      ruin_test        = PASS if runway > 12 months
      largest_risk     = asset with max(allocation × |crash|)
      concentration    = True if any asset > 40%

    Args:
        portfolio: dict with total_value_inr, monthly_expenses_inr, assets[]

    Returns:
        dict with: post_crash_value, runway_months, ruin_test,
                   largest_risk_asset, concentration_warning
    """
    validate_portfolio(portfolio)

    total_value = portfolio["total_value_inr"]
    monthly_expenses = portfolio["monthly_expenses_inr"]
    assets = portfolio["assets"]

    # 1. Post-crash value — how much survives a worst-case crash
    surviving_fraction = sum(
        (a["allocation_pct"] / 100) * (1 + a["expected_crash_pct"] / 100)
        for a in assets
    )
    post_crash_value = round(total_value * surviving_fraction, 2)

    # 2. Runway — months of expenses the survivor value covers
    runway_months = float("inf") if monthly_expenses == 0 else round(post_crash_value / monthly_expenses, 2)

    # 3. Ruin test — can the investor survive at least 1 year?
    ruin_test = "PASS" if runway_months > 12 else "FAIL"

    # 4. Largest risk asset — which single asset hurts the most?
    largest_risk_asset = max(assets, key=lambda a: a["allocation_pct"] * abs(a["expected_crash_pct"]))["name"]

    # 5. Concentration warning — is any position too heavy? (>40%)
    concentration_warning = any(a["allocation_pct"] > 40 for a in assets)

    return {
        "post_crash_value": post_crash_value,
        "runway_months": runway_months,
        "ruin_test": ruin_test,
        "largest_risk_asset": largest_risk_asset,
        "concentration_warning": concentration_warning,
    }


# ── BONUS 1: Dual Scenario (worst + moderate) ───────────

def compute_dual_scenario(portfolio):
    """
    Compare worst-case vs moderate crash (50% of expected severity).
    Example: BTC crash -80% worst → -40% moderate.
    """
    validate_portfolio(portfolio)

    # Build moderate version — halve each asset's crash magnitude
    moderate_portfolio = {
        "total_value_inr": portfolio["total_value_inr"],
        "monthly_expenses_inr": portfolio["monthly_expenses_inr"],
        "assets": [
            {**a, "expected_crash_pct": a["expected_crash_pct"] / 2}
            for a in portfolio["assets"]
        ],
    }

    return {
        "worst_case": compute_risk_metrics(portfolio),
        "moderate": compute_risk_metrics(moderate_portfolio),
    }


# ── BONUS 2: CLI Bar Chart ──────────────────────────────

def print_bar_chart(portfolio, width=40):
    """Print ASCII bar chart of portfolio allocation."""
    validate_portfolio(portfolio)
    assets = portfolio["assets"]
    name_width = max(len(a["name"]) for a in assets)

    print("\n  Portfolio Allocation")
    print("  " + "─" * (name_width + width + 12))
    for a in assets:
        bars = round(a["allocation_pct"] / 100 * width)
        bar = "█" * bars + "░" * (width - bars)
        print(f"  {a['name'].ljust(name_width)}  │ {bar} {a['allocation_pct']:5.1f}%")
    print("  " + "─" * (name_width + width + 12))


# ── Pretty Print Helpers ─────────────────────────────────

def print_metrics(metrics, title="Risk Metrics"):
    """Print risk metrics in a clean table."""
    rows = [
        ("Post-Crash Value",      f"₹ {metrics['post_crash_value']:,.2f}"),
        ("Runway (months)",       f"{metrics['runway_months']}"),
        ("Ruin Test",             metrics["ruin_test"]),
        ("Largest Risk Asset",    metrics["largest_risk_asset"]),
        ("Concentration Warning", "⚠ YES" if metrics["concentration_warning"] else "✓ No"),
    ]
    kw = max(len(r[0]) for r in rows) + 1
    vw = max(len(r[1]) for r in rows) + 1

    print(f"\n  ── {title} ──")
    print(f"  ┌{'─'*kw}┬{'─'*vw}┐")
    for key, val in rows:
        print(f"  │{key.ljust(kw)}│{val.ljust(vw)}│")
    print(f"  └{'─'*kw}┴{'─'*vw}┘")


def print_dual_scenario(scenarios):
    """Print worst-case and moderate scenarios side by side."""
    w, m = scenarios["worst_case"], scenarios["moderate"]
    rows = [
        ("Post-Crash Value",      f"₹ {w['post_crash_value']:,.2f}",  f"₹ {m['post_crash_value']:,.2f}"),
        ("Runway (months)",       f"{w['runway_months']}",            f"{m['runway_months']}"),
        ("Ruin Test",             w["ruin_test"],                     m["ruin_test"]),
        ("Largest Risk Asset",    w["largest_risk_asset"],            m["largest_risk_asset"]),
        ("Concentration Warning", "⚠ YES" if w["concentration_warning"] else "✓ No",
                                  "⚠ YES" if m["concentration_warning"] else "✓ No"),
    ]
    kw = max(len(r[0]) for r in rows) + 1
    ww = max(len(r[1]) for r in rows) + 1
    mw = max(len(r[2]) for r in rows) + 1

    print(f"\n  ── Worst Case vs Moderate (50%) ──")
    print(f"  ┌{'─'*kw}┬{'─'*ww}┬{'─'*mw}┐")
    print(f"  │{'Metric'.ljust(kw)}│{'Worst Case'.ljust(ww)}│{'Moderate'.ljust(mw)}│")
    print(f"  ├{'─'*kw}┼{'─'*ww}┼{'─'*mw}┤")
    for key, wv, mv in rows:
        print(f"  │{key.ljust(kw)}│{wv.ljust(ww)}│{mv.ljust(mw)}│")
    print(f"  └{'─'*kw}┴{'─'*ww}┴{'─'*mw}┘")


# ── Tests ────────────────────────────────────────────────

def run_tests():
    """Test with the standard portfolio + edge cases."""

    # Standard portfolio
    portfolio = {
        "total_value_inr": 10_000_000,
        "monthly_expenses_inr": 80_000,
        "assets": [
            {"name": "BTC",     "allocation_pct": 30, "expected_crash_pct": -80},
            {"name": "NIFTY50", "allocation_pct": 40, "expected_crash_pct": -40},
            {"name": "GOLD",    "allocation_pct": 20, "expected_crash_pct": -15},
            {"name": "CASH",    "allocation_pct": 10, "expected_crash_pct":   0},
        ],
    }
    m = compute_risk_metrics(portfolio)
    # Hand calc: 10M × (0.30×0.20 + 0.40×0.60 + 0.20×0.85 + 0.10×1.0) = 10M × 0.57 = 5.7M
    assert m["post_crash_value"] == 5_700_000.0
    assert m["runway_months"] == 71.25        # 5.7M / 80K
    assert m["ruin_test"] == "PASS"
    assert m["largest_risk_asset"] == "BTC"   # 30×80=2400 > 40×40=1600
    assert m["concentration_warning"] is False # max is 40%, not > 40%
    print("  ✓ Standard portfolio")

    # 100% cash — survives fully, but concentration warning triggers
    cash = {"total_value_inr": 5_000_000, "monthly_expenses_inr": 100_000,
            "assets": [{"name": "CASH", "allocation_pct": 100, "expected_crash_pct": 0}]}
    mc = compute_risk_metrics(cash)
    assert mc["post_crash_value"] == 5_000_000.0
    assert mc["concentration_warning"] is True
    print("  ✓ 100% cash portfolio")

    # Zero expenses — infinite runway
    no_exp = {"total_value_inr": 1_000_000, "monthly_expenses_inr": 0,
              "assets": [{"name": "GOLD", "allocation_pct": 100, "expected_crash_pct": -15}]}
    assert compute_risk_metrics(no_exp)["runway_months"] == float("inf")
    print("  ✓ Zero expenses (infinite runway)")

    # Total wipeout
    wipe = {"total_value_inr": 2_000_000, "monthly_expenses_inr": 50_000,
            "assets": [{"name": "MEME", "allocation_pct": 100, "expected_crash_pct": -100}]}
    mw = compute_risk_metrics(wipe)
    assert mw["post_crash_value"] == 0.0 and mw["ruin_test"] == "FAIL"
    print("  ✓ Total wipeout")

    # Exactly 12 months should FAIL (strict > 12)
    exact = {"total_value_inr": 960_000, "monthly_expenses_inr": 80_000,
             "assets": [{"name": "CASH", "allocation_pct": 100, "expected_crash_pct": 0}]}
    assert compute_risk_metrics(exact)["ruin_test"] == "FAIL"  # 960K/80K = 12.0, not > 12
    print("  ✓ Exactly 12 months → FAIL")

    # Bad allocation sum should raise error
    bad = {"total_value_inr": 1_000_000, "monthly_expenses_inr": 50_000,
           "assets": [{"name": "BTC", "allocation_pct": 50, "expected_crash_pct": -80},
                      {"name": "CASH", "allocation_pct": 30, "expected_crash_pct": 0}]}
    try:
        compute_risk_metrics(bad)
        assert False, "Should have raised"
    except AssertionError:
        print("  ✓ Invalid allocation rejected")

    print("\n  ✅ ALL TESTS PASSED\n")


# ── Main ─────────────────────────────────────────────────

if __name__ == "__main__":
    # Run tests
    print("\n  ── Running Tests ──\n")
    run_tests()

    # Demo output
    portfolio_file = "portfolio.json"
    if portfolio_file:
        portfolio = load_portfolio_from_file(portfolio_file)
    else:
        portfolio = {
        "total_value_inr": 10_000_000,
        "monthly_expenses_inr": 80_000,
        "assets": [
            {"name": "BTC",     "allocation_pct": 30, "expected_crash_pct": -80},
            {"name": "NIFTY50", "allocation_pct": 40, "expected_crash_pct": -40},
            {"name": "GOLD",    "allocation_pct": 20, "expected_crash_pct": -15},
            {"name": "CASH",    "allocation_pct": 10, "expected_crash_pct":   0},
        ],
    }

    print_metrics(compute_risk_metrics(portfolio), "Worst-Case Crash")
    print_dual_scenario(compute_dual_scenario(portfolio))
    print_bar_chart(portfolio)
