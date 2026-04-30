import os
import json
import re
import sys

# Import the LLM SDKs (Errors handled gracefully if missing)
try:
    from google import genai
    from google.genai import errors as gemini_errors
except ImportError:
    genai = None

try:
    from anthropic import Anthropic, APIError as AnthropicAPIError
except ImportError:
    Anthropic = None

try:
    from openai import OpenAI, APIError as OpenAIAPIError
except ImportError:
    OpenAI = None

try:
    from groq import Groq
except ImportError:
    Groq = None

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ==========================================
# 🔑 API KEYS CONFIGURATION 🔑
# ==========================================
def load_env_file():
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    val = val.strip().strip("'\"")
                    if val and key.strip() not in os.environ:
                        os.environ[key.strip()] = val

load_env_file()

KEYS = {
    "GEMINI": os.environ.get("GEMINI_API_KEY", ""),
    "CLAUDE": os.environ.get("CLAUDE_API_KEY", ""),
    "OPENAI": os.environ.get("OPENAI_API_KEY", ""),
    "GROQ": os.environ.get("GROQ_API_KEY", ""),
}

def count_valid_keys() -> int:
    return sum(1 for key in KEYS.values() if key and "YOUR_" not in key)

def check_and_prompt_api_keys(wants_critique: bool = False) -> bool:
    """Ensure we have enough API keys. Returns True if critique can run (>= 2 keys)."""
    if count_valid_keys() >= 2:
        return wants_critique
        
    print(f"\n--- API Key Configuration ---")
    if wants_critique:
        print("Critique mode requires at least TWO valid API keys.")
    else:
        print("At least ONE valid API key is required to run.")
        
    print("Please enter your API keys below (press Enter to skip):")
    
    if not KEYS["GEMINI"]:
        KEYS["GEMINI"] = input("Enter Google Gemini API Key: ").strip()
    if wants_critique and count_valid_keys() >= 2: return True
        
    if not KEYS["GROQ"]:
        KEYS["GROQ"] = input("Enter Groq API Key: ").strip()
    if wants_critique and count_valid_keys() >= 2: return True
        
    if not KEYS["CLAUDE"]:
        KEYS["CLAUDE"] = input("Enter Anthropic Claude API Key: ").strip()
    if wants_critique and count_valid_keys() >= 2: return True
        
    if not KEYS["OPENAI"]:
        KEYS["OPENAI"] = input("Enter OpenAI API Key: ").strip()
        
    valid_count = count_valid_keys()
    
    if valid_count == 0:
        print("\n[ERROR] Not enough API keys provided. At least ONE key is required. Exiting.")
        sys.exit(1)
        
    if wants_critique and valid_count < 2:
        print("\n[INFO] Only 1 API key provided. Disabling critique mode.")
        return False
        
    return wants_critique

# ── Tone Presets ─────────────────────────────────────────
TONE_GUIDELINES = {
    "beginner": (
        "- Write like you're explaining to a friend who has never invested before\n"
        "- Avoid ALL financial jargon — if you must use a term, explain it in parentheses\n"
        "- Use everyday analogies (e.g., 'think of it like putting all your eggs in one basket')\n"
        "- Be warm, reassuring, but honest about risks\n"
        "- Keep sentences short and simple"
    ),
    "experienced": (
        "- Write for someone who has invested for a few years and understands basics\n"
        "- You can use terms like 'allocation', 'diversification', 'drawdown' without explanation\n"
        "- Be direct and analytical — they can handle blunt feedback\n"
        "- Reference specific numbers and percentages freely\n"
        "- Keep it concise and actionable"
    ),
    "expert": (
        "- Write for a finance professional or CFA-level reader\n"
        "- Use proper financial terminology: Sharpe ratio, beta, correlation, tail risk\n"
        "- Be precise and quantitative — reference exact allocations and expected drawdowns\n"
        "- Skip pleasantries, go straight to the analysis\n"
        "- You may suggest advanced instruments (hedging, options, rebalancing bands)"
    ),
}

# --- PROMPT BUILDER ---

def build_portfolio_explanation_prompt(portfolio: dict, tone: str = "beginner") -> str:
    """
    Build a structured prompt with portfolio data embedded.
    """
    if tone not in TONE_GUIDELINES:
        raise ValueError(f"Invalid tone '{tone}'. Choose from: {list(TONE_GUIDELINES.keys())}")

    assets_summary = "\n".join([
        f"- {a['name']}: {a['allocation_pct']}% allocation, expected crash: {a['expected_crash_pct']}%"
        for a in portfolio["assets"]
    ])

    total_value = portfolio["total_value_inr"]
    months_coverage = (
        "unlimited" if portfolio["monthly_expenses_inr"] == 0
        else f"{total_value / portfolio['monthly_expenses_inr']:.0f}"
    )

    prompt = f"""You are a friendly, honest financial advisor explaining a portfolio to a non-expert investor.

Your job: Write a brief, plain-English assessment of the portfolio's risk. Be honest but empathetic.

== PORTFOLIO ==
Total Value: ₹{total_value:,}
Monthly Expenses: ₹{portfolio['monthly_expenses_inr']:,}
Months of Runway (pre-crash): {months_coverage} months

Assets:
{assets_summary}

== YOUR RESPONSE FORMAT ==
Follow this EXACT format with these EXACT headers:

**Risk Summary:**
[3-4 sentences. Plain English assessment. Talk about what worries you most.]

**What's Going Well:**
[One specific, concrete thing the investor is doing right. Reference actual asset names and percentages.]

**What to Consider Changing:**
[One specific, actionable change. Explain WHY with numbers.]

**Verdict:**
[Exactly one word: Aggressive | Balanced | Conservative]

== TONE GUIDELINES ==
{TONE_GUIDELINES[tone]}

== RULES ==
- Be specific: reference actual asset names and percentages from the portfolio above
- Be honest: don't sugarcoat red flags
- Be helpful: give reasons for every piece of criticism
- Keep it to 150-200 words total
- Do NOT add any text before or after the formatted sections
"""
    return prompt


# --- INDIVIDUAL API CALLERS ---

def call_groq(prompt: str, api_key: str) -> str:
    if not Groq: raise ImportError("groq library not installed.")
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile", 
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500
    )
    return response.choices[0].message.content

def call_gemini(prompt: str, api_key: str) -> str:
    if not genai: raise ImportError("google-genai library not installed.")
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
    return response.text

def call_claude(prompt: str, api_key: str) -> str:
    if not Anthropic: raise ImportError("anthropic library not installed.")
    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-3-haiku-20240320",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text

def call_openai(prompt: str, api_key: str) -> str:
    if not OpenAI: raise ImportError("openai library not installed.")
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500
    )
    return response.choices[0].message.content


# --- THE FALLBACK ROUTER ---

def get_ai_explanation_with_fallback(prompt: str, skip_provider: str = None) -> dict:
    """Tries configured LLM APIs one by one."""
    providers = [
        {"name": "Google Gemini", "key": KEYS["GEMINI"], "func": call_gemini},
        {"name": "Groq Llama 3", "key": KEYS["GROQ"], "func": call_groq},
        {"name": "Anthropic Claude", "key": KEYS["CLAUDE"], "func": call_claude},
        {"name": "OpenAI GPT", "key": KEYS["OPENAI"], "func": call_openai},
    ]

    for provider in providers:
        if skip_provider and provider["name"] == skip_provider:
            continue
        api_key = provider["key"].strip()
        if not api_key or "YOUR_" in api_key:
            continue

        print(f"  [Router] Attempting to connect to {provider['name']}...")
        
        try:
            raw_text = provider["func"](prompt, api_key)
            print(f"  [Router] ✅ Success using {provider['name']}!")
            return {"text": raw_text, "provider": provider['name']}
        except Exception as e:
            print(f"  [Router] ⚠️ {provider['name']} failed: {e}")
            print(f"  [Router] Automatically switching to next available provider...\n")

    raise RuntimeError("All configured AI providers failed or no valid keys were provided.")


def parse_explanation(raw_text: str) -> dict:
    """Extract structured fields using regex."""
    result = {}
    sections = {
        "risk_summary": r"\*\*Risk Summary:?\*\*\s*(.*?)(?=\*\*What's Going Well:?\*\*|$)",
        "doing_well": r"\*\*What's Going Well:?\*\*\s*(.*?)(?=\*\*What to Consider Changing:?\*\*|$)",
        "change": r"\*\*What to Consider Changing:?\*\*\s*(.*?)(?=\*\*Verdict:?\*\*|$)",
    }
    
    for key, pattern in sections.items():
        match = re.search(pattern, raw_text, re.DOTALL | re.IGNORECASE)
        if match: result[key] = match.group(1).strip()
    
    verdict_match = re.search(r"\*\*Verdict:?\*\*\s*(.*?)$", raw_text, re.DOTALL | re.IGNORECASE)
    if verdict_match:
        result["verdict"] = verdict_match.group(1).split('\n')[0].strip()
        
    return result


def _wrap_text(text: str, width: int) -> list[str]:
    """Word-wrap text to a given width."""
    words = text.split()
    lines, current = [], ""
    for word in words:
        if len(current) + len(word) + 1 <= width:
            current = f"{current} {word}" if current else word
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]

def print_raw_response(raw_text: str, provider: str):
    """Print the raw LLM response in a bordered box."""
    print(f"\n  ┌── RAW LLM RESPONSE ({provider}) ─────────────────────┐")
    for line in raw_text.strip().split("\n"):
        display = line[:70] + "..." if len(line) > 70 else line
        print(f"  │ {display}")
    print("  └─────────────────────────────────────────────────────┘")

def print_structured_output(parsed: dict):
    """Print the parsed/structured output as a clean table."""
    verdict_icons = {"Aggressive": "🔴", "Balanced": "🟡", "Conservative": "🟢"}
    print("\n  ┌── STRUCTURED OUTPUT ─────────────────────────────────┐")
    print("  │")
    for key, title, icon in [("risk_summary", "Risk Summary:", "📊"), 
                             ("doing_well", "What's Going Well:", "✅"), 
                             ("change", "What to Consider Changing:", "⚠️")]:
        if key in parsed:
            print(f"  │  {icon} {title}")
            for line in _wrap_text(parsed[key], 60):
                print(f"  │     {line}")
            print("  │")
    if "verdict" in parsed:
        icon = verdict_icons.get(parsed["verdict"], "❓")
        print(f"  │  {icon} Verdict: {parsed['verdict']}")
        print("  │")
    print("  └─────────────────────────────────────────────────────┘")

def print_critique(critique_text: str):
    print("\n  ┌── CRITIQUE (accuracy check) ─────────────────────────┐")
    for line in critique_text.strip().split("\n"):
        display = line[:70] + "..." if len(line) > 70 else line
        print(f"  │ {display}")
    print("  └─────────────────────────────────────────────────────┘")

def critique_explanation(portfolio: dict, explanation: str, skip_provider: str = None) -> dict:
    """
    FIX #2: Have a DIFFERENT AI critique the explanation.
    If skip_provider is specified, avoid that provider.
    Returns both text AND provider name for transparency.
    """
    assets_data = json.dumps(portfolio["assets"], indent=2)
    critique_prompt = f"""You are a senior financial risk analyst reviewing an AI-generated portfolio explanation.
    
    == PORTFOLIO DATA ==
    {portfolio}
    
    == EXPLANATION TO CRITIQUE ==
    {explanation}
    
    == YOUR REVIEW ==
    Check for: Accuracy, Missing Risks, Verdict correctness, Overall Grade
    """
    
    print("\n  [Router] Running critique pass with a DIFFERENT AI provider...")
    try:
        response_data = get_ai_explanation_with_fallback(critique_prompt, skip_provider=skip_provider)
        return {
            "text": response_data["text"],
            "provider": response_data["provider"]  # ← NEW: Return provider name
        }
    except Exception as e:
        return {
            "text": f"[Critique failed: {e}]",
            "provider": "Unknown"
        }


if __name__ == "__main__":
    tone = "beginner"
    run_critique = True
    

    #Option 1: Get portfolio from user

    def get_portfolio_from_user() -> dict:
        """
        Ask user to input portfolio details interactively.
        """
        # Prompt for total value
        total_value = int(input("Total Portfolio Value (in INR): "))
        
        # Prompt for monthly expenses
        monthly_expenses = int(input("Monthly Expenses (in INR): "))
    
        # Prompt for assets (loop until user finishes)
        assets = []
        while True:
            asset_input = input("Asset Name (e.g., BTC, NIFTY50) [comma-separated allowed]: ").strip()
            if not asset_input:
                break
                
            asset_names = [a.strip() for a in asset_input.split(',')]
            
            try:
                alloc_input = input(f"Allocation % for {', '.join(asset_names)}: ").strip()
                allocations = [float(a.strip()) for a in alloc_input.split(',')]
                
                crash_input = input(f"Expected Crash % for {', '.join(asset_names)}: ").strip()
                crashes = [float(c.strip()) for c in crash_input.split(',')]
                
                if len(allocations) != len(asset_names) or len(crashes) != len(asset_names):
                    print("Error: Number of allocations and crashes must match the number of assets. Please try again.")
                    continue
                    
                for name, alloc, crash in zip(asset_names, allocations, crashes):
                    assets.append({
                        "name": name,
                        "allocation_pct": alloc,
                        "expected_crash_pct": crash
                    })
            except ValueError:
                print("Error: Please enter valid numbers. Use comma-separated values if multiple assets.")
        
        return {
            "total_value_inr": total_value,
            "monthly_expenses_inr": monthly_expenses,
            "assets": assets
        }
    
    
    
    ## Option 2: Load portfolio from file
    def load_portfolio_from_file(filepath: str) -> dict:
        """Load portfolio from a JSON file."""
        with open(filepath, 'r') as f:
            portfolio = json.load(f)
        return portfolio

    portfolio_file="portfolio.json"
    if portfolio_file:
        portfolio = load_portfolio_from_file(portfolio_file)
    else:
        use_example = input("Use example portfolio for testing? (y/n): ").strip().lower()
        if use_example == 'y':
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
        else:
            portfolio = get_portfolio_from_user()
    
    


    for arg in sys.argv[1:]:
        if arg.startswith("--tone="):
            tone = arg.split("=", 1)[1]
        elif arg == "--critique":
            run_critique = True
        elif arg == "--help":
            print("\nUsage: python task3_gemini.py [OPTIONS]")
            print("\nOptions:")
            print("  --tone=beginner     Simple, jargon-free (default)")
            print("  --tone=experienced  More technical, direct")
            print("  --tone=expert       Full financial terminology")
            print("  --critique          Run a second LLM pass to check accuracy")
            print("  --help              Show this help message")
            sys.exit(0)

    run_critique = check_and_prompt_api_keys(wants_critique=run_critique)
    
    print("=" * 62)
    print("PORTFOLIO EXPLAINER (HIGH-AVAILABILITY MODE)")
    print("=" * 62)
    print(f"\n  Tone: {tone}")
    
    prompt = build_portfolio_explanation_prompt(portfolio, tone=tone)
    
    try:
        response_data = get_ai_explanation_with_fallback(prompt)
        raw_text = response_data["text"]
        provider = response_data["provider"]
        
        # 1. Print RAW API Response
        print_raw_response(raw_text, provider)
        
        # 2. Parse and print STRUCTURED Output
        structured = parse_explanation(raw_text)
        print_structured_output(structured)
        
        print("\n  [PARSED JSON]")
        print(f"  {json.dumps(structured, indent=2, ensure_ascii=False)}")
        
        # 3. BONUS: Critique
        if run_critique:
            print("\n  [Step 2] Critiquing with a different AI provider...")
            critique_data = critique_explanation(portfolio, raw_text, skip_provider=provider)
            print_critique(critique_data["text"])
    
            # Show which AI did what
            print(f"\n  ℹ️  Original explanation by: {provider}")
            print(f"  ℹ️  Critique by: {critique_data['provider']}")
            
    except Exception as e:
        print(f"\n[CRITICAL ERROR] {e}")
