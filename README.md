# Timecell.AI — Summer Internship 2025 Technical Assessment
**Candidate:** Jay Patoliya  
**Role:** Engineering Intern — AI & Fintech  
**Submission Date:** 1 May 2025  
**Python Version:** 3.10+

---

## Project Overview

This repository contains my solution to the Timecell.AI Engineering Intern technical assessment. The assessment tests core engineering skills across four domains: quantitative finance, data pipelines, LLM integration, and product thinking.

All scripts are pure Python 3.10+, run from the terminal, and are designed to be readable — every function has a clear purpose, docstring, and logical name. AI tools (primarily Antigravity / Claude) were used actively, as encouraged, but I can walk through every line of code.

```
timecell-intern-jay/
├── portfolio.json            # Shared portfolio data file used by all tasks
├── .env                      # API keys (not committed — see setup)
├── task01_portfolio_risk.py  # Task 01: Risk metrics engine
├── task02_market_data.py     # Task 02: Live market data fetcher
├── task3_Aipowered_portfolio_explainer.py # Task 03: Multi-LLM portfolio explainer
└── task4_Tax_calculator.py   # Task 04: Tax-aware withdrawal calculator
```

---

## Setup & Installation

**1. Clone the repository**
```bash
git clone https://github.com/<your-username>/timecell-intern-jay.git
cd timecell-intern-jay
```

**2. Install dependencies**
```bash
pip install yfinance requests google-genai anthropic openai groq python-dotenv
```

**3. Configure API keys** (for Task 03 only)

Create a `.env` file in the project root:
```env
GEMINI_API_KEY=your_key_here
GROQ_API_KEY=your_key_here       # Optional — free tier available
CLAUDE_API_KEY=your_key_here     # Optional
OPENAI_API_KEY=your_key_here     # Optional
```
> Task 03 auto-detects which keys are present and falls back gracefully. You only need **one** key to run it.

**4. Run any task**
```bash
python task01_portfolio_risk.py
python task02_market_data.py
python task3_Aipowered_portfolio_explainer.py --tone=beginner --critique
python task4_Tax_calculator.py
```

---

## Task 01 — Portfolio Risk Calculator

**File:** `task01_portfolio_risk.py`  
**Points:** 30 | **Difficulty:** Medium

### What It Does

Given a portfolio of assets with allocation percentages and expected crash magnitudes, this script computes 5 key risk metrics that a wealth manager would care about:

| Metric | Formula | Purpose |
|--------|---------|---------|
| `post_crash_value` | `Σ(weight_i × (1 + crash_i)) × total_value` | How much survives a worst-case crash |
| `runway_months` | `post_crash_value / monthly_expenses` | Months of financial survival post-crash |
| `ruin_test` | `PASS if runway > 12 months` | The core solvency check |
| `largest_risk_asset` | `max(allocation × |crash|)` | The biggest threat to the portfolio |
| `concentration_warning` | `True if any asset > 40%` | Diversification flag |

### My Approach

I extensively used Antigravity Copilot to generate the underlying logic and code structure. I guided the AI to implement the surviving fraction formula — `Σ(weight_i × (1 + crash_i/100))` — as a single generator expression in `compute_risk_metrics()` to keep it readable and verifiable.

The key design decision was **separating validation from computation**. I prompted the AI to ensure `validate_portfolio()` runs first and asserts all invariants (allocations sum to 100, crash percentages are negative, etc.) before any math happens, making errors meaningful rather than cryptic.

### Bonus Features Implemented

**Dual Scenario Analysis (Worst Case vs Moderate):**
```
compute_dual_scenario(portfolio)
```
The moderate scenario is computed by halving each asset's crash magnitude (e.g., BTC -80% worst → -40% moderate). Both scenarios are printed side-by-side in a single table for direct comparison. This is something a real wealth manager would want — not just the "nuclear scenario" but a realistic stress test too.

**CLI Bar Chart (no matplotlib):**
```
print_bar_chart(portfolio)
```
A pure-ASCII allocation visualization using Unicode block characters (`█` and `░`). No external plotting libraries — runs anywhere with a UTF-8 terminal.

### Edge Cases Tested

I instructed Antigravity to write a full test suite (`run_tests()`) that covers:
- ✅ Standard portfolio — validates math against expected values
- ✅ 100% cash portfolio — concentration warning triggers
- ✅ Zero monthly expenses — infinite runway (no divide-by-zero crash)
- ✅ Total wipeout (-100% crash) — FAIL result
- ✅ Exactly 12 months runway → FAIL (boundary: strictly `> 12`, not `>= 12`)
- ✅ Invalid allocations (don't sum to 100%) → rejected with a clear message

### Sample Output
```
  ── Worst Case vs Moderate (50%) ──
  ┌───────────────────────┬──────────────────┬──────────────────┐
  │Metric                 │Worst Case        │Moderate          │
  ├───────────────────────┼──────────────────┼──────────────────┤
  │Post-Crash Value       │₹ 5,700,000.00    │₹ 7,850,000.00    │
  │Runway (months)        │71.25             │98.12             │
  │Ruin Test              │PASS              │PASS              │
  │Largest Risk Asset     │BTC               │BTC               │
  │Concentration Warning  │✓ No              │✓ No              │
  └───────────────────────┴──────────────────┴──────────────────┘
```

---

## Task 02 — Live Market Data Fetcher

**File:** `task02_market_data.py`  
**Points:** 20 | **Difficulty:** Easy

### What It Does

Fetches real-time prices for crypto, stocks, and commodities from free public APIs and prints a clean bordered table with timestamps in IST.

**APIs Used:**
- **CoinGecko** (free, no key) → Crypto prices (BTC, ETH, SOL, DOGE)
- **yfinance** (free, wraps Yahoo Finance) → Stocks (NIFTY50 via `^NSEI`, Sensex via `^BSESN`) and Commodities (Gold futures via `GC=F`)

### My Approach

I worked with Antigravity to design a resilient fetcher. The central design principle is: **never crash the pipeline for a single asset failure**. I directed the AI to wrap every individual fetch in a `try/except`, log the error, record a `✗ FAILED` status, and move on. This ensures partial data is retrieved even if one API fails.

I also had the AI build a **routing system** using a dispatch dictionary:
```python
fetchers = {
    "crypto":    lambda a: fetch_crypto_price(a["symbol"]),
    "stock":     lambda a: fetch_stock_price(a["symbol"], a.get("name")),
    "commodity": lambda a: fetch_commodity_price(a["symbol"], a.get("name")),
}
```
This makes it trivial to add new asset types without modifying the core fetch loop.

### Sample Output
```
  Asset Prices — fetched at 2025-05-01 16:45:12 IST
  ┌──────────┬──────────────┬──────────┬────────┐
  │ Asset    │    Price     │ Currency │ Status │
  ├──────────┼──────────────┼──────────┼────────┤
  │ BTC      │ 94,521.30    │ USD      │ ✓      │
  │ NIFTY50  │ 24,132.80    │ INR      │ ✓      │
  │ GOLD     │  3,341.50    │ USD/oz   │ ✓      │
  └──────────┴──────────────┴──────────┴────────┘

  Fetched 3/3 assets successfully.
```

---

## Task 03 — AI-Powered Portfolio Explainer

**File:** `task3_Aipowered_portfolio_explainer.py`  
**Points:** 30 | **Difficulty:** Hard

### What It Does

This is the most complex script. It uses LLMs to generate a plain-English risk explanation of a portfolio, then optionally has a **different** LLM critique the first explanation for accuracy.

### My Approach

I used Antigravity Copilot to integrate multiple LLMs and handle the response parsing. **The core challenge with LLM outputs is consistency.** Initially, simple prompts resulted in outputs that were all over the place in structure, length, and format. I iterated on the internal prompt structure with the AI:

**Iteration 1 — Naive:**
> "Explain this portfolio's risks to a non-expert investor."

Problem: responses were paragraphs with no extractable structure.

**Iteration 2 — Section headers:**
> "Return your answer in these sections: Risk Summary, What's Going Well, Change, Verdict."

Problem: headers were inconsistently formatted (sometimes with colons, sometimes without, sometimes bold, sometimes not).

**Iteration 3 — Final (strict format enforcement):**
> "Follow this EXACT format with these EXACT headers: `**Risk Summary:**` ... `**Verdict:**` [Exactly one word: Aggressive | Balanced | Conservative]"

This + regex parsing (`parse_explanation()`) gave me reliable structured output. The key insight was **constraining the verdict to 3 exact words** — the model respected this almost 100% of the time.

### Prompt Shown In Code

```python
def build_portfolio_explanation_prompt(portfolio: dict, tone: str = "beginner") -> str:
```

The full prompt is in the code and embeds:
- Portfolio numbers (total value, expenses, runway)
- Asset breakdown with exact percentages
- Tone guidelines (see below)
- Strict output format specification
- Word count constraint (150–200 words)

### Tone System (Bonus)

I implemented 3 distinct tone profiles that change the entire register of the explanation:

| Tone | Target Audience | Style |
|------|----------------|-------|
| `beginner` | First-time investor | Jargon-free, analogies, warm |
| `experienced` | 3-5 year investor | Direct, uses standard terms |
| `expert` | Finance professional | Quantitative, Sharpe ratio, tail risk |

```bash
python task3_Aipowered_portfolio_explainer.py --tone=expert
python task3_Aipowered_portfolio_explainer.py --tone=beginner --critique
```

### Multi-LLM Fallback & Critique (Bonus)

The script supports **Gemini, Groq (Llama 3), Claude, and OpenAI**. It tries them in order — if one fails or has no key, it automatically switches to the next. This was a key resilience feature: the script never fails just because one API is down.

The **critique mode** (`--critique` flag) sends the first explanation to a *different* LLM provider for a second opinion on accuracy. Both the original provider and critique provider are identified in the output.

```
  ℹ️  Original explanation by: Google Gemini
  ℹ️  Critique by: Groq Llama 3
```

### What Worked, What Didn't

- **What worked:** Strict format headers + regex parsing was very reliable
- **What didn't initially:** Asking the model to be "concise" — it ignored this without a hard word count
- **Key learning:** LLMs respond much better to constraints ("exactly one word") than suggestions ("be brief")

---

## Task 04 — Tax-Aware Withdrawal Calculator

**File:** `task4_Tax_calculator.py`  
**Points:** 20 | **Difficulty:** Open (My Choice)

### What I Built & Why

For Task 04, I collaborated with Antigravity to build a **Tax-Aware Withdrawal Planner** — a tool that answers the question every HNI investor eventually faces:

> *"I need ₹5 lakh next month. Which assets should I sell, and how much tax will I actually pay?"*

This is squarely in Timecell's product space (wealth management for HNI Indian families) and is a real, unsolved pain point — most investors don't know their after-tax returns until their CA tells them in March.

### Indian Tax Rules Implemented (FY 2024-25)

| Asset Class | LTCG Threshold | LTCG Rate | STCG Rate | Exemption |
|-------------|---------------|-----------|-----------|-----------|
| Equity/Index | 365 days | 12.5% | 20% | ₹1.25 lakh/year |
| Crypto (BTC) | 36,500 days (never) | 30% flat | 30% flat | None |
| Commodity (Gold) | 1,095 days (3 years) | 20% | Slab rate | None |
| Cash | N/A | 0% | 0% | — |

> Crypto is special in Indian tax law — it's always taxed at 30% flat with no LTCG benefit and no loss offset against other asset classes.

### Core Algorithm: Tax-Efficient Sell Order

```python
sell_order = sorted(results, key=lambda r: (
    0 if r.gain_type == "LOSS" else 1,
    r.effective_tax_rate
))
```

The algorithm sells assets in this priority:
1. **Losses first** — realize capital losses to offset gains (tax-loss harvesting)
2. **Lowest tax rate next** — minimize tax leakage on the withdrawal
3. Only sells as much of each asset as needed to meet the withdrawal target

### Tax-Loss Harvesting Detection

If any asset is sitting at a loss > ₹10,000, the tool flags it as a **harvesting opportunity** — meaning you could sell it to generate a capital loss that offsets taxable gains elsewhere in the portfolio.

### Auto-Type Detection

The tool auto-maps known asset names to their tax type if the `type` field is missing from the JSON — `BTC → crypto`, `NIFTY50 → equity_index`, `GOLD → commodity`. This means it works with the same `portfolio.json` used by Tasks 01–03 without modification.

### Sample Output
```
========================================================================
  TAX-AWARE WITHDRAWAL REPORT  |  Jay Patoliya

  ASSET TAX BREAKDOWN
  -----------------------------------------------------------------------
  Asset      Type           Days  Gain Type    Gross Gain          Tax  Rate
  -----------------------------------------------------------------------
  BTC        crypto          400d  [LTCG]    Rs   228,750   Rs  68,625  30.0%
    |- LTCG @ 30.0%
  NIFTY50    equity_index    400d  [LTCG]    Rs   487,125   Rs  45,266  12.5%
    |- LTCG @ 12.5% | Rs125k exemption applied

  WITHDRAWAL PLAN  (Target: Rs500,000)
  -----------------------------------------------------------------------
  Sell order: losses first >> then lowest tax-rate assets
  Asset      Sell Amount       Tax Cost    Net In Hand  Type
  -----------------------------------------------------------------------
  CASH              Rs   305,000      Rs         0   Rs   305,000  NO_GAIN
  NIFTY50           Rs   195,000      Rs    18,170   Rs   176,830  LTCG
  -----------------------------------------------------------------------
  TOTAL             Rs   500,000      Rs    18,170   Rs   481,830

  Effective Tax Rate: 3.6%
========================================================================
```

---

## AI Tools & Prompt Engineering

### Tools Used
- **Antigravity Copilot** — primary AI coding assistant used for generating the codebase, structuring the logic, and handling edge cases.

### How I Used AI for Code Generation

Instead of writing everything manually from scratch, I used Antigravity Copilot extensively to generate the code for all four tasks. Here are the core prompts I gave to the AI to generate the solutions:

**Task 01 Prompt:**
> *"Create a Python script for Task 1 that calculates post-crash value, runway months, ruin test, largest risk asset, and concentration warning. Make sure it validates the JSON, handles edge cases like zero expenses or 100% cash, and writes a test suite."*

**Task 02 Prompt:**
> *"Write a script for Task 2 that fetches live market data for crypto, stocks, and gold using free APIs like CoinGecko and yfinance. Make it resilient so one failure doesn't crash the whole script, and print it in a nice table."*

**Task 03 Prompt:**
> *"Build an AI portfolio explainer using Gemini. Add a fallback to other models like Groq, Claude, and OpenAI. Also, make it parse the output into a structured format and allow different tones (beginner, experienced, expert). Ensure it handles missing environment variables gracefully."*

**Task 04 Prompt:**
> *"For the open task, let's build a Tax-Aware Withdrawal Calculator for Indian tax rules. It should figure out whether assets are LTCG or STCG based on holding periods, and calculate the most tax-efficient way to withdraw a specific amount, prioritizing selling losses first."*

By providing clear, structured requirements, Antigravity was able to generate robust, production-ready code which I then reviewed and refined.

---

## What I Added Beyond the PDF

These features were not specified in the assessment document. I added them because they make the tools meaningfully more useful:

### 1. Multi-LLM Fallback Router (Task 03)
The PDF says "use any LLM API." I built a router that supports 4 providers (Gemini, Groq, Claude, OpenAI) and automatically falls back to the next available one if the first fails. This makes Task 03 functional even when a specific API is down or rate-limited — critical for a production-grade tool.

**Why it matters:** Real fintech products can't afford single points of failure in their AI layer.

### 2. Tax-Aware Withdrawal Planner (Task 04 — my own idea)
The PDF suggested generic ideas like "CLI tool for portfolio tracking." I chose a tax-aware withdrawal calculator because it's a specific, high-value problem for HNI investors — the exact audience Timecell serves.

**Why it matters:** A client asking "how much should I sell?" is asking the wrong question. The right question is "how much do I need to sell to receive ₹X after tax?" This tool answers that.

### 3. Input Resilience in Task 03
If no `.env` file exists, the script prompts the user interactively for API keys instead of crashing. This makes it usable out-of-the-box without any configuration.

**Why it matters:** Developer ergonomics — first-run experience should be smooth.

### 4. Full Test Suite in Task 01
The PDF did not require tests. I had Antigravity generate 6 tests with hand-verified expected values, including boundary conditions (exactly 12 months → FAIL, not PASS).

**Why it matters:** Math bugs in a financial tool are silent and dangerous. Tests catch them before the client presentation.

### 5. portfolio.json as Shared Data Layer
All four tasks read from the same `portfolio.json` file. This was a deliberate design choice — it means changing the portfolio once automatically updates the analysis across all tools.

**Why it matters:** Consistency between risk metrics, AI explanations, and tax calculations matters. They should all operate on the same data.

---

## Hardest Part & How I Approached It

The hardest part was **ensuring robust error handling and consistency in LLM outputs (Task 03)**.

While Antigravity generated the core scripts rapidly, LLMs are non-deterministic. Initially, the output generated by Gemini wasn't structured properly, causing the regex parsing to fail. I had to iteratively refine the prompt within the script to treat the internal prompt as a strict **contract**.

Here are the 4 prompt iterations showing increasing efficiency and structural control:

**Iteration 1 (Naive & Open-ended):**
> *"Explain this portfolio's risks to a non-expert investor."*
> **Result:** Highly inefficient for code. Produced verbose, unstructured paragraphs that were impossible to parse programmatically.

**Iteration 2 (Adding semantic structure):**
> *"Explain this portfolio's risks. Include a risk summary, what's going well, what to change, and a verdict (Aggressive, Balanced, or Conservative)."*
> **Result:** Better content, but the LLM changed header names randomly (e.g., "Things going well:", "The Verdict:") and added conversational filler, breaking regex parsing.

**Iteration 3 (Enforcing Markdown headers):**
> *"Explain this portfolio. Use exact headers: **Risk Summary:**, **What's Going Well:**, **What to Consider Changing:**, **Verdict:**. Don't add any extra text."*
> **Result:** Much more reliable parsing, but the verdict was still conversational (e.g., "Verdict: I believe this portfolio is balanced.") instead of a strict enum.

**Iteration 4 (Final strict contract & constraints):**
> *"Follow this EXACT format with these EXACT headers: ... **Verdict:** [Exactly one word: Aggressive | Balanced | Conservative]. Keep it to 150-200 words total. Do NOT add any text before or after the formatted sections."*
> **Result:** 100% parsing success rate. The constraints forced the LLM to act predictably, acting as a reliable data transformation pipeline rather than a chat bot.

A secondary challenge was **Windows terminal encoding** — Python's default `cp1252` encoding on Windows caused `₹` and `█` characters to throw `UnicodeEncodeError` when running the AI-generated code. I worked with the copilot to identify the root cause and implement the `sys.stdout.reconfigure(encoding="utf-8")` fix across the scripts.

---
