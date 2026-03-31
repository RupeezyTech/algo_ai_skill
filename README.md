# Indian Algo Trading Skill

**AI-platform-agnostic skill for writing production-quality Python trading strategies for Indian stock markets.**

## Overview

This skill helps you create your own algorithmic trading strategies for Indian markets (NSE, BSE, MCX) with best practices baked in. It doesn't ship pre-built strategies — instead, it teaches AI systems how to help you build safe, realistic, and compliant strategies from scratch.

The skill covers the full lifecycle: backtesting → optimization → paper trading → live deployment, across equity, F&O, currency derivatives, and MCX commodities.

## Key Features

- **Safety-First Defaults**: Every generated strategy includes position sizing, stop-losses, and drawdown limits — no exceptions
- **Realistic Backtesting**: Simulates actual trading costs (STT, brokerage, slippage, margin requirements)
- **16 Reference Files**: Fundamentals (risk management, backtesting, error handling) + advanced modules (regime detection, options Greeks, execution alpha, robustness testing)
- **Indian Market Compliance**: Tick size rounding, DPR validation, auction risk checks, lot size lookups, IST timezone handling
- **Broker Integration**: Rupeezy/Vortex as primary broker, with a modular template (`BROKER_TEMPLATE.md`) for community broker adapters
- **Production Ready**: Graceful shutdown, structured logging, state persistence, and deployment patterns

## Skill Folder Structure

```
indian-algo-trading/
├── SKILL.md                          # Core skill brain — routes to references by context
├── README.md
├── LICENSE                           # Apache 2.0
├── CONTRIBUTING.md
│
├── references/                       # Knowledge base (16 files)
│   ├── strategy-patterns.md          # Educational patterns: momentum, mean reversion, options, etc.
│   ├── risk-management.md            # Position sizing, drawdown controls, margin monitoring
│   ├── indian-market.md              # Timings, expiry calendar, STT, circuit limits, auction risk
│   ├── backtesting.md                # Library selection, realistic costs, parameter optimization
│   ├── error-handling.md             # Order state machine, partial fills, graceful shutdown
│   ├── code-quality.md               # Project structure, logging, testing, type hints
│   ├── options-greeks.md             # Delta-neutral, gamma scalping, theta harvesting, IV vs RV
│   ├── regime-detection.md           # HMM for trending/volatile/sideways, strategy decay
│   ├── india-data-edge.md            # FII/DII flows, OI analysis, PCR, max pain, delivery %
│   ├── execution-alpha.md            # TWAP, VWAP, iceberg, impact cost, intraday timing
│   ├── robustness-testing.md         # Walk-forward, Monte Carlo, sensitivity analysis
│   ├── portfolio-construction.md     # Multi-strategy allocation, correlation-aware sizing
│   ├── psychological-guardrails.md   # Daily loss breaker, consecutive loss pause, killswitch
│   ├── tax-optimization.md           # STCG vs LTCG, tax-loss harvesting, F&O business income
│   ├── python-performance.md         # Vectorization, Numba, Polars, async, profiling
│   └── brokers/
│       ├── rupeezy-vortex.md         # Primary broker — full Vortex SDK reference
│       └── BROKER_TEMPLATE.md        # Template for adding new broker adapters
│
├── scripts/
│   ├── validate_strategy.py          # AST-based linter for common trading code mistakes
│   └── scaffold_strategy.py          # Generate best-practice project skeleton
│
└── assets/
    └── strategy_template/            # Template files used by scaffold script
```

## How It Works

1. You describe the strategy you want to build (e.g., "momentum strategy on Nifty 50 stocks")
2. The skill asks clarifying questions: asset class, live vs backtest, broker, risk tolerance
3. It generates production-quality Python code with proper separation of concerns: signal generation, execution, risk management, and configuration — all in separate modules
4. Every strategy includes: stop-losses, margin checks, tick size rounding, IST timezone, structured logging, and graceful shutdown

## Installation & Usage

### For Skill Users (AI Platforms)

Add this repository as a skill in your AI platform. The skill activates when you mention algo trading, strategy code, backtesting, or related terms.

```bash
git clone https://github.com/AsthaFinance/indian-algo-trading.git
```

### For Developers

```bash
# Clone and set up
git clone https://github.com/AsthaFinance/indian-algo-trading.git
cd indian-algo-trading

# Scaffold a new strategy project
python scripts/scaffold_strategy.py my_strategy

# Validate strategy code against best practices
python scripts/validate_strategy.py path/to/strategy.py
```

## Contributing

We welcome contributions for broker adapters, reference file improvements, scripts, and documentation. See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

**Important**: This skill helps users create their own strategies — it does not ship pre-built strategies. Strategy-related content is maintained by the core team only.

**High-stakes warning**: Incorrect market data or unsafe code patterns can cost real money. All contributions require maintainer review.

## License

Apache License 2.0 — see [LICENSE](LICENSE) file.

## Disclaimer

This skill is for educational and research purposes. Trading carries risk of loss. Backtest results do not guarantee future performance. Always test strategies on paper before live trading. Consult a financial advisor.
