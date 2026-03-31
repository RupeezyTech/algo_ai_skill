# Tax Optimization: Top 1% Edge in After-Tax Returns

The tax system is a feature, not a bug. An 18% return with 2% tax drag becomes 16% after-tax. But if you structure positions correctly, you can reduce tax drag to under 0.5%. This is a 1-2% edge that requires zero edge in trading. Build tax awareness into your strategy execution.

## 1. STCG vs LTCG: The 7.5% Tax Arbitrage

Short-term capital gains (held < 12 months) are taxed at 20% (Section 111A) plus 4% cess = 20.8% effective.
Long-term capital gains (held >= 12 months) are taxed at 12.5% (Section 112A) with ₹1,25,000 exemption per FY.

**The 7.5% gap**: Selling at day 364 costs 20.8%; selling at day 366 costs 12.5%. This is pure tax savings.

**Pattern: Tax-Aware Holding Period Calculation**

```python
from datetime import datetime, timedelta

def calculate_optimal_holding_period(entry_date, current_date, current_unrealized_return):
    """
    Determine whether to exit now (STCG) or hold for LTCG.

    Args:
        entry_date: Date position was opened
        current_date: Current date
        current_unrealized_return: Current P&L as % (e.g., 0.15 for 15%)

    Returns:
        {'recommendation': 'HOLD' or 'EXIT', 'tax_savings': float, 'days_until_ltcg': int}
    """
    holding_period = (current_date - entry_date).days
    days_until_ltcg = 365 - holding_period

    # Tax rates (including 4% cess)
    stcg_rate = 0.208  # 20% + 4% cess
    ltcg_rate = 0.125  # 12.5%

    # Assume position will grow at same rate if held another (days_until_ltcg) days
    assumed_return_per_day = current_unrealized_return / (holding_period + 1e-6)
    projected_return_at_ltcg = assumed_return_per_day * 365

    # Calculate after-tax returns
    after_tax_stcg = current_unrealized_return * (1 - stcg_rate)
    after_tax_ltcg = projected_return_at_ltcg * (1 - ltcg_rate)

    tax_savings = after_tax_ltcg - after_tax_stcg

    # Recommend hold if tax savings > opportunity cost of capital
    # (Use hurdle rate of 0.05% per day or 1% per month)
    hurdle_daily = 0.0005
    opportunity_cost = hurdle_daily * days_until_ltcg * projected_return_at_ltcg

    recommendation = 'HOLD' if tax_savings > opportunity_cost else 'EXIT'

    return {
        'recommendation': recommendation,
        'holding_days': holding_period,
        'days_until_ltcg': days_until_ltcg,
        'current_return_pct': current_unrealized_return * 100,
        'projected_ltcg_return_pct': projected_return_at_ltcg * 100,
        'after_tax_stcg_pct': after_tax_stcg * 100,
        'after_tax_ltcg_pct': after_tax_ltcg * 100,
        'tax_savings_pct': tax_savings * 100
    }

# Usage
entry = datetime(2025, 3, 15)
today = datetime(2026, 3, 10)  # Day 360 of holding
return_pct = 0.20  # 20% unrealized gain

result = calculate_optimal_holding_period(entry, today, return_pct)
print(f"Holding days: {result['holding_days']}")
print(f"Days until LTCG: {result['days_until_ltcg']}")
print(f"Current unrealized return: {result['current_return_pct']:.2f}%")
print(f"After-tax (STCG): {result['after_tax_stcg_pct']:.2f}%")
print(f"After-tax (LTCG): {result['after_tax_ltcg_pct']:.2f}%")
print(f"Tax savings if hold: {result['tax_savings_pct']:.2f}%")
print(f"Recommendation: {result['recommendation']}")
```

## 2. Selling at Day 364 vs 366: The 7.5% Decision

A position opened on day 1 and held for 365 days qualifies for LTCG. Selling on day 364 triggers STCG. The difference: 7.5 percentage points of tax.

Example: ₹1,00,000 position with 25% gain.
- **Exit at day 364 (STCG)**: Gain = ₹25,000. Tax = ₹5,200. After-tax = ₹19,800. Return = 19.8%.
- **Exit at day 366 (LTCG)**: Gain = ₹25,000. Tax = ₹3,125. After-tax = ₹21,875. Return = 21.9%.

**Difference: 2.1% after-tax return**, with zero additional trading edge.

**Pattern: Calendar-Aware Exit Timing**

```python
class TaxAwareLTCGPlanner:
    def __init__(self):
        self.positions = {}  # {position_id: {'entry_date': date, 'quantity': int, 'entry_price': float}}

    def add_position(self, position_id, entry_date, quantity, entry_price):
        self.positions[position_id] = {
            'entry_date': entry_date,
            'quantity': quantity,
            'entry_price': entry_price
        }

    def compute_ltcg_date(self, position_id):
        """Return the date when LTCG tax treatment kicks in."""
        if position_id not in self.positions:
            return None
        entry = self.positions[position_id]['entry_date']
        # LTCG starts on the 366th day (12 months + 1 day)
        ltcg_date = entry + timedelta(days=365)
        return ltcg_date

    def days_until_ltcg(self, position_id, current_date):
        """Days remaining before LTCG kicks in."""
        ltcg_date = self.compute_ltcg_date(position_id)
        if ltcg_date is None:
            return None
        return max(0, (ltcg_date - current_date).days)

    def can_exit_ltcg(self, position_id, current_date):
        """True if position qualifies for LTCG treatment."""
        return self.days_until_ltcg(position_id, current_date) <= 0

    def suggest_exit_window(self, position_id, current_date, max_exit_delay_days=30):
        """
        Suggest the exit window to maximize after-tax return.

        Returns:
            {'optimal_exit_date': date, 'days_to_wait': int, 'tax_benefit': str}
        """
        ltcg_date = self.compute_ltcg_date(position_id)
        days_remaining = (ltcg_date - current_date).days

        if days_remaining <= 0:
            return {
                'optimal_exit_date': current_date,
                'days_to_wait': 0,
                'tax_benefit': 'LTCG_AVAILABLE_NOW'
            }

        if days_remaining <= max_exit_delay_days:
            return {
                'optimal_exit_date': ltcg_date,
                'days_to_wait': days_remaining,
                'tax_benefit': f'WAIT_{days_remaining}_DAYS_FOR_LTCG'
            }

        return {
            'optimal_exit_date': current_date,
            'days_to_wait': 0,
            'tax_benefit': 'TOO_FAR_EXIT_NOW'
        }

# Usage
planner = TaxAwareLTCGPlanner()

position_entry = datetime(2025, 4, 1)
position_id = 'RELIANCE_100'

planner.add_position(position_id, position_entry, quantity=100, entry_price=2500)

# Check on various dates
test_dates = [
    datetime(2026, 2, 15),  # Day 319, not yet LTCG
    datetime(2026, 3, 31),  # Day 364, day before LTCG
    datetime(2026, 4, 1),   # Day 365, LTCG kicks in
]

for test_date in test_dates:
    can_exit = planner.can_exit_ltcg(position_id, test_date)
    days_left = planner.days_until_ltcg(position_id, test_date)
    window = planner.suggest_exit_window(position_id, test_date)
    print(f"{test_date.strftime('%Y-%m-%d')}: Days until LTCG: {days_left}, Can exit LTCG: {can_exit}, Suggest: {window['tax_benefit']}")
```

## 3. Tax-Loss Harvesting: Book Losses Before Financial Year-End

Near the end of FY (March 31), identify positions at losses. Sell them to realize losses, then immediately repurchase (no wash-sale rules in India). Offset gains from profitable positions. Reduce net taxable gains.

**Pattern: Tax-Loss Harvesting Scan**

```python
import pandas as pd

class TaxLossHarvester:
    def __init__(self, fy_end_date=None):
        """
        Args:
            fy_end_date: Financial year end date (default March 31)
        """
        self.fy_end_date = fy_end_date or datetime(2026, 3, 31)
        self.positions = []  # List of {'symbol': str, 'qty': int, 'buy_price': float, 'current_price': float, 'buy_date': date}

    def add_position(self, symbol, quantity, buy_price, current_price, buy_date):
        self.positions.append({
            'symbol': symbol,
            'quantity': quantity,
            'buy_price': buy_price,
            'current_price': current_price,
            'buy_date': buy_date,
            'gain_loss': (current_price - buy_price) * quantity
        })

    def identify_tax_losses(self, current_date):
        """
        Identify positions at losses and prioritize by magnitude.

        Returns:
            DataFrame of loss positions ranked by loss amount
        """
        df = pd.DataFrame(self.positions)
        loss_df = df[df['gain_loss'] < 0].copy()
        loss_df['days_until_fy_end'] = (self.fy_end_date - current_date).days

        # Prioritize by: 1) Larger losses, 2) Closer to FY end, 3) Non-LTCG positions
        loss_df = loss_df.sort_values(['gain_loss', 'days_until_fy_end'], ascending=[True, False])

        return loss_df

    def calculate_tax_offset(self, loss_df, current_gains):
        """
        Calculate how much of current gains can be offset by harvested losses.

        Args:
            loss_df: DataFrame of losses (from identify_tax_losses)
            current_gains: Total capital gains realized in FY (before harvesting)

        Returns:
            {'total_losses': float, 'offsettable_gains': float, 'tax_saved': float}
        """
        total_losses = abs(loss_df['gain_loss'].sum())
        offsettable = min(total_losses, current_gains)
        tax_saved = offsettable * 0.125  # At 12.5% LTCG rate

        return {
            'total_losses': total_losses,
            'offsettable_gains': offsettable,
            'tax_saved': tax_saved
        }

# Usage
harvester = TaxLossHarvester(fy_end_date=datetime(2026, 3, 31))

# Add positions
harvester.add_position('RELIANCE', 50, 2500, 2300, datetime(2025, 6, 1))  # Loss
harvester.add_position('TCS', 100, 3200, 3500, datetime(2025, 8, 1))      # Gain
harvester.add_position('INFY', 75, 1800, 1600, datetime(2025, 9, 1))      # Loss
harvester.add_position('WIPRO', 200, 400, 450, datetime(2025, 10, 1))     # Gain

current_date = datetime(2026, 2, 28)  # 30 days before FY end
losses = harvester.identify_tax_losses(current_date)

print("Tax-Loss Harvesting Candidates:")
print(losses[['symbol', 'quantity', 'buy_price', 'current_price', 'gain_loss', 'days_until_fy_end']])

# Assume ₹50,000 in gains realized
tax_benefit = harvester.calculate_tax_offset(losses, current_gains=50_000)
print(f"\nTax offset: Loss amount {tax_benefit['total_losses']:>10,.0f}")
print(f"             Offsettable gains: {tax_benefit['offsettable_gains']:>10,.0f}")
print(f"             Tax saved: {tax_benefit['tax_saved']:>10,.0f}")
```

## 4. ₹1,25,000 LTCG Exemption Utilization: Batch Redemptions

Every financial year, individuals get ₹1,25,000 of LTCG at zero tax. Use this exemption by strategically timing redemptions of debt funds, ETFs, or index funds that have been held >1 year.

**Pattern: Exemption Utilization Optimizer**

```python
class LTCGExemptionOptimizer:
    def __init__(self, annual_exemption=125_000):
        """
        Args:
            annual_exemption: ₹1,25,000 per FY for LTCG
        """
        self.annual_exemption = annual_exemption
        self.ltcg_used_this_fy = 0
        self.positions = []

    def add_redeemable_position(self, symbol, quantity, cost_basis, current_value, holding_days):
        """Add a position eligible for redemption."""
        self.positions.append({
            'symbol': symbol,
            'quantity': quantity,
            'cost_basis': cost_basis,
            'current_value': current_value,
            'gain': current_value - cost_basis,
            'holding_days': holding_days,
            'ltcg_eligible': holding_days >= 365
        })

    def optimize_redemptions(self):
        """
        Determine which positions to redeem to maximize use of exemption.

        Returns:
            List of redemption recommendations
        """
        ltcg_positions = [p for p in self.positions if p['ltcg_eligible']]
        ltcg_positions = sorted(ltcg_positions, key=lambda x: x['gain'], reverse=True)

        redemptions = []
        remaining_exemption = self.annual_exemption

        for pos in ltcg_positions:
            if pos['gain'] <= remaining_exemption:
                redemptions.append({
                    'symbol': pos['symbol'],
                    'action': 'REDEEM_FULLY_TAX_FREE',
                    'gain': pos['gain'],
                    'tax': 0
                })
                remaining_exemption -= pos['gain']
            elif remaining_exemption > 0:
                # Partial redemption to use up exemption
                redemptions.append({
                    'symbol': pos['symbol'],
                    'action': 'REDEEM_PARTIAL',
                    'gain': remaining_exemption,
                    'tax': 0
                })
                remaining_exemption = 0
                break

        return redemptions, remaining_exemption

# Usage
optimizer = LTCGExemptionOptimizer(annual_exemption=125_000)

optimizer.add_redeemable_position('NIFTY50_ETF', 100, cost_basis=50_000, current_value=62_500, holding_days=400)
optimizer.add_redeemable_position('DEBT_FUND', 1000, cost_basis=100_000, current_value=115_000, holding_days=380)
optimizer.add_redeemable_position('GOLD_ETF', 50, cost_basis=40_000, current_value=52_000, holding_days=370)

redemptions, leftover = optimizer.optimize_redemptions()

print("Recommended redemptions to utilize ₹1,25,000 LTCG exemption:")
for r in redemptions:
    print(f"{r['symbol']:15} | Gain: ₹{r['gain']:>8,.0f} | Tax: ₹{r['tax']:>8,.0f} | {r['action']}")

print(f"Unused exemption: ₹{leftover:,.0f}")
```

## 5. F&O Taxation: Business Income, Not Capital Gains

Futures and options gains are taxed as business income (slab rates: 5-30%) if held >12 months, not at 12.5% LTCG. However, there's ambiguity: if you trade F&O as a speculator (not dealer), gains may still be short-term capital gains at 20%.

**The edge**: High-frequency F&O traders benefit from loss-offset against other business income (salary, consulting). Conversely, positional F&O traders lose the LTCG tax benefit.

**Pattern: F&O vs Cash Tax Comparison**

```python
def compare_fo_vs_cash_tax(notional_exposure, annual_return_pct, individual_tax_slab=0.20, days_held=100):
    """
    Compare tax treatment of F&O vs equity spot.

    Args:
        notional_exposure: Trade size in rupees
        annual_return_pct: Expected return %
        individual_tax_slab: Income tax slab (0.05 to 0.30)
        days_held: Days position held
    """
    annual_gain = notional_exposure * annual_return_pct

    # Equity spot trading (equity list)
    if days_held >= 365:
        # LTCG
        equity_tax_rate = 0.125
        equity_after_tax = annual_gain * (1 - equity_tax_rate)
    else:
        # STCG
        equity_tax_rate = 0.208
        equity_after_tax = annual_gain * (1 - equity_tax_rate)

    # F&O treatment (business income)
    # Short-term: 20% regardless of holding; Long-term: income tax slab
    if days_held >= 365:
        fo_tax_rate = individual_tax_slab
    else:
        fo_tax_rate = 0.20

    fo_after_tax = annual_gain * (1 - fo_tax_rate)

    tax_advantage = fo_after_tax - equity_after_tax

    return {
        'gain_notional': annual_gain,
        'equity_tax_rate': equity_tax_rate,
        'equity_after_tax': equity_after_tax,
        'fo_tax_rate': fo_tax_rate,
        'fo_after_tax': fo_after_tax,
        'tax_advantage_fo': tax_advantage,
        'tax_advantage_pct': (tax_advantage / annual_gain) * 100 if annual_gain > 0 else 0
    }

# Usage: Compare for 20% annual return over 100 days
result = compare_fo_vs_cash_tax(
    notional_exposure=1_000_000,
    annual_return_pct=0.20,
    individual_tax_slab=0.20,
    days_held=100
)

print("F&O vs Equity Tax Comparison (₹10L position, 20% return, 100 days):")
print(f"Gain: ₹{result['gain_notional']:,.0f}")
print(f"Equity tax (STCG): {result['equity_tax_rate']:.1%} | After-tax: ₹{result['equity_after_tax']:,.0f}")
print(f"F&O tax (slab): {result['fo_tax_rate']:.1%} | After-tax: ₹{result['fo_after_tax']:,.0f}")
print(f"F&O advantage: ₹{result['tax_advantage_pct']:.2f}% of gain")
# Result: F&O is 0.8% better (20% vs 20.8%)
```

## 6. STT Impact: Futures 0.05% (Tripled in Budget 2024)

Stock Transaction Tax on F&O:
- **Futures**: 0.05% on selling side (previously 0.02%, tripled in Feb 2024)
- **Options**: 0.062% on selling side (from 0.017%)

A 10% target on a future with 0.05% STT costs 0.5% of notional. Edge must exceed 0.5%.

**Pattern: Minimum Edge Calculator**

```python
def calculate_minimum_edge_fo(contract_notional, stt_rate=0.0005, brokerage_rate=0.0001):
    """
    Calculate minimum edge needed to break even on F&O after taxes and costs.

    Args:
        contract_notional: Notional value of contract
        stt_rate: STT rate (0.0005 for futures, 0.00062 for options)
        brokerage_rate: Brokerage as % of notional

    Returns:
        minimum_edge_bps: Minimum edge in basis points
    """
    # Costs as % of notional
    total_cost_rate = stt_rate + brokerage_rate

    # Convert to basis points (1 bp = 0.01%)
    min_edge_bps = total_cost_rate * 10_000

    # After tax (assume 20% short-term)
    tax_rate = 0.20
    after_tax_min_edge_bps = min_edge_bps / (1 - tax_rate)

    return {
        'stt_cost_bps': stt_rate * 10_000,
        'brokerage_cost_bps': brokerage_rate * 10_000,
        'total_cost_bps': min_edge_bps,
        'after_tax_min_edge_bps': after_tax_min_edge_bps,
        'break_even_return_pct': (after_tax_min_edge_bps / 10_000) * 100
    }

# Usage
result = calculate_minimum_edge_fo(
    contract_notional=1_000_000,
    stt_rate=0.0005,  # 0.05% for futures
    brokerage_rate=0.0001  # 0.01% brokerage
)

print("Minimum edge for profitable F&O trading:")
print(f"STT cost: {result['stt_cost_bps']:.1f} bps")
print(f"Brokerage cost: {result['brokerage_cost_bps']:.1f} bps")
print(f"Total cost pre-tax: {result['total_cost_bps']:.1f} bps")
print(f"Min edge after 20% tax: {result['after_tax_min_edge_bps']:.1f} bps")
print(f"Break-even return: {result['break_even_return_pct']:.2f}%")
# Result: Need 0.075% edge (7.5 bps) after-tax to break even
```

## 7. Intraday vs Delivery: Delivery Has Tax Advantage

Intraday trades (buy and sell same day) are always STCG, taxed at 20.8%.
Delivery trades (held overnight+) benefit from LTCG at 12.5% after 12 months.

For holding periods of 30-364 days, holding in delivery (vs rolling intraday) saves 8.3 percentage points, but increases risk and margin requirements.

**Pattern: Intraday vs Delivery Decision**

```python
def compare_intraday_vs_delivery(daily_edge_bps, holding_days, initial_capital=100_000):
    """
    Compare PnL after-tax: intraday daily vs holding in delivery.

    Args:
        daily_edge_bps: Daily edge in basis points (e.g., 50 bps)
        holding_days: Number of days to hold if in delivery
        initial_capital: Starting capital
    """
    daily_edge_pct = daily_edge_bps / 10_000

    # Intraday: trade daily, each trade taxed at 20.8%
    intraday_cumulative_return = (1 + daily_edge_pct) ** holding_days - 1
    intraday_tax_rate = 0.208
    intraday_after_tax = intraday_cumulative_return * (1 - intraday_tax_rate)

    # Delivery: hold for holding_days, then exit for LTCG (if >365 days)
    delivery_cumulative_return = (1 + daily_edge_pct) ** holding_days - 1
    if holding_days >= 365:
        delivery_tax_rate = 0.125
    else:
        delivery_tax_rate = 0.208  # Still STCG

    delivery_after_tax = delivery_cumulative_return * (1 - delivery_tax_rate)

    return {
        'holding_days': holding_days,
        'pre_tax_return_pct': intraday_cumulative_return * 100,
        'intraday_after_tax_pct': intraday_after_tax * 100,
        'delivery_after_tax_pct': delivery_after_tax * 100,
        'after_tax_difference_pct': (delivery_after_tax - intraday_after_tax) * 100
    }

# Usage: 50 bps daily edge for 30 days
result = compare_intraday_vs_delivery(daily_edge_bps=50, holding_days=30)
print("Intraday vs Delivery (50 bps daily edge, 30 days):")
print(f"Pre-tax return: {result['pre_tax_return_pct']:.2f}%")
print(f"Intraday after-tax: {result['intraday_after_tax_pct']:.2f}%")
print(f"Delivery after-tax: {result['delivery_after_tax_pct']:.2f}%")
print(f"Delivery advantage: {result['after_tax_difference_pct']:.2f}%")

# For 365+ days:
result_long = compare_intraday_vs_delivery(daily_edge_bps=50, holding_days=366)
print("\nIntraday vs Delivery (50 bps daily edge, 366 days):")
print(f"Pre-tax return: {result_long['pre_tax_return_pct']:.2f}%")
print(f"Intraday after-tax: {result_long['intraday_after_tax_pct']:.2f}%")
print(f"Delivery after-tax: {result_long['delivery_after_tax_pct']:.2f}%")
print(f"Delivery advantage: {result_long['after_tax_difference_pct']:.2f}%")
```

## 8. Code Patterns for Tax-Aware Exit Timing

Assemble tax-aware logic into your order exit routine. Before sending a sell order, check tax implications.

```python
class TaxAwareExitManager:
    def __init__(self):
        self.positions = {}

    def add_position(self, position_id, entry_date, entry_price, quantity):
        self.positions[position_id] = {
            'entry_date': entry_date,
            'entry_price': entry_price,
            'quantity': quantity
        }

    def should_exit_now(self, position_id, current_price, current_date, min_profit_threshold=0.02):
        """
        Determine if position should be exited now, or held for LTCG.

        Args:
            position_id: Position ID
            current_price: Current price
            current_date: Current date
            min_profit_threshold: Minimum profit to justify early exit (ignore tax savings)

        Returns:
            {'should_exit': bool, 'reason': str, 'tax_savings_if_hold': float}
        """
        if position_id not in self.positions:
            return {'should_exit': False, 'reason': 'POSITION_NOT_FOUND', 'tax_savings_if_hold': 0}

        pos = self.positions[position_id]
        holding_days = (current_date - pos['entry_date']).days
        unrealized_gain = (current_price - pos['entry_price']) * pos['quantity']
        unrealized_return = (current_price - pos['entry_price']) / pos['entry_price']

        # Check LTCG eligibility
        is_ltcg_eligible = holding_days >= 365

        if is_ltcg_eligible:
            # If already LTCG, exit immediately (no more tax savings to wait for)
            return {
                'should_exit': True,
                'reason': 'LTCG_ELIGIBLE_EXIT_NOW',
                'tax_savings_if_hold': 0
            }

        # Not yet LTCG
        days_until_ltcg = 365 - holding_days

        # Calculate tax savings if we hold
        stcg_tax = unrealized_gain * 0.208
        ltcg_tax = unrealized_gain * 0.125
        tax_savings = stcg_tax - ltcg_tax

        # Compare tax savings against opportunity cost
        opportunity_cost = unrealized_gain * 0.0005 * days_until_ltcg  # 5 bps per day

        if unrealized_return < min_profit_threshold:
            # If profit is small, exit immediately
            return {
                'should_exit': True,
                'reason': 'PROFIT_BELOW_MIN_THRESHOLD',
                'tax_savings_if_hold': tax_savings
            }

        if tax_savings > opportunity_cost:
            return {
                'should_exit': False,
                'reason': f'HOLD_{days_until_ltcg}_DAYS_FOR_TAX_SAVINGS',
                'tax_savings_if_hold': tax_savings
            }

        return {
            'should_exit': True,
            'reason': 'TAX_SAVINGS_LOWER_THAN_OPPORTUNITY_COST',
            'tax_savings_if_hold': tax_savings
        }

# Usage
manager = TaxAwareExitManager()

entry_date = datetime(2025, 6, 1)
manager.add_position('RELIANCE_100', entry_date, entry_price=2500, quantity=100)

current_price = 2850  # 14% gain
current_date = datetime(2026, 2, 15)  # Day 259 of holding

decision = manager.should_exit_now('RELIANCE_100', current_price, current_date, min_profit_threshold=0.10)
print(f"Exit decision: {decision['should_exit']}")
print(f"Reason: {decision['reason']}")
print(f"Tax savings if hold: ₹{decision['tax_savings_if_hold']:,.0f}")
```

## Summary

Tax optimization is not evasion; it's efficient use of the tax code:

- **STCG vs LTCG**: 7.5% tax arbitrage by holding past 365 days.
- **₹1,25,000 exemption**: Zero tax on first ₹1.25L of LTCG annually.
- **Tax-loss harvesting**: Offset gains with losses (no wash-sale rules in India).
- **F&O vs equity**: Understand different tax treatments; impacts edge.
- **STT costs**: F&O requires 0.5%+ edge just to break even after costs and tax.
- **Intraday vs delivery**: Delivery saves 8.3% on taxes if held >365 days.
- **Exit timing**: Hold until LTCG if tax savings exceed opportunity cost.

Build tax awareness into every trade decision. A 1% tax advantage is a 1% edge without any additional trading skill.
