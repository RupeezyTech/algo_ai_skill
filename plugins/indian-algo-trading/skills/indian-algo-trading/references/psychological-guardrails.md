# Psychological Guardrails: Top 1% Risk Management

The difference between profitable trading and ruin is psychology. A 1% edge grows to 100x capital over 5 years if you survive drawdowns. It shrinks to zero if emotion causes you to deviate. Implement hard limits on loss, consecutive failures, and drawdown. Automate discipline.

## 1. Daily Loss Circuit Breaker: Halt After 2% Loss

If your account loses 2% in a single day, stop all trading. Resume the next day at market open. This prevents revenge trading after a bad morning.

**Pattern: Daily Loss Monitor**

```python
class DailyLossCircuitBreaker:
    def __init__(self, daily_loss_limit=-0.02, capital_base=1_000_000):
        """
        Args:
            daily_loss_limit: Max loss as % of capital (e.g., -0.02 for 2%)
            capital_base: Starting capital to calculate loss against
        """
        self.daily_loss_limit = daily_loss_limit
        self.capital_base = capital_base
        self.session_start_capital = capital_base
        self.trading_active = True
        self.last_reset_date = None

    def update_capital(self, current_capital, current_date):
        """Call after each trade or at end of session."""
        # Reset if day changed
        if self.last_reset_date != current_date.date():
            self.session_start_capital = current_capital
            self.trading_active = True
            self.last_reset_date = current_date.date()

        # Calculate daily loss
        daily_loss_pct = (current_capital - self.session_start_capital) / self.session_start_capital

        if daily_loss_pct <= self.daily_loss_limit:
            self.trading_active = False
            return {'status': 'CIRCUIT_BREAKER_HIT', 'loss_pct': daily_loss_pct}

        return {'status': 'OK', 'loss_pct': daily_loss_pct}

    def can_trade(self):
        return self.trading_active

# Usage
from datetime import datetime

breaker = DailyLossCircuitBreaker(daily_loss_limit=-0.02, capital_base=1_000_000)

# Simulate trading session
current_capital = 1_000_000
today = datetime.now()

trades = [1_000_000, 995_000, 989_000, 981_500]  # -0.5%, -1.1%, -1.85%
for i, capital in enumerate(trades):
    result = breaker.update_capital(capital, today)
    print(f"Trade {i+1}: Capital {capital:>10.0f} | {result['status']:20} | Daily loss: {result['loss_pct']:.2%}")
    if not breaker.can_trade():
        print("HALT: Circuit breaker triggered. No more trades today.")
        break
```

## 2. Consecutive Loss Pause: Stop After 5 Consecutive Losses

Five consecutive losing trades signal that the strategy or market regime has changed. Pause trading immediately and reassess. Do not trade until 5 winning trades accumulate.

**Pattern: Consecutive Loss Counter**

```python
class ConsecutiveLossGuard:
    def __init__(self, max_consecutive_losses=5):
        """
        Args:
            max_consecutive_losses: Pause after this many losses in a row
        """
        self.max_consecutive_losses = max_consecutive_losses
        self.consecutive_losses = 0
        self.trading_paused = False
        self.wins_needed_to_resume = max_consecutive_losses

    def record_trade(self, pnl):
        """
        Args:
            pnl: Profit/loss from the trade (positive or negative)

        Returns:
            Status dict
        """
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            # Reset on winning trade
            if self.trading_paused:
                self.wins_needed_to_resume -= 1
            self.consecutive_losses = 0

        # Pause on 5 consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            self.trading_paused = True
            return {
                'status': 'PAUSE_TRIGGERED',
                'consecutive_losses': self.consecutive_losses,
                'wins_needed_to_resume': self.wins_needed_to_resume
            }

        if self.wins_needed_to_resume <= 0:
            self.trading_paused = False
            self.wins_needed_to_resume = self.max_consecutive_losses
            return {
                'status': 'RESUME',
                'consecutive_losses': self.consecutive_losses,
                'wins_needed_to_resume': 0
            }

        return {
            'status': 'OK',
            'consecutive_losses': self.consecutive_losses,
            'trading_paused': self.trading_paused
        }

    def can_trade(self):
        return not self.trading_paused

# Usage
guard = ConsecutiveLossGuard(max_consecutive_losses=5)

# Simulate trades
trade_pnls = [-100, -150, -200, -75, -300, 500, 450, 400, 350, 300]

for i, pnl in enumerate(trade_pnls):
    result = guard.record_trade(pnl)
    print(f"Trade {i+1}: PnL {pnl:>6} | {result['status']:20} | Consecutive losses: {result['consecutive_losses']}")
    if not guard.can_trade():
        print(f"  --> PAUSED. Need {result['wins_needed_to_resume']} wins to resume.")
```

## 3. Weekly Drawdown Throttle: Reduce Size 50% After 5% Weekly Decline

If the week shows a -5% drawdown, cut position size in half for the following week. Resume normal sizing only when the week closes green.

**Pattern: Weekly Drawdown Throttle**

```python
class WeeklyDrawdownThrottle:
    def __init__(self, weekly_drawdown_trigger=-0.05, size_reduction_factor=0.5):
        """
        Args:
            weekly_drawdown_trigger: Trigger position size cut (e.g., -0.05 for 5%)
            size_reduction_factor: Multiply position size by this (e.g., 0.5 for 50% reduction)
        """
        self.weekly_drawdown_trigger = weekly_drawdown_trigger
        self.size_reduction_factor = size_reduction_factor
        self.week_start_capital = None
        self.current_size_multiplier = 1.0
        self.last_reset_week = None

    def update_weekly(self, current_capital, current_week_number, peak_capital_this_week):
        """
        Call at end of each week.

        Args:
            current_capital: Capital at end of week
            current_week_number: Week number (ISO week)
            peak_capital_this_week: Peak capital reached during the week
        """
        # Initialize on first call
        if self.week_start_capital is None:
            self.week_start_capital = current_capital
            return {'status': 'INITIALIZED', 'size_multiplier': self.current_size_multiplier}

        # Reset if new week
        if self.last_reset_week != current_week_number:
            self.last_reset_week = current_week_number

            # Calculate weekly drawdown
            weekly_loss_pct = (current_capital - peak_capital_this_week) / peak_capital_this_week

            # Trigger throttle
            if weekly_loss_pct <= self.weekly_drawdown_trigger:
                self.current_size_multiplier = self.size_reduction_factor
                return {
                    'status': 'THROTTLE_ACTIVATED',
                    'weekly_loss_pct': weekly_loss_pct,
                    'size_multiplier': self.current_size_multiplier
                }

            # Check if week is green; resume normal size
            if current_capital >= self.week_start_capital:
                self.current_size_multiplier = 1.0
                self.week_start_capital = current_capital
                return {
                    'status': 'WEEK_GREEN_RESUME',
                    'size_multiplier': self.current_size_multiplier
                }

        return {'status': 'OK', 'size_multiplier': self.current_size_multiplier}

    def get_position_size(self, base_position_size):
        """Return actual position size after applying throttle multiplier."""
        return base_position_size * self.current_size_multiplier

# Usage
from datetime import datetime, timedelta

throttle = WeeklyDrawdownThrottle(weekly_drawdown_trigger=-0.05, size_reduction_factor=0.5)

# Simulate weekly reports
base_size = 100_000
current_capital = 1_000_000
peak_weekly = 1_000_000

for week in range(1, 5):
    if week == 1:
        result = throttle.update_weekly(current_capital, week, peak_weekly)
    elif week == 2:
        # Week 2: -3% (not triggered)
        current_capital = 970_000
        peak_weekly = 1_000_000
        result = throttle.update_weekly(current_capital, week, peak_weekly)
    elif week == 3:
        # Week 3: -6% (triggered throttle)
        current_capital = 940_000
        peak_weekly = 1_000_000
        result = throttle.update_weekly(current_capital, week, peak_weekly)
    else:
        # Week 4: rebounds to green
        current_capital = 960_000
        peak_weekly = 960_000
        result = throttle.update_weekly(current_capital, week, peak_weekly)

    size = throttle.get_position_size(base_size)
    print(f"Week {week}: {result['status']:25} | Size multiplier: {result['size_multiplier']} | Position: {size:>8.0f}")
```

## 4. Monthly Killswitch: Paper-Trade Only After 15% Monthly Drawdown

If the month shows a -15% loss, stop real trading and switch to paper trading for the rest of the month. Monitor strategy performance in simulation only. Resume live trading next month.

**Pattern: Monthly Killswitch**

```python
class MonthlyKillswitch:
    def __init__(self, monthly_loss_trigger=-0.15):
        """
        Args:
            monthly_loss_trigger: Activate paper trading at this loss (e.g., -0.15 for 15%)
        """
        self.monthly_loss_trigger = monthly_loss_trigger
        self.month_start_capital = None
        self.current_month = None
        self.paper_trading = False
        self.peak_capital_this_month = None

    def update_capital(self, current_capital, current_date):
        """
        Call at end of each trading session.

        Args:
            current_capital: Current account capital
            current_date: Current date
        """
        current_month = current_date.month

        # Reset on month change
        if self.current_month != current_month:
            self.current_month = current_month
            self.month_start_capital = current_capital
            self.paper_trading = False
            self.peak_capital_this_month = current_capital
            return {'status': 'MONTH_RESET', 'paper_trading': False}

        # Track peak
        if current_capital > self.peak_capital_this_month:
            self.peak_capital_this_month = current_capital

        # Calculate monthly loss
        monthly_loss_pct = (current_capital - self.peak_capital_this_month) / self.peak_capital_this_month

        # Trigger killswitch
        if monthly_loss_pct <= self.monthly_loss_trigger and not self.paper_trading:
            self.paper_trading = True
            return {
                'status': 'KILLSWITCH_ACTIVATED',
                'monthly_loss_pct': monthly_loss_pct,
                'paper_trading': True
            }

        return {'status': 'OK', 'monthly_loss_pct': monthly_loss_pct, 'paper_trading': self.paper_trading}

    def should_execute_trade(self):
        """Return False if in paper-trading mode."""
        return not self.paper_trading

# Usage
from datetime import datetime

killswitch = MonthlyKillswitch(monthly_loss_trigger=-0.15)

# Simulate monthly trading
capital = 1_000_000
dates = [
    datetime(2026, 3, 1),
    datetime(2026, 3, 10),
    datetime(2026, 3, 15),
    datetime(2026, 3, 20),
    datetime(2026, 3, 25),
    datetime(2026, 3, 31),
]

capital_values = [1_000_000, 980_000, 950_000, 900_000, 870_000, 860_000]  # -14% by day 25, -13% by end

for date, capital in zip(dates, capital_values):
    result = killswitch.update_capital(capital, date)
    can_trade = killswitch.should_execute_trade()
    print(f"{date.strftime('%Y-%m-%d')}: Capital {capital:>10.0f} | {result['status']:25} | Trade: {'LIVE' if can_trade else 'PAPER'}")
```

## 5. Position Size Reset: Revert to Base Size After Hitting Any Limit

Whenever any guardrail is triggered (daily loss, consecutive loss, drawdown), reset position size to the baseline. This prevents compounding risk after an event.

**Pattern: Position Size Manager**

```python
class PositionSizeManager:
    def __init__(self, base_position_size=50_000):
        """
        Args:
            base_position_size: Default position size in notional terms
        """
        self.base_position_size = base_position_size
        self.current_position_size = base_position_size
        self.size_history = []

    def apply_guardrail_event(self, event_type, multiplier=None):
        """
        Called when a guardrail is triggered.

        Args:
            event_type: 'daily_loss', 'consecutive_loss', 'weekly_drawdown', 'monthly_killswitch'
            multiplier: Optional custom multiplier; if None, reverts to base
        """
        if multiplier is None:
            self.current_position_size = self.base_position_size
        else:
            self.current_position_size = self.base_position_size * multiplier

        self.size_history.append({
            'event': event_type,
            'new_size': self.current_position_size,
            'timestamp': datetime.now()
        })

        return self.current_position_size

    def get_current_size(self):
        return self.current_position_size

    def reset_to_base(self):
        """Explicitly reset to base size."""
        self.current_position_size = self.base_position_size
        return self.current_position_size

# Usage
manager = PositionSizeManager(base_position_size=50_000)

print(f"Initial size: {manager.get_current_size()}")

# Daily loss triggered
size = manager.apply_guardrail_event('daily_loss')
print(f"After daily loss: {size}")

# Weekly drawdown triggered (75% reduction)
size = manager.apply_guardrail_event('weekly_drawdown', multiplier=0.75)
print(f"After weekly drawdown: {size}")

# Reset to base
size = manager.reset_to_base()
print(f"After reset: {size}")
```

## 6. Cooldown Timers: Minimum Wait Between Trades After Loss

After a losing trade, enforce a cooldown: no new trades for 1 hour (or 5 minutes during high-conviction setups). This prevents revenge trading and allows time to reassess.

**Pattern: Trade Cooldown Timer**

```python
from datetime import datetime, timedelta

class TradeCooldownTimer:
    def __init__(self, cooldown_minutes=60, short_cooldown_minutes=5):
        """
        Args:
            cooldown_minutes: Cooldown after a loss
            short_cooldown_minutes: Short cooldown for high-conviction re-entry
        """
        self.cooldown_duration = timedelta(minutes=cooldown_minutes)
        self.short_cooldown = timedelta(minutes=short_cooldown_minutes)
        self.last_losing_trade_time = None
        self.in_cooldown = False
        self.can_short_cooldown = False

    def record_trade(self, pnl):
        """
        Args:
            pnl: Trade profit/loss

        Returns:
            Status dict
        """
        if pnl < 0:
            self.last_losing_trade_time = datetime.now()
            self.in_cooldown = True
            self.can_short_cooldown = False  # Cannot use short cooldown immediately
            return {
                'status': 'LOSING_TRADE_RECORDED',
                'cooldown_active': True,
                'cooldown_expires': self.last_losing_trade_time + self.cooldown_duration
            }
        else:
            # Winning trade; may set short cooldown
            self.can_short_cooldown = True
            return {'status': 'WINNING_TRADE', 'cooldown_active': False}

    def can_trade_now(self):
        """Check if cooldown has expired."""
        if not self.in_cooldown:
            return True

        now = datetime.now()
        if now - self.last_losing_trade_time >= self.cooldown_duration:
            self.in_cooldown = False
            return True

        return False

    def can_trade_short_cooldown(self):
        """Check if short cooldown (5 min) has expired for high-conviction re-entry."""
        if not self.can_short_cooldown:
            return False

        now = datetime.now()
        if now - self.last_losing_trade_time >= self.short_cooldown:
            return True

        return False

# Usage
cooldown = TradeCooldownTimer(cooldown_minutes=60, short_cooldown_minutes=5)

# Record a losing trade
result = cooldown.record_trade(-500)
print(f"Losing trade recorded: {result}")

# Immediately try to trade
can_trade = cooldown.can_trade_now()
print(f"Can trade immediately: {can_trade}")  # False

# After 65 minutes, try again
# (in real code, would use actual time progression)
print(f"Can trade after 65 min: {cooldown.can_trade_now() if datetime.now() - cooldown.last_losing_trade_time > timedelta(minutes=65) else False}")
```

## 7. Max Trades Per Day Cap: Prevent Overtrading

Limit trades to N per day (e.g., max 10). If you're hitting the cap every day, the system is overtrading and likely generating low-edge trades. A hard cap forces discipline.

**Pattern: Daily Trade Counter**

```python
class DailyTradeCounter:
    def __init__(self, max_trades_per_day=10):
        """
        Args:
            max_trades_per_day: Maximum number of trades allowed per calendar day
        """
        self.max_trades_per_day = max_trades_per_day
        self.trades_today = 0
        self.last_reset_date = None

    def record_trade(self, current_date):
        """
        Args:
            current_date: Current date

        Returns:
            Approval boolean
        """
        # Reset on day change
        if self.last_reset_date != current_date.date():
            self.trades_today = 0
            self.last_reset_date = current_date.date()

        # Increment and check limit
        self.trades_today += 1

        if self.trades_today > self.max_trades_per_day:
            return False  # Trade not approved

        return True  # Trade approved

    def get_trades_remaining_today(self):
        return max(0, self.max_trades_per_day - self.trades_today)

# Usage
from datetime import datetime

counter = DailyTradeCounter(max_trades_per_day=10)
today = datetime.now()

for i in range(12):
    approved = counter.record_trade(today)
    remaining = counter.get_trades_remaining_today()
    print(f"Trade {i+1}: {'APPROVED' if approved else 'REJECTED'} | Remaining: {remaining}")
    # Output: Trades 1-10 approved, trades 11-12 rejected
```

## 8. Complete TradingGuardrails Class

Assemble all guardrails into a single class that wraps order execution. Any order must pass all guardrail checks before execution.

```python
class TradingGuardrails:
    """
    Master guardrails controller. All orders pass through here.
    """

    def __init__(self, capital_base=1_000_000):
        self.daily_breaker = DailyLossCircuitBreaker(daily_loss_limit=-0.02, capital_base=capital_base)
        self.consecutive_guard = ConsecutiveLossGuard(max_consecutive_losses=5)
        self.weekly_throttle = WeeklyDrawdownThrottle(weekly_drawdown_trigger=-0.05)
        self.monthly_killswitch = MonthlyKillswitch(monthly_loss_trigger=-0.15)
        self.size_manager = PositionSizeManager(base_position_size=50_000)
        self.cooldown_timer = TradeCooldownTimer(cooldown_minutes=60)
        self.daily_counter = DailyTradeCounter(max_trades_per_day=10)

    def check_order_approval(self, current_capital, current_date, pnl_last_trade=None):
        """
        Comprehensive guardrail check before execution.

        Returns:
            {'approved': bool, 'reasons': list of blocking reasons}
        """
        reasons = []

        # 1. Daily loss breaker
        self.daily_breaker.update_capital(current_capital, current_date)
        if not self.daily_breaker.can_trade():
            reasons.append('daily_loss_circuit_breaker')

        # 2. Consecutive loss guard
        if pnl_last_trade is not None:
            result = self.consecutive_guard.record_trade(pnl_last_trade)
            if not self.consecutive_guard.can_trade():
                reasons.append('consecutive_loss_pause')

        # 3. Monthly killswitch
        ks_result = self.monthly_killswitch.update_capital(current_capital, current_date)
        if not self.monthly_killswitch.should_execute_trade():
            reasons.append('monthly_killswitch_paper_trading')

        # 4. Cooldown timer
        if not self.cooldown_timer.can_trade_now():
            reasons.append('trade_cooldown_active')

        # 5. Daily trade cap
        if not self.daily_counter.record_trade(current_date):
            reasons.append('max_trades_per_day_exceeded')

        approved = len(reasons) == 0
        return {
            'approved': approved,
            'reasons': reasons,
            'position_size': self.size_manager.get_current_size()
        }

    def execute_order(self, symbol, quantity, side, current_capital, current_date, pnl_last_trade=None):
        """
        Execute order if it passes all guardrail checks.

        Returns:
            {'executed': bool, 'order_id': str or None, 'blocked_by': list}
        """
        approval = self.check_order_approval(current_capital, current_date, pnl_last_trade)

        if not approval['approved']:
            return {
                'executed': False,
                'order_id': None,
                'blocked_by': approval['reasons']
            }

        # Adjust quantity based on current size multiplier
        adjusted_qty = int(quantity * (approval['position_size'] / self.size_manager.base_position_size))

        # Execute (in real code, send to broker)
        order_id = f"ORDER_{datetime.now().timestamp()}"
        return {
            'executed': True,
            'order_id': order_id,
            'adjusted_quantity': adjusted_qty,
            'blocked_by': []
        }

    def apply_guardrail_event(self, event_type, multiplier=None):
        """Apply a guardrail event (e.g., after hitting a limit)."""
        self.size_manager.apply_guardrail_event(event_type, multiplier)

# Usage
guardrails = TradingGuardrails(capital_base=1_000_000)

current_capital = 1_000_000
current_date = datetime.now()

# Attempt trade 1
approval1 = guardrails.execute_order(
    symbol='RELIANCE',
    quantity=100,
    side='BUY',
    current_capital=current_capital,
    current_date=current_date,
    pnl_last_trade=None
)
print(f"Trade 1 approval: {approval1}")

# Simulate losing trade
current_capital = 990_000
pnl_last = -10_000

# Attempt trade 2 (after loss)
approval2 = guardrails.execute_order(
    symbol='TCS',
    quantity=100,
    side='BUY',
    current_capital=current_capital,
    current_date=current_date,
    pnl_last_trade=pnl_last
)
print(f"Trade 2 approval: {approval2}")
```

## Summary

Psychological guardrails transform a profitable strategy into a surviving strategy. Without these hard limits:

- **Daily loss** → leads to revenge trading and larger losses
- **Consecutive losses** → indicate regime change; pause prevents drowning
- **Weekly drawdown** → reduces size to protect capital during down periods
- **Monthly killswitch** → paper trading allows learning without capital bleed
- **Cooldown timers** → force recovery between losing trades
- **Trade caps** → prevent overtrading in low-edge environments
- **Position size resets** → ensure consistent risk across events

Implement ALL of these guardrails, not just one or two. The 1% edge survives compound leverage and drawdowns. The non-compliant trader does not.
