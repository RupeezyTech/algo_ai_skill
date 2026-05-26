# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
