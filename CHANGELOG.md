# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.10] - 2026-05-26

### Added

- **`OrderTracker` — postback-driven, event-callback-based order lifecycle tracking.** Lives canonically in `references/code-quality.md` and the scaffolder ships an equivalent `order_tracker.py` for live strategies. Public API:
  - `tracker.initialize()` — one-time startup seed from `client.orders()` + `client.trades()` so historical (already-terminal) orders don't fire `on_terminal` on the first refresh.
  - `tracker.on_update(ws, msg)` — wired to `wire.on_order_update`; non-blocking, schedules a debounced refresh.
  - `tracker.on_terminal = callback` — fires once per `order_id` when it first reaches `COMPLETED` / `REJECTED` / `CANCELLED`. This is the **primary order-outcome path for live strategies**; runs on the refresh worker thread (callers using it must synchronise shared state).
  - `tracker.wait(order_id, timeout)` — blocking wait. `timeout` is **required** (no default) — pass `float("inf")` to mean forever. Script / test primitive only; do not call from a live strategy main loop.
  - `tracker.cancel_and_wait(order_id, timeout)` — cancel an order and block until the broker confirms terminal state. Returns the actual final status; callers MUST check it before placing a replacement (a fill can race the cancel).
  - `tracker.status / order / fills / avg_fill_price` — read-side accessors for current state.
- **Scaffolder generates the live-strategy state-machine layout by default.**
  - New file `order_tracker.py` (live mode only — skipped in `--type backtest`).
  - `main.py` (live) now wires: `client` → `OrderTracker(client)` → `initialize()` → `Strategy(...)` → `tracker.on_terminal = strategy.on_order_terminal` → `VortexFeed(...)` → `wire.on_order_update = tracker.on_update` → `wire.connect(threaded=True)` → `time.sleep(1)`. Order matters: `initialize` before `place_order`, `on_terminal` wired before `wire.connect`.
  - `strategy.py` (live) gains an `on_order_terminal(self, order_id, status)` method with `COMPLETED` / `REJECTED` / `CANCELLED` branches. The old `on_order_fill` / `on_order_cancel` stubs are gone. `next(tick)` docstring now explicitly forbids `tracker.wait()` inside the strategy main loop.

### Changed

- **Critical Rule 9 fully rewritten — "postback is a signal, orderbook is the truth".** All five postback envelope types (`order`, `trade`, `sl_trigger`, `gtt_order`, `position_conversion`) are listed with what each one signals and where to refresh from. Strategy code no longer parses `msg["data"]` as the new state; it refreshes from `client.orders()` + `client.trades()` (the canonical source of truth). Postbacks are coalesced via a 500 ms debounce so a many-fill order doesn't trip the REST rate limit; after each refresh, if new postbacks arrived during the API calls, the worker refreshes again immediately (no extra debounce wait). Live strategies wire `tracker.on_terminal`; `wait()` is reframed as the script primitive with required `timeout`.
- **`references/brokers/rupeezy-vortex.md` Common Patterns** rewritten around `OrderTracker.on_terminal` + `initialize()`. The previous inline `threading.Event` example is gone in favour of using the class; `cancel_and_wait` shown as the safe kill-before-replace primitive.
- **`references/brokers/rupeezy-vortex.md` `client.orders()` / `client.order_history()` callouts** rewritten so they distinguish between "polling in a sleep-loop" (the anti-pattern) and "postback-driven refresh" (the recommended pattern). `orders()` is now explicitly endorsed as the canonical refresh target.
- **Halved SKILL.md.** Always-loaded content dropped from 405 lines / 22 KB / ~5.5K tokens to ~216 lines / ~11 KB / ~2.8K tokens. No rules removed; only verbosity. Step-1 questions, code-architecture explainer, Critical Rule 8, Strategy Output Format file lists, Backtesting Standards, and Proactive Suggestions were all rewritten as terse bullets pointing to references for detail. Every numbered rule is preserved with the same mandate.

### Fixed

- **Skill was inadvertently teaching order-status polling.** A user-reported output from an earlier revision polled `client.orders()` in a `while time.sleep(N)` loop. Three concrete teaching errors fixed:
  - Critical Rule 9 only said "Connect WebSocket BEFORE placing orders" — explained the consequence of late-connection but didn't forbid polling. An AI could satisfy the rule literally while polling.
  - `references/brokers/rupeezy-vortex.md` documented `client.orders()` and `client.order_history()` with no warning that they were for one-shot inspection.
  - `references/code-quality.md` shipped a `wait_for_order_fill()` function that polled `broker.get_order_status()` in a sleep-loop, with a docstring rationalising "polling instead of events to avoid callback hell". This was the actual teaching source for the failing AI output.
- **Postback callback was reading the inner payload as if it were at the top level.** The SDK passes the full envelope `{"type": ..., "data": {...}, "client_code": ...}` to `on_order_update`; example code was doing `data["order_id"]` instead of `msg["data"]["order_id"]` — would `KeyError` on real traffic. All examples now filter on `msg["type"]` first and unwrap `msg["data"]`.
- **Order-state machine race when thread-start fails.** `OrderTracker.on_update`'s spawn-worker path now uses `try/finally` to reset `_worker_running` if `Thread.start()` raises. Without this, a transient OS thread-resource failure would leave the flag stuck at `True` and silently disable all future refreshes.
- Stale `lookup_token(master, "RELIANCE", "NSE_EQ")` snippet in the broker reference's "Common Patterns / Full Order Lifecycle" example that survived the 1.1.7 ticker rewrite — now uses `ticker="NSE:RELIANCE"`.
- `references/code-quality.md` `OrderTracker._apply` now deduplicates `on_terminal` fires via `_notified_terminal` set, so an order that stays terminal across multiple refreshes only fires the callback once.

## [1.1.9] - 2026-05-26

### Changed

- **Eliminated five places where the skill contradicted itself on the loopback OAuth login.** A clean read by an LLM consumer could previously interpret the manual auth-code paste flow as compliant. Specifically:
  - Step 1 question 4 — "default to the loopback SSO pattern" rewritten as a hard `MUST` with an explicit decision tree ("self-hosted → ship login.py + auth.py" vs "container → don't"). Headless / SSH-only edge case is called out as non-exempting.
  - Code Architecture diagram — the `(self-hosted only)` parenthetical that read as "optional" replaced with two explicit deployment-keyed file lists labelled `REQUIRED`.
  - Critical Rule 8 — promoted from "use the loopback SSO login" (suggestion-flavoured) to "Self-hosted strategies MUST ship login.py + auth.py — no exceptions". Adds an explicit list of patterns that are forbidden (`input("auth code: ")`, `VORTEX_ACCESS_TOKEN` in `.env`, `broker.py` with a manual auth_code parameter) and rebuts three common edge-case excuses (headless box, "portal might not allow localhost", minimal-deps).
  - Strategy Output Format (the section LLMs use as the final file checklist) — was omitting `login.py` and `auth.py` entirely. Now shows two deployment-keyed file lists; container packages explicitly **must not** include `login.py`/`auth.py`.
  - `references/brokers/rupeezy-vortex.md` — deleted the "Advanced (only when the loopback server can't run)" escape hatch that explicitly told the LLM "headless → fall back to manual paste"; replaced with the SSH port-forward recipe. Collapsed the duplicate "Authentication / Self-Hosted OAuth Flow" subsection that was contradicting the Deployment Modes section above it.

## [1.1.7] - 2026-05-26

### Added

- **Loopback SSO login pattern for self-hosted strategies.** New critical Rule 8 in `SKILL.md` requires shipping a `login.py` that spins up a stdlib `HTTPServer` on `127.0.0.1:8765/callback`, opens the SSO URL in the browser, and exchanges the captured `auth_token` for an `access_token` automatically. End users never see either token. Strategies read the cached token via `auth.get_client()`. Eliminates the most common end-user bug (confusing `auth_token` with `access_token`).
- `scripts/scaffold_strategy.py` gained a `--deployment {self-hosted,container}` flag (default `self-hosted`). Self-hosted scaffolds ship `login.py` + `auth.py`; `main.py` calls `get_client()`; `.env.example` carries `VORTEX_API_KEY` + `VORTEX_APPLICATION_ID`; `requirements.txt` pulls in `python-dotenv`. Container scaffolds **skip** the login files entirely: `main.py` does zero-arg `VortexAPI()` (platform injects `VORTEX_ACCESS_TOKEN`), `.env.example` warns against putting broker credentials in `.env`, and `python-dotenv` is dropped from `requirements.txt`. "Next steps" output branches accordingly.
- `references/brokers/rupeezy-vortex.md` Self-Hosted section rewritten with full `login.py` + `auth.py` code listings; manual OAuth flow demoted to an "advanced/headless only" footnote.

### Changed

- **Ticker-first guidance for vortex-api >= 2.1.8.** Critical Rule 1 in `SKILL.md` and the entire `references/brokers/rupeezy-vortex.md` reference now teach identifying instruments by ticker (`"NSE:RELIANCE"`) instead of `(exchange, token)` pairs. Updated examples:
  - `place_order(ticker=...)`, `historical_candles(ticker=...)`, `get_order_margin(ticker=...)`
  - `client.quotes(instruments=["NSE:RELIANCE"], ...)` — tickers accepted directly
  - `wire.subscribe(ticker=..., mode=...)` and reading `tick["ticker"]` from VortexFeed updates
  - `client.instruments.get_by_ticker(...)` / `get_by_exchange_token` / `get_by_isin` / `all_by_underlying` / `filter` replace hand-rolled CSV scanning
- Replaced the broken `from vortex import Client` + `master[master['tradingsymbol']==…]` snippet in `references/backtesting.md` with a working ticker-form `historical_candles` call.
- `references/indian-market.md` tick-size lookup, data-sources table, and "Always download fresh instrument master" sections now point to `client.instruments` for Vortex while remaining broker-agnostic.
- `scripts/validate_strategy.py` — the "hardcoded token" violation message now recommends the ticker form first, with `client.instruments.get_by_ticker(...)` as the metadata-access path.
- Documented the IDX ticker convention for indices (`"NSE:NIFTYIDX"`, `"NSE:BANKNIFTYIDX"`, `"BSE:SENSEXIDX"`) — the suffix lives on the ticker, the underlying symbol stays bare.
- Bumped `requirements.txt` example from `vortex-api>=1.0.0` to `vortex-api>=2.1.8`.

### Notes

- Legacy `(exchange, token)` form is still accepted by the SDK but emits `FutureWarning`. One legacy example is retained per surface (orders, websocket) so users on older code can recognise the deprecated pattern.

## [1.1.4] - 2026-03-31

### Changed

- Restructured repo to native plugin layout (skill files under `skills/indian-algo-trading/`)
- Repo is now directly installable as a Cowork marketplace — no build step needed
- Updated Makefile for new directory structure

## [1.1.1] - 2026-03-31

### Added

- `marketplace.json` for plugin discoverability in marketplaces
- Dual packaging: `.skill` (platform-agnostic) and `.plugin` (Claude + Rupeezy MCP)
- `.mcp.json` bundling Rupeezy Trading and Strategy Platform MCP servers
- Makefile with `skill`, `plugin`, `all`, `release`, `validate`, and `test-scaffold` targets
- CONTRIBUTING_BROKER.md — step-by-step guide for adding broker adapters with AI prompt template
- `validate_broker_adapter.py` — automated broker adapter validation script

### Changed

- Removed MCP tool docs from `rupeezy-vortex.md` (auto-discovered via `.mcp.json`)

## [1.0.0] - 2026-03-31

### Added

**Core Skill**

- SKILL.md with pre-flight checklist, reference routing table, 13 critical rules, and code architecture patterns
- Progressive disclosure: 290-line brain routes to 16 reference files by context

**Reference Files (16)**

- `strategy-patterns.md` — 6 core + 5 advanced strategy patterns with code skeletons
- `risk-management.md` — position sizing (fixed fractional, ATR, Kelly Lite), drawdown controls, F&O margin monitoring
- `indian-market.md` — market timings, expiry calendar, STT rates FY 2025-26, circuit limits, auction risk, tick sizes, DPR, NSE no-API rule
- `backtesting.md` — library selection guide, realistic transaction costs, parameter optimization
- `error-handling.md` — order state machine, partial fills, graceful shutdown, state persistence
- `code-quality.md` — project structure, logging, pytest patterns, config management
- `options-greeks.md` — Black-Scholes, delta-neutral, gamma scalping, theta harvesting, IV vs RV
- `regime-detection.md` — HMM for 3 regimes, strategy decay via rolling Sharpe
- `india-data-edge.md` — FII/DII flows, OI analysis, PCR, max pain, delivery %, rollover, GIFT Nifty
- `execution-alpha.md` — TWAP, VWAP, iceberg, impact cost, NSE intraday timing patterns
- `robustness-testing.md` — walk-forward optimization, Monte Carlo, sensitivity analysis
- `portfolio-construction.md` — multi-strategy allocation, correlation-aware sizing, decay rotation
- `psychological-guardrails.md` — daily loss breaker, consecutive loss pause, weekly throttle, killswitch
- `tax-optimization.md` — STCG vs LTCG (20% vs 12.5%), tax-loss harvesting, F&O business income
- `python-performance.md` — vectorization, Numba JIT, Polars, async, profiling workflow

**Broker Support**

- `brokers/rupeezy-vortex.md` — full Vortex SDK reference (primary broker)
- `brokers/BROKER_TEMPLATE.md` — 12-section template for community broker adapters
- `brokers/CONTRIBUTING_BROKER.md` — step-by-step guide for adding a new broker with AI prompt template, verification checklist, and maintainer review process

**Scripts**

- `validate_strategy.py` — AST-based linter checking for hardcoded tokens, missing stop-loss, print statements, NSE scraping, tick size rounding
- `validate_broker_adapter.py` — validates broker adapter docs against template structure, checks for placeholders, constants completeness, OAuth flow documentation
- `scaffold_strategy.py` — generates best-practice project skeleton with main.py, strategy.py, risk_manager.py, guardrails.py, config.py, tests/

**Assets**

- `assets/strategy_template/` — 9 standalone template files matching scaffold output, browsable as reference

**Evals**

- `evals/evals.json` — 10 test prompts with 65 assertions covering all critical skill capabilities

**Governance**

- CONTRIBUTING.md with 6 contribution types, trust tiers, DCO, code of conduct
- Strategy patterns are core-team only (not open for community contribution)
- Apache 2.0 license
