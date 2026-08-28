# Indian Stock Market Reference for Algo Trading

This document provides essential market mechanics and regulations for building algorithmic trading strategies on Indian exchanges. Use this as your authoritative source before writing strategy code.

## 1. Market Timings

### Equity (NSE/BSE)

| Phase | Time | Purpose |
|-------|------|---------|
| Pre-open Auction | 9:00-9:15 AM | Structure **changes 7 Sep 2026** — see §1B. Until then: order entry 9:00-9:08, matching 9:08-9:12, buffer 9:12-9:15 |
| **Continuous Trading — non-CAS scrips** | **9:15 AM - 3:30 PM** | Main continuous session |
| **Continuous Trading — CAS scrips** | **9:15 AM - 3:15 PM** | Cash securities with F&O contracts; closing auction follows (§1A) |
| Closing Auction Session (CAS scrips) | 3:15-3:35 PM | No order entry 3:15-3:20; limit+market 3:20-3:25; limit only to a random close 3:28-3:30; matching 3:30-3:35 (§1A) |
| Post-Close Session | 3:50-4:00 PM | Orders at the day's closing price. Moved from 3:40 PM by the CAS framework, for CAS and non-CAS securities alike |

**Critical Point — there are now two different closes.** For a **CAS scrip** (cash security
with live derivative contracts) continuous trading ends at **3:15 PM**; after that the only
route to the market is a limit order into the closing auction, inside a ±3% band (§1A). For
every other cash security continuous trading ends at 3:30 PM.

Intraday square-off is done by your **broker's RMS**, not by the exchange, on the broker's own
schedule — published cutoffs range from about 3:00 to 3:12 PM for CAS scrips and are policy,
not regulation. Never rely on it: set your own exit deadline in code, comfortably before
continuous trading ends for that symbol, and read your broker's stated cutoff rather than
assuming one.

### F&O Market (NSE)

- Regular: 9:15 AM - **3:40 PM** (index and stock derivatives alike; extended by the CAS
  framework — CAS itself applies to the cash segment only)
- Late: 3:40-11:55 PM (only for closing trades, no fresh positions)

> **Cash/F&O divergence, from 3 Aug 2026.** A CAS scrip's cash leg stops continuous trading at
> 3:15 PM while its future keeps trading until 3:40 PM. For those 25 minutes a cash-vs-futures
> hedge, cash-futures arbitrage, or covered position **cannot have its cash leg rebalanced**.
> Flatten before 3:15 PM or size for that basis risk explicitly.
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

## 1A. Closing Auction Session (CAS) — live since 3 August 2026

**Scope**: cash segment only, and only securities that have **live derivative contracts**.
Everything else — non-F&O cash, all F&O, currency, MCX — keeps its old timings. This doc
calls an affected security a **CAS scrip**.

**Never hardcode the CAS scrip list.** Eligibility tracks derivatives eligibility and moves
with SEBI's F&O reviews. Resolve it at runtime: NSE publishes a CAS flag in the equity
security master (`security.txt`, field 13), and some broker APIs expose a `cas_eligible`
boolean. Otherwise derive it — does this symbol have any live F&O contract?

```python
# Rupeezy/Vortex has no documented CAS flag — derive from the F&O master
is_cas_scrip = bool(client.instruments.all_by_underlying("NSE_FO", "RELIANCE"))
```

### Cash-segment day, CAS scrip

| Window (IST) | What happens | What you can send |
|---|---|---|
| 9:15 - 3:15 | Continuous trading (CTS). **Ends 3:15 PM, not 3:30.** | Everything, as usual |
| 3:00 - 3:15 | Reference-price measurement window (VWAP of trades here) | Normal CTS orders |
| 3:15 - 3:20 | Reference price + band computed. Untriggered SL, disclosed-quantity and out-of-band orders cancelled here. | **Nothing** — exchange rejects all order entry with an error code |
| 3:20 - 3:25 | Order collection. No trades execute. | Limit **and** market — add, modify, cancel |
| 3:25 - random close | Order collection, restricted. No trades execute. | **Limit only.** Add/modify/cancel of market orders all rejected |
| random close | System-driven, **anytime between 3:28 and 3:30** | — |
| 3:30 - 3:35 | Order matching, trade confirmation, closing price | — |
| 3:50 - 4:00 | Post-close session at the day's closing price (moved from 3:40) | Post-close orders |

**Non-CAS securities**: CTS to 3:30 PM, close = VWAP of the last 30 min of CTS. Their
post-close moved to 3:50-4:00 PM too.

**Equity derivatives**: the segment runs to **3:40 PM**, index and stock alike. CAS does not
apply to derivatives. So a CAS scrip's cash leg is frozen from 3:15 PM while its future keeps
trading for another 25 minutes — a cash/F&O hedge cannot be rebalanced in that window.

### Reference price and bands

- **Reference price** = VWAP of trades **3:00-3:15 PM** (15 minutes, not 30). Fallbacks in
  order: the day's LTP → previous day's close → for corporate actions, the adjusted close.
- **Cash band during CAS: ±3% of the reference price, static** — it does not flex. New orders
  outside it are auto-rejected; resting CTS orders outside it are cancelled at 3:15 PM.
- **Stock futures, 3:15-3:40 PM**: ±3% from a *separately computed futures* reference price,
  with dynamic band flexing suspended. NSE warns the cancellation of out-of-band futures
  orders at 3:15 PM is **sequential, explicitly not instantaneous** — don't assume an atomic
  flush at 3:15:00.
- **Options**: bands and LPP unchanged all day, 9:00 AM - 3:40 PM.
- Reference prices and bands are computed **independently by each exchange**. The same stock
  can have a different band and a different closing price on NSE and BSE.

### Order types in CAS

| Type | In CAS |
|---|---|
| Limit | Allowed. Counts toward the equilibrium price |
| Market | Allowed 3:20-3:25 only for new/modify/cancel. Counts toward equilibrium price |
| Stop-loss (untriggered) | **Not allowed.** Resting ones cancelled at 3:15 PM. An SL that already triggered into a plain limit order during CTS carries forward as a normal limit order |
| Iceberg / disclosed quantity | **Not allowed**, cancelled at 3:15 PM. NSE requires `DisclosedVol = 0` on every CAS order |
| Algo market orders | **Allowed**, no penalty — this reverses the earlier blanket ban |
| IOC | **Do not rely on it.** NSE says IOC is not allowed in CAS; BSE's guidelines describe IOC orders inside CAS being cancelled at session end. The documents conflict |
| MOC / LOC | Indian exchanges do not offer these order types at all — not a CAS-specific rule |

**Trap**: market orders resting from the 3:20-3:25 window are **not flushed at 3:25**. They
stay in the book and still match, ahead of limit orders. Only *requests* about them are barred
after 3:25. Do not code a 3:25 purge.

### Carry-forward and priority

- Unexecuted CTS limit orders carry into CAS, **except** untriggered stop-loss,
  iceberg/disclosed-quantity, and out-of-band orders.
- Carried-forward orders keep **higher time priority** than orders placed inside CAS.
  Modifying one resets that priority.
- **Matching priority: market orders beat limit orders.** Everything fills at the single
  equilibrium price.

### How the closing price is formed

Closing price = the **equilibrium price**: the price at which maximum volume is executable.
Tie-breaks in order: minimum unmatched quantity → price closest to the reference price. If no
equilibrium price is discovered, the reference price becomes the close.

### Knock-on effects you will hit in code

- Anything keyed to "the close" changed meaning on 3 Aug 2026 for CAS scrips — daily close,
  previous close, next-day DPR base, circuit-band base, MTM marks.
- **Expiry settlement of stock derivatives** is now the volume-weighted average of cash-segment
  *closing* prices (the CAS equilibrium prices) across exchanges.
- **There are NO BARS for a CAS scrip between 3:15 and 3:30 PM.** Not empty bars, not
  zero-volume bars — no candles at all. There is no continuous matching in that window, so
  there are no trade prints to build them from. The last continuous candle ends at 3:15 PM
  and the auction arrives as a single print. This is a silent failure mode; see
  "Bar gaps on CAS scrips" below.
- Any close series spanning 3 Aug 2026 has a **methodology break** in it.
- CAS is not held on a day when a market-wide circuit breaker halts trading for the remainder
  of the day; closes revert to VWAP-30min / LTP. *(Documented in BSE's notice only.)*
- The **Pre-Open Auction Session is realigned to the same shape effective 7 September 2026** —
  see §1B. Branch on the date in any pre-open code.

### Bar gaps on CAS scrips (3:15-3:30 PM)

No candles exist in this window. Everything below fails **silently** — no exception, no empty
row, just a shorter series than the code assumes.

| Pattern | What actually happens |
|---|---|
| `df.iloc[-1]` at 3:22 PM | Returns the **3:14 bar**. Your "current price" is 8 minutes stale and never updates. Signals fire on a dead quote |
| Fixed bar-count lookback (`df.tail(20)`) | Silently reaches further back in wall-clock time after 3:15 than it does at 11 AM. Indicator windows shift meaning |
| "Wait for the next bar" loops | Never satisfied from 3:15. The loop spins or hangs until the process is killed |
| Expecting N bars/day (375 one-minute bars) | A CAS scrip yields ~360 continuous bars. Any assertion or reshape on a fixed count breaks |
| Timestamp-continuity / gap detection | Fires a false "data feed dropped" alert every single day at 3:15 |
| `ffill()` across the gap | Fabricates 15 minutes of prices that never traded, then blends them into the auction print |

**What to do instead:** drive closing-window logic off the **clock**, not off bar arrival —
`datetime.now(IST) >= time(15, 15)`, never "has a new bar appeared?". Treat the bar series as
ending at 3:15 PM for CAS scrips, and take the closing price from the daily bar or the broker's
close field rather than from an intraday candle. If you resample or align across symbols,
expect CAS and non-CAS scrips to have **different bar counts for the same day** — join on
timestamp, never on position.

### Broker layer — never hardcode, always verify

The rules above are the **exchange** layer. Your broker sits in front of it, and its behaviour
is policy, not regulation:

- **Intraday (MIS) auto-square-off time.** No exchange document sets one. Published cutoffs
  across major brokers range from roughly 3:00 to 3:12 PM for CAS scrips and differ per broker.
  Read your broker's policy; never hardcode a number.
- **Order buffering 3:15-3:20 PM.** The exchange rejects everything in this window. Some brokers
  queue orders locally and forward them at 3:20; **Rupeezy does not — it rejects them.** Never
  assume the broker is holding your order; verify per broker.
- **GTT, AMO, cover and bracket orders** around CAS are broker products; no exchange circular
  covers them. **On Rupeezy, GTTs stop triggering at 3:15 PM on CAS scrips.**
- **Net effect on a CAS scrip:** the exchange cancels resting stop-losses at 3:15 PM, and on
  Rupeezy broker-side GTT triggers stop at the same moment. There is then **no mechanism that
  protects a cash position through the auction.** Be flat before 3:15 PM, or place a deliberate
  auction limit order inside the ±3% band and accept that it may not fill. Do not design around
  a stop that "will fire during the auction" — nothing will fire.

**Sources**: SEBI circular `SEBI/HO/47/11/11(3)2025-MRD-POD2/I/2765/2026` (16 Jan 2026);
NSE `NSE/CMTR/73362` circular 38/2026 (18 Mar 2026); NSE CAS FAQ v1.0 (May 2026); BSE Notice
20260610-41 (10 Jun 2026). Do not cite broker blogs or news explainers — several published the
wrong session length after go-live.

---

## 1B. Pre-Open Auction Session realignment — effective 7 September 2026

To align the pre-open with CAS, the pre-open session is restructured. It stays 15 minutes
(9:00-9:15 AM) but gains CAS's phase shape: market orders first, then limit-only with a
**system-driven random close**.

| Session | Particulars | Start | Duration |
|---|---|---|---|
| 1 | Order entry period for both limit and market orders | 9:00 AM | 5 mins |
| 2 | Order entry only for limit orders. No modification/cancellation allowed for market orders. **Random close in the last 2 minutes** | 9:05 AM | 5 mins |
| 3 | Order matching | 9:10 AM | 2 mins |
| 4 | Transition of orders from pre-open session to CTS | 9:12 AM | 3 mins |

**What this breaks in code:**

- **The 9:08 AM cutoff is gone.** Any strategy with a hardcoded 9:08 pre-open deadline is
  wrong from 7 Sep 2026. Order entry now runs to a random close **anytime between 9:08 and
  9:10 AM** — there is no safe "submit at 9:07:59" and no pull-at-the-last-second. Assume
  anything live after 9:08 will trade.
- **Market orders are barred after 9:05 AM**, and market orders already resting cannot be
  modified or cancelled after that — the same trap as CAS at 3:25 PM (§1A). Resting market
  orders still match, and match first.
- **Matching moved** from 9:08-9:12 to 9:10-9:12; the transition window is 9:12-9:15.
- This applies to the **whole cash segment**, not just CAS scrips.

**Until 6 September 2026** the old structure applies (order entry 9:00-9:08, matching
9:08-9:12, buffer 9:12-9:15). Branch on the date rather than swapping the constants — a
backtest spanning the changeover needs both.

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

```python
if instrument_type == "equity_intraday":
    is_cas = symbol_has_live_derivatives(symbol)   # runtime lookup, never a hardcoded list
    # Your own hard deadline, comfortably before continuous trading ends for this symbol.
    # Your broker's MIS auto-square-off is separate and is policy (~3:00-3:12 PM) — read it.
    hard_exit_deadline = time(15, 5) if is_cas else time(15, 20)

    check_current_volume()            # low volume = higher settlement-auction risk
    check_current_circuit_band()      # already yellow/orange?
    if volume_low or circuit_high or now_ist.time() >= hard_exit_deadline:
        log_warning("no safe exit window remaining — refusing short")
        return False
```

Size the entry so you can be flat by that deadline. On a CAS scrip there is no late-session
continuous liquidity to bail you out, and the resting stop-loss you were counting on is
cancelled at 3:15 PM.

### Mitigation Strategy

**Strongly prefer F&O (futures/options) for short positions**. F&O positions are cash-settled;
there is no **settlement-auction** risk (a different thing from the Closing Auction Session in
§1A). You can hold until 3:40 PM and exit cleanly.

A cash short cannot do this. From 3 Aug 2026 a cash short in a CAS scrip must be covered
**before 3:15 PM**: after that there is no continuous book, the untriggered stop-loss has been
cancelled by the exchange, and the only exit is a limit order into the auction inside the ±3%
band — with no market order available after 3:25 PM.

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
| NSE Equity | NSE_EQ | Highest (except liquid FnO) | 0.05 (or 1 for low-price stocks) | 9:15-3:30 PM; **CAS scrips 9:15-3:15 continuous + auction 3:15-3:35** (§1A) | Equities |
| NSE F&O | NSE_FO | Very high (indices, popular stocks) | 0.05 (futures), 0.05 (options) | 9:15-**3:40 PM** | Derivatives. Runs 25 min past the cash close of CAS scrips — hedges unrebalanceable 3:15-3:40 |
| NSE Currency | NSE_CD | High | 0.0025 | 9:00 AM-5:00 PM | Forex pairs |
| MCX Commodity | MCX_FO | Moderate-high | 1-5 (by contract) | 9:00 AM-11:30 PM | Commodities |
| BSE Equity | BSE_EQ | Lower than NSE | 0.01-0.05 | Same split as NSE_EQ | Equities. CAS runs independently per exchange — resolve eligibility, bands and close per exchange |
| BSE F&O | BSE_FO | Lower than NSE | 0.05 | 9:15-**3:40 PM** | Derivatives (avoid—NSE has better liquidity) |

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

Read it off the `Instrument` object — never assume, never hardcode:
```python
# Rupeezy/Vortex (vortex-api >= 2.1.8)
tick_size = client.instruments.get_by_ticker("NSE:RELIANCE").tick
```

For other brokers, look up from their instrument master alongside the token. Tick size varies by instrument, exchange, and price level.

---

## 11. Daily Price Range / DPR (Order Price Limits)

Exchanges set a **Daily Price Range (DPR)** for each instrument — the maximum and
minimum price at which orders can be placed for the day. The broker's OMS checks this
BEFORE the order reaches the exchange.

### What Happens

- Orders with prices outside the DPR band are **rejected immediately** by the broker
- This affects: limit orders, stop-loss trigger prices, and target prices
- DPR is based on the previous day's **official** closing price ± the circuit limit percentage.
  For a CAS scrip that close is the auction equilibrium price (§1A) — read it from the broker's
  previous-close field; do not derive it from a trailing 30-minute VWAP, which is the
  pre-3-Aug-2026 definition.

### Common Pitfalls

- **Deep stop-losses**: A stop-loss at -15% when the stock has a 10% circuit band → rejected
- **Ambitious targets**: A target at +25% when DPR is ±20% → rejected
- **After-gap scenarios**: After a gap-up/gap-down open, the effective price range shifts

### Closing Auction price band (CAS scrips)

During CAS a **second, tighter** band applies: orders must be within **±3% of the CAS reference
price** (VWAP of 3:00-3:15 PM), static for the session. It is usually narrower than DPR, so the
effective limit is `min(DPR, CAS band)`. Out-of-band orders are auto-rejected and resting CTS
orders outside the band are cancelled at 3:15 PM. There is no market-order rescue after 3:25 PM.
If your broker does not publish the reference price, accumulate `price * volume` yourself from
3:00 PM — it does not exist before 3:15.

### Code Pattern

```python
CAS_BAND = 0.03            # ±3% of the CAS reference price
CAS_START = time(15, 15)

def validate_price_within_dpr(price, lower_dpr, upper_dpr, now_ist=None,
                              is_cas_scrip=False, cas_ref_price=None):
    """Effective price limit = min(DPR band, CAS band). Raises if out of range."""
    lo, hi = lower_dpr, upper_dpr

    if is_cas_scrip and now_ist is not None and now_ist.time() >= CAS_START:
        if cas_ref_price is None:
            raise ValueError(
                "CAS scrip after 15:15 but no reference price available — "
                "cannot construct a valid auction limit price."
            )
        lo = max(lo, cas_ref_price * (1 - CAS_BAND))
        hi = min(hi, cas_ref_price * (1 + CAS_BAND))

    if price < lo or price > hi:
        raise ValueError(
            f"Price {price} outside effective range [{lo}, {hi}]. "
            f"Order will be rejected."
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
| Instrument master | Broker SDK (e.g., Vortex `client.instruments.get_by_ticker(...)`; `client.download_master()` for whole-universe scans) |
| FII/DII flows | Broker API (if available) or third-party data providers |
| Open Interest by participant | Broker API (if available) or third-party data providers |
| Bulk/block deals | Third-party data providers |
| Corporate actions | Third-party data providers |

---

## 13. Master Data & Runtime Requirements

### Always Resolve Instruments at Runtime

- **Do not hardcode** lot sizes, tick sizes, tokens, or segment mappings
- Lot sizes change (e.g., BANKNIFTY reduced from 20 to 15 lot in 2023)
- Tick sizes vary by instrument and can change
- On Rupeezy/Vortex, use `client.instruments.get_by_ticker(...)` — the SDK caches `master.csv` on disk and downloads it at most once per IST trading day. For other brokers, call their equivalent of `client.download_master()` at strategy start.

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

- [ ] Confirm market timings per instrument (NSE vs MCX vs BSE) **and whether each cash symbol
      is a CAS scrip** — resolved at runtime, never hardcoded
- [ ] CAS scrips: intraday exit deadline set before **3:15 PM** (not 3:25), and your broker's own
      MIS auto-square-off time read from its policy page rather than assumed
- [ ] No reliance on a resting exchange-side stop-loss or disclosed-quantity order after 3:15 PM
      on a CAS scrip — the exchange cancels them at auction start
- [ ] Auction-routed orders are LIMIT only after 3:25 PM, clamped to min(DPR, ±3% of the
      3:00-3:15 VWAP)
- [ ] Anything keyed to "the close" re-checked — for CAS scrips the close is the auction
      equilibrium price, and it differs between NSE and BSE for the same stock
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

**Last Updated**: August 2026
**Applicable Regulations**: SEBI (Regulating Algorithmic Trading) Regulations 2023 + latest
amendments; SEBI Closing Auction Session framework, live 3 August 2026 (cash segment,
securities with live derivative contracts — see §1A). The Pre-Open Auction Session realignment
is effective 7 September 2026 and is not yet in force.
**Disclaimer**: This is a reference guide. CAS scrip eligibility and exact phase timings must be
verified against the current exchange circular — the eligible list moves with SEBI's F&O
eligibility reviews. Always verify with your broker's current rules and RMS settings before
deploying live code.
