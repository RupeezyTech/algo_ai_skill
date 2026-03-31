# Indian Algo Trading

**Production-quality Python trading strategies for Indian markets — AI-assisted, from backtest to live.**

## Overview

This plugin helps you build algorithmic trading strategies for Indian markets (NSE, BSE, MCX) with best practices baked in. It doesn't ship pre-built strategies — instead, it teaches AI how to help you design safe, realistic, and compliant strategies from scratch.

Covers the full lifecycle: backtesting → optimization → paper trading → live deployment, across equity, F&O, currency derivatives, and MCX commodities.

---

## Installation

### Claude Code Plugin

```bash
# Register the marketplace (one-time)
claude plugin marketplace add RupeezyTech/algo_ai_skill

# Install
claude plugin install indian-algo-trading@rupeezy
```

### Standalone Skill

Download from [Releases](https://github.com/RupeezyTech/algo_ai_skill/releases) and extract:

```bash
unzip indian-algo-trading-*.skill -d ~/.claude/skills/indian-algo-trading/
```

### Local dev / testing

```bash
git clone https://github.com/RupeezyTech/algo_ai_skill.git
claude --plugin-dir ./algo_ai_skill
```

---

## Usage

Once installed, the skill activates automatically when you ask about:

- Writing a strategy (`"write a moving average crossover for Nifty"`)
- Backtesting (`"backtest this on 2022-2024 data with realistic costs"`)
- Live trading (`"make this strategy production-ready for live deployment"`)
- F&O automation (`"iron condor strategy for weekly expiry"`)
- Risk management (`"add position sizing and daily loss limits"`)

The skill will ask clarifying questions (asset class, live vs backtest, broker, risk tolerance) before generating code.

---

## What Gets Generated

Every strategy follows a strict separation of concerns:

```
my_strategy/
├── main.py          # Entry point, scheduling, SIGTERM handler
├── strategy.py      # Signal generation only
├── execution.py     # Order placement, fill tracking
├── risk_manager.py  # Position sizing, exposure checks, drawdown limits
├── config.py        # All parameters — no hardcoded values
└── requirements.txt
```

Every strategy includes: stop-losses, margin checks, tick size rounding, IST timezone, structured logging, and graceful shutdown. No exceptions.

---

## Reference Library (16 files)

| File | Covers |
|------|--------|
| `strategy-patterns.md` | Momentum, mean reversion, options, pairs trading |
| `risk-management.md` | Position sizing, drawdown controls, margin monitoring |
| `indian-market.md` | Timings, expiry calendar, STT, circuit limits, auction risk |
| `backtesting.md` | Library selection, realistic costs, parameter optimization |
| `error-handling.md` | Order state machine, partial fills, graceful shutdown |
| `code-quality.md` | Project structure, logging, testing, type hints |
| `options-greeks.md` | Delta-neutral, gamma scalping, theta harvesting, IV vs RV |
| `regime-detection.md` | HMM for trending/volatile/sideways, strategy decay |
| `india-data-edge.md` | FII/DII flows, OI analysis, PCR, max pain, delivery % |
| `execution-alpha.md` | TWAP, VWAP, iceberg, impact cost, intraday timing |
| `robustness-testing.md` | Walk-forward, Monte Carlo, sensitivity analysis |
| `portfolio-construction.md` | Multi-strategy allocation, correlation-aware sizing |
| `psychological-guardrails.md` | Daily loss breaker, consecutive loss pause, killswitch |
| `tax-optimization.md` | STCG vs LTCG, tax-loss harvesting, F&O business income |
| `python-performance.md` | Vectorization, Numba, Polars, async, profiling |
| `brokers/rupeezy-vortex.md` | Full Vortex SDK reference for live trading |

---

## Repository Structure

```
algo_ai_skill/
├── .claude-plugin/
│   └── marketplace.json              # Marketplace catalog (GitHub sync)
│
├── plugins/
│   └── indian-algo-trading/
│       ├── .claude-plugin/
│       │   └── plugin.json           # Plugin manifest
│       ├── .mcp.json                 # Rupeezy MCP server config
│       └── skills/
│           └── indian-algo-trading/
│               ├── SKILL.md          # Skill instructions + routing logic
│               ├── references/       # 16 reference files
│               └── scripts/
│                   ├── scaffold_strategy.py      # Generate strategy skeleton
│                   └── validate_strategy.py      # AST linter for common mistakes
│
├── evals/
│   └── evals.json                    # 10 skill evaluation test cases
│
├── build/                            # Generated — gitignored
│   ├── *.skill                       # Standalone skill zip (GitHub release)
│   └── *.plugin                      # Full plugin zip (Anthropic marketplace)
│
└── Makefile                          # Build, validate, release
```

---

## Developer Commands

```bash
# Build both artifacts
make all

# Build standalone skill zip only
make skill

# Build full plugin zip only
make plugin

# Validate JSON manifests and SKILL.md frontmatter
make validate

# Test scaffold script generates valid output
make test-scaffold

# Scaffold a new strategy project
python plugins/indian-algo-trading/skills/indian-algo-trading/scripts/scaffold_strategy.py my_strategy

# Validate strategy code against best practices
python plugins/indian-algo-trading/skills/indian-algo-trading/scripts/validate_strategy.py path/to/strategy.py

# Cut a release (requires git tag + gh CLI)
git tag -a v1.1.4 -m "Release v1.1.4"
make release
```

---

## Contributing

Contributions are welcome and encouraged. The most impactful areas:

- **Broker adapters** — add support for Zerodha, AngelOne, Fyers, Upstox, or any other broker using the [BROKER_TEMPLATE](plugins/indian-algo-trading/skills/indian-algo-trading/references/brokers/BROKER_TEMPLATE.md). Step-by-step guide in [CONTRIBUTING_BROKER.md](plugins/indian-algo-trading/skills/indian-algo-trading/references/brokers/CONTRIBUTING_BROKER.md).
- **Reference file improvements** — corrections, new sections, updated regulations (SEBI circulars, lot size changes, STT rates)
- **Scripts and tooling** — backtesting utilities, data analysis tools, strategy validators

See [CONTRIBUTING.md](CONTRIBUTING.md) for review requirements and timelines.

> **High-stakes project**: incorrect market data or unsafe code patterns can cost real money. All contributions require maintainer review before merge.

---

## License

Apache License 2.0 — see [LICENSE](LICENSE).

## Disclaimer

For educational and research purposes. Trading carries risk of loss. Backtest results do not guarantee future performance. Always paper trade before going live. Consult a financial advisor.
