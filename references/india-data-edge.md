# India Data Edge: FII/DII Flow, Sentiment, & Structural Signals

## Overview
Exploit India-specific data advantages: FII/DII flows, put-call ratios, max pain, delivery percentages, F&O ban impacts, rollover dynamics, bulk/block deals, GIFT Nifty gaps, and rebalancing flows. Each is a forward-looking signal if interpreted correctly.

## Important: Data Access

**NSE does NOT provide any public data API.** All data discussed below must be sourced
from your broker's API (if supported) or third-party data providers. Never scrape NSE
website directly. The code patterns below assume you have the data in a DataFrame —
the *source* of that data depends on your broker and data provider setup.

---

## FII/DII Daily Flow Tracking

FII/DII daily activity data is available through broker APIs (if supported) or
third-party data providers. Track cumulative flows for week/month:

```python
import pandas as pd

def analyze_fii_dii_flow(df):
    """
    Analyze FII/DII flow data.
    Input: DataFrame with columns [date, fii_buy, fii_sell, dii_buy, dii_sell]
    Source: Broker API or third-party data provider (NOT NSE directly)

    Returns: DataFrame with columns:
      - date
      - fii_buy, fii_sell, fii_net
      - dii_buy, dii_sell, dii_net
      - fii_cumulative (rolling 5-day, 20-day, 60-day)
    """
    # Example hardcoded; in live, fetch from NSE API
    fii_dii_data = pd.DataFrame({
        'date': pd.date_range('2026-01-01', periods=60, freq='D'),
        'fii_net': np.random.randn(60) * 500  # Rs Cr
    })

    fii_dii_data['fii_net_5d'] = fii_dii_data['fii_net'].rolling(5).sum()
    fii_dii_data['fii_net_20d'] = fii_dii_data['fii_net'].rolling(20).sum()
    fii_dii_data['fii_cumulative'] = fii_dii_data['fii_net'].cumsum()

    return fii_dii_data

def fii_signal(fii_data_today, fii_5d_avg, trend_strength=500):
    """
    FII signal: if large inflows, buy. If large outflows, sell.
    trend_strength: threshold in Rs Cr
    """
    if fii_data_today > trend_strength:
        return 1, 'FII_BUY'
    elif fii_data_today < -trend_strength:
        return -1, 'FII_SELL'
    else:
        return 0, 'FII_NEUTRAL'

# Usage
fii_df = parse_nse_fii_dii_flow()
today_flow = fii_df['fii_net'].iloc[-1]
signal, label = fii_signal(today_flow, fii_df['fii_net_5d'].iloc[-1], trend_strength=400)
print(f"Today FII flow: Rs {today_flow:.0f} Cr -> Signal: {label}")
```

## Participant-Wise Open Interest (OI) Analysis

Track OI migration by participant (FII vs DII vs Pro vs Client):

```python
def track_oi_by_participant(oi_snapshot_previous, oi_snapshot_current):
    """
    NSE provides OI breakdown by participant segment.
    oi_snapshot: dict with keys 'fii_oi', 'dii_oi', 'pro_oi', 'client_oi'

    Compare OI changes to infer positioning.
    """
    participants = ['fii_oi', 'dii_oi', 'pro_oi', 'client_oi']

    oi_change = {}
    for participant in participants:
        prev_oi = oi_snapshot_previous.get(participant, 0)
        curr_oi = oi_snapshot_current.get(participant, 0)
        oi_change[participant] = curr_oi - prev_oi

    total_oi_change = sum(oi_change.values())

    # Analyze OI distribution shift
    fii_oi_pct = oi_snapshot_current['fii_oi'] / sum(oi_snapshot_current.values())
    dii_oi_pct = oi_snapshot_current['dii_oi'] / sum(oi_snapshot_current.values())

    return {
        'oi_change': oi_change,
        'fii_oi_pct': fii_oi_pct,
        'dii_oi_pct': dii_oi_pct,
        'total_oi_change': total_oi_change
    }

# Example data
oi_prev = {'fii_oi': 1e6, 'dii_oi': 0.8e6, 'pro_oi': 0.3e6, 'client_oi': 0.5e6}
oi_curr = {'fii_oi': 1.05e6, 'dii_oi': 0.75e6, 'pro_oi': 0.32e6, 'client_oi': 0.48e6}

oi_analysis = track_oi_by_participant(oi_prev, oi_curr)
print(f"FII OI % of total: {oi_analysis['fii_oi_pct']:.1%}")
print(f"FII OI change: {oi_analysis['oi_change']['fii_oi']:.0f}")
```

## Put-Call Ratio (PCR) as Sentiment Indicator

High PCR = put buying = bearish sentiment. Low PCR = call buying = bullish:

```python
def compute_pcr_sentiment(put_oi_total, call_oi_total):
    """
    Put-Call Ratio: total put OI / total call OI
    PCR > 1.5: extreme bearish (contrarian buy signal)
    PCR 0.8-1.2: neutral
    PCR < 0.6: extreme bullish (contrarian sell signal)
    """
    pcr = put_oi_total / call_oi_total if call_oi_total > 0 else 0

    if pcr > 1.5:
        sentiment = 'EXTREME_BEARISH'
        signal = 1  # Contrarian BUY
    elif pcr > 1.2:
        sentiment = 'BEARISH'
        signal = 0.5
    elif pcr < 0.6:
        sentiment = 'EXTREME_BULLISH'
        signal = -1  # Contrarian SELL
    elif pcr < 0.8:
        sentiment = 'BULLISH'
        signal = -0.5
    else:
        sentiment = 'NEUTRAL'
        signal = 0

    return pcr, sentiment, signal

# Example
put_oi = 50e6
call_oi = 40e6

pcr, sentiment, signal = compute_pcr_sentiment(put_oi, call_oi)
print(f"PCR: {pcr:.2f} -> {sentiment} (Signal: {signal})")
```

## Max Pain Theory: Expiry-Day Price Target

Calculate max pain (strike where most options expire worthless):

```python
def calculate_max_pain(strikes_with_oi, spot_price):
    """
    Max Pain: the strike price where total OI (calls + puts) expires worthless.
    Price tends to gravitate toward max pain on expiry day.

    strikes_with_oi: list of dicts with 'strike', 'call_oi', 'put_oi'
    spot_price: current spot price
    """
    max_loss = 0
    max_pain_strike = None

    for strike_data in strikes_with_oi:
        strike = strike_data['strike']
        call_oi = strike_data['call_oi']
        put_oi = strike_data['put_oi']

        # Loss to call holders if price < strike: call_oi * (strike - price)
        # Loss to put holders if price > strike: put_oi * (price - strike)
        # Max pain minimizes total loss, i.e., OI * |price_move|

        # Total OI pressure at this strike
        total_oi = call_oi + put_oi
        estimated_loss = total_oi * abs(strike - spot_price)

        if estimated_loss > max_loss:
            max_loss = estimated_loss
            max_pain_strike = strike

    return max_pain_strike, max_loss

# Example: strikes from 23000 to 24000
strikes = [
    {'strike': 23000, 'call_oi': 100000, 'put_oi': 500000},
    {'strike': 23500, 'call_oi': 300000, 'put_oi': 400000},
    {'strike': 24000, 'call_oi': 400000, 'put_oi': 150000},
]

max_pain, loss = calculate_max_pain(strikes, spot_price=23500)
print(f"Max Pain Strike: {max_pain} (Total OI loss: Rs {loss:.0f})")
```

## Delivery Percentage Analysis

High delivery % = institutional accumulation; low % = day-trader activity:

```python
def analyze_delivery_percentage(volumes_data):
    """
    volumes_data: DataFrame with columns 'date', 'total_volume', 'delivery_volume'

    High delivery (>70%) on up days = institutional buying (bullish)
    Low delivery (<30%) on up days = day-trading (neutral/bearish)
    """
    volumes_data['delivery_pct'] = (
        volumes_data['delivery_volume'] / volumes_data['total_volume']
    )

    # Rolling 5-day average
    volumes_data['delivery_pct_5d'] = volumes_data['delivery_pct'].rolling(5).mean()

    # Signal
    recent_delivery_pct = volumes_data['delivery_pct_5d'].iloc[-1]

    if recent_delivery_pct > 0.70:
        signal = 1
        label = 'INSTITUTIONAL_ACCUMULATION'
    elif recent_delivery_pct < 0.30:
        signal = -1
        label = 'DAY_TRADER_ACTIVITY'
    else:
        signal = 0
        label = 'MIXED'

    return signal, label, recent_delivery_pct

# Example
volumes = pd.DataFrame({
    'date': pd.date_range('2026-01-01', periods=20, freq='D'),
    'total_volume': np.random.randint(1e6, 5e6, 20),
    'delivery_volume': np.random.randint(0.3e6, 3.5e6, 20)
})

signal, label, pct = analyze_delivery_percentage(volumes)
print(f"5-day avg delivery: {pct:.1%} -> {label}")
```

## F&O Ban Period Dynamics

When NSE bans F&O on a stock, spot premium inflates and cash-and-carry spreads widen:

```python
def detect_fno_ban_impact(spot_price, cash_futures_basis_bps, days_to_expiry):
    """
    Spot-Futures basis typically 5-15 bps before ban.
    Post-ban: basis widens to 50-200 bps (no arbitrage to narrow it).

    cash_futures_basis_bps: (Futures - Spot) / Spot * 10000
    """
    normal_basis_bps = 15
    ban_basis_bps = 100

    if cash_futures_basis_bps > ban_basis_bps:
        return {
            'signal': 'LIKELY_BAN_OR_LIQUIDITY_CRISIS',
            'opportunity': 'SHORT_FUTURE_LONG_SPOT',
            'basis_widening': cash_futures_basis_bps - normal_basis_bps
        }
    else:
        return {
            'signal': 'NORMAL',
            'opportunity': None,
            'basis_widening': 0
        }

# Example
ban_impact = detect_fno_ban_impact(spot_price=1000, cash_futures_basis_bps=120, days_to_expiry=10)
print(ban_impact)
```

## Rollover Analysis: OI Migration Between Expiries

Track OI shift from near-expiry to next month (rollover day):

```python
def analyze_rollover(oi_current_expiry, oi_next_expiry, date_label='expiry'):
    """
    On rollover day (last day of near expiry), OI migrates to next month.
    Calculate rollover %, used to estimate exit liquidity.
    """
    rollover_pct = oi_next_expiry / (oi_current_expiry + oi_next_expiry)

    if rollover_pct > 0.85:
        return {
            'assessment': 'HEAVY_ROLLOVER',
            'liquidity': 'POOR_IN_NEAR',
            'recommendation': 'REDUCE_NEAR_MONTH_POSITION'
        }
    elif rollover_pct < 0.50:
        return {
            'assessment': 'LIGHT_ROLLOVER',
            'liquidity': 'DECENT_IN_NEAR',
            'recommendation': 'SAFE_TO_HOLD'
        }
    else:
        return {
            'assessment': 'NORMAL_ROLLOVER',
            'liquidity': 'MODERATE',
            'recommendation': 'MONITOR'
        }

# Example
rollover = analyze_rollover(oi_current_expiry=5e6, oi_next_expiry=8e6)
print(rollover)
```

## Bulk & Block Deal Signals

Large institutional trades (bulk deals) signal intent:

```python
def parse_bulk_block_deals(deal_log):
    """
    deal_log: list of dicts with 'date', 'symbol', 'volume', 'price', 'buyer_type'

    Accumulate large deals by buyer type (FII, DII, HNI).
    Signal institutional positioning.
    """
    institutional_deals = [d for d in deal_log if d['buyer_type'] in ['FII', 'DII']]

    fii_volume = sum([d['volume'] for d in institutional_deals if d['buyer_type'] == 'FII'])
    dii_volume = sum([d['volume'] for d in institutional_deals if d['buyer_type'] == 'DII'])

    fii_momentum = fii_volume - (sum([d['volume'] for d in deal_log[-5:] if d['buyer_type'] == 'FII']) or 1)

    if fii_momentum > 0:
        signal = 1
        label = 'FII_ACCUMULATING'
    else:
        signal = -1
        label = 'FII_DISTRIBUTING'

    return signal, label, fii_volume, dii_volume

# Example
deals = [
    {'date': '2026-03-31', 'symbol': 'NIFTY', 'volume': 1e6, 'buyer_type': 'FII'},
    {'date': '2026-03-30', 'symbol': 'NIFTY', 'volume': 0.5e6, 'buyer_type': 'DII'},
]

signal, label, fii_vol, dii_vol = parse_bulk_block_deals(deals)
print(f"FII Volume: {fii_vol:.0f} -> {label}")
```

## GIFT Nifty Pre-Market Gap Indicator

GIFT Nifty (Singapore Nifty futures) trade before NSE opens. Use gap to predict spot open:

```python
def gift_nifty_open_gap(gift_nifty_settlement_prev, nse_nifty_close_prev, nse_nifty_open_today):
    """
    gap = (gift_nifty_settlement_prev - nse_nifty_close_prev) / nse_nifty_close_prev * 10000 bps

    Large positive gap (> 50 bps) = bullish open expected
    Large negative gap (< -50 bps) = bearish open expected
    """
    gap_bps = (gift_nifty_settlement_prev - nse_nifty_close_prev) / nse_nifty_close_prev * 10000

    if gap_bps > 50:
        signal = 1
        label = 'BULLISH_GAP'
    elif gap_bps < -50:
        signal = -1
        label = 'BEARISH_GAP'
    else:
        signal = 0
        label = 'NEUTRAL_GAP'

    return signal, label, gap_bps

# Example
signal, label, gap = gift_nifty_open_gap(23600, 23500, 23520)
print(f"GIFT Gap: {gap:.0f} bps -> {label}")
```

## Index Rebalancing Flows

Nifty 50 / Sensex rebalancing causes predictable option expiries and stock flows:

```python
def detect_rebalancing_period():
    """
    Nifty 50 rebalances quarterly (Mar, Jun, Sep, Dec).
    Alert 2 weeks before: large institutional moves to mirror indices.
    F&O liquidity spikes on rebalance announcement day.
    """
    import datetime
    today = datetime.date.today()
    month = today.month

    rebalance_months = [3, 6, 9, 12]
    days_until_rebalance = 0

    for r_month in rebalance_months:
        if r_month > month:
            rebalance_date = datetime.date(today.year, r_month, 15)
            days_until_rebalance = (rebalance_date - today).days
            break

    if 0 <= days_until_rebalance <= 14:
        return {
            'alert': 'REBALANCING_IMMINENT',
            'days': days_until_rebalance,
            'recommendation': 'EXPECT_HIGH_VOLUME_AND_GAMMA_RISK'
        }
    else:
        return {'alert': 'NO_REBALANCING', 'days': days_until_rebalance}

rebal = detect_rebalancing_period()
print(rebal)
```

## Data Access Integration

```python
def fetch_all_india_edge_signals():
    """
    Consolidated daily data fetch for all edge signals.
    Execute once per day at market open.
    """
    signals = {}

    # 1. FII/DII
    fii_df = parse_nse_fii_dii_flow()
    signals['fii'] = fii_signal(fii_df['fii_net'].iloc[-1], fii_df['fii_net_5d'].iloc[-1])

    # 2. PCR
    put_oi, call_oi = fetch_nse_option_chain_oi()
    signals['pcr'] = compute_pcr_sentiment(put_oi, call_oi)

    # 3. Max Pain
    strikes = fetch_nse_strikes_with_oi()
    signals['max_pain'] = calculate_max_pain(strikes, spot_price=fetch_nse_spot())

    # 4. GIFT Nifty gap
    signals['gift_gap'] = gift_nifty_open_gap(
        fetch_gift_nifty_settlement(),
        fetch_nse_nifty_prev_close(),
        fetch_nse_nifty_open()
    )

    # 5. Delivery %
    volumes = fetch_delivery_volumes()
    signals['delivery'] = analyze_delivery_percentage(volumes)

    return signals

# signals['fii'], signals['pcr'], signals['max_pain'], signals['gift_gap'], signals['delivery']
```

## Summary

- **FII/DII flows**: Daily tracking, accumulate 5-20 day. Buy on inflows > 400Cr, sell on outflows < -400Cr
- **PCR**: High (>1.5) is contrarian buy; low (<0.6) is contrarian sell
- **Max Pain**: Price gravitates here on expiry; use as target
- **Delivery %**: >70% = institutional; <30% = day traders
- **F&O ban**: Widens basis 50+ bps; short futures vs long spot
- **Rollover %**: >85% = poor liquidity; reduce exposure
- **Bulk deals**: FII accumulation = bullish
- **GIFT Nifty gap**: >50 bps = bullish; <-50 bps = bearish
- **Rebalancing**: Every 3 months in Mar/Jun/Sep/Dec; expect gamma spikes
- Combine all signals for robust multi-factor edge
