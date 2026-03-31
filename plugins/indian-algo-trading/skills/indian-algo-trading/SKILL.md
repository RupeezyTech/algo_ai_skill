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
version: 1.1.6
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
4. **Deployment mode?** Running on Rupeezy's container platform (auto-auth, no OAuth needed),
   or self-hosted on own machine? All Indian brokers mandatorily use OAuth 2.0 for
   self-hosted strategies — the code must handle the OAuth callback flow to obtain
   an access token. Only container platforms (like Rupeezy's) inject credentials automatically.
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

```
main.py          → Entry point, initialization, scheduling
strategy.py      → Signal generation ONLY (no order placement here)
execution.py     → Order placement, fill tracking (no signal logic here)
risk_manager.py  → Position sizing, exposure checks, drawdown limits
guardrails.py    → Psychological guardrails (daily loss limits, cooldowns)
config.py        → All configurable parameters (no hardcoded values)
```

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

Tokens change daily. Always look them up from the instrument master by symbol.

```python
# WRONG — will break tomorrow
token = 2885

# RIGHT — dynamic lookup
master = client.download_master()
token = lookup_token(master, symbol="RELIANCE", exchange="NSE_EQ")
```

### 2. NEVER hardcode lot sizes

Lot sizes change with corporate actions and SEBI directives. Look them up from the
instrument master.

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

### 8. Connect WebSocket BEFORE placing orders

If you connect after placing an order, that order's status update is lost. Always
connect WebSocket feed as the first step after authentication.

### 9. NEVER short sell illiquid equities intraday

Short selling equities carries auction risk. If the stock hits upper circuit, you
cannot exit and face penalties of 20%+ above your sell price. Check volume and circuit
band before shorting. Prefer F&O for short positions. Read `references/indian-market.md`
for full details on auction risk.

### 10. ALWAYS respect tick sizes

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

### 11. ALWAYS respect Daily Price Range (DPR)

Exchanges set a daily price range (circuit limit band) for each instrument. Orders
with prices outside this range are rejected by the broker's OMS before they even
reach the exchange. This commonly trips up limit orders and stop-loss orders.

- For limit orders: ensure price is within the DPR band
- For stop-loss orders: ensure trigger price is within DPR
- If placing orders far from current market price (e.g., deep stop-losses), check
  that the price falls within the allowed range
- DPR information is available from the broker's quote/market data

### 12. Account for calendar spread margin removal on expiry day

On expiry day, calendar spread margin benefits are removed. Margin can jump 5-10x
(e.g., ₹26K → ₹2.6L per lot). Check if any spread leg expires today and ensure
full margin is available. Read `references/risk-management.md` for details.

### 13. NSE does NOT provide a public data API

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

When generating a complete strategy, output these files:

```
strategy_name/
├── main.py              # Entry point
├── strategy.py          # Signal generation
├── risk_manager.py      # Risk checks
├── config.py            # All parameters
├── requirements.txt     # Dependencies
└── README.md            # What this strategy does, parameters, risks
```

For backtest-only strategies, a single file is acceptable but must still include:
risk management, realistic costs, and clear parameter documentation.

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
