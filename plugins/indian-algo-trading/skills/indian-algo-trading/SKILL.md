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
version: 1.1.12
---

# Indian Algo Trading — Strategy Writing Skill

Write production-quality Python trading strategies for Indian markets. Every strategy must be safe enough to run with real money.

## Before Writing Any Code

### Step 1: Understand the User's Intent

Ask (skip any already answered):

1. **Asset class** — equity, F&O, currency, commodities?
2. **Live or backtest?**
3. **Broker** — Rupeezy/Vortex (default; see `references/brokers/rupeezy-vortex.md`) or other (check `references/brokers/`)?
4. **Deployment** — self-hosted (user runs `python main.py` themselves; MUST ship `login.py`+`auth.py`, see Rule 8) or Rupeezy container (zip uploaded via MCP; zero-arg `VortexAPI()`, no login files)?
5. **Risk tolerance** — max loss per trade / day / drawdown. Defaults if unknown: 1% / 3% / 10%.

### Step 2: Discuss Strategy Design

Before any code: entry logic, exit logic (stop-loss is mandatory), position sizing, scheduling, hedging (warn against naked options selling).

### Step 3: Route to the Right References

Load only what's relevant. Core references — read when topic comes up:

| Need | File |
|---|---|
| New strategy | `references/strategy-patterns.md` |
| Risk / position sizing | `references/risk-management.md` |
| Backtesting | `references/backtesting.md` |
| Indian market rules (expiry, timings, margins) | `references/indian-market.md` |
| Error handling | `references/error-handling.md` |
| Code quality / testing | `references/code-quality.md` |
| Rupeezy/Vortex SDK | `references/brokers/rupeezy-vortex.md` |

Advanced (suggest proactively when context fits): `options-greeks.md`, `regime-detection.md`, `india-data-edge.md`, `execution-alpha.md`, `robustness-testing.md`, `portfolio-construction.md`, `psychological-guardrails.md`, `tax-optimization.md`, `python-performance.md`. Don't wait for the user to ask — for MA crossover suggest regime detection; for 40% CAGR backtest demand robustness testing.

---

## Code Architecture Rules

Every strategy MUST follow this structure. No exceptions.

### Separation of Concerns

```
main.py          → entry point, initialization, scheduling
strategy.py      → signal generation ONLY (no order placement)
execution.py     → order placement, fill tracking (no signal logic)
risk_manager.py  → position sizing, exposure checks, drawdown limits
guardrails.py    → daily loss limits, cooldowns
config.py        → all configurable parameters
```

**Self-hosted only**, add `login.py` (loopback OAuth server) + `auth.py` (`get_client()` helper). Container packages must not include these. See Rule 8.

Signal generation and execution are always in separate modules so signals can be tested independently and execution can be swapped between backtest and live without touching signal code.

### Configuration Externalized

Every tunable parameter lives in `config.py` or env vars: symbols, quantities, thresholds, indicator periods, risk caps, schedules. Broker credentials always env-var, never in code.

### Risk Manager as Gatekeeper

Every order goes through `risk_manager.approve(signal)` before submission. The manager checks position size, daily loss, drawdown, margin, and concentration. Full implementation in `references/risk-management.md`.

```python
def place_order(signal):
    if not risk_manager.approve(signal):
        logger.warning(f"Risk manager rejected: {signal.reason}")
        return None
    return execution.submit_order(signal)
```

### Structured Logging

Use `logging`, not `print()`. Log every decision with timestamp, symbol, action, reason, price, qty, current P&L.

### Graceful Shutdown

Handle SIGTERM/SIGINT: cancel pending orders, optionally square off, log final state. Critical for container deployments where the platform can stop the strategy any time.

---

## Critical Rules — Violations Cause Real Money Loss

These are non-negotiable. Every strategy must follow them.

### 1. NEVER hardcode instrument tokens

Tokens change daily. Pass `ticker="<EXCHANGE>:<SYMBOL>"` to every Vortex API (`place_order`, `historical_candles`, `get_order_margin`, `client.quotes`, `wire.subscribe`) on `vortex-api >= 2.1.8`. Feed ticks carry `tick["ticker"]`.

```python
client.place_order(ticker="NSE:RELIANCE", ...)              # RIGHT
inst = client.instruments.get_by_ticker("NSE:RELIANCE")     # for lot_size, tick, isin
```

Ticker shapes: equities `"NSE:RELIANCE"`; indices append `IDX` (`"NSE:NIFTYIDX"`) but the F&O `symbol` field stays bare (so option-chain filter is `symbol == "NIFTY"`); F&O contracts each have their own ticker — use `client.instruments.all_by_underlying("NSE_FO", "NIFTY")` to enumerate. For other brokers, use whatever symbolic identifier they expose — never raw numeric tokens.

### 2. NEVER hardcode lot sizes

Lot sizes change with corporate actions and SEBI directives. Read them off the instrument object: `client.instruments.get_by_ticker("NSE:NIFTYIDX").lot_size`. For other brokers, look them up from the instrument master.

### 3. ALWAYS use stop-losses

Every strategy ships with one. If the user explicitly refuses, warn and add a wide-buffer stop anyway; document the risk.

### 4. ALWAYS check margin before placing orders

Call `get_order_margin()` first. If insufficient, log and skip — don't crash.

### 5. ALWAYS handle order rejections

Every `place_order` wrapped in try/except. Rejections happen routinely (margin, price-out-of-range, exchange down).

### 6. NEVER ignore partial fills

A "buy 100" can fill 60 now + 40 later, or 60 then cancel. Track fill state precisely.

### 7. ALWAYS set IST timezone explicitly

```python
import pytz; IST = pytz.timezone("Asia/Kolkata")
```

Never rely on system timezone.

### 8. Self-hosted strategies MUST ship `login.py` + `auth.py`

For self-hosted (anywhere the user runs `python main.py` themselves, including headless boxes), generate `login.py` and `auth.py`. No exceptions. Never generate `input("auth code: ")`, `VORTEX_ACCESS_TOKEN` in `.env`, or a `broker.py` that exposes a manual auth_code. Run `scripts/scaffold_strategy.py --deployment self-hosted` or replicate its output; the full pattern is in `references/brokers/rupeezy-vortex.md`.

Why: `auth_token` (the `?auth=...` redirect param) and `access_token` (the long-lived bearer) are different. Users confuse them. The loopback HTTP server on `127.0.0.1:8765/callback` does `client.exchange_token()` automatically so the user never sees either token.

Does **not** apply to the container platform — there `VORTEX_ACCESS_TOKEN` is injected at runtime, `main.py` uses zero-arg `VortexAPI()`, and `login.py`/`auth.py` would be dead code that breaks at runtime.

### 9. Order updates have split authority across surfaces. Never sleep-poll.

`VortexFeed.on_order_update` is the only way to learn an order changed in real time. Connect the feed *before* any `place_order` so the first push isn't lost. The callback fires for **five** envelope types — all signal that state changed for some `order_id`:

| `msg["type"]` | What changed |
|---|---|
| `"order"` | order status transition |
| `"trade"` | a fill happened (partial or final) |
| `"sl_trigger"` | a stop-loss order triggered into a live order |
| `"gtt_order"` | GTT placement / trigger lifecycle |
| `"position_conversion"` | MIS ↔ CNC conversion |

**Authority is split between surfaces — this matters because the REST orderbook can lag postbacks by tens of seconds on the same order:**

- **Postback `data.status`** — authoritative for **status transitions**. WS pushes arrive within ms. If a postback says terminal (REJECTED / COMPLETED / CANCELLED), believe it immediately and fire your `on_terminal` callback. Don't wait for REST.
- **`client.orders()` / `client.trades()`** — authoritative for **fill quantities, traded_price, and other fields the postback can drop or lag**. Refresh from these on every postback (coalesced 500 ms debounce) to fold in the canonical fill data.
- **Downgrade guard**: once terminal is recorded for an order_id (from a postback), a later non-terminal REST row for that same order_id is **stale** — merge fill fields but DO NOT overwrite the status. `OrderTracker._apply` does this.

Coalescing rule: first postback → 500 ms debounce → one `orders()` + `trades()` call → update local state → if new postbacks landed during the REST calls, refresh again immediately (no further wait). Postbacks during the 500 ms window accumulate for free, so a many-fill order doesn't trip the REST rate limit.

**Do NOT poll** `client.orders()` / `client.order_history()` / `client.trades()` on a sleep-loop. Polling is timer-driven. Refresh-on-postback is event-driven — the REST API is called *only* when a postback indicates something changed.

**Order outcomes are events, not return values.** Live strategies wire `tracker.on_terminal = strategy.on_order_terminal` and receive `(order_id, status)` callbacks for every terminal transition — even if no thread was blocked waiting. **Do NOT call `tracker.wait()` inside the strategy main loop** (`next(tick)` or signal handlers); `wait()` is the script / test / `cancel_and_wait()` primitive only. Its `timeout` is required (pass `float("inf")` to wait forever). Call `tracker.initialize()` once at startup before placing any orders so `on_terminal` doesn't fire spuriously for orders that were already terminal earlier in the day.

**Terminal-status detection is substring-based**, not strict set membership. Brokers may decorate canonical tokens (`REJECTED_BY_RMS`, `AMO_CANCELLED`, `EXECUTED_PARTIAL`); normalise via substring match against `("REJECTED", "CANCELLED", "EXECUTED", "COMPLETED")`. Canonical tokens: `"COMPLETED"`/`"EXECUTED"` (same state — postback uses COMPLETED, orderbook uses EXECUTED), `"REJECTED"`, `"CANCELLED"`. The reference `OrderTracker._terminal_token()` handles this.

**Rejection reason field name varies by surface** — postback envelope uses `status_message`, REST orderbook row uses `error_reason`, `place_order` response uses `message`. Always check all three (or use `tracker.rejection_reason(order_id)` which does).

```python
# Minimal sketch — use OrderTracker (references/code-quality.md) in real strategies.
import threading, time

dirty, lock, running = set(), threading.Lock(), [False]

def on_postback(ws, msg):
    oid = (msg.get("data") or {}).get("order_id")
    if not oid: return
    with lock:
        dirty.add(oid)
        if not running[0]:
            running[0] = True
            try:
                threading.Thread(target=worker, daemon=True).start()
            except Exception:
                running[0] = False  # reset on thread-start failure
                raise

def worker():
    time.sleep(0.5)  # debounce: let bursty trade postbacks accumulate
    while True:
        with lock:
            if not dirty:
                running[0] = False; return
            dirty.clear()
        book, trades = client.orders(), client.trades()
        # update local state from book + trades; fire any waiter Events here
        # loop — no extra sleep; if more postbacks landed during the API call,
        # the next iteration refreshes immediately.

wire.on_order_update = on_postback   # SDK property name is legacy; receives all 5 types
wire.connect(threaded=True)
```

For the full thread-safe class with `wait(order_id)`, `fills(order_id)`, `avg_fill_price(order_id)`, see `OrderTracker` in `references/code-quality.md`.

### 10. NEVER short sell illiquid equities intraday

Auction risk: stock hits upper circuit → you can't exit → 20%+ penalty above your sell price. Check volume + circuit band before shorting; prefer F&O for shorts. Details in `references/indian-market.md`.

### 11. ALWAYS respect tick sizes

Round prices to the instrument's `tick` (from `client.instruments.get_by_ticker(...).tick`). Mis-tick prices get rejected.

```python
def round_to_tick(price, tick): return round(round(price / tick) * tick, 2)
```

### 12. ALWAYS respect Daily Price Range (DPR)

Exchanges set a daily circuit-limit band per instrument. Orders outside it are rejected by the broker's OMS before reaching the exchange — common cause of failed deep stop-losses and ambitious targets. Read DPR from the broker's quote/market data and clamp `price` / `trigger_price` accordingly.

### 13. Account for calendar spread margin removal on expiry day

On expiry day, calendar-spread margin benefits are removed and required margin can jump 5-10x (₹26K → ₹2.6L per lot). Check if any spread leg expires today and pre-flight margin. See `references/risk-management.md`.

### 14. NSE has no public data API

All market data (quotes, historical candles, OI, FII/DII, depth) must come through the broker API or third-party providers. Never write code that scrapes or calls NSE endpoints directly.

---

## Backtesting Standards

Every backtest must include realistic friction. Zero-cost backtests produce fantasy returns.

- **Costs**: STT (eq 0.1%, fut 0.05%, opt 0.1%) + brokerage + exchange. `commission=0.001` minimum in backtesting.py (raise for options). Rates in `references/indian-market.md`.
- **Slippage**: ≥0.05% liquid, 0.1-0.2% illiquid; double near F&O expiry.

If CAGR > 30%, flag and require robustness testing (walk-forward, Monte Carlo, OOS). If parameters are tunable, run grid optimization with heatmap. See `references/robustness-testing.md`.

---

## Strategy Output Format

**Both modes:** `main.py`, `strategy.py`, `risk_manager.py`, `config.py`, `requirements.txt`, `README.md`.

**Self-hosted only, additionally:** `login.py`, `auth.py`, `.env.example` (with `VORTEX_API_KEY` + `VORTEX_APPLICATION_ID` only — never `VORTEX_ACCESS_TOKEN`). `requirements.txt` includes `python-dotenv`.

**Container only:** `requirements.txt` does NOT include `python-dotenv`; no `.env.example` for credentials (platform injects them).

Backtest-only strategies can be a single file as long as risk management, realistic costs, and parameters are present. If a backtest touches `VortexAPI`, the self-hosted layout applies.

---

## Proactive Suggestions

After generating a strategy, offer the relevant ones:

- **Regime detection** when the strategy assumes a single regime (trending OR sideways).
- **Robustness testing** (walk-forward, Monte Carlo) when going live or when CAGR > 30%.
- **Psychological guardrails** (daily loss caps, consecutive-loss pause) on any live strategy.
- **Tax optimization** when holding-period tweaks could move trades from STCG (20%) to LTCG (12.5%).
- **VWAP execution** for orders > 5% of ADV.
- **Vectorization** when you see Python loops over price data.
