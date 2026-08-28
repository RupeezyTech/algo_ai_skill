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
version: 1.2.1
---

# Indian Algo Trading — Strategy Writing Skill

Write production-quality Python trading strategies for Indian markets. Every strategy must be safe enough to run with real money.

## Who You Are Talking To

The user is a **trader, not a programmer**. Assume they cannot read Python, cannot review your code for correctness, and cannot debug an error message. You are the only reviewer this code will ever have — every safeguard is your responsibility, not theirs.

- **Ask questions they can answer.** Trading vocabulary (strike, stop-loss, lot, expiry, intraday) is fine. Software vocabulary (container, env var, dependency, SDK, token, deployment) is not.
- **Never block on a question they can't answer.** Pick a safe default, state it in one line, move on.
- **Explain in plain English before and after** — confirm the strategy before coding (Step 2), explain what you built after (Strategy Output Format).
- **Walk them through anything they must do themselves.** Give one command per line and say what a good result looks like. Never say "set an environment variable" — say "open the file called `.env` and put your key after the `=`", and prefer writing the file for them.
- **Money in rupees, never bare percentages**, in anything the user reads.

## Before Writing Any Code

### Step 1: Understand the User's Intent

Ask (skip any already answered):

1. **Asset class** — equity, F&O, currency, commodities? If cash equity: are any symbols F&O-eligible? Those are CAS scrips — continuous trading ends 3:15 PM and their exit deadline differs (Rule 16).
2. **Live or backtest?**
3. **Broker** — Rupeezy/Vortex (default; see `references/brokers/rupeezy-vortex.md`) or other (check `references/brokers/`)?
4. **Where should it run?** Ask this in plain words — do **not** say "self-hosted", "container", "deployment" or "MCP" to the user:
   > "Two choices: **(a) Rupeezy runs it for you** — you install nothing and it keeps trading even when your laptop is off. **(b) You run it yourself** — it lives on your own computer or a rented server, and only trades while that machine is on and the program is running."

   If the user is unsure, says "whichever is easier", or has no server → pick **(a)**, say so in one line, and move on. Never stall here.
   Internal mapping: (a) = Rupeezy container — zero-arg `VortexAPI()`, no login files. (b) = self-hosted — MUST ship `login.py`+`auth.py` (Rule 8).
5. **Risk tolerance** — ask in rupees, not percent: "How much are you OK losing on one bad trade, and what's the most you'd accept losing in a single day before the bot stops?" If they answer in percent or don't know, ask for total capital and convert. Defaults if unknown: 1% of capital per trade / 3% per day / 10% max drawdown — and **always state them back in rupees**.

### Step 2: Discuss Strategy Design

Before any code, agree on: entry logic; exit logic (stop-loss is mandatory — and on a CAS scrip it cannot be a resting exchange-side SL after 3:15 PM, Rule 16); position sizing; scheduling (agree the intraday exit deadline explicitly — before 3:15 PM for cash CAS scrips, 3:20-3:25 for non-CAS cash and F&O); hedging (warn against naked options selling; note a cash/F&O hedge cannot be rebalanced 3:15-3:40).

Then **confirm before coding.** Write the strategy back as a numbered list of plain-English rules plus one worked example with real rupee numbers on their stated capital. Ask "Is that exactly what you want it to do?" and wait. If they correct anything, restate the whole list rather than patching it verbally.

### Step 3: Route to the Right References

Load only what's relevant. Core references — read when topic comes up:

| Need | File |
|---|---|
| New strategy | `references/strategy-patterns.md` |
| Risk / position sizing | `references/risk-management.md` |
| Backtesting | `references/backtesting.md` |
| Indian market rules (expiry, timings, closing auction/CAS, square-off, margins) | `references/indian-market.md` |
| Error handling | `references/error-handling.md` |
| Code quality / testing | `references/code-quality.md` |
| Rupeezy/Vortex SDK — auth, instruments, orders, constants | `references/brokers/rupeezy-vortex.md` |
| Vortex depth — backtest prep, lifecycle examples, error handling | `references/brokers/rupeezy-vortex-advanced.md` (only when you need it) |

**Load the minimum.** Two rules that save most of the budget:

- Load `indian-market.md` unconditionally for any strategy trading cash equity intraday — the closing-auction timings (Rule 16) are not something to infer.
- **If you scaffolded, you do NOT need `code-quality.md` for order tracking.** The scaffolder writes a working `order_tracker.py` and `market_session.py`; reading the canonical listings only duplicates what is already on disk. Open it only to debug tracker behaviour or to write tests.

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

The square-off path must be session-aware: for cash equity in a CAS scrip after 3:15 PM there is no continuous book and a market order will fail (and is rejected outright after 3:25). Either route a LIMIT order into the auction inside the ±3% band, or log loudly that the position is carrying to settlement. Never let the handler report success on an unfilled square-off.

---

## Critical Rules — Violations Cause Real Money Loss

These are non-negotiable. Every strategy must follow them.

> **⚠ Silent-until-live failure modes: Rules 1, 11, 12, 13, 15, 16.** These pass `py_compile`, `pytest`, and often a WebSocket smoke test — they blow up only on the first real broker interaction, on a later trading day when something rolls, or at 3:15 PM when the closing auction starts (Rule 16). Walk these six explicitly whenever you scaffold or modify a strategy. Each rule's body names the specific failure.

### 1. NEVER hardcode instrument tokens

Tokens change daily. Pass `ticker="<EXCHANGE>:<SYMBOL>"` to every Vortex API (`place_order`, `historical_candles`, `get_order_margin`, `client.quotes`, `wire.subscribe`) on `vortex-api >= 2.1.8`. Never build a ticker from `exchange:symbol` (breaks on F&O) — read `inst.ticker` from the master. Feed ticks are tagged with `tick.get("ticker")` (best-effort enrichment; `exchange`/`token` always present).

```python
client.place_order(ticker="NSE:RELIANCE", ...)              # RIGHT
inst = client.instruments.get_by_ticker("NSE:RELIANCE")     # for lot_size, tick, isin
```

Ticker shapes: equities `"NSE:RELIANCE"`; indices append `IDX` (`"NSE:NIFTYIDX"`) but the F&O `symbol` field stays bare (so option-chain filter is `symbol == "NIFTY"`); F&O contracts each have their own ticker — use `client.instruments.all_by_underlying("NSE_FO", "NIFTY")` to enumerate. For other brokers, use whatever symbolic identifier they expose — never raw numeric tokens.

### 2. NEVER hardcode lot sizes

Lot sizes change with corporate actions and SEBI directives. Read them off the instrument object: `client.instruments.get_by_ticker("NSE:NIFTYIDX").lot_size`. For other brokers, look them up from the instrument master.

### 3. ALWAYS use stop-losses

Every strategy ships with one. If the user explicitly refuses, warn and add a wide-buffer stop anyway; document the risk.

**CAS caveat:** on a CAS scrip the exchange cancels untriggered stop-loss and disclosed-quantity orders at 3:15 PM (Rule 16). A resting broker-side SL is not protection through the close — and on Rupeezy a **GTT is not a substitute, it stops triggering at 3:15 PM too**. Nothing broker-side protects a cash position through the auction. Either flatten before 3:15 PM, or hold the stop **in-process** and, if it fires after 3:15, send a LIMIT order into the auction inside the ±3% band.

### 4. ALWAYS check margin before placing orders

Call `get_order_margin()` first. If insufficient, log and skip — don't crash.

### 5. ALWAYS handle order rejections

Every `place_order` wrapped in try/except. Rejections happen routinely (margin, price-out-of-range, exchange down).

### 6. NEVER ignore partial fills

A "buy 100" can fill 60 now + 40 later, or 60 then cancel. Track fill state precisely.

### 7. ALWAYS set IST timezone explicitly

**The strategy container runs in UTC.** `datetime.now()` / `utcnow()` and other naive clocks return UTC, not IST — so without an explicit timezone every market-hours and scheduling check is off by 5h30m. Make every time value timezone-aware in IST.

```python
import pytz
from datetime import datetime
IST = pytz.timezone("Asia/Kolkata")
now = datetime.now(IST)   # timezone-aware IST — NOT datetime.now() / utcnow()
```

Never rely on the system timezone (it is UTC) or on naive datetimes.

### 8. Self-hosted strategies MUST ship `login.py` + `auth.py`

For self-hosted (anywhere the user runs `python main.py` themselves, including headless boxes), generate `login.py` and `auth.py`. No exceptions. Never generate `input("auth code: ")`, `VORTEX_ACCESS_TOKEN` in `.env`, or a `broker.py` that exposes a manual auth_code. Run `scripts/scaffold_strategy.py --deployment self-hosted` or replicate its output; the full pattern is in `references/brokers/rupeezy-vortex.md`.

Why: `auth_token` (the `?auth=...` redirect param) and `access_token` (the long-lived bearer) are different. Users confuse them. The loopback HTTP server on `127.0.0.1:8765/callback` does `client.exchange_token()` automatically so the user never sees either token.

Does **not** apply to the container platform — there `VORTEX_ACCESS_TOKEN` is injected at runtime, `main.py` uses zero-arg `VortexAPI()`, and `login.py`/`auth.py` would be dead code that breaks at runtime.

### 9. Order updates have split authority across surfaces. Never sleep-poll.

`VortexFeed.on_order_update` is the only way to learn an order changed in real time. Connect the feed *before* any `place_order` so the first push isn't lost. The callback fires for **five** envelope types — `order`, `trade`, `sl_trigger`, `gtt_order`, `position_conversion` — all signal that state changed for some `order_id`. See `references/brokers/rupeezy-vortex.md` for the payload table and per-type meaning.

**Authority is split between surfaces** because REST orderbook can lag postbacks by tens of seconds on the same order:

- **Postback `data.status`** is authoritative for **status transitions** — believe terminal postbacks immediately, don't wait for REST.
- **`client.orders()` / `client.trades()`** are authoritative for **fill quantities, traded_price, avg fill** — refresh from these on every postback (coalesced 500 ms debounce so a many-fill order doesn't trip the REST rate limit).
- **Downgrade guard**: once terminal is recorded for an order_id, a later non-terminal REST row is stale — merge fill fields but DO NOT overwrite the status.

**Do NOT poll** `client.orders()` / `client.order_history()` / `client.trades()` on a sleep-loop. Refresh-on-postback is event-driven — REST is called *only* when a postback indicates a change.

**Order outcomes are events, not return values.** Live strategies wire `tracker.on_terminal = strategy.on_order_terminal` to receive `(order_id, status)` callbacks for every terminal transition. **Do NOT call `tracker.wait()` inside the strategy main loop** — `wait()` is the script / test / `cancel_and_wait()` primitive only; its `timeout` is required (pass `float("inf")` for forever). Call `tracker.initialize()` once at startup before placing orders so historical fills don't fire spurious callbacks.

Terminal-status detection is **substring-based** to catch broker-decorated forms (`REJECTED_BY_RMS`, `AMO_CANCELLED`); canonical tokens are `COMPLETED` / `EXECUTED` (same state — postback uses COMPLETED, orderbook uses EXECUTED), `REJECTED`, `CANCELLED`. Rejection-reason field name varies by surface (`status_message` / `error_reason` / `message`) — use `tracker.rejection_reason(order_id)`.

The reference `OrderTracker` in `references/code-quality.md` (and the scaffolded `order_tracker.py`) implements all of this — wire it, don't re-implement.

**CAS mass-cancel:** at 3:15 PM the exchange cancels every untriggered SL and disclosed-quantity order on CAS scrips, one message per order, producing a burst of exchange-initiated `CANCELLED` postbacks. `on_order_terminal` must not read these as the user withdrawing protection, and must never infer a position was closed from an SL cancellation.

### 10. NEVER short sell illiquid equities intraday

**Settlement-auction** risk (a different mechanism from the Closing Auction Session in Rule 16): stock hits upper circuit → you can't exit → 20%+ penalty above your sell price. Check volume + circuit band before shorting; prefer F&O for shorts. A cash short in a CAS scrip must additionally be flat before 3:15 PM — after that there is no continuous book and the resting stop-loss has been cancelled. Details in `references/indian-market.md`.

### 11. ALWAYS respect tick sizes

Round prices to the instrument's `tick` (from `client.instruments.get_by_ticker(...).tick`). Mis-tick prices get rejected.

```python
def round_to_tick(price, tick): return round(round(price / tick) * tick, 2)
```

### 12. ALWAYS respect Daily Price Range (DPR)

Exchanges set a daily circuit-limit band per instrument. Orders outside it are rejected by the broker's OMS before reaching the exchange — common cause of failed deep stop-losses and ambitious targets. Read DPR from the broker's quote/market data and clamp `price` / `trigger_price` accordingly.

On a CAS scrip during the closing auction a second, tighter band applies: ±3% of the auction reference price (VWAP of 3:00-3:15 PM). Clamp to `min(DPR, CAS band)` for any auction-routed order, and compute the reference price yourself from 3:00 PM ticks if the broker doesn't publish it. See Rule 16 and `references/indian-market.md` §1A/§11.

### 13. Account for calendar spread margin removal on expiry day

On expiry day, calendar-spread margin benefits are removed and required margin can jump 5-10x (₹26K → ₹2.6L per lot). Check if any spread leg expires today and pre-flight margin. See `references/risk-management.md`.

### 14. NSE has no public data API

All market data (quotes, historical candles, OI, FII/DII, depth) must come through the broker API or third-party providers. Never write code that scrapes or calls NSE endpoints directly.

### 15. Pass SDK enum instances, not their string values

The Vortex SDK runtime-typechecks every `transaction_type`, `product`, `variety`, `validity`, `mode`, `exchange`, `resolution` argument via `isinstance(value, EnumClass)`. Passing the string value (`"INTRADAY"`) where the SDK expects the enum (`Vc.ProductTypes.INTRADAY`) raises `TypeError: product must be of type ProductTypes` **even though the enum's `.value` IS "INTRADAY"** — the check is class-based, not value-based. Silent until the first live `place_order` / `get_order_margin`; `py_compile` and unit tests don't catch it.

```python
from vortex_api import Constants as Vc

# WRONG — string passes type-hint, fails at runtime on first live call
client.place_order(product="INTRADAY", ...)

# RIGHT — enum instance
client.place_order(product=Vc.ProductTypes.INTRADAY, ...)
```

If you store these in `config.py`, store the enum directly (the scaffolded `config.py` does). Name ≠ value for many `Vc.*` enums (`Vc.VarietyTypes.REGULAR_LIMIT_ORDER.value == "RL"`, `Vc.ExchangeTypes.NSE_EQUITY.value == "NSE_EQ"`), so a stringly-typed config with `getattr(Vc.X, name)` lookup also works but only if you store the **member name**, not the value.

### 16. Cash-equity intraday exits must clear the Closing Auction Session

Since 3 Aug 2026 the cash segment has **three different closes**, so no single market-close constant is correct. **Never hardcode a session time — import `market_session.py`** (the scaffolder generates it; it encodes every boundary below):

```python
import market_session as session

self.segment = session.segment_for(client, "RELIANCE")   # resolve ONCE at startup
if session.should_exit_now(self.segment)[0]:             # not `if now > time(15,25)`
    self.square_off()
```

| Segment | Continuous ends | Then |
|---|---|---|
| Cash **with** F&O contracts (CAS scrip) | **3:15 PM** | Call auction sets the close; random end 3:28-3:30 |
| Cash without F&O contracts | 3:30 PM | Unchanged |
| Equity derivatives | **3:40 PM** | Extended by the CAS framework |

What this breaks in code — the parts no import can fix:

- **Untriggered stop-loss and disclosed-quantity orders are cancelled by the exchange at 3:15 PM**, and on Rupeezy GTTs stop triggering then too. **Nothing broker-side protects a cash position through the auction** (Rule 3). Be flat before 3:15, or send a deliberate auction limit order.
- **Price band** in the auction is ±3% of the 3:00-3:15 VWAP reference price — usually tighter than DPR, so clamp to the narrower (Rule 12). Limit orders only after 3:25; Rupeezy rejects rather than buffers orders during 3:15-3:20.
- **"The close" changed meaning** — it is the auction equilibrium price, and it differs between NSE and BSE for the same stock.
- **No candles exist for a CAS scrip between 3:15 and 3:30 PM** — not empty bars, none at all. `df.iloc[-1]` at 3:22 returns the 3:14 bar, so "current price" is silently stale, and "wait for the next bar" loops never fire. Drive closing-window logic off the clock, never off bar arrival.
- **Resolve the segment at runtime**, never from a hardcoded symbol list — the F&O universe moves with SEBI reviews.

The **pre-open realigns to the same shape on 7 Sep 2026** (random close 9:08-9:10); `session.pre_open_schedule()` branches on the date for you.

Full timeline, order-type table, carry-forward and broker-layer rules: `references/indian-market.md` §1A and §1B.

---

## Backtesting Standards

Every backtest must include realistic friction. Zero-cost backtests produce fantasy returns.

- **Costs**: STT (eq 0.1%, fut 0.05%, opt 0.1%) + brokerage + exchange. `commission=0.001` minimum in backtesting.py (raise for options). Rates in `references/indian-market.md`.
- **Slippage**: ≥0.05% liquid, 0.1-0.2% illiquid; double near F&O expiry.
- **CAS structural break (3 Aug 2026)**: for CAS scrips the daily close switched from a last-30-minutes VWAP to the auction equilibrium price. Any series spanning that date has a regime break in its Close column — flag it, don't fit close-anchored signals across it, and rebuild intraday volume profiles from post-CAS data only.
- **Intraday exit fills**: model the last continuous fill at 3:15 PM for CAS scrips, not 3:25/3:29. A backtest that exits "at the close" is assuming an auction fill at the equilibrium price — state and stress that assumption.

If CAGR > 30%, flag and require robustness testing (walk-forward, Monte Carlo, OOS). If parameters are tunable, run grid optimization with heatmap. See `references/robustness-testing.md`.

---

## Strategy Output Format

**Both modes:** `main.py`, `strategy.py`, `risk_manager.py`, `config.py`, `market_session.py`, `requirements.txt`, `README.md`.

**Scaffold, don't handwrite.** Run `scripts/scaffold_strategy.py` and edit the generated `strategy.py` — the output already satisfies Rules 1, 2, 7, 8, 11, 15 and 16 by construction, and its writes are ASCII-guarded for the container. Handwriting six files from scratch reintroduces every one of those as a memory test.

**Self-hosted only, additionally:** `login.py`, `auth.py`, `.env.example` (with `VORTEX_API_KEY` + `VORTEX_APPLICATION_ID` only — never `VORTEX_ACCESS_TOKEN`). `requirements.txt` includes `python-dotenv`.

**Container only:** `requirements.txt` does NOT include `python-dotenv`; no `.env.example` for credentials (platform injects them).

Backtest-only strategies can be a single file as long as risk management, realistic costs, and parameters are present. If a backtest touches `VortexAPI`, the self-hosted layout applies.

### Mandatory gate before handover

The user cannot review this code — you are the only reviewer. Before handing anything over:

```bash
python scripts/validate_strategy.py <strategy_dir>/
```

Run it on the **whole directory**. Interpret the output yourself; never paste it at the user. Exit 2 (hardcoded token/lot size, NSE scraping) is blocking — fix and re-run. Exit 1 warnings are per-file substring heuristics, so a warning on `strategy.py` (no order code) or `config.py` (no timezone) is expected — confirm each is a false positive against the actual file before dismissing it. The validator does **not** cover the silent-until-live rules (1, 11, 12, 13, 15, 16); hand-check those yourself.

If the script isn't reachable from the install, replicate its checks by hand rather than skipping the gate.

### Explaining the result

The README is the only artifact this user can read. After generating any strategy:

1. **Restate what it does** in 5-8 numbered plain-English lines — no code, no library names.
2. **State the money numbers**: risk per trade, daily stop, and worst observed drawdown, in rupees on their actual capital.
3. **Say what it will not do** — the failure modes it doesn't handle, and what happens if the machine or container stops.
4. **Give the exact run and stop instructions**, one command per line, with expected output.

If CAGR > 30%, say so plainly and unprompted before the user gets excited: numbers that good usually mean the settings were fitted to past data. Then run robustness testing and report the outcome in the same plain terms — read the heatmap yourself rather than handing it over.

---

## Proactive Suggestions

After generating a strategy, offer the relevant ones:

- **Regime detection** when the strategy assumes a single regime (trending OR sideways).
- **Robustness testing** (walk-forward, Monte Carlo) when going live or when CAGR > 30%.
- **Psychological guardrails** (daily loss caps, consecutive-loss pause) on any live strategy.
- **Tax optimization** when holding-period tweaks could move trades from STCG (20%) to LTCG (12.5%).
- **VWAP execution** for orders > 5% of ADV. On CAS scrips the schedule must end by 3:15 PM — compress the profile into 9:15-3:15 and route any residual as one deliberate auction limit order. Pre-Aug-2026 volume profiles overweight the final 30 minutes with liquidity that has moved into the auction.
- **Vectorization** when you see Python loops over price data.
