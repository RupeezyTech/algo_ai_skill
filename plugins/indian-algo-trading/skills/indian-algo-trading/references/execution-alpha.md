# Execution Alpha: TWAP, VWAP, Timing, & Impact Optimization

## Overview
Win 5-20 bps per trade via optimal execution. Deploy TWAP for time-splits, VWAP for volume-weighting, iceberg orders for stealth, impact modeling to predict slippage. Exploit NSE intraday seasonality: power hours, lunch trap, closing swing. Master expiry-day execution. Avoid stop hunts in final 10 minutes.

## Impact Cost Modeling

Estimate price impact before executing:

```python
def estimate_impact_cost(order_size, daily_volume_avg, price_level, volatility):
    """
    Price impact formula (simplified):
    impact_bps = sqrt(order_size / daily_volume) * volatility * sqrt(time_window)

    order_size: shares to buy/sell
    daily_volume_avg: typical daily volume
    price_level: current price
    volatility: annualized vol
    """
    order_pct_of_volume = order_size / daily_volume_avg

    # Impact grows with sqrt(order size / volume)
    impact_bps = (np.sqrt(order_pct_of_volume) * volatility * 100) * 10000

    # Cap at reasonable levels
    impact_bps = np.clip(impact_bps, 1, 50)

    return impact_bps

# Example: buy 50,000 shares, daily volume 1M, vol 18%, price 500
impact = estimate_impact_cost(
    order_size=50000,
    daily_volume_avg=1e6,
    price_level=500,
    volatility=0.18
)
print(f"Estimated impact: {impact:.1f} bps")

# Expected entry: 500 + impact = 500 + (500 * impact / 10000) = 500.25
effective_price = 500 * (1 + impact / 10000)
print(f"Expected entry price: {effective_price:.2f} (vs best bid {500:.2f})")
```

## TWAP: Time-Weighted Average Price Execution

Split order into N equal time slices over a window. Execute one slice per interval:

```python
def twap_execution_plan(total_quantity, target_period_minutes=30, intervals=10):
    """
    TWAP: split order into equal-size chunks, execute every interval.
    target_period_minutes: e.g., 30 minutes to complete buy
    intervals: number of slices

    Returns: list of (time_offset_minutes, quantity_to_buy)
    """
    interval_size = total_quantity / intervals
    time_step = target_period_minutes / intervals

    plan = []
    for i in range(intervals):
        time_offset = i * time_step
        plan.append({
            'time_offset_minutes': time_offset,
            'quantity': interval_size,
            'target_price': None  # Market order, accept execution price
        })

    return plan

# Execute
total_buy = 100000
plan = twap_execution_plan(total_buy, target_period_minutes=30, intervals=10)

print(f"TWAP Plan: Buy {total_buy} over 30 min in 10 slices of {plan[0]['quantity']:.0f} each")
for i, step in enumerate(plan[:3]):
    print(f"  Step {i+1}: +{step['time_offset_minutes']:.1f} min -> {step['quantity']:.0f} shares")
```

## VWAP: Volume-Weighted Average Price Execution

Weight execution against predicted intraday volume profile. Buy more during high-volume periods:

```python
def vwap_execution_plan(total_quantity, intraday_volume_profile, trading_hours=6.5):
    """
    intraday_volume_profile: dict with keys '9:15-10:00', '10:00-10:30', ..., '15:00-15:30'
    values: expected volume % of daily in each slot

    Allocate order proportional to volume in each slot.
    """
    plan = []
    cumulative_qty = 0

    sorted_slots = sorted(intraday_volume_profile.keys())
    total_vol_pct = sum(intraday_volume_profile.values())

    for slot in sorted_slots:
        vol_pct = intraday_volume_profile[slot]
        qty_for_slot = total_quantity * (vol_pct / total_vol_pct)
        cumulative_qty += qty_for_slot

        plan.append({
            'time_slot': slot,
            'volume_pct': vol_pct,
            'quantity': qty_for_slot
        })

    return plan

# Example: intraday volume profile for Nifty (morning bias)
volume_profile = {
    '9:15-9:45': 0.12,    # opening range, 12% of daily vol
    '9:45-10:30': 0.18,   # power hour, 18% of daily vol
    '10:30-12:00': 0.15,  # mid-morning
    '12:00-1:30': 0.08,   # lunch trap, low vol
    '1:30-2:30': 0.12,    # post-lunch
    '2:30-3:15': 0.20,    # closing swing, high vol
    'CAS_AUCTION': 0.15   # CAS scrips: single crossing at the random close — NOT sliceable
}
# For a CAS scrip (cash symbol with F&O contracts) continuous trading ends 3:15 PM.
# 'CAS_AUCTION' is not a time slot: route that quantity to ONE auction limit order placed
# before 3:15, never to the time-slicer. Non-CAS cash keeps a '3:15-3:30' slot; derivatives
# now run to 3:40 PM. Volume profiles fitted on pre-Aug-2026 data overweight the final
# 30 minutes with liquidity that has since moved into the auction — refit on recent data.

vwap_plan = vwap_execution_plan(100000, volume_profile)
for step in vwap_plan[:3]:
    print(f"{step['time_slot']}: {step['volume_pct']:.0%} of daily -> {step['quantity']:.0f} shares")
```

## Iceberg Orders: Show Only Visible Fraction

Hide bulk of order to avoid signaling intent to market:

> **CAS warning.** NSE/BSE icebergs are disclosed-quantity orders, and the exchange **cancels
> all disclosed-quantity orders at 3:15 PM** on CAS scrips — any unfilled hidden residual is
> cancelled, not carried into the auction. NSE requires `DisclosedVol = 0` on every CAS order.
> Complete iceberg execution by ~3:10 PM, or convert the residual into an explicit auction
> limit order before 3:15.

```python
def iceberg_order_structure(total_quantity, visible_pct=0.10, price_level=500):
    """
    Show only 10% of total order (visible), hide 90% (hidden).
    Execution: visible lot filled, hidden portion revealed incrementally.

    total_quantity: full quantity
    visible_pct: % of order shown in order book (e.g., 10%)
    price_level: limit price
    """
    visible_qty = total_quantity * visible_pct
    hidden_qty = total_quantity - visible_qty

    order = {
        'order_type': 'ICEBERG',
        'total_quantity': total_quantity,
        'visible_quantity': visible_qty,
        'hidden_quantity': hidden_qty,
        'price': price_level,
        'instruction': f'Show {visible_qty:.0f}, then reveal {hidden_qty:.0f} in tranches'
    }

    return order

# Example: buy 100k, show only 10k
iceberg = iceberg_order_structure(100000, visible_pct=0.10, price_level=500)
print(f"Iceberg order: {iceberg['visible_quantity']:.0f} visible, {iceberg['hidden_quantity']:.0f} hidden")
```

## NSE Intraday Seasonality Patterns

Exploit time-of-day effects in Nifty/Sensex:

```python
def nse_intraday_seasonality():
    """
    NSE (IST, UTC+5:30) opens 9:15 AM. The close depends on segment since CAS
    (3 Aug 2026): cash symbols WITH F&O contracts end continuous trading at 3:15 PM
    then run a call auction to matching at 3:30-3:35; cash without F&O ends 3:30 PM;
    equity derivatives end 3:40 PM. The buckets below describe CONTINUOUS trading only.

    KEY PATTERNS:
    1. Opening Range (9:15-9:45): Highest volatility, gap moves, momentum setup
    2. Power Hour (9:45-10:30): Strong directional bias, best for momentum
    3. Mid-Morning (10:30-12:00): Trend continuation, low vol, easy to predict
    4. Lunch Trap (12:00-1:30): Lowest liquidity, whipsaw risk, avoid trend
    5. Post-Lunch (1:30-2:30): Mean reversion, range bound
    6. Closing Swing (2:30-3:15): High vol, algos front-run: best for options.
       Last continuous window for CAS scrips.
    7a. Closing Auction (3:15 -> random close 3:28-3:30, matching 3:30-3:35), CAS
        scrips only: call auction, ±3% band, no market-order requests after 3:25,
        untriggered SL and disclosed-qty orders cancelled at 3:15.
    7b. Final Sprint (3:20-3:30), non-CAS cash and derivatives: stop hunts, thin book.
    """
    seasonality = {
        '9:15-9:45': {
            'period': 'OPENING_RANGE',
            'volatility': 'VERY_HIGH',
            'strategy': 'MOMENTUM_SETUP',
            'liquidity': 'EXCELLENT',
            'recommendation': 'TRADE_CAREFULLY, BREAKOUT_PRONE'
        },
        '9:45-10:30': {
            'period': 'POWER_HOUR',
            'volatility': 'HIGH',
            'strategy': 'MOMENTUM_FOLLOWING',
            'liquidity': 'EXCELLENT',
            'recommendation': 'BEST_FOR_MOMENTUM, TREND_FOLLOWING'
        },
        '10:30-12:00': {
            'period': 'MID_MORNING',
            'volatility': 'MODERATE',
            'strategy': 'TREND_CONTINUATION',
            'liquidity': 'GOOD',
            'recommendation': 'PREDICTABLE, LOWER_RISK'
        },
        '12:00-1:30': {
            'period': 'LUNCH_TRAP',
            'volatility': 'LOW_WITH_WHIPS',
            'strategy': 'AVOID_TRENDS',
            'liquidity': 'POOR',
            'recommendation': 'AVOID_MOMENTUM, FADES_MOVES, MEANDER'
        },
        '1:30-2:30': {
            'period': 'POST_LUNCH',
            'volatility': 'MODERATE',
            'strategy': 'MEAN_REVERSION',
            'liquidity': 'MODERATE',
            'recommendation': 'RANGE_BOUND, REVERSAL_PLAYS'
        },
        '2:30-3:15': {
            'period': 'CLOSING_SWING',
            'volatility': 'VERY_HIGH',
            'strategy': 'OPTIONS_GAMMA_HEDGING',
            'liquidity': 'EXCELLENT',
            'recommendation': 'BEST_FOR_OPTIONS, GAMMA_SCALP, ALGOS_ACTIVE',
            'note': 'Last continuous window for CAS scrips (cash + F&O contracts)'
        },
        '3:15-3:35_CAS': {
            'period': 'CLOSING_AUCTION',
            'volatility': 'DISCONTINUOUS',
            'strategy': 'AUCTION_LIMIT_ONLY',
            'liquidity': 'CONCENTRATED_SINGLE_PRINT',
            'recommendation': ('BEST_VENUE_FOR_CLOSE_BENCHMARKED_FLOW; '
                               'NO_CONTINUOUS_EXECUTION; NO_STOPS_ACTIVE'),
            'note': 'CAS scrips only. ±3% band, limit-only after 3:25, random close 3:28-3:30'
        },
        '3:20-3:30_NON_CAS': {
            'period': 'FINAL_SPRINT',
            'volatility': 'EXTREME',
            'strategy': 'AVOID',
            'liquidity': 'POOR',
            'recommendation': 'STOP_HUNTS, GAPS_TO_CLOSE, AVOID_NEW_LONGS',
            'note': 'Non-CAS cash (to 3:30) and derivatives (to 3:40)'
        }
    }

    return seasonality

seasonality = nse_intraday_seasonality()
print(seasonality['9:45-10:30'])
# Output: Power Hour is best for momentum trading
```

## Timing Strategy: Select Optimal Entry Window

```python
def select_execution_time(signal_strength, market_regime, target_slippage_bps=5):
    """
    Match execution time to signal and market conditions.
    """
    if market_regime == 'TRENDING' and signal_strength > 0.8:
        return {
            'window': '9:45-10:30',  # Power Hour
            'reason': 'Strong momentum in trending market',
            'expected_slippage': 3
        }
    elif market_regime == 'SIDEWAYS' and signal_strength > 0.7:
        return {
            'window': '1:30-2:30',  # Post-lunch mean reversion
            'reason': 'Mean reversion in sideways market',
            'expected_slippage': 2
        }
    elif market_regime == 'VOLATILE':
        return {
            'window': '2:30-3:15',  # Closing swing (gamma activity); CAS scrips stop here
            'reason': 'Options gamma hedging, high vol beneficial',
            'expected_slippage': 5
        }
    else:
        return {
            'window': '10:30-12:00',  # Mid-morning, default
            'reason': 'Default safe window',
            'expected_slippage': 3
        }

execution_window = select_execution_time(signal_strength=0.85, market_regime='TRENDING')
print(f"Execute in: {execution_window['window']} ({execution_window['reason']})")
```

## Expiry-Day Execution Considerations

Expiry days (last Thursday of month) have extreme gamma and liquidity swings:

```python
def expiry_day_execution_rules(days_to_expiry, order_size, daily_volume_avg):
    """
    On expiry day (T=0):
    - Gamma is extreme, pin risk real
    - Liquidity spikes near max pain
    - Avoid illiquid strikes and times
    - Close 30 min before expiry
    - Avoid new directional positions
    """
    if days_to_expiry == 0:
        return {
            'alert': 'EXPIRY_DAY',
            'actions': [
                'CLOSE_ALL_POSITIONS_BY_3:00_PM',
                'AVOID_NEW_LONGS_AFTER_2:30_PM',
                'EXPECT_EXTREME_VOLATILITY',
                'PIN_RISK_ON_ATM_STRIKES',
                'AVOID_ILLIQUID_STRIKES'
            ],
            'execution_window': '9:15-3:00_PM_ONLY',
            'recommended_order_type': 'MARKET_TO_LIQUIDITY'
        }
    elif days_to_expiry == 1:
        return {
            'alert': 'ONE_DAY_BEFORE_EXPIRY',
            'actions': [
                'REDUCE_POSITION_SIZE_BY_50%',
                'AVOID_ILLIQUID_STRIKES',
                'TIGHTEN_STOP_LOSSES',
                'EXPECT_GAMMA_SQUEEZE'
            ],
            'execution_window': '9:15-2:30_PM_PREFERRED'
        }
    else:
        return {
            'alert': 'NORMAL_DAY',
            'actions': ['PROCEED_WITH_NORMAL_EXECUTION']
        }

expiry_rules = expiry_day_execution_rules(days_to_expiry=0, order_size=100000, daily_volume_avg=1e6)
print(expiry_rules)
```

## Closing-Window Risk: auction (CAS scrips) vs stop hunts (everything else)

Two different endgames since 3 Aug 2026. For a **CAS scrip** (cash symbol with F&O contracts)
the continuous book shuts at 3:15 PM and a call auction sets the close. For non-CAS cash and
for derivatives the old stop-hunt dynamic still applies into 3:30 / 3:40 PM.

```python
from datetime import time as dtime

CAS_CONTINUOUS_END = dtime(15, 15)   # cash, symbol has F&O contracts
CAS_MKT_ORDER_BAN  = dtime(15, 25)   # market-order requests rejected from here
CAS_RANDOM_CLOSE   = dtime(15, 28)   # order entry can end any time from here to 15:30

def closing_window_state(now, segment='CASH_CAS', close_time=dtime(15, 30)):
    """
    CASH_CAS timeline:
      <= 15:05     normal continuous trading
      15:05-15:15  LAST CHANCE — the continuous book closes at 15:15
      15:15        auction opens; exchange cancels untriggered SL + disclosed-qty orders;
                   limit and market orders accepted from 15:20
      15:25        limit orders only; market-order requests rejected
      15:28-15:30  random close — assume anything live will trade, there is no
                   pull-at-15:29:59
    Other segments keep the old stop-hunt logic against their own close
    (non-CAS cash 15:30, derivatives 15:40).
    """
    if segment == 'CASH_CAS':
        if now >= CAS_RANDOM_CLOSE:
            return {'alert': 'CAS_CLOSING',
                    'recommendation': 'NO_ACTION_POSSIBLE — order entry may end any second'}
        if now >= CAS_MKT_ORDER_BAN:
            return {'alert': 'CAS_LIMIT_ONLY',
                    'recommendation': 'LIMIT_ORDERS_ONLY inside ±3% of the reference price'}
        if now >= CAS_CONTINUOUS_END:
            return {'alert': 'CAS_AUCTION',
                    'recommendation': 'AUCTION_ONLY — no continuous book, stops already cancelled'}
        if now >= dtime(15, 5):
            return {'alert': 'CAS_LAST_CHANCE',
                    'recommendation': 'CLOSE_ALL_OPEN_POSITIONS before 15:15'}
        return {'alert': 'NORMAL_TRADING', 'recommendation': 'PROCEED_WITH_EXECUTION'}

    # non-CAS cash and derivatives — original stop-hunt logic
    time_to_close = (pd.Timestamp.combine(pd.Timestamp.today(), close_time) -
                     pd.Timestamp.combine(pd.Timestamp.today(), now)).total_seconds() / 60
    if time_to_close < 10:
        return {
            'alert': 'STOP_HUNT_WINDOW_ACTIVE',
            'recommendation': 'CLOSE_ALL_OPEN_POSITIONS',
            'reasoning': 'Extreme vol, stop liquidity hunts, gaps into close',
            'time_to_close_minutes': time_to_close
        }
    elif time_to_close < 20:
        return {
            'alert': 'PRE_CLOSE_RISK_ELEVATED',
            'recommendation': 'REDUCE_SIZE_BY_50%',
            'time_to_close_minutes': time_to_close
        }
    return {'alert': 'NORMAL_TRADING', 'recommendation': 'PROCEED_WITH_EXECUTION'}

# During final 10 min
stop_hunt_alert = closing_window_state(pd.Timestamp.now().time(), segment='CASH_CAS')
if 'HUNT' in stop_hunt_alert['alert']:
    print(f"ALERT: {stop_hunt_alert['alert']} - {stop_hunt_alert['recommendation']}")
```

## Live Execution Loop: TWAP + Seasonality

```python
def execute_order_with_seasonality_awareness(
    total_quantity,
    order_side,  # 'BUY' or 'SELL'
    signal_strength,
    market_regime,
    current_price
):
    """
    Integrated execution orchestration combining TWAP, VWAP, seasonality, impact.
    """
    # 1. Check if in stop-hunt window
    stop_hunt_status = closing_window_state(pd.Timestamp.now().time(), segment=segment)
    if stop_hunt_status['alert'] not in ('NORMAL_TRADING',):
        return {'status': 'REJECTED', 'reason': stop_hunt_status['alert']}

    # 2. Estimate impact
    impact_bps = estimate_impact_cost(
        order_size=total_quantity,
        daily_volume_avg=1e6,
        price_level=current_price,
        volatility=0.18
    )

    # 3. Select execution window
    exec_window = select_execution_time(signal_strength, market_regime)

    # 4. Build TWAP plan
    twap_plan = twap_execution_plan(
        total_quantity=total_quantity,
        target_period_minutes=30,
        intervals=10
    )

    return {
        'status': 'PLANNED',
        'total_quantity': total_quantity,
        'expected_impact_bps': impact_bps,
        'execution_window': exec_window['window'],
        'twap_slices': len(twap_plan),
        'first_slice_qty': twap_plan[0]['quantity'],
        'expected_entry': current_price * (1 + impact_bps / 10000) if order_side == 'BUY' else current_price * (1 - impact_bps / 10000)
    }

plan = execute_order_with_seasonality_awareness(
    total_quantity=100000,
    order_side='BUY',
    signal_strength=0.85,
    market_regime='TRENDING',
    current_price=23500
)
print(f"Execution Plan: {plan['status']}")
print(f"  Window: {plan['execution_window']}")
print(f"  Impact: {plan['expected_impact_bps']:.1f} bps")
print(f"  Expected Entry: {plan['expected_entry']:.2f}")
```

## Summary

- **Impact cost**: sqrt(order_size/daily_vol) * vol * 100 bps. Typical: 5-20 bps
- **TWAP**: Split into 10 equal slices over 30 min. Best for large orders in calm markets
- **VWAP**: Weight by intraday volume profile. Buy more during power hours (9:45-10:30)
- **Iceberg**: Hide 90%, show 10% to avoid signaling intent
- **Power Hour (9:45-10:30)**: Best for momentum. Execute here for strong signals
- **Lunch Trap (12:00-1:30)**: Avoid trends. Low vol, whipsaw, unpredictable
- **Closing Swing (2:30-3:15)**: Highest vol, best for gamma scalping & options. Last continuous window for CAS scrips
- **Closing Auction (3:15-3:35, CAS scrips)**: Call auction sets the close. Limit-only after 3:25, ±3% band, random close 3:28-3:30. Stops already cancelled at 3:15
- **Final Sprint (3:20-3:30, non-CAS cash; to 3:40 derivatives)**: Stop hunts, gaps. Close ALL well before
- **Expiry Day**: Extreme gamma. Close by 3:00 PM, avoid new longs after 2:30 PM
- **Combine**: Select window by regime, execute TWAP over target period, monitor impact cost
