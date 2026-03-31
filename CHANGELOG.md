# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.2] - 2026-03-31

### Changed
- Version bump for release alignment

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
