"""
task04_tax_calculator.py
Tax-Aware Withdrawal Calculator — Indian Tax Rules (LTCG / STCG)
Timecell.ai Summer Internship 2025 — Task 04
"""

import json
from dataclasses import dataclass

# ── Indian Capital Gains Tax Rules (FY 2024-25) ──────────────────────────────
# (ltcg_threshold_days, ltcg_rate, stcg_rate, ltcg_exemption_inr)
TAX_RULES = {
    "equity_index": (365,   0.125, 0.20, 125_000),  # Listed equity/index funds
    "crypto":       (36500, 0.30,  0.30, 0),          # Crypto: flat 30%, no benefit
    "commodity":    (1095,  0.20,  None, 0),           # Gold: 3yr LTCG, slab for STCG
    "cash":         (0,     0.0,   0.0,  0),           # No gains
}

SLAB_TAX_RATE = 0.30  # Assumed highest income-tax slab for STCG on non-equity


@dataclass
class AssetTaxResult:
    name: str
    asset_type: str
    holding_days: int
    gain_type: str          # LTCG, STCG, LOSS, NO_GAIN
    gross_gain_inr: float
    tax_inr: float
    net_proceeds_inr: float
    effective_tax_rate: float
    is_harvesting_opportunity: bool
    note: str


def classify_gain(asset: dict, total_portfolio_value: float) -> AssetTaxResult:
    name       = asset["name"]
    
    # Auto-map types if missing
    default_type_map = {"BTC": "crypto", "NIFTY50": "equity_index", "GOLD": "commodity", "CASH": "cash"}
    atype      = asset.get("type", default_type_map.get(name.upper(), "cash"))
    
    hold_days  = asset.get("holding_days", 400)  # default 400 days
    alloc_pct  = asset["allocation_pct"]
    
    market_value = total_portfolio_value * (alloc_pct / 100)
    cost       = asset.get("purchase_price_inr", market_value * 0.7) # Default to 30% unrealised gain
    gain         = market_value - cost

    if atype not in TAX_RULES:
        return AssetTaxResult(name, atype, hold_days, "UNKNOWN", gain, 0, market_value, 0, False, "Unknown type")

    ltcg_days, ltcg_rate, stcg_rate, exemption = TAX_RULES[atype]

    if gain < 0:
        return AssetTaxResult(
            name=name, asset_type=atype, holding_days=hold_days,
            gain_type="LOSS", gross_gain_inr=round(gain, 2), tax_inr=0,
            net_proceeds_inr=round(market_value, 2), effective_tax_rate=0.0,
            is_harvesting_opportunity=(gain < -10_000),
            note=f"Capital loss of Rs{abs(gain):,.0f}. Can offset gains."
        )

    if gain == 0:
        return AssetTaxResult(name, atype, hold_days, "NO_GAIN", 0, 0, round(market_value, 2), 0, False, "No taxable gain.")

    is_ltcg = hold_days >= ltcg_days
    gain_type = "LTCG" if is_ltcg else "STCG"

    if is_ltcg:
        taxable_gain = max(0, gain - exemption)
        tax = taxable_gain * ltcg_rate
        note = (f"LTCG @ {ltcg_rate*100:.1f}%"
                + (f" | Rs{exemption/1000:.0f}k exemption applied" if exemption else ""))
    else:
        rate = stcg_rate if stcg_rate else SLAB_TAX_RATE
        tax  = gain * rate
        note = f"STCG @ {rate*100:.1f}% (held {hold_days}d, need {ltcg_days}d for LTCG)"

    net_proceeds = market_value - tax
    eff_rate     = (tax / gain * 100) if gain > 0 else 0

    return AssetTaxResult(
        name=name, asset_type=atype, holding_days=hold_days,
        gain_type=gain_type, gross_gain_inr=round(gain, 2),
        tax_inr=round(tax, 2), net_proceeds_inr=round(net_proceeds, 2),
        effective_tax_rate=round(eff_rate, 2),
        is_harvesting_opportunity=False, note=note
    )


def compute_withdrawal_plan(portfolio: dict, withdrawal_amount: float) -> dict:
    total_val = portfolio["total_value_inr"]
    results   = [classify_gain(a, total_val) for a in portfolio["assets"]]

    # Sell losses first (offset gains), then cheapest tax-rate assets
    sell_order = sorted(results, key=lambda r: (
        0 if r.gain_type == "LOSS" else 1,
        r.effective_tax_rate
    ))

    remaining     = withdrawal_amount
    sell_plan     = []

    for r in sell_order:
        if remaining <= 0:
            break
        asset_value = total_val * (
            next(a["allocation_pct"] for a in portfolio["assets"] if a["name"] == r.name) / 100
        )
        sell_amt   = min(asset_value, remaining)
        sell_ratio = sell_amt / asset_value if asset_value > 0 else 0
        tax_cost   = r.tax_inr * sell_ratio

        sell_plan.append({
            "asset":       r.name,
            "sell_amount": round(sell_amt, 2),
            "tax_cost":    round(tax_cost, 2),
            "net_in_hand": round(sell_amt - tax_cost, 2),
            "gain_type":   r.gain_type,
            "note":        r.note,
        })
        remaining -= sell_amt

    total_tax  = sum(p["tax_cost"] for p in sell_plan)
    total_sold = sum(p["sell_amount"] for p in sell_plan)
    total_net  = sum(p["net_in_hand"] for p in sell_plan)

    return {
        "requested_withdrawal_inr": withdrawal_amount,
        "total_to_sell_inr":        round(total_sold, 2),
        "total_tax_inr":            round(total_tax, 2),
        "net_in_hand_inr":          round(total_net, 2),
        "effective_tax_rate_pct":   round((total_tax / total_sold * 100) if total_sold else 0, 2),
        "sell_plan":                sell_plan,
        "asset_analysis":           results,
        "harvesting_opportunities": [r.name for r in results if r.is_harvesting_opportunity],
    }


def fmt(val: float) -> str:
    return f"Rs{val:>12,.0f}"


def print_report(portfolio: dict, plan: dict):
    W   = 72
    SEP = "-" * W

    print(f"\n{'='*W}")
    print(f"  TAX-AWARE WITHDRAWAL REPORT  |  {portfolio.get('owner', 'Unknown User')}")
    print(f"{'='*W}")

    # Asset breakdown
    print(f"\n  ASSET TAX BREAKDOWN")
    print(f"  {SEP}")
    print(f"  {'Asset':<10} {'Type':<14} {'Days':>5} {'Gain Type':<9} {'Gross Gain':>13} {'Tax':>12} {'Rate':>7}")
    print(f"  {SEP}")

    for r in plan["asset_analysis"]:
        tag = {"LTCG": "[LTCG]", "STCG": "[STCG]", "LOSS": "[LOSS]", "NO_GAIN": "[NONE]"}.get(r.gain_type, "")
        print(f"  {r.name:<10} {r.asset_type:<14} {r.holding_days:>5}d  {tag:<9} {fmt(r.gross_gain_inr)}{fmt(r.tax_inr)}  {r.effective_tax_rate:>5.1f}%")
        print(f"    |- {r.note}")

    # Harvesting
    if plan["harvesting_opportunities"]:
        print(f"\n  TAX-LOSS HARVESTING OPPORTUNITIES")
        print(f"  {SEP}")
        for name in plan["harvesting_opportunities"]:
            r = next(x for x in plan["asset_analysis"] if x.name == name)
            print(f"  >> Sell {name}: realise loss of Rs{abs(r.gross_gain_inr):,.0f} to offset gains")

    # Withdrawal plan
    print(f"\n  WITHDRAWAL PLAN  (Target: Rs{plan['requested_withdrawal_inr']:,.0f})")
    print(f"  {SEP}")
    print(f"  Sell order: losses first >> then lowest tax-rate assets")
    print()
    print(f"  {'Asset':<10} {'Sell Amount':>14} {'Tax Cost':>12} {'Net In Hand':>13} {'Type':<8}")
    print(f"  {SEP}")

    for p in plan["sell_plan"]:
        print(f"  {p['asset']:<10} {fmt(p['sell_amount'])}{fmt(p['tax_cost'])}{fmt(p['net_in_hand'])}  {p['gain_type']}")

    print(f"  {SEP}")
    print(f"  {'TOTAL':<10} {fmt(plan['total_to_sell_inr'])}{fmt(plan['total_tax_inr'])}{fmt(plan['net_in_hand_inr'])}")
    print(f"\n  Effective Tax Rate: {plan['effective_tax_rate_pct']:.1f}%")

    req = plan["requested_withdrawal_inr"]
    net = plan["net_in_hand_inr"]
    tax = plan["total_tax_inr"]

    if net < req:
        print(f"\n  [!] After-tax you receive Rs{net:,.0f} — Rs{req-net:,.0f} short.")
        print(f"      To net Rs{req:,.0f} in hand, sell ~Rs{req+tax:,.0f} total.")
    else:
        print(f"\n  [OK] You receive Rs{net:,.0f} after Rs{tax:,.0f} in taxes.")

    print(f"\n{'='*W}\n")


def main():
    with open("portfolio.json") as f:
        portfolio = json.load(f)

    print(f"\nPortfolio: {portfolio.get('owner', 'Unknown User')}")
    print(f"Total Value: Rs{portfolio['total_value_inr']:,.0f}")

    try:
        raw = input("\nWithdrawal amount? Rs").strip()
        amount = float(raw.replace(",", ""))
    except (ValueError, EOFError):
        amount = 500_000
        print(f"Using: Rs{amount:,.0f}")

    plan = compute_withdrawal_plan(portfolio, amount)
    print_report(portfolio, plan)


if __name__ == "__main__":
    main()