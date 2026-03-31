# Rupeezy Vortex Broker Adapter Reference

Complete reference for the Vortex Python SDK — the primary trading API for the Rupeezy algorithmic trading platform. This document covers authentication, order placement, market data, backtesting, and deployment patterns.

---

## Installation

Install the SDK via pip:

```bash
pip install vortex-api
```

Add to `requirements.txt`:
```
vortex-api>=1.0.0
```

---

## Deployment Modes

### Container Platform (Rupeezy Managed)

Strategy runs inside a Docker container managed by Rupeezy. No Docker setup required. Code deployment is declarative — credentials are injected automatically.

**Setup:**
- Create zip bundle with `main.py` and `requirements.txt` at root level
- Upload to platform; container builds and deploys automatically
- Platform handles starting/stopping on user-configured schedules

**Initialization:**
```python
from vortex_api import VortexAPI

# Zero-arg init — credentials injected by platform
client = VortexAPI()

# Immediately ready to use
holdings = client.holdings()
```

**Container constraints:**
- Python 3.12, 3.13, or 3.14 only (slim image)
- Only `vortex-api.rupeezy.in`, `wire.rupeezy.in`, `static.rupeezy.in` reachable
- Do NOT write logs to files — use print() or client logger; view logs on platform
- Do NOT add scheduling logic — platform manages start/stop times via cron
- Platform handles container lifecycle; strategy code runs once per schedule

### Self-Hosted (User's System)

Strategy runs on your own machine/server. Manual OAuth authentication required.

**Setup:**
1. Create application on Vortex portal → obtain Application ID and API Key
2. Configure OAuth callback URL on portal
3. Visit `https://flow.rupeezy.in?applicationId={APPLICATION_ID}`
4. After login, capture `auth={auth_code}` from callback URL
5. Exchange auth code for access token

**Initialization:**
```python
from vortex_api import VortexAPI

# Explicit credentials
client = VortexAPI(api_key="your_api_key", application_id="your_application_id")

# Exchange auth code for access token
client.exchange_token("received_auth_code")
# client.access_token is now available
```

**Environment variables (recommended):**
```bash
export VORTEX_API_KEY=your_api_key
export VORTEX_APPLICATION_ID=your_application_id
export VORTEX_ACCESS_TOKEN=your_access_token
```

```python
# Zero-arg init picks up credentials from environment
client = VortexAPI()
```

---

## Authentication

### Container Platform
Credentials are injected at runtime. Use zero-argument initialization:
```python
client = VortexAPI()
```

Enable debug logging if needed:
```python
client = VortexAPI(enable_logging=True)
```

### Self-Hosted OAuth Flow
1. User visits `https://flow.rupeezy.in?applicationId={APPLICATION_ID}`
2. After authentication, redirect contains `?auth={auth_code}`
3. Exchange auth code for persistent access token:

```python
from vortex_api import VortexAPI

client = VortexAPI(api_key="key", application_id="app_id")
client.exchange_token(auth_code)  # Populates client.access_token

# Save access_token for future use — it persists across sessions
saved_token = client.access_token
```

### Environment Variables
Both deployment modes support environment-based configuration:
- `VORTEX_API_KEY` — API secret (self-hosted only)
- `VORTEX_APPLICATION_ID` — Application ID (self-hosted only)
- `VORTEX_ACCESS_TOKEN` — Access token (optional, auto-generated on auth)

---

## Instrument Master (Critical)

Tokens change daily. Always look them up by symbol — never hardcode tokens.

### Download Master Data
```python
from vortex_api import VortexAPI

client = VortexAPI()
master = client.download_master()  # Returns list of lists

# First row is header
headers = master[0]
# Columns: token, exchange, symbol, instrument_name, expiry_date,
#          option_type, strike_price, tick, lot_size, ...

# Remaining rows are instrument data
for row in master[1:]:
    token = row[headers.index("token")]
    symbol = row[headers.index("symbol")]
    exchange = row[headers.index("exchange")]
    lot_size = row[headers.index("lot_size")]
    # ... process
```

### Token Lookup Pattern
```python
def lookup_token(master, symbol, exchange="NSE_EQ"):
    """Find instrument token by symbol and exchange."""
    headers = master[0]
    symbol_idx = headers.index("symbol")
    exchange_idx = headers.index("exchange")
    token_idx = headers.index("token")

    for row in master[1:]:
        if row[symbol_idx] == symbol and row[exchange_idx] == exchange:
            return int(row[token_idx])
    return None

# Usage
token = lookup_token(master, "RELIANCE", "NSE_EQ")  # Returns 2885
```

### Lot Size Lookup
Lot sizes are dynamic and instrument-specific. Always look them up:
```python
def get_lot_size(master, token):
    """Return lot size for an instrument token."""
    headers = master[0]
    token_idx = headers.index("token")
    lot_size_idx = headers.index("lot_size")

    for row in master[1:]:
        if int(row[token_idx]) == token:
            return int(row[lot_size_idx])
    return 1  # Default if not found

# Usage
lot = get_lot_size(master, 2885)  # Returns lot size for that token
quantity = 2 * lot  # Always scale by lot size for F&O instruments
```

### Master Data Columns
| Column | Type | Example | Notes |
|--------|------|---------|-------|
| token | int | 2885 | Unique identifier — look up by symbol |
| exchange | str | NSE_EQ | NSE_EQ, BSE_EQ, NSE_FO, BSE_FO, MCX_FO |
| symbol | str | RELIANCE | Stable across sessions |
| instrument_name | str | EQUITIES | EQUITIES, EQIDX, FUTSTK, OPTIDX, etc. |
| expiry_date | str | 2025-04-30 | Empty for equities; YYYY-MM-DD for F&O |
| option_type | str | CE | CE, PE, or empty |
| strike_price | float | 1000.00 | 0 for non-options |
| tick | float | 0.05 | Minimum price movement |
| lot_size | int | 1 | For equities: 1; for F&O: contract multiplier |

---

## Order Placement

### Core Method: place_order()

```python
from vortex_api import VortexAPI, Constants as Vc

client = VortexAPI()

order = client.place_order(
    exchange=Vc.ExchangeTypes.NSE_EQUITY,     # Exchange type
    token=2885,                                 # Instrument token (from master)
    transaction_type=Vc.TransactionSides.BUY, # BUY or SELL
    product=Vc.ProductTypes.DELIVERY,          # DELIVERY, INTRADAY, MTF
    variety=Vc.VarietyTypes.REGULAR_LIMIT_ORDER,  # Order variety
    quantity=1,                                 # Number of units
    price=2400.0,                              # Limit price (0 for market)
    trigger_price=0.0,                         # Trigger price for SL orders
    disclosed_quantity=0,                      # Iceberg order quantity
    validity=Vc.ValidityTypes.FULL_DAY,       # DAY, IOC, AMO
)

print(f"Order ID: {order.get('data', {}).get('order_id')}")
```

### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| exchange | str | Yes | Exchange type: NSE_EQ, BSE_EQ, NSE_FO, BSE_FO, MCX_FO |
| token | int | Yes | Instrument token from master (never hardcode) |
| transaction_type | str | Yes | BUY or SELL |
| product | str | Yes | DELIVERY, INTRADAY, MTF |
| variety | str | Yes | RL, RL-MKT, SL, SL-MKT |
| quantity | int | Yes | Number of shares/units |
| price | float | Yes | Limit price; 0 for market orders |
| trigger_price | float | Yes | Trigger for stop-loss orders; 0 otherwise |
| disclosed_quantity | int | No | Partial disclosure for iceberg orders |
| validity | str | Yes | DAY, IOC, or AMO |

### Order Types

**Regular Limit Order (RL)**
```python
# Buy 1 share of Reliance at ₹2400
order = client.place_order(
    exchange=Vc.ExchangeTypes.NSE_EQUITY,
    token=2885,
    transaction_type=Vc.TransactionSides.BUY,
    variety=Vc.VarietyTypes.REGULAR_LIMIT_ORDER,
    quantity=1,
    price=2400.0,
    trigger_price=0.0,
    validity=Vc.ValidityTypes.FULL_DAY,
    product=Vc.ProductTypes.DELIVERY,
)
```

**Market Order (RL-MKT)**
```python
# Buy immediately at market price
order = client.place_order(
    exchange=Vc.ExchangeTypes.NSE_EQUITY,
    token=2885,
    transaction_type=Vc.TransactionSides.BUY,
    variety=Vc.VarietyTypes.REGULAR_MARKET_ORDER,
    quantity=1,
    price=0.0,  # Zero for market orders
    trigger_price=0.0,
    validity=Vc.ValidityTypes.FULL_DAY,
    product=Vc.ProductTypes.INTRADAY,
)
```

**Stop Loss Limit Order (SL)**
```python
# Sell 1 share if price falls to ₹2350, at limit ₹2340
order = client.place_order(
    exchange=Vc.ExchangeTypes.NSE_EQUITY,
    token=2885,
    transaction_type=Vc.TransactionSides.SELL,
    variety=Vc.VarietyTypes.STOP_LIMIT_ORDER,
    quantity=1,
    price=2340.0,         # Limit price
    trigger_price=2350.0, # Trigger price (for SELL: trigger > price)
    validity=Vc.ValidityTypes.FULL_DAY,
    product=Vc.ProductTypes.DELIVERY,
)
```

**Stop Loss Market Order (SL-MKT)**
```python
# Sell immediately at market if price reaches trigger
order = client.place_order(
    exchange=Vc.ExchangeTypes.NSE_EQUITY,
    token=2885,
    transaction_type=Vc.TransactionSides.SELL,
    variety=Vc.VarietyTypes.STOP_MARKET_ORDER,
    quantity=1,
    price=0.0,            # Market (zero)
    trigger_price=2350.0, # Trigger price
    validity=Vc.ValidityTypes.FULL_DAY,
    product=Vc.ProductTypes.DELIVERY,
)
```

### Error Handling
```python
import requests

try:
    order = client.place_order(...)
    if order.get("status") == "error":
        print(f"Order rejected: {order.get('message')}")
    else:
        order_id = order.get("data", {}).get("order_id")
        print(f"Order placed: {order_id}")
except requests.exceptions.HTTPError as e:
    print(f"API error: {e.response.status_code} - {e.response.text}")
```

### Margin Check Before Order
```python
# Calculate required margin before placing order
margin = client.get_order_margin(
    exchange=Vc.ExchangeTypes.NSE_EQUITY,
    token=2885,
    transaction_type=Vc.TransactionSides.BUY,
    product=Vc.ProductTypes.DELIVERY,
    variety=Vc.VarietyTypes.REGULAR_LIMIT_ORDER,
    quantity=10,
    price=2400.0,
    mode=Vc.OrderMarginModes.NEW_ORDER,
)

available_margin = client.funds().get("data", {}).get("equity", {}).get("margin_available")
required = margin.get("data", {}).get("margin")

if required > available_margin:
    print(f"Insufficient margin: need {required}, have {available_margin}")
    # Do not place order
else:
    order = client.place_order(...)
```

---

## Order Management

### Cancel Order
```python
result = client.cancel_order(order_id="ORDER_ID_STRING")
if result.get("status") == "success":
    print("Order cancelled")
else:
    print(f"Cancellation failed: {result.get('message')}")
```

### Modify Order
```python
result = client.modify_order(
    order_id="ORDER_ID_STRING",
    variety=Vc.VarietyTypes.REGULAR_LIMIT_ORDER,
    quantity=2,          # New quantity
    price=2420.0,        # New limit price
    trigger_price=0.0,   # New trigger (if applicable)
    traded_quantity=0,   # Already-filled quantity
    disclosed_quantity=0,
    validity=Vc.ValidityTypes.FULL_DAY,
)
```

### Order History
```python
history = client.order_history(order_id="ORDER_ID_STRING")
# Returns list of status changes for a single order
for event in history.get("data", []):
    print(f"  {event.get('status')} at {event.get('timestamp')}")
```

### All Orders
```python
orders = client.orders()
for o in orders.get("data", []):
    print(f"  {o.get('order_id')}: {o.get('symbol')} "
          f"{o.get('transaction_type')} {o.get('quantity')} @ {o.get('price')}")
```

---

## Portfolio Data

### Positions
```python
positions = client.positions()

# Net positions (carried forward + today)
for pos in positions.get("data", {}).get("net", []):
    qty = pos.get("quantity")
    avg_price = pos.get("average_price")
    ltp = current_ltp(pos.get("token"))
    pnl = (ltp - avg_price) * qty
    print(f"  {pos.get('symbol')}: qty={qty}, avg={avg_price}, P&L={pnl}")

# Day positions (today only)
for pos in positions.get("data", {}).get("day", []):
    print(f"  Today: {pos.get('symbol')} qty={pos.get('quantity')}")
```

### Holdings (Equity Delivery)
```python
holdings = client.holdings()
total_invested = 0

for h in holdings.get("data", []):
    invested = h.get("invested_value")
    current = h.get("current_value")
    pnl = current - invested
    total_invested += invested
    print(f"  {h.get('symbol')}: invested={invested}, current={current}, P&L={pnl}")

print(f"Total invested: {total_invested}")
```

### Funds
```python
funds = client.funds()
equity = funds.get("data", {}).get("equity", {})

print(f"Available margin: {equity.get('margin_available')}")
print(f"Trading power: {equity.get('trading_power')}")
print(f"Margin utilised: {equity.get('margin_utilised')}")
print(f"Withdrawable: {equity.get('withdrawable_balance')}")
```

### Trades
```python
trades = client.trades()

for t in trades.get("trades", []):
    pnl = (t.get("trade_price") - entry_price) * t.get("trade_quantity")
    print(f"  {t.get('trade_no')}: {t.get('symbol')} {t.get('transaction_type')} "
          f"qty={t.get('trade_quantity')} @ {t.get('trade_price')}")
```

---

## Market Data

### Live Quotes
```python
# Instrument format: "{exchange}-{token}"
quotes = client.quotes(
    instruments=["NSE_EQ-2885", "NSE_EQ-26000"],  # Reliance, NIFTY
    mode=Vc.QuoteModes.LTP,
)

for key, q in quotes.get("data", {}).items():
    print(f"{key}: LTP={q.get('last_trade_price')}")
```

**Quote Modes:**
- `LTP` — Last Traded Price only (smallest data)
- `OHLCV` — Open, High, Low, Close, Volume + LTP
- `FULL` — OHLCV + bid/ask depth (5 levels) + open interest + DPR limits

### Historical Candles
```python
import datetime

client = VortexAPI()
master = client.download_master()
token = lookup_token(master, "RELIANCE", "NSE_EQ")

# Daily candles for last 30 days
end = datetime.datetime.now()
start = end - datetime.timedelta(days=30)

candles = client.historical_candles(
    exchange=Vc.ExchangeTypes.NSE_EQUITY,
    token=token,
    to=end,
    start=start,
    resolution=Vc.Resolutions.DAY,
)

# Returns dict with keys: t (timestamp), o (open), h (high), l (low), c (close), v (volume)
for i in range(len(candles["t"])):
    ts = candles["t"][i]
    close = candles["c"][i]
    volume = candles["v"][i]
    print(f"  {ts}: close={close}, volume={volume}")
```

**Resolution Options:**
- Intraday: 1, 2, 3, 4, 5, 10, 15, 30, 45, 60, 120, 180, 240 minutes
- Daily, Weekly, Monthly: 1D, 1W, 1M

**Data Availability:**
- Equities: Years of history
- Intraday candles: ~3 months
- Futures: Current contract only (expired contracts deleted)
- Options: Until expiry only

---

## WebSocket Feed (VortexFeed)

Real-time price updates and order notifications via WebSocket.

### Setup
```python
from vortex_api import VortexFeed
from vortex_api import Constants as Vc

client = VortexAPI()

wire = VortexFeed(access_token=client.access_token)
```

### Callbacks
```python
def on_connect(ws, response):
    """Called when WebSocket is ready. Subscribe here."""
    ws.subscribe("NSE_EQ", 26000, Vc.QuoteModes.LTP)    # NIFTY
    ws.subscribe("NSE_EQ", 2885, Vc.QuoteModes.FULL)    # RELIANCE

def on_price_update(ws, data):
    """Called with price tick data."""
    for tick in data:
        token = tick["token"]
        ltp = tick["last_trade_price"]
        print(f"Token {token}: {ltp}")

def on_order_update(ws, data):
    """Called with order/trade notifications."""
    print(f"Order status: {data.get('order_id')} = {data.get('status')}")

def on_close(ws, code, reason):
    """Called when connection closes."""
    print(f"Closed: {code} - {reason}")

def on_error(ws, code, reason):
    """Called on connection error."""
    print(f"Error: {code} - {reason}")

wire.on_connect = on_connect
wire.on_price_update = on_price_update
wire.on_order_update = on_order_update
wire.on_close = on_close
wire.on_error = on_error
```

### Connection
```python
# Threaded mode — main thread continues after this line
wire.connect(threaded=True)

# Blocking mode — waits forever (use for long-running processes)
wire.connect()
```

### Subscribe / Unsubscribe
```python
# Subscribe to an instrument
wire.subscribe("NSE_EQ", 2885, "ltp")

# Unsubscribe
wire.unsubscribe("NSE_EQ", 2885)
```

### Important Notes
- **Connect immediately after initializing the client** — if you place an order before connecting, you'll miss the order update notification
- **Subscribe in on_connect()** — subscriptions are re-established automatically on reconnect
- **Reconnection is automatic** — SDK handles retries with exponential backoff; do not implement reconnect logic yourself
- **SDK manages reactor** — use `wire.stop()` to cleanly shut down; avoid calling it unless necessary

---

## Backtesting

The platform supports multiple Python backtesting libraries. Results are saved and visualized on the web dashboard.

### Supported Libraries
- **backtesting.py** — Pass stats from `Backtest.run()`
- **vectorbt** — Pass a `vbt.Portfolio` object
- **backtrader** — Pass the strategy from `cerebro.run()[0]`

### Save Backtest Result
```python
from backtesting import Backtest, Strategy

# ... run backtest ...
stats = bt.run()

client.save_backtest_result(
    stats=stats,
    name="SMA Crossover on RELIANCE",
    symbol="RELIANCE",
    description="10/30 SMA crossover, daily bars",
    tags=["sma", "crossover", "daily"],
)
```

**Parameters:**
- `stats` (required) — Result object from backtesting library
- `name` (required) — Display name
- `symbol` — Instrument symbol
- `description` — Strategy notes
- `tags` — Keywords for filtering

**Returns:** `{"status": "success", "backtest_id": "uuid", "url": "..."}`

### Data Preparation for backtesting.py
```python
import datetime
import pandas as pd
from vortex_api import VortexAPI, Constants as Vc

client = VortexAPI()
master = client.download_master()
token = lookup_token(master, "RELIANCE", "NSE_EQ")

# Fetch daily candles
end = datetime.datetime.now()
start = end - datetime.timedelta(days=365)

candles = client.historical_candles(
    exchange=Vc.ExchangeTypes.NSE_EQUITY,
    token=token,
    to=end,
    start=start,
    resolution=Vc.Resolutions.DAY,
)

# Create DataFrame with proper column names (capitalized)
df = pd.DataFrame({
    "Open": candles["o"],
    "High": candles["h"],
    "Low": candles["l"],
    "Close": candles["c"],
    "Volume": candles["v"],
}, index=pd.to_datetime(candles["t"], unit="s"))

df.sort_index(inplace=True)

# Now use df with Backtest
from backtesting import Backtest
from backtesting.lib import crossover
from backtesting.test import SMA

class SmaCross(Strategy):
    fast = 10
    slow = 30

    def init(self):
        self.sma_fast = self.I(SMA, self.data.Close, self.fast)
        self.sma_slow = self.I(SMA, self.data.Close, self.slow)

    def next(self):
        if crossover(self.sma_fast, self.sma_slow):
            if not self.position:
                self.buy()
        elif crossover(self.sma_slow, self.sma_fast):
            if self.position:
                self.position.close()

bt = Backtest(df, SmaCross, cash=100_000, commission=0.001)
stats = bt.run()

client.save_backtest_result(
    stats=stats,
    name="SMA 10/30",
    symbol="RELIANCE",
    tags=["sma"],
)
```

### Parameter Optimization
```python
bt = Backtest(df, SmaCross, cash=100_000, commission=0.001)

stats, heatmap = bt.optimize(
    fast=range(5, 20, 2),
    slow=range(20, 50, 5),
    maximize="Sharpe Ratio",
    return_heatmap=True,
)

client.save_optimization_result(
    stats=stats,
    heatmap=heatmap,
    name="SMA Grid Search",
    symbol="RELIANCE",
    maximize="Sharpe Ratio",
    param_ranges={
        "fast": range(5, 20, 2),
        "slow": range(20, 50, 5),
    },
)
```

---

## Constants Reference

Access all constants via `from vortex_api import Constants as Vc`.

### Exchange Types
| Constant | Value | Exchange |
|----------|-------|----------|
| Vc.ExchangeTypes.NSE_EQUITY | "NSE_EQ" | NSE stocks & indices |
| Vc.ExchangeTypes.BSE_EQUITY | "BSE_EQ" | BSE stocks |
| Vc.ExchangeTypes.NSE_FO | "NSE_FO" | NSE futures & options |
| Vc.ExchangeTypes.BSE_FO | "BSE_FO" | BSE futures & options |
| Vc.ExchangeTypes.MCX | "MCX_FO" | MCX commodity futures |
| Vc.ExchangeTypes.NSE_CURRENCY | "NSE_CD" | NSE currency derivatives |

### Transaction Types
| Constant | Value |
|----------|-------|
| Vc.TransactionSides.BUY | "BUY" |
| Vc.TransactionSides.SELL | "SELL" |

### Order Varieties
| Constant | Value | Description |
|----------|-------|-------------|
| Vc.VarietyTypes.REGULAR_LIMIT_ORDER | "RL" | Limit order |
| Vc.VarietyTypes.REGULAR_MARKET_ORDER | "RL-MKT" | Market order |
| Vc.VarietyTypes.STOP_LIMIT_ORDER | "SL" | Stop loss + limit |
| Vc.VarietyTypes.STOP_MARKET_ORDER | "SL-MKT" | Stop loss + market |

### Product Types
| Constant | Value | Description |
|----------|-------|-------------|
| Vc.ProductTypes.DELIVERY | "DELIVERY" | CNC — held in demat |
| Vc.ProductTypes.INTRADAY | "INTRADAY" | MIS — squared off at day end |
| Vc.ProductTypes.MTF | "MTF" | Margin trading (NSE_EQ only) |

### Validity Types
| Constant | Value | Description |
|----------|-------|-------------|
| Vc.ValidityTypes.FULL_DAY | "DAY" | Valid until end of trading day |
| Vc.ValidityTypes.IMMEDIATE_OR_CANCEL | "IOC" | Immediate execution or cancel |
| Vc.ValidityTypes.AFTER_MARKET | "AMO" | After-market order |

### Quote Modes
| Constant | Value | Data |
|----------|-------|------|
| Vc.QuoteModes.LTP | "ltp" | Last traded price only |
| Vc.QuoteModes.OHLCV | "ohlcv" | OHLCV + LTP |
| Vc.QuoteModes.FULL | "full" | OHLCV + depth + OI + DPR |

### Resolutions (Historical Candles)
| Constant | Value | Period |
|----------|-------|--------|
| Vc.Resolutions.MIN_1 | "1" | 1 minute |
| Vc.Resolutions.MIN_5 | "5" | 5 minutes |
| Vc.Resolutions.MIN_15 | "15" | 15 minutes |
| Vc.Resolutions.MIN_30 | "30" | 30 minutes |
| Vc.Resolutions.MIN_60 | "60" | 1 hour |
| Vc.Resolutions.DAY | "1D" | Daily |
| Vc.Resolutions.WEEK | "1W" | Weekly |
| Vc.Resolutions.MONTH | "1M" | Monthly |

---

## Container Platform Rules

When deploying to Rupeezy's container platform, follow these constraints:

### Networking
- Only three hosts are reachable: `vortex-api.rupeezy.in`, `wire.rupeezy.in`, `static.rupeezy.in`
- Do not make external API calls (no requests to third-party services)
- Use only bundled Python packages

### Logging & Debugging
- Do not write logs to files — logs are not accessible to users
- Use `print()` or the client's built-in logger; view logs on the platform dashboard
- Enable SDK debug logging with `client = VortexAPI(enable_logging=True)` if requested

### Scheduling
- Do not implement scheduling logic in code
- Rupeezy platform manages start/stop times via cron expressions
- Each container invocation runs the strategy once from start to finish
- Use tools `create_schedule`, `list_schedules`, `update_schedule` to set up automated runs

### Python Version
- Use Python 3.12, 3.13, or 3.14
- Containers run on `python:{version}-slim` image (minimal dependencies)

### Requirements File
Keep `requirements.txt` minimal. Example:
```
vortex-api>=1.0.0
pandas>=2.0.0
numpy>=1.24.0
```

---

## Common Patterns

### Full Order Lifecycle
```python
from vortex_api import VortexAPI, VortexFeed
from vortex_api import Constants as Vc
import time

client = VortexAPI()

# Download master and look up token
master = client.download_master()
token = lookup_token(master, "RELIANCE", "NSE_EQ")

# Connect feed BEFORE placing order (don't miss update)
wire = VortexFeed(access_token=client.access_token)

orders_placed = {}

def on_order_update(ws, data):
    order_id = data.get("order_id")
    status = data.get("status")
    print(f"Order {order_id}: {status}")
    orders_placed[order_id] = status

wire.on_order_update = on_order_update
wire.connect(threaded=True)

time.sleep(1)  # Let connection stabilize

# Place order
order = client.place_order(
    exchange=Vc.ExchangeTypes.NSE_EQUITY,
    token=token,
    transaction_type=Vc.TransactionSides.BUY,
    product=Vc.ProductTypes.DELIVERY,
    variety=Vc.VarietyTypes.REGULAR_LIMIT_ORDER,
    quantity=1,
    price=2400.0,
    trigger_price=0.0,
    validity=Vc.ValidityTypes.FULL_DAY,
)

order_id = order.get("data", {}).get("order_id")
print(f"Placed: {order_id}")

# Wait for confirmation
timeout = 30
start = time.time()
while time.time() - start < timeout:
    if order_id in orders_placed and orders_placed[order_id] == "CONFIRMED":
        print("Order confirmed!")
        break
    time.sleep(0.5)

wire.close()
```

### Position Monitoring
```python
import time

client = VortexAPI()
wire = VortexFeed(access_token=client.access_token)

positions_data = {}

def on_price_update(ws, data):
    for tick in data:
        token = tick["token"]
        ltp = tick["last_trade_price"]
        positions_data[token] = ltp

def on_connect(ws, response):
    # Subscribe to monitored instruments
    ws.subscribe("NSE_EQ", 2885, "ltp")
    ws.subscribe("NSE_EQ", 26000, "ltp")

wire.on_connect = on_connect
wire.on_price_update = on_price_update
wire.connect(threaded=True)

# Monitor positions for 60 seconds
for i in range(60):
    positions = client.positions()
    for pos in positions.get("data", {}).get("net", []):
        token = pos.get("token")
        qty = pos.get("quantity")
        avg = pos.get("average_price")

        if token in positions_data:
            ltp = positions_data[token]
            pnl = (ltp - avg) * qty
            print(f"  {pos.get('symbol')}: qty={qty}, avg={avg}, ltp={ltp}, P&L={pnl}")

    time.sleep(1)

wire.close()
```

### Risk Management
```python
def can_trade(client, required_capital):
    """Check if sufficient margin available before placing order."""
    funds = client.funds()
    available = funds.get("data", {}).get("equity", {}).get("margin_available", 0)
    return available >= required_capital

# Usage
if can_trade(client, 50000):
    order = client.place_order(...)
else:
    print("Insufficient margin")
```

---

## Error Handling

### Order Rejection
```python
order = client.place_order(...)

if order.get("status") == "error":
    error_msg = order.get("message")
    print(f"Order rejected: {error_msg}")
    # Handle rejection: invalid quantity, insufficient margin, etc.
elif order.get("status") == "success":
    order_id = order.get("data", {}).get("order_id")
    print(f"Order accepted: {order_id}")
```

### API Errors
```python
import requests

try:
    result = client.place_order(...)
except requests.exceptions.HTTPError as e:
    status = e.response.status_code
    text = e.response.text
    print(f"HTTP {status}: {text}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## Summary

This reference covers the complete Vortex SDK workflow: initialization, authentication, master data lookup, order placement, portfolio monitoring, market data, backtesting, and deployment. Follow the patterns here to build robust algorithmic trading strategies on Rupeezy's platform.

**Key takeaways:**
- Always look up tokens by symbol — never hardcode
- Connect WebSocket immediately after client initialization
- Use container platform for managed deployment; self-hosted for custom control
- Backtest strategies before going live using save_backtest_result()
- Handle errors gracefully; verify margin before placing orders
