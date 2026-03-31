# Backtesting Reference for Indian Algorithmic Trading Strategies

## Overview

Backtesting validates strategy logic against historical data before live deployment. This guide covers library selection, data preparation, realistic cost modeling, and implementation patterns for Indian market strategies.

---

## 1. Library Selection Guide

Choose your backtesting library based on strategy complexity and analysis needs:

| Library | Best For | Strengths | Limitations |
|---------|----------|-----------|-------------|
| **backtesting.py** | Single instrument, quick prototyping, simple signals | Simple syntax, fast iteration, intuitive API | Single-threaded, limited order types, no multi-asset |
| **vectorbt** | Multi-parameter sweeps, correlation analysis, portfolio analysis | Fastest execution (vectorized), built-in heatmaps, multi-instrument | Steeper learning curve, requires NumPy/Pandas fluency |
| **backtrader** | Complex order types, multi-asset portfolios, event-driven logic | Supports OCO/bracket orders, market phases, portfolio-level decisions | Slower than vectorbt, verbose configuration, memory-heavy |

**Recommendation:** Start with `backtesting.py` for signal validation, use `vectorbt` for parameter optimization, escalate to `backtrader` only for multi-leg strategies.

---

## 2. Data Preparation

### DataFrame Format (CRITICAL)

All libraries expect OHLCV data in this exact format:

```python
import pandas as pd
from datetime import datetime

# Correct format: capitalized columns, datetime index
df = pd.DataFrame({
    'Open': [100.0, 101.5, 102.0],
    'High': [101.0, 102.5, 103.0],
    'Low': [99.5, 101.0, 101.5],
    'Close': [100.5, 102.0, 102.5],
    'Volume': [1000000, 1200000, 950000]
}, index=pd.DatetimeIndex([
    '2025-01-01 09:15:00',
    '2025-01-02 09:15:00',
    '2025-01-03 09:15:00'
], name='datetime'))

# Verify before backtesting
assert df.index.name == 'datetime'
assert all(col in df.columns for col in ['Open', 'High', 'Low', 'Close', 'Volume'])
assert df.index.is_monotonic_increasing
```

### Fetching Data from Vortex API

Use `client.historical_candles()` to fetch from Vortex:

```python
from vortex import Client

client = Client()

# Download master to find token
master = client.download_master()
nifty_token = master[master['tradingsymbol'] == 'NIFTY50']['token'].iloc[0]

# Fetch historical data
candles = client.historical_candles(
    instrument_token=nifty_token,
    interval='1D',
    from_date='2023-01-01',
    to_date='2025-12-31'
)

# Convert to required format
df = pd.DataFrame(candles)
df['datetime'] = pd.to_datetime(df['timestamp'])
df = df.set_index('datetime')
df = df[['Open', 'High', 'Low', 'Close', 'Volume']].sort_index()
```

### Data Availability Matrix

Plan your backtest period based on instrument type:

| Instrument | Historical Availability | Notes |
|------------|--------------------------|-------|
| Equities (NSE/BSE spot) | 10+ years available | Use full history to capture regimes |
| Equity intraday (1min-15min) | ~3 months rolling | Older data often purged; check Vortex limits |
| Futures (NSE FO) | Current contract only | Use continuous contracts or roll logic |
| Options | Until expiry only | Expired options unavailable; use synthetic proxy |

**For expired futures/options:** Use spot data as a proxy. Adjust volatility expectations, as options carry time decay that spot contracts do not.

---

## 3. Realistic Transaction Costs (CRITICAL)

Ignoring costs is the #1 reason backtests fail in live trading. Indian markets have complex cost structures:

### Cost Breakdown

```
Equity Delivery (buy-hold):
  - STT (Security Transaction Tax): 0.1%
  - Brokerage: 0.01-0.05%
  - Exchange charges: 0.005%
  - Stamp duty: minimal
  Total: ~0.15-0.2% round-trip

Equity Intraday (MIS):
  - STT: 0.025% (lower for intraday)
  - Brokerage: 0.03-0.05%
  - Exchange charges: 0.005%
  Total: ~0.06-0.1% round-trip

Futures (NSE FO):
  - Brokerage: 0.01-0.05%
  - Exchange charges: 0.002%
  - No STT (taxed at settlement)
  Total: ~0.06-0.08% round-trip

Options:
  - Brokerage: 0.05-0.1%
  - Exchange charges: 0.05%
  - STT on premium: 0.05%
  Total: ~0.1-0.2% round-trip
```

### Applying Costs in Backtests

**backtesting.py:**

```python
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import pandas as pd

class MyStrategy(Strategy):
    def init(self):
        pass

    def next(self):
        if not self.position:
            self.buy()
        elif self.position and len(self) % 20 == 0:
            self.position.close()

# Set commission for equity delivery
bt = Backtest(df, MyStrategy, commission=.002)  # 0.2%
result = bt.run()

# For equity intraday, use lower commission
bt = Backtest(df, MyStrategy, commission=.001)  # 0.1%
```

**vectorbt:**

```python
import vectorbt as vbt

# Apply slippage and commission during portfolio simulation
pf = vbt.Portfolio.from_signals(
    close=df['Close'],
    entries=entry_signals,
    exits=exit_signals,
    init_cash=100000,
    fees=0.001,  # commission per trade
    freq='1D'
)
```

**backtrader:**

```python
import backtrader as bt

class MyStrategy(bt.Strategy):
    def __init__(self):
        pass

    def next(self):
        pass

cerebro = bt.Cerebro()
broker = cerebro.getbroker()
broker.setcommission(commission=0.001)  # 0.1% per transaction
cerebro.addstrategy(MyStrategy)
```

### Slippage Estimation

Add slippage (price movement between signal and execution) based on liquidity:

- **Liquid instruments (NIFTY, BANKNIFTY, large-cap stocks):** 0.05% slippage
- **Illiquid mid-caps:** 0.1-0.2% slippage
- **Near options expiry:** 0.2-0.5% slippage (volatility smile distortion)

Apply as additional cost:

```python
# backtesting.py doesn't have built-in slippage; add to commission
equity_intraday_cost = 0.001  # commission
slippage = 0.0005             # 0.05% liquid
bt = Backtest(df, Strategy, commission=equity_intraday_cost + slippage)
```

---

## 4. Avoiding Common Pitfalls

### Look-Ahead Bias

**WRONG:** Using tomorrow's high/low to place today's stop:

```python
# NEVER DO THIS
def next(self):
    if self.data.Close[-1] > self.data.High[0]:  # Using future high
        self.buy()
```

**CORRECT:** Only use data up to current bar:

```python
def next(self):
    if self.data.Close[-1] > self.data.Close[-2]:  # Past data only
        self.buy()
```

### Survivorship Bias

Stocks that survived to today may have had poor predecessors. Always use point-in-time universe:

```python
# Download historical master data or use versioned constituents
# Test on Index constituents as of each date (if available)
# For smaller universes, accept survivorship bias explicitly in your report
```

### Overfitting

If your strategy breaks when you change a parameter by 10%, it's overfitted:

```python
# OVERFITTED: Works only for RSI threshold 30-35
# ROBUST: Works for RSI threshold 20-45

# Test parameter sensitivity:
params_to_test = [20, 25, 30, 35, 40, 45]
results = []
for rsi_threshold in params_to_test:
    bt = Backtest(df, PartialStrategy(rsi_threshold=rsi_threshold))
    result = bt.run()
    results.append(result['Return [%]'])

# Plot and check smoothness
import matplotlib.pyplot as plt
plt.plot(params_to_test, results)
plt.xlabel('RSI Threshold')
plt.ylabel('Return %')
plt.show()  # Should be smooth curve, not spiky
```

### Minimum Trade Count

Fewer than 50 trades = insufficient statistical significance. A strategy with 10 trades could succeed by luck alone:

```python
# Always check trade count
result = bt.run()
print(f"Trade count: {result['# Trades']}")
if result['# Trades'] < 50:
    print("WARNING: Too few trades. Results may be unreliable.")
```

---

## 5. backtesting.py Patterns

### Basic Strategy Structure

```python
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from backtesting.test import GOOG
import talib

class RsiMeanReversion(Strategy):
    # Parameters to optimize
    rsi_period = 14
    rsi_threshold = 30

    def init(self):
        # Precompute indicators once
        close = self.data.Close
        self.rsi = self.I(talib.RSI, close, self.rsi_period)

    def next(self):
        # Called on each candle
        if self.rsi[-1] < self.rsi_threshold and not self.position:
            self.buy()
        elif self.rsi[-1] > 70 and self.position:
            self.position.close()

# Single backtest
bt = Backtest(df, RsiMeanReversion, cash=100000, commission=.001)
result = bt.run()
print(result)

# Parameter optimization
stats = bt.optimize(
    rsi_period=range(10, 30, 2),
    rsi_threshold=range(20, 40, 5),
    maximize='Sharpe Ratio',
    constraint=lambda p: p.rsi_period < p.rsi_threshold * 2,
    return_heatmap=True
)
print(stats)
```

### Custom Indicator Wrapping

```python
def init(self):
    # Wrap custom indicators with self.I()
    def custom_indicator(close, period):
        return close.rolling(period).mean()

    self.moving_avg = self.I(custom_indicator, self.data.Close, 20)

def next(self):
    if self.data.Close[-1] > self.moving_avg[-1]:
        self.buy()
```

### Saving Results

```python
from vortex import Client

client = Client()

# Save single backtest
result = bt.run()
client.save_backtest_result(
    result=result,
    strategy_name='RSI Mean Reversion',
    instrument='NIFTY50',
    from_date='2023-01-01',
    to_date='2025-12-31'
)

# Save optimization results
stats, heatmap = bt.optimize(
    rsi_period=range(10, 30, 2),
    return_heatmap=True
)
client.save_optimization_result(
    results=stats,
    heatmap=heatmap,
    strategy_name='RSI Mean Reversion',
    parameter_names=['rsi_period', 'rsi_threshold']
)
```

---

## 6. vectorbt Patterns

Use vectorbt for rapid multi-parameter sweeps on large datasets:

```python
import vectorbt as vbt
import pandas as pd
import numpy as np

# Signal generation (vectorized)
close = df['Close'].values
entry_signal = (close > np.roll(close, 1)) & (close > np.roll(close, 2))
exit_signal = (close < np.roll(close, 1))

# Portfolio from signals
pf = vbt.Portfolio.from_signals(
    close=df['Close'],
    entries=entry_signal,
    exits=exit_signal,
    init_cash=100000,
    fees=0.001,
    freq='1D'
)

print(pf.stats())
print(pf.total_return())

# Multi-parameter sweep
entry_thresholds = [0.01, 0.02, 0.03]
results = {}

for threshold in entry_thresholds:
    entry_sig = (close > np.roll(close, 1)) & (close > (1 + threshold))
    pf = vbt.Portfolio.from_signals(close=df['Close'], entries=entry_sig, exits=exit_signal)
    results[threshold] = pf.total_return()

print(results)
```

---

## 7. backtrader Patterns

Use backtrader for complex multi-leg and multi-asset strategies:

```python
import backtrader as bt

class MyStrategy(bt.Strategy):
    def __init__(self):
        self.sma = bt.indicators.SimpleMovingAverage(self.data, period=20)

    def next(self):
        if self.data.Close[0] > self.sma[0]:
            if not self.position:
                self.buy()
        else:
            if self.position:
                self.sell()

class MyAnalyzers(bt.Cerebro):
    def __init__(self):
        self.cerebro = bt.Cerebro()

    def run(self, data, strategy):
        self.cerebro.adddata(data)
        self.cerebro.addstrategy(strategy)
        self.cerebro.broker.setcommission(commission=0.001)

        # Add analyzers
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        self.cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')

        results = self.cerebro.run()
        return results[0]
```

---

## 8. Parameter Optimization

Always optimize when your strategy has tunable parameters. Optimization reduces guesswork and reveals robust parameter ranges:

```python
# backtesting.py optimization with heatmap
stats = bt.optimize(
    rsi_period=range(10, 31, 2),
    rsi_sell_threshold=range(60, 81, 5),
    maximize='Sharpe Ratio',
    return_heatmap=True
)

# Extract and plot heatmap
import matplotlib.pyplot as plt

heatmap = stats._heatmap
plt.imshow(heatmap, cmap='RdYlGn', aspect='auto')
plt.xlabel('RSI Sell Threshold')
plt.ylabel('RSI Period')
plt.colorbar(label='Sharpe Ratio')
plt.title('Parameter Optimization Heatmap')
plt.show()

# Identify robust region (plateau of high Sharpe)
print(f"Best parameters: {stats._best}")
print(f"Best Sharpe Ratio: {stats['Sharpe Ratio']}")
```

---

## 9. Performance Tips

### Precompute Indicators

```python
# SLOW: Recalculate on every bar
def next(self):
    rsi = talib.RSI(self.data.Close, 14)  # Recalculated 10,000 times

# FAST: Precompute once
def init(self):
    self.rsi = self.I(talib.RSI, self.data.Close, 14)

def next(self):
    if self.rsi[-1] < 30:  # Direct access, O(1)
        self.buy()
```

### Limit Grid Search Dimensions

More parameters = exponential combinations. Limit optimization to 3-6 parameters:

```python
# 2 params × 10 values = 100 combinations (fast)
bt.optimize(period=range(10, 20), threshold=range(1, 11), return_heatmap=True)

# 5 params × 10 values = 100,000 combinations (slow)
# Avoid this; use manual sensitivity analysis instead
```

### Use Polars for Large Datasets

For datasets >1M rows, use Polars instead of Pandas:

```python
import polars as pl

# Load with Polars (2-3x faster)
df = pl.read_csv('large_file.csv')

# Convert to Pandas for backtesting.py
df_pandas = df.to_pandas()

bt = Backtest(df_pandas, MyStrategy)
result = bt.run()
```

---

## Checklist Before Live Deployment

- [ ] Trade count > 50
- [ ] Sharpe Ratio > 1.0 (ideal: >1.5)
- [ ] Maximum Drawdown < 20% (ideal: <10%)
- [ ] Win Rate > 50% or Profit Factor > 1.5
- [ ] Parameter robustness tested (±10% change)
- [ ] Realistic costs applied (commission + slippage)
- [ ] No look-ahead bias in logic
- [ ] Optimization results saved and reproducible
- [ ] Equity curve smooth (no sudden spikes)
- [ ] Out-of-sample validation performed (optional but recommended)

---

## References

- backtesting.py: https://kernc.github.io/backtesting.py/
- vectorbt: https://vectorbt.dev/
- backtrader: https://www.backtrader.com/
- TA-Lib: https://github.com/mrjbq7/ta-lib
