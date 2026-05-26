# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.10] - 2026-05-26

### Added

- **`OrderTracker` class** (canonical in `references/code-quality.md`; scaffolded as `order_tracker.py` for live strategies). Postback-driven, refreshes from orderbook + tradebook with 500 ms debounce, fires `on_terminal(order_id, status)` for every terminal transition. API: `initialize`, `on_update`, `on_terminal`, `wait(order_id, timeout)` (timeout required), `cancel_and_wait`, `status`/`order`/`fills`/`avg_fill_price`.
- **Scaffolder** generates `order_tracker.py` for `--type live`; wires it through `main.py` (`initialize` → `on_terminal` → connect feed) and adds an `on_order_terminal` method to `strategy.py` (replaces the empty `on_order_fill`/`on_order_cancel` stubs).

### Changed

- **Critical Rule 9 rewritten** — postback is a signal, orderbook is the truth. Names all five envelope types (`order`, `trade`, `sl_trigger`, `gtt_order`, `position_conversion`); strategy code refreshes from `client.orders()`/`client.trades()` instead of parsing `msg["data"]`; postbacks coalesced via 500 ms debounce. Live strategies use `on_terminal`; `wait()` reframed as a script/test primitive with required `timeout`.
- **Broker reference** Common Patterns rewritten around `OrderTracker.on_terminal` + `initialize()`; `orders()`/`order_history()` callouts now distinguish sleep-loop polling (anti-pattern) from postback-driven refresh (recommended).
- **SKILL.md halved** — 405 → 216 lines, ~5.5K → ~2.8K always-loaded tokens. No rules removed, only verbosity. Step-1, Code Architecture, Rule 8, Output Format, Backtesting Standards, and Proactive Suggestions rewritten as terse bullets.

### Fixed

- **Skill was teaching order-status polling.** `references/code-quality.md` shipped a `wait_for_order_fill()` that polled `broker.get_order_status()` in a `while time.sleep(0.5)` loop, with a docstring rationalising "polling instead of events to avoid callback hell". Rewritten as event-driven; Rule 9 and broker callouts now explicitly forbid sleep-loop polling.
- **Postback envelope shape.** Real payload is `{type, data, client_code}`; examples were reading the inner fields at the top level (would `KeyError` on real traffic). All examples now filter on `msg["type"]` and unwrap `msg["data"]`.
- **Thread-start race** in `OrderTracker.on_update` — `try/finally` resets `_worker_running` if `Thread.start()` raises, preventing silent permanent refresh stoppage.
- **`on_terminal` deduplication** via `_notified_terminal` set; an order staying terminal across multiple refreshes only fires the callback once.
- Stale `lookup_token(master, "RELIANCE", "NSE_EQ")` snippet in broker reference Common Patterns — now `ticker="NSE:RELIANCE"`.
- **`COMPLETED` vs `EXECUTED` alias** — same state under two names (postback envelope returns `COMPLETED`, `client.orders()` returns `EXECUTED`). `OrderTracker.TERMINAL` and `SUCCESS` now include both. Without this, the orderbook refresh would never fire `on_terminal` for filled orders.
- **Postback-vs-REST lag broke the reference `OrderTracker` on rejections** (field-test fix). Real-world: WS pushes `REJECTED` postbacks within ms of `place_order` returning, but `client.orders()` keeps returning `PENDING` for the same `order_id` for ~30 seconds. The previous "postback = signal, REST = truth" model missed rejections and let stale REST overwrite a terminal status. Reframed as **split authority**: postback `data.status` is authoritative for status transitions; REST is authoritative for fill quantities / prices. `OrderTracker.on_update` now fast-paths terminal `order` postbacks (mirrors payload into cache, fires `on_terminal` synchronously on the WS thread). `_apply` has a **downgrade guard**: once a terminal status is recorded, a later non-terminal REST row merges fill fields but does NOT overwrite `status`.
- **Substring terminal-status detection.** Brokers emit decorated forms (`REJECTED_BY_RMS`, `AMO_CANCELLED`, `EXECUTED_PARTIAL`). The previous strict set membership check missed these. `OrderTracker._terminal_token()` substring-matches against canonical tokens and normalises the stored `status` field; the original verbose form is preserved in `raw_status`.
- **Response envelope keys differ per endpoint** (field-test fix). `client.orders()` returns `{"orders": [...]}`, `client.trades()` returns `{"trades": [...]}` — NOT `{"data": [...]}` (which is the holdings/positions/funds shape). `OrderTracker._orders_rows()` / `_trades_rows()` chain through the common key names. Broker reference gains an explicit "Endpoint response envelope keys" table.
- **SDK signature drift since 2.1.8** (field-test fixes). `client.orders()` and `client.trades()` now require `(limit, offset)` positional args (raises `TypeError` if omitted); `OrderTracker._fetch_orderbook` / `_fetch_tradebook` try the new form and fall back to no-args on `TypeError`. `place_order`'s `disclosed_quantity` is REQUIRED (broker reference parameter table updated). `get_order_margin` response is flat (`{"required_margin", "available_margin", "status"}`) — not nested under `"data"`; broker reference example rewritten to use the flat shape and dropped the `funds()` double-call.
- **Rejection reason field name varies by surface** (field-test fix). Postback envelope uses `status_message`; REST orderbook row uses `error_reason`; `place_order` response uses `message`. Added `OrderTracker.rejection_reason(order_id)` accessor that walks the chain. Scaffolded `strategy.py.on_order_terminal` uses it. Broker reference Order Rejection section documents all three field names with a table.
- **Instrument master quirks** (field-test fix). `expiry_date` is `YYYYMMDD` in the master CSV, ISO in REST orderbook rows, and `"29May2026"` in postbacks for the same contract. Documented in the broker reference Instrument Master section with a recommendation to lexicographically compare master-CSV expiry strings instead of parsing. Futures rows use `option_type='XX'` (sometimes `'  '`), not `None`/`""` — documented the robust filter idiom.
- **`funds()` unreliable as a margin-availability source** (field-test fix). On some accounts it returned `{}` with no buckets — would `KeyError` on `funds()["data"]["equity"]["margin_available"]`. Broker reference Margin Check example rewritten to read `available_margin` directly from `get_order_margin`'s response (one round-trip, stable shape) and explicitly warn against the funds()-double-call pattern.
- **Scaffolded `config.py` now calls `load_dotenv()` at module top** (field-test fix). Previously a caller importing `config.py` before `auth.py` would read empty env vars. config.py uses a `try: from dotenv import load_dotenv` guard so it's harmless on container deployments. `auth.py` no longer duplicates the call; it just `import config` for the side-effect. `requirements.txt` keeps `python-dotenv` in both deployments so the import is always available. Documented that the PyPI package is `python-dotenv` (NOT `dotenv` — separate, unrelated package).

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
