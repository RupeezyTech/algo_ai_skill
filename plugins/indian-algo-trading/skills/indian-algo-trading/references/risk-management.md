# Risk Management Reference for Indian Algo Trading Strategies

## Overview

Implement robust risk management in Python trading strategies for NSE/BSE/MCX. This reference covers position sizing, stop-loss patterns, drawdown controls, portfolio heat, and F&O-specific risks with runnable code examples.

---

## 1. Position Sizing Models

### Fixed Fractional Position Sizing

Risk a fixed percentage (1-2%) of total capital per trade. Recommended for most strategies.

```python
def fixed_fractional_position_size(capital, risk_percent, entry_price, stop_loss_price):
    """
    Calculate position size based on fixed percentage risk.

    Args:
        capital: Total trading capital (float)
        risk_percent: Risk per trade as % (e.g., 0.02 for 2%)
        entry_price: Entry price (float)
        stop_loss_price: Stop loss price (float)

    Returns:
        Position size in quantity (int)
    """
    risk_amount = capital * risk_percent
    price_diff = abs(entry_price - stop_loss_price)

    if price_diff == 0:
        return 0

    position_size = risk_amount / price_diff
    return int(position_size)

# Example: Capital ₹100,000, risk 2%, entry ₹500, stop ₹490
quantity = fixed_fractional_position_size(
    capital=100000,
    risk_percent=0.02,
    entry_price=500,
    stop_loss_price=490
)
# Risk = 100,000 * 0.02 = ₹2,000
# Price diff = 500 - 490 = ₹10
# Quantity = 2,000 / 10 = 200 shares
```

### ATR-Based Volatility-Adjusted Position Sizing

Scale position size inversely to volatility. Higher volatility → smaller size.

```python
def atr_based_position_size(capital, risk_percent, atr_value, entry_price):
    """
    Calculate position size using ATR (Average True Range) for volatility adjustment.

    Args:
        capital: Total trading capital (float)
        risk_percent: Risk per trade as % (e.g., 0.02 for 2%)
        atr_value: Current ATR value (float) — 14-period ATR
        entry_price: Entry price (float)

    Returns:
        Position size in quantity (int)
    """
    risk_amount = capital * risk_percent
    stop_loss_price = entry_price - (2 * atr_value)  # 2 ATR buffer
    price_diff = entry_price - stop_loss_price

    if price_diff == 0:
        return 0

    position_size = risk_amount / price_diff
    return int(position_size)

# Example: Entry ₹500, ATR ₹5, capital ₹100,000, risk 2%
# Stop loss = 500 - (2 * 5) = ₹490
# Risk amount = 100,000 * 0.02 = ₹2,000
# Position size = 2,000 / 10 = 200 shares
quantity = atr_based_position_size(
    capital=100000,
    risk_percent=0.02,
    atr_value=5,
    entry_price=500
)
```

### Kelly Lite Position Sizing

Use 25-50% of the full Kelly criterion for conservative sizing. Full Kelly is aggressive for trading.

```python
def kelly_lite_position_size(capital, win_rate, avg_win, avg_loss, kelly_fraction=0.35):
    """
    Calculate position size using Kelly Lite (fractional Kelly).

    Full Kelly = (bp - q) / b, where:
        b = ratio of win to loss
        p = win probability
        q = loss probability (1 - p)

    Kelly Lite = full Kelly * kelly_fraction (typically 0.25-0.50)

    Args:
        capital: Total trading capital (float)
        win_rate: Probability of winning trade (0.0-1.0)
        avg_win: Average profit per winning trade (float)
        avg_loss: Average loss per losing trade (float)
        kelly_fraction: Fraction of Kelly to use (0.25-0.50)

    Returns:
        Position size as fraction of capital (float 0.0-1.0)
    """
    if avg_loss == 0 or win_rate == 0 or win_rate == 1:
        return 0.0

    b = avg_win / avg_loss  # Win/loss ratio
    p = win_rate
    q = 1 - win_rate

    full_kelly = (b * p - q) / b
    kelly_lite = full_kelly * kelly_fraction

    # Ensure fraction stays between 0 and reasonable maximum
    kelly_lite = max(0.0, min(kelly_lite, 0.25))  # Never exceed 25% per trade

    return kelly_lite

# Example: 55% win rate, avg win ₹1,000, avg loss ₹800, use 35% of Kelly
kelly_fraction = kelly_lite_position_size(
    capital=100000,
    win_rate=0.55,
    avg_win=1000,
    avg_loss=800,
    kelly_fraction=0.35
)
# Full Kelly ≈ ((1000/800) * 0.55 - 0.45) / (1000/800) ≈ 0.154 (15.4%)
# Kelly Lite (35%) = 0.154 * 0.35 ≈ 0.054 (5.4% of capital)
position_size = int(100000 * kelly_fraction)  # ₹5,400 per trade
```

---

## 2. Stop-Loss Patterns

### Fixed Percentage Stop-Loss

Exit when price moves against entry by fixed %.

```python
def fixed_percentage_stop(entry_price, stop_percent=2.0, is_long=True):
    """
    Calculate stop-loss price at fixed percentage from entry.

    Args:
        entry_price: Entry price (float)
        stop_percent: Stop loss % from entry (e.g., 2.0 for 2%)
        is_long: True for long, False for short

    Returns:
        Stop loss price (float)
    """
    stop_offset = entry_price * (stop_percent / 100.0)

    if is_long:
        stop_loss_price = entry_price - stop_offset
    else:
        stop_loss_price = entry_price + stop_offset

    return stop_loss_price

# Example: Buy at ₹500, 2% stop loss
stop = fixed_percentage_stop(entry_price=500, stop_percent=2.0, is_long=True)
# stop = 500 - (500 * 0.02) = ₹490
```

### ATR-Based Trailing Stop

Adjust stop dynamically based on ATR; trails profit on winners.

```python
def atr_trailing_stop(entry_price, current_price, atr_value,
                      atr_multiplier=2.0, is_long=True):
    """
    Calculate ATR-based trailing stop for long/short positions.

    Args:
        entry_price: Entry price (float)
        current_price: Current market price (float)
        atr_value: Current ATR value (float)
        atr_multiplier: Stop = price ± (ATR * multiplier)
        is_long: True for long, False for short

    Returns:
        Updated stop loss price (float)
    """
    stop_offset = atr_value * atr_multiplier

    if is_long:
        # Long: stop trails below current price
        stop_loss_price = current_price - stop_offset
        # Never move stop closer than entry
        stop_loss_price = min(stop_loss_price, entry_price)
    else:
        # Short: stop trails above current price
        stop_loss_price = current_price + stop_offset
        # Never move stop closer than entry
        stop_loss_price = max(stop_loss_price, entry_price)

    return stop_loss_price

# Example: Long at ₹500, current ₹510, ATR ₹5
# Stop = 510 - (5 * 2) = ₹500 (trails with price)
stop = atr_trailing_stop(
    entry_price=500,
    current_price=510,
    atr_value=5,
    atr_multiplier=2.0,
    is_long=True
)
```

### Time-Based Exit (Market Close Square-Off)

Always square off positions before market close. Critical for F&O in India (4:00 PM NSE close).

```python
def should_exit_on_time(current_time, market_close_time="15:30",
                        buffer_minutes=5, is_intraday=True):
    """
    Determine if position should be exited based on time.

    Args:
        current_time: Current time (str "HH:MM" or datetime)
        market_close_time: Market close time (str "HH:MM")
        buffer_minutes: Exit buffer before close (int)
        is_intraday: True for intraday, False for overnight

    Returns:
        Boolean: True if should exit
    """
    from datetime import datetime, timedelta

    if isinstance(current_time, str):
        current_time = datetime.strptime(current_time, "%H:%M").time()
    if isinstance(market_close_time, str):
        market_close_time = datetime.strptime(market_close_time, "%H:%M").time()

    # For intraday F&O: square off by 3:25 PM (NSE close 3:30 PM)
    exit_time = (datetime.combine(datetime.today(), market_close_time) -
                 timedelta(minutes=buffer_minutes)).time()

    return current_time >= exit_time if is_intraday else False

# Example: Exit F&O 5 minutes before 3:30 PM close
should_exit = should_exit_on_time(
    current_time="15:25",
    market_close_time="15:30",
    buffer_minutes=5,
    is_intraday=True
)
# Returns True: must square off now
```

### Indicator-Based Exit (RSI Reversal)

Exit when momentum reverses (e.g., RSI overbought/oversold).

```python
def rsi_based_exit(current_rsi, is_long=True,
                   overbought=70, oversold=30):
    """
    Determine exit based on RSI reversal signal.

    Args:
        current_rsi: Current RSI value (0-100)
        is_long: True for long position, False for short
        overbought: RSI threshold for overbought (e.g., 70)
        oversold: RSI threshold for oversold (e.g., 30)

    Returns:
        Boolean: True if should exit
    """
    if is_long:
        # Exit long if RSI breaks below overbought after reaching it
        return current_rsi > overbought
    else:
        # Exit short if RSI breaks above oversold after reaching it
        return current_rsi < oversold

# Example: Long position, current RSI 75
should_exit = rsi_based_exit(current_rsi=75, is_long=True, overbought=70)
# Returns True: overbought, consider exiting
```

---

## 3. Drawdown Controls

Implement multi-level drawdown protection to halt or reduce trading during losses.

```python
class DrawdownController:
    """
    Manage trading activity based on drawdown thresholds.
    Implements: per-trade cap, daily limit, weekly throttle,
    monthly killswitch, max drawdown circuit breaker.
    """

    def __init__(self, initial_capital,
                 max_per_trade_loss=0.02,      # 2% per trade
                 daily_loss_limit=0.03,        # 3% per day
                 weekly_loss_limit=0.05,       # 5% per week
                 monthly_loss_limit=0.15,      # 15% per month
                 max_drawdown_limit=0.15):     # 15% max drawdown
        """
        Args:
            initial_capital: Starting capital (float)
            max_per_trade_loss: Max loss per trade as % of capital
            daily_loss_limit: Max daily loss % before halt
            weekly_loss_limit: Max weekly loss % before reduce 50%
            monthly_loss_limit: Max monthly loss % before paper-only
            max_drawdown_limit: Max drawdown % overall
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.peak_capital = initial_capital

        self.max_per_trade_loss = max_per_trade_loss
        self.daily_loss_limit = daily_loss_limit
        self.weekly_loss_limit = weekly_loss_limit
        self.monthly_loss_limit = monthly_loss_limit
        self.max_drawdown_limit = max_drawdown_limit

        # Tracking
        self.daily_pnl = 0.0
        self.weekly_pnl = 0.0
        self.monthly_pnl = 0.0
        self.trades_today = []

    def update_capital(self, new_capital):
        """Update capital after trade."""
        pnl = new_capital - self.current_capital

        self.current_capital = new_capital
        self.peak_capital = max(self.peak_capital, new_capital)

        self.daily_pnl += pnl
        self.weekly_pnl += pnl
        self.monthly_pnl += pnl

        self.trades_today.append(pnl)

    def get_per_trade_max_loss(self):
        """Maximum capital at risk per trade."""
        return self.current_capital * self.max_per_trade_loss

    def check_per_trade_limit(self, trade_loss):
        """
        Check if trade loss exceeds per-trade cap.
        Returns: Boolean, True if trade OK
        """
        max_loss = self.get_per_trade_max_loss()
        return abs(trade_loss) <= max_loss

    def check_daily_limit(self):
        """
        Check if daily loss exceeded, halt trading.
        Returns: trading_allowed (bool), reason (str)
        """
        daily_loss_percent = abs(self.daily_pnl) / self.current_capital

        if daily_loss_percent >= self.daily_loss_limit:
            return False, f"Daily loss limit {self.daily_loss_limit*100}% exceeded"
        return True, "Daily limit OK"

    def check_weekly_limit(self):
        """
        Check if weekly loss exceeded, reduce position size by 50%.
        Returns: size_multiplier (float 0.5-1.0), reason (str)
        """
        weekly_loss_percent = abs(self.weekly_pnl) / self.initial_capital

        if weekly_loss_percent >= self.weekly_loss_limit:
            return 0.5, f"Weekly loss {weekly_loss_percent*100:.1f}%, reducing size 50%"
        return 1.0, "Weekly limit OK"

    def check_monthly_limit(self):
        """
        Check if monthly loss exceeded, paper-trade only.
        Returns: paper_trading_only (bool), reason (str)
        """
        monthly_loss_percent = abs(self.monthly_pnl) / self.initial_capital

        if monthly_loss_percent >= self.monthly_loss_limit:
            return True, f"Monthly loss {monthly_loss_percent*100:.1f}%, paper-trade only"
        return False, "Monthly limit OK"

    def check_max_drawdown(self):
        """
        Check if max drawdown exceeded, circuit breaker.
        Returns: trading_allowed (bool), reason (str)
        """
        drawdown = (self.peak_capital - self.current_capital) / self.peak_capital

        if drawdown >= self.max_drawdown_limit:
            return False, f"Max drawdown {drawdown*100:.1f}%, circuit breaker triggered"
        return True, "Max drawdown OK"

# Example usage:
risk_ctrl = DrawdownController(
    initial_capital=100000,
    max_per_trade_loss=0.02,    # 2% per trade
    daily_loss_limit=0.03,       # 3% per day
    weekly_loss_limit=0.05,      # 5% per week
    monthly_loss_limit=0.15,     # 15% per month
    max_drawdown_limit=0.15      # 15% overall
)

# After a losing trade
risk_ctrl.update_capital(98000)  # Lost ₹2,000
allowed, reason = risk_ctrl.check_daily_limit()
# Check: 2,000 / 100,000 = 2% loss < 3% limit → OK
```

---

## 4. Portfolio Heat (Total Open Risk)

Monitor aggregate risk across all open positions.

```python
def calculate_portfolio_heat(positions, capital):
    """
    Calculate total open risk as % of capital.
    Risk per position = position_size * (entry - stop_loss)

    Args:
        positions: List of dicts with keys:
                   {'symbol', 'quantity', 'entry_price', 'stop_loss', 'is_long'}
        capital: Total trading capital (float)

    Returns:
        total_heat % (float 0.0-1.0)
    """
    total_risk = 0.0

    for pos in positions:
        risk_amount = abs(pos['entry_price'] - pos['stop_loss']) * pos['quantity']
        total_risk += risk_amount

    heat = total_risk / capital if capital > 0 else 0.0
    return heat

def check_portfolio_heat(positions, capital, max_heat=0.06):
    """
    Ensure total portfolio heat < 6% of capital.

    Returns: can_trade (bool), current_heat (float), reason (str)
    """
    heat = calculate_portfolio_heat(positions, capital)

    if heat > max_heat:
        return False, heat, f"Portfolio heat {heat*100:.1f}% > limit {max_heat*100}%"

    return True, heat, f"Portfolio heat {heat*100:.1f}% OK"

# Example: 3 open positions
positions = [
    {'symbol': 'RELIANCE', 'quantity': 100, 'entry_price': 500, 'stop_loss': 490, 'is_long': True},
    {'symbol': 'TCS', 'quantity': 50, 'entry_price': 1000, 'stop_loss': 980, 'is_long': True},
    {'symbol': 'INFY', 'quantity': 75, 'entry_price': 600, 'stop_loss': 590, 'is_long': True},
]
capital = 100000

can_trade, heat, reason = check_portfolio_heat(positions, capital, max_heat=0.06)
# RELIANCE risk = 10 * 100 = ₹1,000
# TCS risk = 20 * 50 = ₹1,000
# INFY risk = 10 * 75 = ₹750
# Total heat = 2,750 / 100,000 = 2.75% < 6% → can trade
```

---

## 5. F&O Specific Risk Management

Indian F&O markets have unique margin dynamics. Calendar spreads and physical delivery require careful monitoring.

### Margin Monitoring

```python
def monitor_fo_margin(client, position_symbol, lot_size):
    """
    Monitor F&O margin requirements using Vortex client.

    Args:
        client: Vortex trading client (vortex.Client)
        position_symbol: Symbol for F&O instrument (str)
        lot_size: Lot size for the instrument (int)

    Returns:
        Dictionary with margin details
    """
    # Get available funds
    funds = client.get_funds()
    available_margin = funds.get('margin_available', 0)

    # Get order margin for 1 lot
    # NOTE: This is a hypothetical calculation — actual margin
    # must come from exchange or broker API
    margin_per_lot = estimate_fo_margin(position_symbol, lot_size)

    return {
        'available_margin': available_margin,
        'margin_per_lot': margin_per_lot,
        'max_lots': int(available_margin / margin_per_lot) if margin_per_lot > 0 else 0,
        'symbol': position_symbol
    }

def estimate_fo_margin(symbol, lot_size, multiplier=5000):
    """
    Rough estimate of F&O margin (varies by exchange/broker).
    For actual trading, use client.get_order_margin().

    Typical: Nifty futures ≈ ₹50K-70K per lot
    Bank Nifty ≈ ₹35K-50K per lot
    """
    if 'BANKNIFTY' in symbol:
        return 40000
    elif 'NIFTY' in symbol:
        return 60000
    else:
        return lot_size * multiplier  # Generic estimate
```

### Calendar Spread Margin Explosion

Critical: Near expiry, calendar spreads jump 5-10x in margin.

```python
def check_calendar_spread_expiry_risk(position, days_to_expiry=2):
    """
    Warn about calendar spread margin explosion near expiry.
    Margin can jump from ₹26K to ₹2.6L per lot on expiry day.

    Args:
        position: Dict with symbol, quantity, entry_price
        days_to_expiry: Days until contract expiry (int)

    Returns:
        risk_alert (str or None)
    """
    if days_to_expiry <= 2:
        margin_multiplier = 5 if days_to_expiry == 0 else 2.5
        alert = (
            f"WARNING: {position['symbol']} expiry in {days_to_expiry} days\n"
            f"Calendar spread margin will jump ~{margin_multiplier}x\n"
            f"Current: ₹26K → Near expiry: ₹{26000 * margin_multiplier:,.0f}\n"
            f"Plan exit or reduce size immediately."
        )
        return alert

    return None

# Example: Calendar spread with 2 days to expiry
position = {'symbol': 'NIFTY_APR', 'quantity': 1, 'entry_price': 23500}
alert = check_calendar_spread_expiry_risk(position, days_to_expiry=2)
if alert:
    print(alert)
    # Output: Margin jump from ₹26K to ₹65K per lot
```

### Physical Delivery Margin on Stock F&O

Stock F&O near expiry require physical delivery margin (separate from initial margin).

```python
def check_stock_fo_delivery_margin(symbol, quantity, price, days_to_expiry=2):
    """
    Stock F&O near expiry require physical delivery margin.
    Typically ~20% of contract value.

    Args:
        symbol: Stock symbol (str)
        quantity: Total quantity (int)
        price: Price per share (float)
        days_to_expiry: Days to contract expiry (int)

    Returns:
        delivery_margin_required (float)
    """
    contract_value = quantity * price

    # Delivery margin increases as expiry approaches
    if days_to_expiry <= 1:
        delivery_margin_pct = 0.25  # 25% on last day
    elif days_to_expiry <= 3:
        delivery_margin_pct = 0.20  # 20% within 3 days
    else:
        delivery_margin_pct = 0.10  # 10% default

    delivery_margin = contract_value * delivery_margin_pct

    return delivery_margin

# Example: 500 RELIANCE shares @ ₹500, 1 day to expiry
delivery_margin = check_stock_fo_delivery_margin(
    symbol='RELIANCE',
    quantity=500,
    price=500,
    days_to_expiry=1
)
# Contract value = 500 * 500 = ₹2,50,000
# Delivery margin (25%) = ₹62,500 ADDITIONAL
```

### Naked Options Selling Risk

Warn: naked short options have unlimited loss potential.

```python
def validate_naked_options_sale(position_type, is_short=True):
    """
    CRITICAL: Validate naked options selling.
    Naked short calls/puts = unlimited loss potential.

    Args:
        position_type: 'CALL' or 'PUT'
        is_short: True for short/sell, False for long/buy

    Returns:
        is_safe (bool), warning (str)
    """
    if is_short:
        warning = (
            f"NAKED {position_type} SALE: UNLIMITED LOSS POTENTIAL\n"
            f"Short calls: loss unlimited on upside\n"
            f"Short puts: loss up to strike * quantity\n"
            f"REQUIREMENT: Always hedge with opposite spread or cap risk with stop loss.\n"
            f"Use call spreads (call debit/credit) or put spreads (put debit/credit)."
        )
        return False, warning

    return True, "Long option position - limited loss to premium paid"

# Example: Selling naked call
is_safe, warning = validate_naked_options_sale(position_type='CALL', is_short=True)
if not is_safe:
    print(warning)
    # Output: Warns about unlimited loss
```

---

## 6. Complete RiskManager Class

Production-ready risk manager combining all patterns.

```python
class RiskManager:
    """
    Comprehensive risk manager for Indian algo trading strategies.
    Enforces position sizing, stop losses, drawdowns, portfolio heat,
    and F&O-specific risk controls.
    """

    def __init__(self, client, initial_capital,
                 max_risk_percent=0.02, max_heat_percent=0.06):
        """
        Args:
            client: Vortex trading client
            initial_capital: Starting capital (float)
            max_risk_percent: Max risk per trade (e.g., 0.02 for 2%)
            max_heat_percent: Max portfolio heat (e.g., 0.06 for 6%)
        """
        self.client = client
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.peak_capital = initial_capital

        self.max_risk_percent = max_risk_percent
        self.max_heat_percent = max_heat_percent

        self.positions = {}  # Track open positions
        self.daily_pnl = 0.0

    def calculate_position_size(self, entry_price, stop_loss_price):
        """Calculate safe position size using fixed fractional method."""
        risk_amount = self.current_capital * self.max_risk_percent
        price_diff = abs(entry_price - stop_loss_price)

        if price_diff == 0:
            return 0

        return int(risk_amount / price_diff)

    def validate_trade(self, symbol, entry_price, stop_loss_price, quantity):
        """
        Full validation before entry.

        Returns:
            approved (bool), reason (str)
        """
        # 1. Check position size
        recommended_qty = self.calculate_position_size(entry_price, stop_loss_price)
        if quantity > recommended_qty:
            return False, f"Size too large: {quantity} > recommended {recommended_qty}"

        # 2. Check per-trade risk
        trade_risk = abs(entry_price - stop_loss_price) * quantity
        if trade_risk > self.current_capital * self.max_risk_percent:
            return False, f"Trade risk {trade_risk} exceeds {self.max_risk_percent*100}%"

        # 3. Check portfolio heat (simulate addition)
        positions_copy = self.positions.copy()
        positions_copy[symbol] = {
            'quantity': quantity,
            'entry_price': entry_price,
            'stop_loss': stop_loss_price
        }

        heat = calculate_portfolio_heat(
            [p for p in positions_copy.values()],
            self.current_capital
        )

        if heat > self.max_heat_percent:
            return False, f"Portfolio heat {heat*100:.1f}% > limit {self.max_heat_percent*100}%"

        # 4. Check margin for F&O
        if 'FUT' in symbol or 'OPT' in symbol:
            margin_req = estimate_fo_margin(symbol, quantity)
            funds = self.client.get_funds()
            available = funds.get('margin_available', 0)

            if margin_req > available:
                return False, f"Insufficient margin: {margin_req} > {available}"

        return True, "Trade approved"

    def record_trade(self, symbol, entry_price, stop_loss_price, quantity):
        """Record open position for tracking."""
        self.positions[symbol] = {
            'quantity': quantity,
            'entry_price': entry_price,
            'stop_loss': stop_loss_price,
            'entry_time': None  # Add timestamp if needed
        }

    def update_capital(self, new_capital):
        """Update capital after trade execution."""
        pnl = new_capital - self.current_capital
        self.current_capital = new_capital
        self.peak_capital = max(self.peak_capital, new_capital)
        self.daily_pnl += pnl

    def get_portfolio_heat(self):
        """Get current portfolio heat percentage."""
        return calculate_portfolio_heat(
            [p for p in self.positions.values()],
            self.current_capital
        )

    def get_available_capital_for_trade(self):
        """Calculate max capital available for next trade."""
        current_heat = self.get_portfolio_heat()
        available_heat = self.max_heat_percent - current_heat
        return max(0.0, available_heat * self.current_capital)

# Example usage:
# from vortex import Client
# client = Client(access_token='your_token')
#
# rm = RiskManager(client, initial_capital=100000, max_risk_percent=0.02)
#
# approved, reason = rm.validate_trade(
#     symbol='RELIANCE',
#     entry_price=500,
#     stop_loss_price=490,
#     quantity=200
# )
#
# if approved:
#     rm.record_trade('RELIANCE', 500, 490, 200)
#     print(f"Current heat: {rm.get_portfolio_heat()*100:.1f}%")
```

---

## Key Takeaways

1. **Always size positions to risk, never reward.** Fixed fractional at 1-2% per trade is safest.
2. **Implement multi-level drawdown controls** — daily halt, weekly throttle, monthly circuit breaker.
3. **Monitor total portfolio heat** — never exceed 6% open risk on capital.
4. **Respect F&O margin dynamics** — calendar spreads explode 5-10x near expiry; physical delivery adds margin.
5. **Never sell naked options** — unlimited loss potential. Always hedge or use spreads.
6. **Always exit before market close** — especially critical for Indian F&O (3:30 PM NSE).
7. **Use ATR for volatility-adjusted stops** — scale size inversely to volatility.

Implement the `RiskManager` class in every strategy to enforce these rules automatically.
