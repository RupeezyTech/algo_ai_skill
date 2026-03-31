# Broker Adapter Template

This template guides community contributors in adding support for a new broker. Follow the sections below and replace all `[PLACEHOLDER]` text with broker-specific information.

## 1. Broker Identification

- **Broker Name:** [PLACEHOLDER: e.g., "XYZ Securities Ltd"]
- **Website:** [PLACEHOLDER: https://example.com]
- **Python SDK Name:** [PLACEHOLDER: e.g., "xyz-broker-sdk"]
- **SDK Version:** [PLACEHOLDER: e.g., "2.1.0"]
- **Support for Indian Markets:** NSE, BSE, MCX (specify which)
- **Regulation:** [PLACEHOLDER: SEBI registration number]

## 2. Installation

Provide exact pip installation command:

```bash
pip install [PLACEHOLDER: broker-sdk-name]
```

Pin the version in requirements.txt:

```
[PLACEHOLDER: broker-sdk-name]==X.Y.Z
```

List any system dependencies (e.g., OpenSSL, Redis):

- [PLACEHOLDER: system dependency 1]
- [PLACEHOLDER: system dependency 2]

## 3. Authentication Pattern

**All Indian brokers are mandatorily required to use OAuth 2.0 for authentication.**
The only exception is container-based deployment (like Rupeezy's platform) where
credentials are injected by the platform.

For self-hosted strategies, the authentication flow will always be:
1. User registers an application on the broker's developer portal → gets client_id / app_id and API secret
2. User is redirected to the broker's login page for authorization
3. Broker redirects back to a callback URL with an authorization code
4. Your code exchanges the auth code for an access token
5. Access token is used for all subsequent API calls (usually valid for one trading day)

**Document this broker's specific OAuth 2.0 flow:**

- **Developer Portal URL:** [PLACEHOLDER: URL where user creates an app]
- **Authorization URL:** [PLACEHOLDER: URL user is redirected to for login]
- **Required Credentials:** [PLACEHOLDER: application_id, api_secret, etc.]
- **Token Validity:** [PLACEHOLDER: e.g., "valid until midnight IST" or "24 hours"]
- **Refresh Token Support:** [PLACEHOLDER: yes/no, and how to refresh]

**Example OAuth flow:**

```python
from [broker_module] import Client

# Step 1: Initialize with app credentials
client = Client(
    api_key="[PLACEHOLDER: YOUR_API_KEY]",
    application_id="[PLACEHOLDER: YOUR_APP_ID]"
)

# Step 2: Generate login URL (user visits this in browser)
login_url = client.get_login_url()
# Returns: https://[broker].com/authorize?app_id=...

# Step 3: User logs in, broker redirects to your callback with auth_code
# Step 4: Exchange auth code for access token
client.exchange_token(auth_code="[received_from_callback]")
# client.access_token is now set — ready to use
```

**Environment variables to set:**

```
BROKER_API_KEY=[your_key]
BROKER_APPLICATION_ID=[your_app_id]
BROKER_ACCESS_TOKEN=[your_token]
```

## 4. Instrument Master / Symbol Lookup

Describe how to fetch available instruments and look up tokens/symbols:

**Method to download master data:**

```python
master = client.download_master()
# Returns: DataFrame with columns [symbol, exchange, token, lot_size, tick_size, ...]
```

**Symbol lookup example:**

```python
nse_reliance = master[
    (master['symbol'] == 'RELIANCE') &
    (master['exchange'] == 'NSE')
]
token = nse_reliance['token'].iloc[0]
```

**Data format:**
- Columns provided: [PLACEHOLDER: list columns like symbol, exchange, token, lot_size]
- Update frequency: [PLACEHOLDER: daily/weekly/on-demand]
- Update mechanism: [PLACEHOLDER: API call / file download / WebSocket]

## 5. Order Placement

Map all order types and their broker-specific parameters:

**Order types supported:**

| Generic Type | Broker Code | Parameters | Example |
|---|---|---|---|
| BUY_MARKET | [PLACEHOLDER] | [PLACEHOLDER] | [PLACEHOLDER] |
| SELL_MARKET | [PLACEHOLDER] | [PLACEHOLDER] | [PLACEHOLDER] |
| BUY_LIMIT | [PLACEHOLDER] | [PLACEHOLDER] | [PLACEHOLDER] |
| SELL_LIMIT | [PLACEHOLDER] | [PLACEHOLDER] | [PLACEHOLDER] |
| BUY_STOPLOSS | [PLACEHOLDER] | [PLACEHOLDER] | [PLACEHOLDER] |
| SELL_STOPLOSS | [PLACEHOLDER] | [PLACEHOLDER] | [PLACEHOLDER] |
| BUY_STOPLOSS_LIMIT | [PLACEHOLDER] | [PLACEHOLDER] | [PLACEHOLDER] |
| SELL_STOPLOSS_LIMIT | [PLACEHOLDER] | [PLACEHOLDER] | [PLACEHOLDER] |

**Place order API:**

```python
order = client.place_order(
    symbol="RELIANCE",
    exchange="NSE",
    transaction_type="BUY",
    quantity=1,
    order_type="LIMIT",
    price=2500.50,
    product="DELIVERY",  # or INTRADAY, MTF, BTST
    trigger_price=None   # for stop-loss orders
)
# Returns: order_id
```

**Quantity validation:** Lot sizes must be enforced. Round quantity to nearest lot before placing.

## 6. Order Management

Describe APIs to view, modify, and cancel orders:

**Get order status:**

```python
order_status = client.get_order(order_id)
# Returns: {order_id, status, filled_qty, pending_qty, price, executed_price, ...}
```

**Valid status values:** [PLACEHOLDER: e.g., PENDING, SUBMITTED, FILLED, PARTIALLY_FILLED, CANCELLED, REJECTED]

**Modify order:**

```python
client.modify_order(order_id, quantity=10, price=2500.0)
```

**Cancel order:**

```python
client.cancel_order(order_id)
```

**Get order history (today):**

```python
orders = client.get_orders()
# Returns: list of order objects
```

## 7. Positions, Holdings, and Funds

Retrieve account state and equity exposure:

**Get positions (open P&L):**

```python
positions = client.get_positions()
# Returns: [
#   {symbol, quantity, avg_price, last_price, pnl, pnl_percent, ...}
# ]
```

**Get holdings (equity balance):**

```python
holdings = client.get_holdings()
# Returns: [
#   {symbol, quantity, avg_price, last_price, value, pnl, ...}
# ]
```

**Get available margin and funds:**

```python
funds = client.get_funds()
# Returns: {
#   available_balance, utilized_balance, margin_available,
#   collateral, margin_multiplier, ...
# }
```

## 8. WebSocket / Real-Time Feed

Describe how to subscribe to live price updates:

**Connection setup:**

```python
from [broker_module] import WebSocket

ws = WebSocket(
    api_key="[PLACEHOLDER: YOUR_API_KEY]",
    on_message=handle_tick
)

def handle_tick(data):
    # data format: {symbol, ltp, bid, ask, volume, timestamp, ...}
    print(f"{data['symbol']}: {data['ltp']}")

ws.subscribe(symbols=['RELIANCE', 'INFY'], mode='ltp')  # or 'quote', 'depth'
ws.connect()
```

**Data format:**
- Fields returned: [PLACEHOLDER: ltp, bid, ask, volume, oi, etc.]
- Subscription modes: [PLACEHOLDER: ltp / quote / depth]
- Disconnection handling: [PLACEHOLDER: auto-reconnect / manual]

## 9. Historical Data

Describe how to fetch OHLCV candles:

**API to get historical data:**

```python
candles = client.get_historical_data(
    symbol="RELIANCE",
    exchange="NSE",
    interval="1minute",  # or "5minute", "15minute", "1hour", "1day"
    from_date="2026-01-01",
    to_date="2026-03-31"
)
# Returns: DataFrame with columns [timestamp, open, high, low, close, volume]
```

**Supported intervals:** [PLACEHOLDER: 1min, 5min, 15min, 30min, 1hour, 1day, etc.]

**Data limitations:**
- Maximum lookback period: [PLACEHOLDER: days/months]
- Minimum candle size: [PLACEHOLDER: e.g., 1 minute]
- Data accuracy: [PLACEHOLDER: e.g., adjusted for splits/dividends]

## 10. Constants Mapping Table

Map generic algo-trading types to broker-specific codes:

```python
# Exchange mapping
EXCHANGE_MAP = {
    "NSE_EQ": "[PLACEHOLDER: broker code for NSE equity]",
    "NSE_FO": "[PLACEHOLDER: broker code for NSE derivatives]",
    "BSE_EQ": "[PLACEHOLDER: broker code for BSE equity]",
    "MCX_FO": "[PLACEHOLDER: broker code for MCX futures]",
}

# Product type mapping
PRODUCT_MAP = {
    "DELIVERY": "[PLACEHOLDER: broker code]",
    "INTRADAY": "[PLACEHOLDER: broker code]",
    "MTF": "[PLACEHOLDER: broker code]",
    "BTST": "[PLACEHOLDER: broker code]",
}

# Transaction type mapping
TRANSACTION_MAP = {
    "BUY": "[PLACEHOLDER: broker code]",
    "SELL": "[PLACEHOLDER: broker code]",
}

# Order type mapping
ORDER_TYPE_MAP = {
    "MARKET": "[PLACEHOLDER: broker code]",
    "LIMIT": "[PLACEHOLDER: broker code]",
    "STOPLOSS": "[PLACEHOLDER: broker code]",
    "STOPLOSS_LIMIT": "[PLACEHOLDER: broker code]",
}

# Order status mapping
STATUS_MAP = {
    "[PLACEHOLDER: broker status 1]": "PENDING",
    "[PLACEHOLDER: broker status 2]": "SUBMITTED",
    "[PLACEHOLDER: broker status 3]": "FILLED",
    "[PLACEHOLDER: broker status 4]": "PARTIALLY_FILLED",
    "[PLACEHOLDER: broker status 5]": "CANCELLED",
    "[PLACEHOLDER: broker status 6]": "REJECTED",
}
```

## 11. Deployment Considerations

**Production readiness checklist:**

- [ ] Rate limits: [PLACEHOLDER: e.g., "10 requests per second"]
- [ ] Request/response timeout: [PLACEHOLDER: e.g., "30 seconds"]
- [ ] Order placement latency: [PLACEHOLDER: e.g., "< 500ms typical"]
- [ ] API reliability / SLA: [PLACEHOLDER: e.g., "99.5% uptime"]
- [ ] Market hours availability: [PLACEHOLDER: e.g., "9:15 AM - 3:30 PM IST"]
- [ ] Production API endpoint: [PLACEHOLDER: https://api.broker.com]
- [ ] Sandbox / paper trading endpoint: [PLACEHOLDER: https://sandbox.broker.com]

**Connection pooling and retries:**

```python
# Recommended retry logic for rate-limited APIs
max_retries = 3
backoff_factor = 2  # exponential backoff
```

**Logging best practices:**

- Log all order placements with order_id and reason
- Log cancellations and modifications with old/new values
- Log WebSocket connection state changes
- Use structured logging with timestamps

## 12. Known Limitations

Document any gaps or gotchas with this broker:

- [PLACEHOLDER: Limitation 1]
- [PLACEHOLDER: Limitation 2]
- [PLACEHOLDER: Limitation 3]

**Workarounds:**

- [PLACEHOLDER: Workaround for limitation 1]
- [PLACEHOLDER: Workaround for limitation 2]

**Unsupported features:**

- [PLACEHOLDER: Feature not supported]
- [PLACEHOLDER: Feature not supported]

---

**Contributor Notes:**

Complete all sections above. Add code examples that are copy-paste ready. Test your adapter against the validation script (`validate_strategy.py`) before submitting.
