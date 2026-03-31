# Indian Markets Trading Strategy Patterns Reference

This document teaches AI assistants to recognize, design, and code trading strategies for Indian equities and derivatives. Each pattern includes market conditions, failure modes, key parameters, and Python code skeletons.

---

## 1. Momentum / Trend Following

**When It Works:**
- Strong trending markets (uptrend or downtrend)
- Clear directional bias with higher highs/lows
- Volume confirmation of price moves
- Post-breakout consolidation rebounds

**When It Fails:**
- Sideways/choppy markets (5-10% range oscillation)
- Whipsaws after reversals
- During consolidation phases
- High volatility spikes without directional follow-through

**Key Parameters:**
- Fast MA period: 9-20 (SMA/EMA)
- Slow MA period: 50-200
- RSI threshold: overbought >70, oversold <30
- MACD fast/slow periods: 12/26, signal: 9
- Minimum volume threshold: above 20-day average

**Risk Warnings:**
- Place tight stop-losses (1-2% below entry for long)
- Exit if trend weakens (MA flattens or crossover reverses)
- Avoid during economic news releases on India earnings days
- Size positions smaller in choppy 10-4 PM sessions

**Python Skeleton — SMA Crossover:**
```python
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import pandas as pd

class SMACrossover(Strategy):
    fast_ma = 9
    slow_ma = 50

    def init(self):
        self.fast = self.I(lambda x: pd.Series(x).rolling(self.fast_ma).mean(), self.data.Close)
        self.slow = self.I(lambda x: pd.Series(x).rolling(self.slow_ma).mean(), self.data.Close)

    def next(self):
        if not self.position:
            if crossover(self.fast, self.slow):
                self.buy()
        elif crossover(self.slow, self.fast):
            self.position.close()

bt = Backtest(data, SMACrossover, cash=100000)
bt.run()
```

---

## 2. Mean Reversion

**When It Works:**
- Range-bound / sideways markets
- Overbought/oversold extremes followed by reversals
- High volatility (India VIX > 20) pulling price back
- Overnight gaps that mean-revert intraday

**When It Fails:**
- Strong uptrends (keep hitting upper Bollinger Band)
- Strong downtrends (keep hitting lower band)
- Sustained volatility breakouts
- News-driven directional moves

**Key Parameters:**
- Bollinger Band periods: 20-period MA, 2-2.5 std dev
- RSI period: 14, entry at <20 (oversold) or >80 (overbought)
- VWAP distance: +/- 1-2% deviation
- Timeframe: 5-30 min intraday, daily for longer trades

**Risk Warnings:**
- Check trend direction first; only mean-revert in choppy markets
- Use ATR-based stops (2x ATR from entry)
- Avoid mean reversion against strong trend (can blow account)
- Reduce size if India VIX >30 (execution slippage risk)

**Python Skeleton — RSI Oversold Bounce:**
```python
from backtesting import Backtest, Strategy

class RSIMeanReversion(Strategy):
    rsi_period = 14
    oversold = 20
    overbought = 80

    def init(self):
        self.rsi = self.I(lambda x: RSI(x, self.rsi_period), self.data.Close)

    def next(self):
        if not self.position and self.rsi[-1] < self.oversold:
            self.buy()
        elif self.position and self.rsi[-1] > 50:
            self.position.close()

def RSI(data, period=14):
    delta = pd.Series(data).diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))
```

---

## 3. Options Selling (Theta Decay)

**When It Works:**
- High implied volatility (IV > 1.5 std dev above average)
- Selling premium in the last 14 days to expiration
- Range-bound underlying (flat delta targeting)
- Using hedged structures (strangles, iron condors)

**When It Fails:**
- Naked short calls/puts: unlimited loss risk during gap moves
- Selling into crashes (2008 style) without hedge
- Ignoring delta exposure (too directional)
- Earnings announcements, RBI MPC decisions, budget day

**Key Parameters:**
- IV percentile: >50th for premium selling
- Delta targets: +/- 15-20 delta for short legs (25-30 delta acceptable)
- Position size: risk <2% of account per trade
- Expiry timeframe: sell 7-14 days before expiration
- Width of wings: 100-200 points on NIFTY50, 200-400 on BANKNIFTY

**Risk Warnings:**
- **CRITICAL: Never naked short options.** Always use defined-risk spreads.
- Naked short calls: unlimited loss if underlying rallies.
- Naked short puts: account can be wiped if underlying crashes.
- Iron condors cap max loss to spread width; strangles require hedges.
- Monitor Greeks daily: gamma acceleration in last 3-5 days.
- Exit 50-75% of max profit; don't hold to expiration.

**Python Skeleton — Iron Condor Framework:**
```python
from backtesting import Backtest, Strategy

class IronCondor(Strategy):
    iv_threshold = 0.6  # Sell when IV > 60th percentile
    days_to_expiry = 7  # Sell 7 days before expiration

    def init(self):
        self.iv_percentile = self.I(lambda x: IV_percentile(x), self.data.Close)

    def next(self):
        if self.iv_percentile[-1] > self.iv_threshold and not self.position:
            # Sell OTM call spread (short 20-delta call, long 25-delta call)
            # Sell OTM put spread (short 20-delta put, long 25-delta put)
            # Track Greeks daily
            self.position = self.buy(size=-2)  # Placeholder: use options chain

        # Exit at 50% of max profit or 1 day before expiry
        if self.position and (self.position.pl_pct >= 0.5 or days_remaining <= 1):
            self.position.close()
```

---

## 4. VWAP Strategy

**When It Works:**
- Institutional volume anchors to VWAP intraday
- Price bounces off VWAP after small pullbacks (5-10 min)
- Trend reversal confirmation at VWAP level
- Opening gaps mean-revert to VWAP by 11 AM

**When It Fails:**
- Major news catalyst breaks VWAP (RBI rate decision)
- Strong trend ignores VWAP (trades 3-5% above/below)
- Low liquidity stocks where VWAP is unreliable
- End of day (3:15-3:30 PM) when institutional flow dominates

**Key Parameters:**
- VWAP band: +/- 0.5-1.5% envelope
- Intraday timeframe: 5-15 minute bars
- Volume confirmation: trade above 20-day average vol
- Deviation distance: >1% from VWAP = strong signal

**Risk Warnings:**
- VWAP resets at market open (9:15 AM IST)
- Use only during regular hours (9:15 AM - 3:30 PM IST)
- Avoid trading first 30 minutes (high uncertainty)
- Don't fade VWAP in strong trending sessions

**Python Skeleton — VWAP Mean Reversion:**
```python
from backtesting import Backtest, Strategy

class VWAPMeanReversion(Strategy):
    vwap_std = 1.0  # 1 standard deviation band

    def init(self):
        self.vwap = self.I(self.calculate_vwap, self.data.Close, self.data.Volume)

    def next(self):
        price = self.data.Close[-1]
        deviation = abs(price - self.vwap[-1]) / self.vwap[-1]

        if not self.position and deviation > self.vwap_std:
            if price < self.vwap[-1]:
                self.buy()  # Below VWAP
            else:
                self.sell()  # Above VWAP
        elif self.position and deviation < 0.2:
            self.position.close()

    def calculate_vwap(self, close, volume):
        return (close * volume).rolling(window=252).sum() / volume.rolling(window=252).sum()
```

---

## 5. Breakout Strategy

**When It Works:**
- Opening Range Breakout (ORB) in first 30 minutes
- Volume surge confirms breakout (3x average)
- Donchian breakout after consolidation
- Directional bias in overnight news/futures

**When It Fails:**
- False breakouts (reversals within 5 minutes)
- Lunch hour traps (12:00-1:30 PM)
- Low-volume breakouts (reversal likely)
- End-of-day breakouts (no follow-through next day)

**Key Parameters:**
- ORB range: first 30 minutes (9:15-9:45 AM IST)
- Breakout threshold: >3% above/below range, >2x avg volume
- Donchian period: 20-30 days for swing breakouts
- Stop-loss: below/above range breakout level
- Best time windows: 9:45-10:30 AM, 2:00-3:15 PM
- Avoid: 12:00-1:30 PM (lunch liquidity trap)

**Risk Warnings:**
- **Avoid 12:00-1:30 PM window:** spreads widen, reversals common.
- False breakouts carry max drawdown risk; use tight stops.
- Low-volume breakouts: exit if no follow-through within 5 candles.
- Overnight gaps can invalidate intraday ORB levels.

**Python Skeleton — Opening Range Breakout:**
```python
from backtesting import Backtest, Strategy

class OpeningRangeBreakout(Strategy):
    orb_minutes = 30
    vol_multiplier = 2.0

    def init(self):
        self.orb_high = None
        self.orb_low = None
        self.avg_vol = self.I(lambda x: pd.Series(x).rolling(20).mean(), self.data.Volume)

    def next(self):
        if len(self.data) < 5:  # Skip first 30 min candles
            if self.orb_high is None:
                self.orb_high = self.data.High[-1]
                self.orb_low = self.data.Low[-1]
            else:
                self.orb_high = max(self.orb_high, self.data.High[-1])
                self.orb_low = min(self.orb_low, self.data.Low[-1])

        if len(self.data) == 5 and not self.position:
            if (self.data.Close[-1] > self.orb_high and
                self.data.Volume[-1] > self.avg_vol[-1] * self.vol_multiplier):
                self.buy()
            elif (self.data.Close[-1] < self.orb_low and
                  self.data.Volume[-1] > self.avg_vol[-1] * self.vol_multiplier):
                self.sell()
```

---

## 6. Pairs Trading

**When It Works:**
- High correlation pairs (e.g., ICICI Bank + HDFC Bank, TCS + Infosys)
- Cointegrated pairs with mean-reverting spread
- Divergence recovers within 5-20 trading days
- Sector-wide moves with temporary stock-specific decoupling

**When It Fails:**
- Structural break in correlation (merger, sector shift)
- One leg stops trading or halted (low liquidity)
- Divergence widens due to fundamental change
- High slippage executing both legs simultaneously

**Key Parameters:**
- Minimum correlation: >0.8 over 252-day period
- Cointegration ADF test p-value: <0.05
- Z-score entry: +/- 2.0 std dev (spread >= 2σ)
- Z-score exit: 0 (mean reversion target)
- Hedge ratio: β from linear regression (beta = cov/var)
- Rebalance frequency: daily to weekly

**Risk Warnings:**
- Pairs can decouple permanently (use ADF test to confirm stationary)
- Execution slippage on both legs reduces profit edge
- Index rebalancing days can whipsaw pairs temporarily
- Position sizing: equal weight or hedge-ratio weighted

**Python Skeleton — Cointegrated Pairs:**
```python
from backtesting import Backtest, Strategy
from statsmodels.tsa.stattools import coint
import numpy as np

class PairsTrading(Strategy):
    z_entry = 2.0
    z_exit = 0.5

    def init(self):
        # Pre-compute cointegration and hedge ratio
        self.hedge_ratio = self.calculate_hedge_ratio()
        self.spread_mean = 0
        self.spread_std = 1

    def next(self):
        spread = self.data.Close[-1] - self.hedge_ratio * self.data_pair.Close[-1]
        z_score = (spread - self.spread_mean) / self.spread_std

        if not self.position and abs(z_score) > self.z_entry:
            if z_score > self.z_entry:
                self.buy()
                self.sell_pair()  # Placeholder: short the other leg
            else:
                self.sell()
                self.buy_pair()

        elif self.position and abs(z_score) < self.z_exit:
            self.position.close()

    def calculate_hedge_ratio(self):
        # Ordinary Least Squares: spread = price1 - beta * price2
        return np.cov(self.data.Close, self.data_pair.Close)[0, 1] / np.var(self.data_pair.Close)
```

---

## 7. Advanced Patterns (Pointer Reference)

### Calendar Spreads
- Sell near-month option, buy far-month option
- Profit from theta decay differential
- Theta peaks 7-14 days before expiry
- Use on NIFTY/BANKNIFTY futures or options

### Event-Driven
- RBI Monetary Policy Committee (MPC) decisions (6 times/year)
- Quarterly earnings announcements
- Union Budget (Feb 1 annually)
- FII flows / month-end rebalancing
- Avoid trading 30 min before/after major events (extreme volatility)

### Multi-Timeframe Confirmation
- Daily chart: identify trend direction
- 4-hour chart: find pullback opportunities
- 15-minute chart: precise entry/exit timing
- Entry only when all timeframes align

### Volatility Arbitrage
- India VIX vs realized volatility
- Short IV when India VIX > historical vol + 20%
- Long straddles when IV << realized vol
- Rebalance Greeks weekly

### Sector Rotation
- Track Nifty sector indices (Nifty Bank, IT, Pharma, Auto)
- Relative strength: momentum sectors outperform
- Rebalance monthly on last trading day
- Hedge with index puts in downtrend

---

## General Risk Management Rules

1. **Position Sizing:** Risk no more than 2% of account per trade
2. **Stop-Loss Discipline:** Always use hard stops; never move against position
3. **Profit Targets:** Exit 50-75% at target; let winners run with trailing stops
4. **Slippage Buffer:** Add 0.05-0.1% to expected entry/exit prices
5. **Liquidity Check:** Trade only symbols with >100k daily volume
6. **Drawdown Monitoring:** Exit strategy if running loss > 15% account
7. **Correlation Check:** Avoid correlated positions (max 3 similar sector trades)
8. **News Risk:** Reduce size before earnings, RBI decisions, budget day

---

## IST Market Hours
- Regular: 9:15 AM - 3:30 PM IST
- Pre-open: 9:00-9:15 AM (order entry, no execution)
- Post-close: 3:40-4:00 PM (institutional clearing only)
- Holidays: Check NSE/BSE calendar before deploying strategies

---

## References for Further Study
- NSE India: https://www.nseindia.com/ (master data, circuit limits)
- BSE India: https://www.bseindia.com/
- India VIX: Published on NSE, check volatility regime
- Backtesting libraries: backtesting.py, vectorbt, backtrader
- Options Greeks: Calculate delta, gamma, theta, vega daily
