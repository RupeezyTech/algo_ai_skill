# Rupeezy Vortex Broker Reference -- Advanced

Depth material split out of `rupeezy-vortex.md` to keep the core reference small enough
to load cheaply. Read the core file first; come here for backtest data prep, end-to-end
lifecycle examples, and broker-specific error handling.

Core reference: `references/brokers/rupeezy-vortex.md`

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

## Common Patterns

### Full Order Lifecycle

Use the `OrderTracker` class from `references/code-quality.md` (or the scaffolder-generated `order_tracker.py`). It coalesces postbacks, refreshes from `client.orders()` + `client.trades()`, and fires an `on_terminal(order_id, status)` callback for every terminal transition. Strategy code never parses `msg["data"]` and never polls the REST APIs on a timer.

```python
from vortex_api import VortexAPI, VortexFeed
from vortex_api import Constants as Vc
from order_tracker import OrderTracker
import time

client  = VortexAPI()
tracker = OrderTracker(client)
tracker.initialize()                # seed cache; historical fills don't fire on_terminal

def on_order_terminal(order_id, status):
    """Fires on the OrderTracker worker thread when an order reaches terminal."""
    order = tracker.order(order_id)
    if status == "COMPLETED":
        print(f"FILL {order_id} qty={order['traded_quantity']} avg={tracker.avg_fill_price(order_id):.2f}")
    elif status == "REJECTED":
        print(f"REJECTED {order_id}: {order.get('status_message')}")
    elif status == "CANCELLED":
        print(f"CANCELLED {order_id}")

tracker.on_terminal = on_order_terminal

wire = VortexFeed(access_token=client.access_token)
wire.on_order_update = tracker.on_update   # legacy SDK property name; receives all 5 types
wire.connect(threaded=True)
time.sleep(1)  # let the connection stabilise

# Place orders without blocking — the callback handles outcomes.
order = client.place_order(
    ticker="NSE:RELIANCE",
    transaction_type=Vc.TransactionSides.BUY,
    product=Vc.ProductTypes.DELIVERY,
    variety=Vc.VarietyTypes.REGULAR_LIMIT_ORDER,
    quantity=1,
    price=2400.0,
    trigger_price=0.0,
    validity=Vc.ValidityTypes.FULL_DAY,
)
order_id = order["data"]["order_id"]

# strategy continues to run; on_order_terminal fires whenever the order completes.
# If you need to kill this order before placing a replacement:
final = tracker.cancel_and_wait(order_id, timeout=10)
if final != "CANCELLED":
    print(f"unexpected final state: {final} — do not place a replacement blindly")

wire.close()
```

`tracker.wait(order_id, timeout)` exists for tests and one-shot scripts. **Do not use it inside a live strategy main loop.** The `timeout` argument is required — pass `float("inf")` if you genuinely want to block forever.

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

The rejection-reason field name **varies across the three surfaces** that can report a rejection for the same `order_id`:

| Surface | Field |
|---|---|
| Postback envelope (`wire.on_order_update` → `msg["data"]`) | `status_message` |
| REST orderbook row (`client.orders()`) | `error_reason` |
| `place_order()` synchronous response | `message` |

Always use the chained fallback (or `OrderTracker.rejection_reason(order_id)`, which does this for you):

```python
def rejection_reason(row):
    return row.get("status_message") or row.get("error_reason") or row.get("message")

order = client.place_order(...)

if order.get("status") == "error":
    print(f"Order rejected: {rejection_reason(order)}")
elif order.get("status") == "success":
    order_id = order["data"]["order_id"]
    print(f"Order accepted: {order_id}")
```

For rejections that arrive later (after `place_order` returned success but the RMS rejected during execution), the strategy's `on_order_terminal(order_id, status)` callback should also log `tracker.rejection_reason(order_id)`. The reference scaffolder generates this in `strategy.py`.

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
