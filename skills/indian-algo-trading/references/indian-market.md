# Indian Stock Market Reference for Algo Trading

This document provides essential market mechanics and regulations for building algorithmic trading strategies on Indian exchanges. Use this as your authoritative source before writing strategy code.

## 1. Market Timings

### Equity (NSE/BSE)

| Phase | Time | Purpose |
|-------|------|---------|
| Pre-open Order Entry | 9:00-9:08 AM | Submit orders for pre-open auction |
| Pre-open Matching | 9:08-9:12 AM | Exchange matches orders at equilibrium price |
| Pre-open Buffer | 9:12-9:15 AM | Cooldown before regular trading starts |
| **Regular Trading** | **9:15 AM - 3:30 PM** | Main continuous trading session |
| Post-Close Auction | 3:40-4:00 PM | Trading at closing price (bulk orders only) |

**Critical Point**: Regular session closes at **3:30 PM sharp**. All intraday positions not squared by 3:29:59 PM will be forcibly closed by the exchange.

### F&O Market (NSE)

- Regular: 9:15 AM - 3:30 PM
- Late: 3:40-11:55 PM (only for closing trades, no fresh positions)
- After-Market Orders (AMO):
  - Equity: 3:45 PM - 8:57 AM next day
  - F&O: 3:45 PM - 9:10 AM next day

**Note**: AMO orders submitted after market close are queued and execute at next market open based on pre-open auction (equity) or 9:15 AM opening (F&O).

### MCX Commodity Futures

- Extended hours: 9:00 AM - 11:30 PM (same day settlement for many contracts)
- Higher leverage, different margin rules apply

### GIFT Nifty (Pre-market Indicator)

- Trading on ICCX: ~19 hours daily, ~8:15 AM IST opening
- **Use as leading indicator**: Opens before Indian market, reflects global overnight movement
- Not directly eligible for arbitrage into domestic NIFTY during pre-open (different exchange rules)

---

## 2. F&O Expiry Calendar & Rules

### Expiry Dates

| Instrument | Expiry Day | Frequency | Notes |
|------------|-----------|-----------|-------|
| NIFTY Weekly | Every Tuesday | Weekly | Only NIFTY has weeklies |
| BANKNIFTY, FINNIFTY, MIDCPNIFTY | Last Tuesday of month | Monthly only | Weeklies **discontinued** (Feb 2024) |
| All Index/Stock Futures | Last Tuesday of month | Monthly | NSE standard |
| All BSE Index Expiries | Last **Thursday** of month | Monthly | Different from NSE |
| Index Options (NIFTY, BANKNIFTY) | Last Tuesday | Monthly | Weekly NIFTY options available |
| Stock Options | Last Thursday | Monthly | Check symbol-specific calendar |

### Holiday Rule for Expirations

**If expiry date is a holiday (market closed), the expiry moves to the previous trading day.** For example:
- If last Tuesday falls on a national holiday, expiry is moved to Monday.
- Check the exchange holiday calendar before assuming standard expiry dates.

### Implications for Strategy

- **NIFTY weeklies expiry causes volatility on Tuesdays**. Gamma risk is highest on expiry day.
- **Calendar spread margins change on expiry day**: Index spreads have margin relief removed; single-stock spreads losing relief in May 2026.
- Always monitor expiry calendar and adjust position sizing accordingly.

---

## 3. Circuit Limits (Halts & Restrictions)

### Individual Stock Circuits

Circuits are triggered progressively on **percentage moves from yesterday's close**:

| Circuit Level | Upper Limit | Lower Limit | Trading Status |
|--------------|------------|-----------|-----------------|
| Green | +2% | -2% | Normal trading continues |
| Yellow | +5% | -5% | Restriction phase, panic orders auto-rejected |
| Orange | +10% | -10% | Trading halted for 45 minutes (10:00 AM or 2:45 PM) |
| Red | +20% | -20% | Trading halted until 3:25 PM for recovery |

**What happens**: When a stock hits yellow/orange/red limit, trading halts and a 5-minute cooling period begins. During this window, you can cancel but cannot place new orders in cash market.

### Market-Wide Circuit Breakers (Indices)

When NIFTY50 or SENSEX moves:

| Decline | Trading Halt Duration |
|---------|----------------------|
| -10% | 1 hour (or until 3:30 PM if triggered after 2:30 PM) |
| -15% | 2 hours (or until 3:30 PM) |
| -20% | Market closes for the day |

**Implication**: A sudden market shock can halt the entire market. Maintain dry powder for opportunities and avoid overleveraging in margin positions.

---

## 4. Short Selling Auction Risk (CRITICAL FOR INTRADAY)

This is the **most dangerous trap** for Indian intraday traders.

### The Problem

If you short-sell equity in intraday (margin delivery) and the stock **hits the upper circuit**, the exchange will **forcibly close your position at auction**. You cannot exit.

### Auction Close-out Price Calculation

The exchange auctions your position at the **highest of**:
1. Highest price on T-day (trading day)
2. Highest price on T+1 (auction day)
3. **20% above yesterday's closing price** (absolute floor)

**Example**: Stock XYZ closes at 100 on Monday. You short 100 shares intraday. On Tuesday, it hits upper circuit at 120 (20% move). The auction closes your position at the highest price between Tuesday's trading range and Wednesday's auction, but never below 120.

### Penalty Structure

- **Auction Penalty**: 0.05% of auction close-out value
- **GST**: 18% applied on top of the penalty
- **Total penalty**: ~0.059% of position value (non-trivial for large shorts)

### Code Pattern for Risk Management

Before allowing a short-sale order, always check:

```
if (instrument_type == "equity_intraday"):
    check_current_volume()           # Low volume = higher auction risk
    check_current_circuit_band()     # Is it already in yellow/orange?
    check_time_to_3pm()              # Closing margin is tightest
    if (volume_low OR circuit_high OR time_after_2pm):
        log_warning("High auction risk on short")
        return False
```

### Mitigation Strategy

**Strongly prefer F&O (futures/options) for short positions**. F&O positions are cash-settled; there is no auction risk. You can hold the position until 3:30 PM and exit cleanly.

---

## 5. Transaction Costs (FY 2025-26)

Build these into your strategy's break-even calculation.

### STT (Securities Transaction Tax)

| Instrument | Rate | Direction | Notes |
|-----------|------|-----------|-------|
| Equity Delivery | 0.1% | Buy-side | Paid on both buy and sell |
| Equity Intraday | 0.025% | Sell-side | Only on exit (market-to-market) |
| Equity Futures | 0.05% | Sell-side | Only on sell-close |
| Index Futures | 0.02% | Sell-side | Lower rate than stock futures |
| Options (CE/PE) | 0.1% | Sell-side | Paid on exit/assignment |

### Other Charges (All Instruments)

| Fee | Rate | Notes |
|-----|------|-------|
| Exchange Transaction Charge | 0.002-0.006% | Varies by segment |
| SEBI Turnover Fee | 0.0001-0.0002% | Regulatory fee |
| Stamp Duty | Negligible | Electronic trading |
| Brokerage | Firm-dependent | Usually 0.03-0.05% for algorithmic |

### Total Round-Trip Cost Estimates

For 1 Lakh rupees position:

| Strategy | Total Cost | Break-even Move |
|----------|-----------|-----------------|
| Equity intraday buy-sell | ~100 | 0.1% |
| Equity futures buy-sell | ~150 | 0.15% |
| Index options (buy 1 contract) | ~200-300 | Depends on premium paid |
| Equity delivery (buy-hold-sell) | ~200 | 0.2% |

**Implication**: Intraday strategies need move >0.1% to be profitable after costs. Mean-reversion strategies targeting 0.05% moves will lose money.

---

## 6. Settlement & Delivery

### T+1 Settlement (Standard)

- **Equity**: All equity trades (delivery or intraday squared) settle on T+1.
- **F&O**: Futures settle daily (mark-to-market); options settle at expiry.
- **Margin**: On T-day, you pay upfront margin to your broker. On T+1, margin is released once the trade settles.

### T+0 Optional Settlement

- Available for **top 500 stocks** (NIFTY500 constituents).
- Investor can opt to receive shares same day as purchase.
- Rarely used in algo trading; standard is T+1.

---

## 7. Exchange Segments

Always confirm the correct segment symbol before placing orders.

| Segment | Code | Liquidity | Tick Size | Hours | Use Case |
|---------|------|-----------|-----------|-------|----------|
| NSE Equity | NSE_EQ | Highest (except liquid FnO) | 0.05 (or 1 for low-price stocks) | 9:15-3:30 PM | Equities |
| NSE F&O | NSE_FO | Very high (indices, popular stocks) | 0.05 (futures), 0.05 (options) | 9:15-3:30 PM | Derivatives |
| NSE Currency | NSE_CD | High | 0.0025 | 9:00 AM-5:00 PM | Forex pairs |
| MCX Commodity | MCX_FO | Moderate-high | 1-5 (by contract) | 9:00 AM-11:30 PM | Commodities |
| BSE Equity | BSE_EQ | Lower than NSE | 0.01-0.05 | 9:15-3:30 PM | Equities (avoid unless specific reason) |
| BSE F&O | BSE_FO | Lower than NSE | 0.05 | 9:15-3:30 PM | Derivatives (avoid—NSE has better liquidity) |

**Best Practice**: Route all orders to NSE_EQ and NSE_FO. Liquidity is 10-100x higher than BSE.

---

## 8. SEBI Regulations for Algo Trading

### Order-to-Trade Ratio (OTR)

- **Max ratio**: 50:1 (50 orders placed, only 1 must execute on average)
- **Breach penalty**: Fine + possible trading account suspension
- **Implication**: Don't flood the market with layered orders. Algo strategies using order-cancel patterns must track this closely.

### Calendar Spread Margin Relief (Expiring Feature)

- **Indices** (NIFTY, BANKNIFTY, FINNIFTY): Relief **ends February 2025** (already expired)
- **Single-stock spreads**: Relief **ends May 2026**
- After expiry, margin requirement for calendar spreads increases significantly (~50% higher)

**Action Item**: Recheck margin requirements in June 2026 if running calendar spread strategies.

### Upfront Margin Collection

- Brokers must collect **full margin upfront** before order execution.
- No "margin utilization after execution" allowed.
- If margin insufficient, order is rejected at submission.

---

## 9. Important Calendar Events

Plan for volatility spikes and liquidity changes around these dates:

### RBI Monetary Policy Committee (MPC) Meetings

- Held every 6 weeks (roughly 8 meetings per year)
- Announcement date: Typically 2:00 PM IST
- **Impact**: Massive volatility in 15 minutes, then long-term repricing. Avoid holding concentrated positions 1 hour before announcement.

### Union Budget (National)

- Usually **1st February** of each fiscal year (or announced by Minister of Finance in January)
- **Impact**: High volatility in first 30 minutes; then sectoral rotation all day
- **Implication**: Rebalancing strategies may hit higher slippage

### Monthly F&O Expiry (Last Tuesday of Month)

- **Gamma Squeezes**: Options expire, gamma hedging unwinds cause sharp 1-2% moves in final hour
- **Volume Surge**: 200%+ above daily average in last 30 minutes
- **Implication**: Good opportunity for mean-reversion if you can manage execution timing

### Other High-Impact Dates

- **Corporate earnings seasons**: April-May (Q4 FY), July-Aug (Q1), Oct-Nov (Q2), Jan (Q3)
- **Options expiry weeks**: Elevated IV, wider spreads
- **Holidays**: Market closed (plan for Friday-to-Monday gaps if holiday on Monday)

---

## 10. Tick Sizes (CRITICAL — Orders Rejected Without This)

Every instrument has a minimum price increment (tick size). Order prices MUST be
rounded to the nearest valid tick or the broker's OMS rejects the order instantly.

### How Tick Sizes Work

- The tick size is in the `tick` column of the instrument master
- Common values: ₹0.05 for most equities, ₹0.01 for some, varies for F&O
- An order at ₹247.12 when tick size is ₹0.05 → **REJECTED**. Must be ₹247.10 or ₹247.15.

### Mandatory Code Pattern

```python
def round_to_tick(price, tick_size):
    """Round price to nearest valid tick. MUST be called before every order."""
    return round(round(price / tick_size) * tick_size, 2)

# Usage — apply to EVERY price before order placement
order_price = round_to_tick(calculated_price, tick_size)
stop_loss_price = round_to_tick(calculated_sl, tick_size)
target_price = round_to_tick(calculated_target, tick_size)
```

### Where to Get Tick Size

Look up from instrument master alongside the token:
```python
master = client.download_master()
headers = master[0]
tick_idx = headers.index("tick")
# ... find your instrument row ...
tick_size = float(row[tick_idx])
```

Never assume a tick size. It varies by instrument, exchange, and price level.

---

## 11. Daily Price Range / DPR (Order Price Limits)

Exchanges set a **Daily Price Range (DPR)** for each instrument — the maximum and
minimum price at which orders can be placed for the day. The broker's OMS checks this
BEFORE the order reaches the exchange.

### What Happens

- Orders with prices outside the DPR band are **rejected immediately** by the broker
- This affects: limit orders, stop-loss trigger prices, and target prices
- DPR is based on the previous day's close ± the circuit limit percentage

### Common Pitfalls

- **Deep stop-losses**: A stop-loss at -15% when the stock has a 10% circuit band → rejected
- **Ambitious targets**: A target at +25% when DPR is ±20% → rejected
- **After-gap scenarios**: After a gap-up/gap-down open, the effective price range shifts

### Code Pattern

```python
def validate_price_within_dpr(price, lower_dpr, upper_dpr):
    """Check if order price falls within the Daily Price Range."""
    if price < lower_dpr or price > upper_dpr:
        raise ValueError(
            f"Price {price} outside DPR range [{lower_dpr}, {upper_dpr}]. "
            f"Order will be rejected by OMS."
        )
    return True

# Get DPR from quote data (if available from broker API)
# Or estimate from previous close and circuit band
prev_close = 1500.0
circuit_pct = 0.20  # 20% band
lower_dpr = round_to_tick(prev_close * (1 - circuit_pct), tick_size)
upper_dpr = round_to_tick(prev_close * (1 + circuit_pct), tick_size)
```

When placing orders far from current price (wide stop-losses, distant targets),
always validate against DPR first.

---

## 12. NSE Does NOT Provide a Public Data API

**NSE does not offer any direct API for programmatic data access.** This is a common
misconception. All market data must come through your broker's API or third-party
data providers.

### What This Means for Strategy Code

- **Live quotes**: Use broker API (`client.quotes()`)
- **Historical candles**: Use broker API (`client.historical_candles()`)
- **Order book / depth**: Use broker WebSocket feed
- **FII/DII data**: Available from broker API if supported, or third-party providers
- **Open Interest**: Available from broker API if supported
- **Delivery data**: Third-party providers only

### What NOT to Do

- Never scrape NSE website — it's rate-limited, legally questionable, and breaks frequently
- Never assume NSE has a REST API you can call directly
- Never write `requests.get("https://www.nseindia.com/api/...")` — this will fail

### Data Sources

| Data Type | Where to Get It |
|-----------|----------------|
| Live prices, quotes | Broker API (e.g., Vortex `client.quotes()`) |
| Historical OHLCV | Broker API (e.g., Vortex `client.historical_candles()`) |
| Instrument master | Broker API (e.g., Vortex `client.download_master()`) |
| FII/DII flows | Broker API (if available) or third-party data providers |
| Open Interest by participant | Broker API (if available) or third-party data providers |
| Bulk/block deals | Third-party data providers |
| Corporate actions | Third-party data providers |

---

## 13. Master Data & Runtime Requirements

### Always Download Fresh Instrument Master

- **Do not hardcode** lot sizes, tick sizes, tokens, or segment mappings
- Lot sizes change (e.g., BANKNIFTY reduced from 20 to 15 lot in 2023)
- Tick sizes vary by instrument and can change
- Call `client.download_master()` at strategy start to fetch current instrument data

### Fields to Load Per Instrument

From instrument master, always load:
- `token`: Unique instrument ID (changes daily for options)
- `lot_size`: Minimum tradeable quantity
- `tick`: Minimum price movement — **round all prices to this**
- `exchange`: Segment code (NSE_EQ, NSE_FO, etc.)
- `symbol`: Trading symbol
- `expiry_date`: For derivatives (YYYYMMDD format)
- `option_type`: CE or PE for options
- `strike_price`: For options

### Time-Sensitive Data

- **Circuit limits / DPR**: Can change intra-day; check before placing orders
- **Open interest**: For options, critical to assess liquidity before entry
- **Bid-ask spread**: Widens during news/earnings; tightens during boring periods

---

## Summary Checklist for Strategy Launch

- [ ] Confirm market timings for your instruments (NSE vs MCX vs BSE)
- [ ] Check F&O expiry calendar; flag expiry week for elevated volatility
- [ ] Confirm circuit band width for each instrument (2% for large-cap, wider for small-cap)
- [ ] **Avoid short-selling equity intraday** if circuit/volume risk is high (use F&O instead)
- [ ] Calculate round-trip transaction costs; ensure break-even move is achievable
- [ ] Build OTR tracking if using order-cancel patterns
- [ ] Load instrument master (don't hardcode lot sizes, tokens, or tick sizes)
- [ ] **Round all order prices to tick size** before submission
- [ ] **Validate all prices against DPR** before submission
- [ ] Plan for settlement lag (T+1); don't assume instant fund availability
- [ ] Monitor calendar for RBI/Budget events; consider lower leverage on those days
- [ ] Route to NSE_EQ and NSE_FO; avoid BSE unless forced by liquidity constraints
- [ ] **All market data via broker API** — never scrape NSE directly

---

**Last Updated**: March 2026
**Applicable Regulations**: SEBI (Regulating Algorithmic Trading) Regulations 2023 + latest amendments
**Disclaimer**: This is a reference guide. Always verify with your broker's current rules and RMS settings before deploying live code.
