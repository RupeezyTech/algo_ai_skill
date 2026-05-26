---
name: indian-algo-trading
description: >
  Write production-quality Python automated trading strategies for the Indian stock market.
  Covers the full lifecycle: backtesting, optimization, paper trading, and live deployment
  across equity, F&O, currency derivatives, and MCX commodities. Bakes in best practices
  for risk management, position sizing, order handling, and Indian market-specific rules.
  Rupeezy/Vortex is the primary broker with a template for community broker adapters.

  MANDATORY TRIGGERS: Use this skill whenever the user mentions algo trading, automated
  trading, trading bot, trading strategy, backtest, backtesting, strategy code, quant
  strategy, systematic trading, or any task involving writing Python code to trade on
  Indian stock exchanges (NSE, BSE, MCX). Also trigger when the user mentions Rupeezy,
  Vortex API, vortex-api, or asks about F&O strategy automation, options selling bot,
  intraday strategy, or positional strategy. Even if the user just says "write a strategy"
  or "help me automate my trading" — use this skill.
version: 1.1.9
---

# Indian Algo Trading — Strategy Writing Skill

Write production-quality Python trading strategies for Indian markets. Every strategy
generated must be safe enough to run with real money — not just a backtest toy.

## Before Writing Any Code

### Step 1: Understand the User's Intent

Ask these questions (skip any the user has already answered):

1. **What are you trading?** Equity, F&O (futures/options), currency derivatives, or commodities?
2. **Live trading or backtesting?** Are you writing code to execute real trades, or to test a strategy on historical data?
3. **Which broker?** Rupeezy/Vortex (primary), or another broker? Read `references/brokers/rupeezy-vortex.md` for Rupeezy. For others, check if a broker adapter exists in `references/brokers/`.
4. **Deployment mode?** This question changes what files you generate. There are exactly two answers:

   **a) Self-hosted** (anything the user runs themselves: own laptop, own VPS, own server, cron on their machine, headless box, EC2 instance, etc.). The strategy package **MUST include** `login.py` and `auth.py`. `login.py` runs a loopback HTTP server on `127.0.0.1:8765/callback`, opens the SSO URL in the browser via `webbrowser.open()`, captures the `?auth=...` query param, calls `client.exchange_token()`, and caches `access_token` to `.access_token.json`. `auth.py` exposes `get_client()` which the rest of the strategy uses. **Do not ask the user to copy/paste an auth_token.** Do not generate "manual OAuth paste" code. See Critical Rule 8 — it is non-negotiable.

   **b) Rupeezy container platform** (user uploads a zip via the Rupeezy MCP, platform manages the container). The strategy package **MUST NOT include** `login.py` or `auth.py`. The platform injects `VORTEX_ACCESS_TOKEN` at runtime; `main.py` uses zero-arg `VortexAPI()` directly.

   If the user is ambiguous, ask. If they say "local", "my machine", "my laptop", "my server", "self-hosted", or "I'll run it myself" — that is answer (a) and you MUST scaffold the loopback OAuth server. Headless boxes do not change this — the server binds to 127.0.0.1 and the user opens the SSO URL on whichever device has a browser; SSH port-forwarding handles the callback.
5. **Risk tolerance?** Max loss per trade, max daily loss, max drawdown they're comfortable with. If they don't know, suggest safe defaults: 1% per trade, 3% daily, 10% max drawdown.

### Step 2: Discuss Strategy Design

Before writing a single line of code, discuss:

- **Entry logic** — What signal triggers a buy/sell? (indicator crossover, price action, options premium, etc.)
- **Exit logic** — Stop-loss (mandatory), target price, trailing stop, time-based exit?
- **Position sizing** — Fixed quantity, fixed rupee amount, ATR-based, or Kelly?
- **Scheduling** — When does this run? Market hours only? Pre-market? Specific times?
- **Hedging** — If F&O: naked or hedged? (Warn strongly against naked options selling)

### Step 3: Route to the Right References

Based on what the user needs, read the appropriate reference files:

| User's Need                                    | Reference File                         |
| ---------------------------------------------- | -------------------------------------- |
| Writing a new strategy                         | `references/strategy-patterns.md`      |
| Risk management / position sizing              | `references/risk-management.md`        |
| Backtesting a strategy                         | `references/backtesting.md`            |
| Indian market rules (expiry, timings, margins) | `references/indian-market.md`          |
| Production error handling                      | `references/error-handling.md`         |
| Code quality / testing / logging               | `references/code-quality.md`           |
| Rupeezy/Vortex API specifics                   | `references/brokers/rupeezy-vortex.md` |

**Advanced modules — suggest proactively when the context calls for it:**

| Context                            | Reference File                           |
| ---------------------------------- | ---------------------------------------- |
| F&O / options strategy             | `references/options-greeks.md`           |
| "When should I run this strategy?" | `references/regime-detection.md`         |
| Using FII/DII/OI data              | `references/india-data-edge.md`          |
| Executing large orders             | `references/execution-alpha.md`          |
| "Is my backtest reliable?"         | `references/robustness-testing.md`       |
| Running multiple strategies        | `references/portfolio-construction.md`   |
| Preventing emotional overrides     | `references/psychological-guardrails.md` |
| Tax efficiency                     | `references/tax-optimization.md`         |
| Performance / speed issues         | `references/python-performance.md`       |

Do not wait for the user to ask for advanced modules. If someone asks for a moving average
strategy, generate it, then suggest: "This would benefit from regime detection to avoid
sideways markets. Want me to add that?" If a backtest shows 40% CAGR, warn: "This needs
robustness testing before going live."

---

## Code Architecture Rules

Every strategy MUST follow this structure. No exceptions.

### Separation of Concerns

**Self-hosted strategies (user runs the code on their own machine) — REQUIRED files:**

```
main.py          → Entry point, initialization, scheduling
login.py         → REQUIRED. Loopback SSO callback server. User runs it once per ~24h.
auth.py          → REQUIRED. Credential helpers: get_client(), save_token().
strategy.py      → Signal generation ONLY (no order placement here)
execution.py     → Order placement, fill tracking (no signal logic here)
risk_manager.py  → Position sizing, exposure checks, drawdown limits
guardrails.py    → Psychological guardrails (daily loss limits, cooldowns)
config.py        → All configurable parameters (no hardcoded values)
```

**Rupeezy container platform — REQUIRED files (no login.py / auth.py):**

```
main.py          → Entry point; uses zero-arg VortexAPI() (platform injects credentials)
strategy.py      → Signal generation
execution.py     → Order placement
risk_manager.py  → Risk checks
guardrails.py    → Guardrails
config.py        → All parameters
```

The deciding question: does the user run the Python script themselves? If yes → self-hosted, ship `login.py` + `auth.py`. If they upload a zip via the Rupeezy MCP → container, skip them. There is no third mode.

Signal generation and execution are ALWAYS in separate modules. This allows:

- Testing signals independently of execution
- Swapping execution between backtest and live without changing signal logic
- Reviewing signal quality without wading through order management code

### Configuration Externalized

Every tunable parameter lives in `config.py` or environment variables:

- Symbols, quantities, thresholds, indicator periods
- Risk parameters (max loss, position size, drawdown limit)
- Scheduling parameters (start time, end time, frequency)
- Broker credentials (ALWAYS environment variables, never in code)

### Risk Manager as Gatekeeper

Every order passes through the risk manager before submission:

```python
# This pattern is mandatory in every strategy
def place_order(signal):
    if not risk_manager.approve(signal):
        logger.warning(f"Risk manager rejected: {signal.reason}")
        return None
    return execution.submit_order(signal)
```

The risk manager checks: position size limits, daily loss limits, drawdown limits,
margin availability, and exposure concentration. Read `references/risk-management.md`
for the full implementation.

### Structured Logging

Every trade decision logged with: timestamp, symbol, action, reason, price, quantity,
and current P&L state. Use Python's `logging` module, never `print()`.

```python
logger.info(f"BUY signal | {symbol} | price={price} | reason={reason} | risk={risk_pct}%")
```

### Graceful Shutdown

Handle SIGTERM/SIGINT. On shutdown: cancel pending orders, optionally square off
positions, log final state. This is critical for container deployments where the
platform can stop your strategy at any time.

---

## Critical Rules — Violations Cause Real Money Loss

These are non-negotiable. Every strategy must follow them.

### 1. NEVER hardcode instrument tokens

Tokens change daily. Identify instruments by their **ticker** (`<EXCHANGE>:<SYMBOL>`) and let the SDK resolve everything else. On `vortex-api >= 2.1.8` (Rupeezy/Vortex), the ticker is accepted directly by every API: `place_order(ticker=...)`, `historical_candles(ticker=...)`, `get_order_margin(ticker=...)`, `client.quotes(instruments=["NSE:RELIANCE"], ...)`, `wire.subscribe(ticker=...)`, and every feed tick carries a `tick["ticker"]` field.

```python
# WRONG — will break tomorrow
token = 2885
client.place_order(exchange="NSE_EQ", token=2885, ...)

# RIGHT — ticker form, never goes stale
client.place_order(ticker="NSE:RELIANCE", ...)

# Need the instrument's metadata (lot size, tick size, ISIN, expiry)?
inst = client.instruments.get_by_ticker("NSE:RELIANCE")
print(inst.lot_size, inst.tick, inst.isin)
```

Ticker conventions for the Rupeezy master:

- **Equities**: `"NSE:RELIANCE"`, `"BSE:TATAMOTORS"`
- **Indices**: append `IDX` — `"NSE:NIFTYIDX"`, `"NSE:BANKNIFTYIDX"`, `"BSE:SENSEXIDX"`. The underlying `symbol` field stays bare (`"NIFTY"`), so F&O option-chain filtering uses `symbol == "NIFTY"`.
- **F&O contracts**: each contract has its own ticker; use `client.instruments.all_by_underlying("NSE_FO", "NIFTY")` to iterate a chain.

For brokers that don't have a ticker-first surface, use whatever symbolic identifier the broker exposes — never raw numeric tokens.

### 2. NEVER hardcode lot sizes

Lot sizes change with corporate actions and SEBI directives. Read them off the instrument object: `client.instruments.get_by_ticker("NSE:NIFTYIDX").lot_size`. For other brokers, look them up from the instrument master.

### 3. ALWAYS use stop-losses

No strategy ships without a stop-loss. If the user explicitly asks for no stop-loss,
warn them and add it anyway with a wide buffer. Document the risk.

### 4. ALWAYS check margin before placing orders

Call the margin API before submitting. If insufficient, log it and skip — don't crash.

### 5. ALWAYS handle order rejections

Orders get rejected (insufficient margin, price out of range, exchange down). Every
`place_order` call must have error handling with try/except.

### 6. NEVER ignore partial fills

Track fill state precisely. A "buy 100" order might fill 60 now and 40 later, or
fill 60 and get cancelled for the rest. The strategy must handle this.

### 7. ALWAYS set IST timezone explicitly

```python
import pytz
IST = pytz.timezone("Asia/Kolkata")
```

All time comparisons use IST. Never rely on system timezone.

### 8. Self-hosted strategies MUST ship `login.py` + `auth.py` — no exceptions

If the user is running the strategy on their own machine (laptop, VPS, EC2, headless box, anywhere they invoke `python main.py` themselves), the generated package **MUST include** `login.py` (loopback OAuth server) and `auth.py` (credential helpers). This is not a suggestion, not a default, not "prefer when convenient". It is mandatory.

**Why this rule exists.** End users routinely confuse `auth_token` with `access_token`:

- `auth_token` — the short-lived `?auth=...` query parameter that lands on the OAuth callback URL. Single-use, expires in minutes.
- `access_token` — the long-lived bearer token that `client.exchange_token(auth_token)` returns. This is what every API call uses, what you cache, and what you pass into `VortexAPI`.

Every "my strategy stopped working after a day" bug report traces back to a user pasting an `auth_token` where the SDK wanted an `access_token`. The loopback server pattern eliminates the confusion at the source by doing the exchange automatically.

**What `login.py` does (this is the only correct implementation):**

1. Spins up a stdlib `HTTPServer` on `127.0.0.1:8765/callback`.
2. Opens `client.login_url(callback_param=...)` in the browser via `webbrowser.open(...)`.
3. Captures the `?auth=...` query param from the redirect.
4. Calls `client.exchange_token(auth_token)` automatically — user never sees this token.
5. Caches `client.access_token` to `.access_token.json`.

`main.py` and the rest of the strategy read the cached token via `auth.get_client()`. The user runs `python login.py` once per ~24h.

**What you must NOT generate** (these are all wrong, regardless of how the user phrases the request):

- Code that prints "paste your auth code here" or `input("auth code: ")`.
- Code that reads `VORTEX_ACCESS_TOKEN` from `.env`. The `.env` file holds only `VORTEX_API_KEY` and `VORTEX_APPLICATION_ID` (both persistent); the `access_token` lives in `.access_token.json`, populated by `login.py`.
- Code that does `client.exchange_token(...)` with a hand-pasted argument anywhere in the strategy.
- A `broker.py` or similar abstraction that exposes a manual auth_code parameter to the user.

**Edge cases that do NOT exempt you from this rule:**

- Headless box / no GUI on the strategy machine → user opens the SSO URL on whatever device has a browser; SSH local port-forwarding (`ssh -L 8765:127.0.0.1:8765 user@server`) makes the loopback callback reach the box. Still scaffold `login.py`.
- "Vortex portal might not allow `127.0.0.1` as a redirect URI" → it does. The user configures it themselves under their app's settings in the API Center.
- Minimal-dependencies request → `login.py` uses only stdlib (`http.server`, `webbrowser`, `urllib.parse`, `threading`). No extra deps.

**User's one-time setup** (instruct them to do this; do not do it in code):

In the Rupeezy API Center → their app → set the redirect URL to `http://127.0.0.1:8765/callback`. Tell them this exactly once when you ship the strategy.

The scaffolder (`scripts/scaffold_strategy.py --deployment self-hosted`) generates these files correctly. When writing strategies from scratch, replicate that pattern.

**This rule does NOT apply to the Rupeezy container platform.** When the user uploads a zip via the Rupeezy MCP, the platform injects `VORTEX_ACCESS_TOKEN` at runtime. In that mode, `main.py` does zero-arg `VortexAPI()` and **must not include** `login.py` or `auth.py` (they'd be dead code that breaks at runtime — no browser, no writable disk for the token cache).

### 9. Connect WebSocket BEFORE placing orders

If you connect after placing an order, that order's status update is lost. Always
connect WebSocket feed as the first step after authentication.

### 10. NEVER short sell illiquid equities intraday

Short selling equities carries auction risk. If the stock hits upper circuit, you
cannot exit and face penalties of 20%+ above your sell price. Check volume and circuit
band before shorting. Prefer F&O for short positions. Read `references/indian-market.md`
for full details on auction risk.

### 11. ALWAYS respect tick sizes

Every instrument has a minimum tick size (from the instrument master's `tick` column).
Order prices MUST be rounded to the nearest valid tick. Placing an order at ₹100.03
when the tick size is ₹0.05 will get rejected.

```python
# Round price to nearest tick
def round_to_tick(price, tick_size):
    return round(round(price / tick_size) * tick_size, 2)

# Example: tick_size = 0.05
# round_to_tick(100.03, 0.05) → 100.05
# round_to_tick(247.12, 0.05) → 247.10
```

Look up tick size from the instrument master alongside the token. Never assume a
tick size — it varies by instrument and exchange.

### 12. ALWAYS respect Daily Price Range (DPR)

Exchanges set a daily price range (circuit limit band) for each instrument. Orders
with prices outside this range are rejected by the broker's OMS before they even
reach the exchange. This commonly trips up limit orders and stop-loss orders.

- For limit orders: ensure price is within the DPR band
- For stop-loss orders: ensure trigger price is within DPR
- If placing orders far from current market price (e.g., deep stop-losses), check
  that the price falls within the allowed range
- DPR information is available from the broker's quote/market data

### 13. Account for calendar spread margin removal on expiry day

On expiry day, calendar spread margin benefits are removed. Margin can jump 5-10x
(e.g., ₹26K → ₹2.6L per lot). Check if any spread leg expires today and ensure
full margin is available. Read `references/risk-management.md` for details.

### 14. NSE does NOT provide a public data API

NSE does not offer any direct data API for programmatic access. All market data
(quotes, historical candles, order book) must come through your broker's API.
Alternative data like FII/DII flows, OI, delivery percentages — if available — come
from the broker's API or third-party data providers, NOT from NSE directly. Never
write code that tries to scrape or call NSE endpoints.

---

## Backtesting Standards

Every backtest must include realistic friction. Fantasy backtests with zero costs
produce fantasy returns.

- **Transaction costs**: STT (equity 0.1%, futures 0.05%, options 0.1%) + brokerage +
  exchange charges. Read `references/indian-market.md` for current rates.
- **Slippage**: Minimum 0.05% for liquid stocks, 0.1-0.2% for illiquid. Double it
  for F&O near expiry.
- **Commission parameter**: Set `commission=0.001` minimum in backtesting.py (covers
  STT + brokerage for most cases). Adjust higher for options.

When a backtest shows extraordinary returns (>30% CAGR), always flag it and suggest
robustness testing: walk-forward analysis, Monte Carlo simulation, and out-of-sample
validation. Read `references/robustness-testing.md`.

If the strategy has tunable parameters, ALWAYS suggest parameter optimization with
heatmap visualization. This shows the user how sensitive the strategy is to parameter
choices — fragile strategies that only work with exact parameters are overfitted.

---

## Strategy Output Format

The file list depends on deployment mode (see Step 1 question 4 and Critical Rule 8). There are only two correct shapes.

**Self-hosted (user runs `python main.py` themselves):**

```
strategy_name/
├── main.py              # Entry point. Calls auth.get_client(); never touches credentials directly.
├── login.py             # REQUIRED. Loopback OAuth server. Run once per ~24h.
├── auth.py              # REQUIRED. get_client() + save_token() helpers.
├── strategy.py          # Signal generation
├── risk_manager.py      # Risk checks
├── config.py            # All parameters
├── requirements.txt     # vortex-api>=2.1.8, python-dotenv, pandas, numpy, pytz
├── .env.example         # VORTEX_API_KEY + VORTEX_APPLICATION_ID only (never VORTEX_ACCESS_TOKEN)
└── README.md            # What this strategy does, parameters, risks, login flow instructions
```

**Rupeezy container platform (user uploads a zip via the Rupeezy MCP):**

```
strategy_name/
├── main.py              # Uses zero-arg VortexAPI() — platform injects VORTEX_ACCESS_TOKEN
├── strategy.py          # Signal generation
├── risk_manager.py      # Risk checks
├── config.py            # All parameters
├── requirements.txt     # vortex-api>=2.1.8, pandas, numpy, pytz (NO python-dotenv)
└── README.md            # What this strategy does, parameters, risks
```

Container packages **must not** include `login.py` or `auth.py` (no browser, no writable disk for token cache — they'd break at runtime). Self-hosted packages **must always** include both.

For backtest-only strategies, a single file is acceptable but must still include: risk management, realistic costs, and clear parameter documentation. Backtests don't need `login.py` if they only read cached historical data and never call live APIs — but if they touch `VortexAPI`, the self-hosted layout applies.

---

## Proactive Suggestions

After generating any strategy, consider suggesting these improvements:

1. **Regime detection** — "This strategy assumes the market is always [trending/sideways].
   Adding regime detection would pause it during unfavorable conditions."
2. **Robustness testing** — "Before going live, let's validate this with Monte Carlo
   simulation to check if the edge is real."
3. **Psychological guardrails** — "Want me to add daily loss limits and a consecutive
   loss pause to prevent overtrading?"
4. **Tax optimization** — "This strategy generates short-term gains taxed at 20%.
   Adjusting the holding period could save 7.5% in taxes."
5. **Execution quality** — "For orders larger than 5% of average daily volume, VWAP
   execution would reduce slippage."
6. **Performance** — If the code uses Python loops over price data, flag it:
   "This loop can be vectorized with pandas for a 50x speedup."
