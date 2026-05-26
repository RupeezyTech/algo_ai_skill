# Code Quality and Testing for Trading Strategies

This reference covers code organization, testing practices, and quality standards for building maintainable trading strategies. Follow these patterns to ensure your code is reliable, testable, and production-ready.

## 1. Project Structure: Standard Module Layout

Organize trading strategies into distinct, testable modules. This separation allows testing signal logic independently from order execution, and makes the codebase easier to modify and debug.

### Recommended Directory Layout

```
my_strategy/
├── main.py                 # Entry point, orchestrates pipeline
├── strategy/
│   ├── __init__.py
│   └── signal_generator.py # Buy/sell signal logic
├── execution/
│   ├── __init__.py
│   └── order_executor.py   # Place orders, track fills
├── risk_manager/
│   ├── __init__.py
│   └── position_limiter.py # Enforce position size limits
├── guardrails/
│   ├── __init__.py
│   └── circuit_breaker.py  # Halt trading on anomalies
├── config.py               # Configuration, parameters
├── logger.py               # Logging setup
├── requirements.txt
└── tests/
    ├── test_signal_generator.py
    ├── test_order_executor.py
    ├── test_position_limiter.py
    └── conftest.py         # Shared pytest fixtures
```

### Module Responsibilities

```python
# main.py: Orchestrates the entire strategy pipeline

import logging
from strategy.signal_generator import SignalGenerator
from execution.order_executor import OrderExecutor
from risk_manager.position_limiter import PositionLimiter
from guardrails.circuit_breaker import CircuitBreaker
import vortex

def main():
    # Initialize components
    client = vortex.Client()
    signal_gen = SignalGenerator(client)
    executor = OrderExecutor(client)
    risk_manager = PositionLimiter(max_position_size=1000)
    breaker = CircuitBreaker(max_daily_loss=-50000)

    logging.info("Strategy starting")

    while True:
        try:
            # Generate signal
            signal = signal_gen.analyze_market()

            # Check risk constraints
            if not risk_manager.can_trade(signal):
                logging.warning("Signal rejected by risk manager")
                continue

            # Execute if guardrails permit
            if breaker.is_safe():
                executor.execute_signal(signal)
            else:
                logging.critical("Circuit breaker tripped. Halting.")
                break

            time.sleep(1)

        except Exception as e:
            logging.error(f"Error in main loop: {e}", exc_info=True)
```

## 2. Logging Best Practices

Never use `print()`. Use the `logging` module with appropriate log levels. Implement structured trade journals in JSON format for machine-readable records and easier post-trade analysis.

### Logging Setup

```python
# logger.py: Centralized logging configuration

import logging
import json
from datetime import datetime

def setup_logging(log_file: str = "strategy.log"):
    """Configure logging with both file and console handlers."""

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Console handler: INFO and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    console_handler.setFormatter(console_format)

    # File handler: DEBUG and above (detailed logs)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    file_handler.setFormatter(file_format)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

def log_trade(
    symbol: str,
    side: str,
    quantity: int,
    price: float,
    reason: str,
    order_id: str
) -> None:
    """Log trade event in structured JSON format."""
    trade_record = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": "trade_executed",
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "price": price,
        "reason": reason,
        "order_id": order_id,
    }

    logger = logging.getLogger()
    logger.info(json.dumps(trade_record))
```

### Log Levels: When to Use Each

```python
import logging

logger = logging.getLogger(__name__)

# DEBUG: Low-level diagnostic info. Use sparingly in production.
logger.debug("Order update received: order_id=123, filled=50/100")

# INFO: High-level trade events and strategy milestones.
logger.info("BUY signal: RELIANCE at 2500.00 (reason: MA crossover)")

# WARNING: Risk alerts or recoverable errors that may need attention.
logger.warning("Position size {qty} exceeds limit {max_qty}")

# ERROR: Failures that prevent a single trade but don't halt the strategy.
logger.error("Failed to fetch quotes for symbol INVALID: not found")

# CRITICAL: System-level failures that halt the strategy.
logger.critical("Circuit breaker triggered. Losses exceed limit. Halting.")
```

### Structured Trade Journal

```python
import json
from dataclasses import asdict, dataclass

@dataclass
class TradeEvent:
    """Structured trade event for JSON logging."""
    timestamp: str
    order_id: str
    symbol: str
    side: str  # BUY or SELL
    quantity: int
    price: float
    reason: str  # Why this trade was executed
    status: str  # PENDING, FILLED, REJECTED
    filled_quantity: int = 0
    average_fill_price: float = 0.0
    pnl: float = 0.0

def log_trade_journal(
    trade: TradeEvent,
    journal_file: str = "trade_journal.json"
) -> None:
    """Append trade event to JSON trade journal."""
    with open(journal_file, "a") as f:
        f.write(json.dumps(asdict(trade)) + "\n")

# Usage
event = TradeEvent(
    timestamp=datetime.utcnow().isoformat(),
    order_id="order-123",
    symbol="RELIANCE",
    side="BUY",
    quantity=100,
    price=2500.00,
    reason="RSI oversold, buy signal",
    status="FILLED",
    filled_quantity=100,
    average_fill_price=2500.00,
    pnl=0.0
)
log_trade_journal(event)
```

## 3. Testing Patterns: Unit, Integration, and Property-Based Tests

### Test Fixtures for Market Data

```python
# tests/conftest.py: Shared pytest fixtures

import pytest
from unittest.mock import Mock
import pandas as pd

@pytest.fixture
def sample_ohlcv_data():
    """Fixture providing sample OHLCV data."""
    return pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=10, freq="1h"),
        "open": [100, 101, 99, 102, 103, 101, 100, 104, 105, 103],
        "high": [102, 103, 101, 104, 105, 103, 102, 106, 107, 105],
        "low": [99, 100, 98, 101, 102, 100, 99, 103, 104, 102],
        "close": [101, 100, 100, 103, 104, 102, 101, 105, 106, 104],
        "volume": [1000, 1100, 900, 1200, 1300, 1100, 950, 1400, 1500, 1250],
    })

@pytest.fixture
def mock_broker_client():
    """Fixture providing a mocked broker client."""
    client = Mock()
    client.get_quotes.return_value = {
        "NSE:RELIANCE": {
            "ltp": 2500.00,
            "high": 2510.00,
            "low": 2490.00,
            "volume": 5000000,
        }
    }
    client.place_order.return_value = {"order_id": "test-order-123"}
    return client

@pytest.fixture
def mock_broker_position():
    """Fixture providing mocked broker position data."""
    return {
        "net": [
            {
                "symbol": "RELIANCE",
                "quantity": 0,
                "average_price": 2500.00,
                "pnl": 0,
            }
        ]
    }
```

### Unit Tests: Test Signal Generation in Isolation

```python
# tests/test_signal_generator.py

import pytest
from strategy.signal_generator import SignalGenerator, Signal

class TestSignalGenerator:
    def test_bullish_crossover_generates_buy_signal(
        self,
        sample_ohlcv_data,
        mock_broker_client
    ):
        """Test that moving average crossover generates BUY signal."""
        gen = SignalGenerator(mock_broker_client)

        # Compute moving averages on fixture data
        signal = gen.check_ma_crossover(sample_ohlcv_data)

        assert signal is not None
        assert signal.side == "BUY"

    def test_rsi_oversold_generates_buy_signal(
        self,
        sample_ohlcv_data,
        mock_broker_client
    ):
        """Test RSI oversold condition generates buy signal."""
        gen = SignalGenerator(mock_broker_client)

        signal = gen.check_rsi_oversold(sample_ohlcv_data)

        if sample_ohlcv_data["close"].iloc[-1] < 101:  # Price condition
            assert signal.side == "BUY"
        else:
            assert signal is None

    def test_no_signal_when_conditions_not_met(
        self,
        sample_ohlcv_data,
        mock_broker_client
    ):
        """Test that no signal is generated when conditions aren't met."""
        gen = SignalGenerator(mock_broker_client)
        flat_data = sample_ohlcv_data.copy()
        flat_data["close"] = 100.0  # Flat prices

        signal = gen.analyze_market(flat_data)

        assert signal is None
```

### Integration Tests: Full Pipeline

```python
# tests/test_order_executor.py

import pytest
from execution.order_executor import OrderExecutor
from strategy.signal_generator import Signal

class TestOrderExecutor:
    def test_executor_places_order_on_signal(
        self,
        mock_broker_client,
        mock_broker_position
    ):
        """Test that executor places order when signal arrives."""
        executor = OrderExecutor(mock_broker_client)
        mock_broker_client.get_positions.return_value = mock_broker_position

        signal = Signal(
            side="BUY",
            symbol="RELIANCE",
            quantity=100,
            reason="MA crossover"
        )

        executor.execute_signal(signal)

        # Verify order was placed
        mock_broker_client.place_order.assert_called_once()
        call_args = mock_broker_client.place_order.call_args
        assert call_args.kwargs["symbol"] == "RELIANCE"
        assert call_args.kwargs["quantity"] == 100

    def test_executor_respects_position_limits(
        self,
        mock_broker_client,
        mock_broker_position
    ):
        """Test that executor doesn't exceed position size limits."""
        executor = OrderExecutor(mock_broker_client, max_position=100)
        mock_broker_position["net"][0]["quantity"] = 100
        mock_broker_client.get_positions.return_value = mock_broker_position

        signal = Signal(
            side="BUY",
            symbol="RELIANCE",
            quantity=50,
            reason="test"
        )

        # Should reject because position is at limit
        executor.execute_signal(signal)

        mock_broker_client.place_order.assert_not_called()
```

### Property-Based Tests with Hypothesis

```python
# tests/test_signal_properties.py

import pytest
from hypothesis import given, strategies as st
from strategy.signal_generator import SignalGenerator

class TestSignalProperties:
    @given(
        price=st.floats(min_value=100, max_value=1000),
        volume=st.integers(min_value=1000, max_value=1000000)
    )
    def test_signal_quantity_never_negative(
        self,
        price,
        volume,
        mock_broker_client
    ):
        """Property: Generated signal quantity must always be positive."""
        gen = SignalGenerator(mock_broker_client)

        signal = gen.calculate_position_size(price, volume)

        assert signal.quantity > 0, "Quantity must be positive"

    @given(
        prices=st.lists(
            st.floats(min_value=100, max_value=1000),
            min_size=5,
            max_size=100
        )
    )
    def test_moving_average_within_price_range(
        self,
        prices,
        mock_broker_client
    ):
        """Property: MA should never exceed price range."""
        gen = SignalGenerator(mock_broker_client)

        ma = gen.calculate_moving_average(prices)

        assert min(prices) <= ma <= max(prices), \
            "MA must be within price range"
```

## 4. Configuration Management

Use environment variables for secrets and a dataclass for strategy parameters. This allows changing strategy behavior without code changes.

```python
# config.py: Configuration and parameters

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class StrategyConfig:
    """Strategy parameters and settings."""

    # API credentials (from environment)
    api_key: str
    api_secret: str

    # Strategy parameters
    max_position_size: int = 1000
    max_daily_loss: float = -50000.0
    rsi_oversold_threshold: int = 30
    ma_fast_period: int = 10
    ma_slow_period: int = 50

    # Execution settings
    order_timeout_seconds: int = 30
    position_reconcile_interval: int = 300

    @staticmethod
    def from_env() -> "StrategyConfig":
        """Load config from environment variables."""
        return StrategyConfig(
            api_key=os.getenv("VORTEX_API_KEY", ""),
            api_secret=os.getenv("VORTEX_API_SECRET", ""),
            max_position_size=int(
                os.getenv("MAX_POSITION_SIZE", "1000")
            ),
            max_daily_loss=float(
                os.getenv("MAX_DAILY_LOSS", "-50000")
            ),
            rsi_oversold_threshold=int(
                os.getenv("RSI_OVERSOLD", "30")
            ),
            ma_fast_period=int(
                os.getenv("MA_FAST", "10")
            ),
            ma_slow_period=int(
                os.getenv("MA_SLOW", "50")
            ),
        )

# Usage
config = StrategyConfig.from_env()

print(f"Position size limit: {config.max_position_size}")
print(f"Daily loss limit: {config.max_daily_loss}")
```

### Environment File Example

```bash
# .env file (never commit to version control)

VORTEX_API_KEY=your_api_key_here
VORTEX_API_SECRET=your_api_secret_here
MAX_POSITION_SIZE=1000
MAX_DAILY_LOSS=-50000
RSI_OVERSOLD=30
MA_FAST=10
MA_SLOW=50
```

Load with:

```python
from dotenv import load_dotenv
load_dotenv()

config = StrategyConfig.from_env()
```

## 5. Type Hints: Always Use Type Annotations

Type hints make code self-documenting and catch errors early. Use them for all function signatures.

```python
from typing import Optional, List, Dict, Union
import pandas as pd
from dataclasses import dataclass

@dataclass
class Signal:
    """Trade signal with type hints."""
    side: str  # "BUY" or "SELL"
    symbol: str
    quantity: int
    reason: str

def analyze_market(
    symbol: str,
    ohlcv_data: pd.DataFrame
) -> Optional[Signal]:
    """
    Analyze market and generate signal.

    Args:
        symbol: Trading symbol (e.g., "RELIANCE")
        ohlcv_data: OHLCV dataframe with columns
                    [open, high, low, close, volume]

    Returns:
        Signal object if conditions met, None otherwise
    """
    if ohlcv_data.empty:
        return None

    close_prices: List[float] = ohlcv_data["close"].tolist()
    ma_fast: float = sum(close_prices[-10:]) / 10
    ma_slow: float = sum(close_prices[-50:]) / 50

    if ma_fast > ma_slow:
        return Signal(
            side="BUY",
            symbol=symbol,
            quantity=100,
            reason="MA crossover"
        )

    return None

def get_positions(
    client
) -> Dict[str, int]:
    """
    Fetch current positions from broker.

    Returns:
        Dict mapping symbol to quantity
    """
    positions: Dict[str, int] = {}

    try:
        response: Dict = client.get_positions()
        for pos in response.get("net", []):
            symbol: str = pos["symbol"]
            quantity: int = pos["quantity"]
            positions[symbol] = quantity
    except Exception as e:
        logging.error(f"Failed to fetch positions: {e}")

    return positions
```

## 6. Docstrings: Explain the "Why"

Write docstrings that explain intent and trade-offs, not just what the code does.

```python
def calculate_position_size(
    capital: float,
    risk_percent: float = 2.0
) -> int:
    """
    Calculate position size based on risk budget.

    This function uses fixed-fractional position sizing:
    position_size = (capital * risk_percent) / price

    This approach prevents catastrophic losses if a trade
    goes against you. By risking only 2% of capital per trade,
    you can withstand 50 consecutive losses and still have capital
    remaining for recovery.

    Args:
        capital: Total account capital in rupees
        risk_percent: Percentage of capital to risk per trade (default 2%)

    Returns:
        Position size in shares

    Example:
        >>> calculate_position_size(capital=100000, risk_percent=2.0)
        2000  # Risk 2000 rupees per trade
    """
    return int((capital * risk_percent) / 100)

import logging
import threading
import time
from typing import Callable, Optional


logger = logging.getLogger(__name__)


class OrderTracker:
    """
    Postback-driven order tracker with split authority across surfaces.

    Authority model (matters — REST orderbook can lag postbacks by tens of
    seconds on the same broker; see SKILL.md Critical Rule 9):

      - **Postback `data.status`** — authoritative for STATUS TRANSITIONS.
        WS pushes arrive within ms. If a postback says terminal (REJECTED /
        CANCELLED / COMPLETED), believe it immediately. Do not wait for REST.
      - **REST orderbook / tradebook** — authoritative for FILL QUANTITIES,
        traded_price, avg fill price, and other fields the postback can drop
        or lag. Refresh on every postback (coalesced 500 ms debounce) to fold
        these in.
      - **Downgrade guard**: once a terminal status is recorded, a later
        non-terminal REST row must NOT overwrite it (REST is stale; postback
        was already correct).

    Terminal-status detection uses **substring match** against canonical
    tokens (`COMPLETED`, `EXECUTED`, `REJECTED`, `CANCELLED`). Brokers may
    decorate them (`REJECTED_BY_RMS`, `AMO_CANCELLED`); we normalise to the
    canonical token and preserve the original in `raw_status`.

    `on_terminal` fires once per `order_id` when it first reaches terminal,
    via either the postback fast-path (sync, on the WS thread) or the REST
    refresh (on the worker thread). Strategy code: serialize state mutations
    with a lock or queue events.

    `wait()` exists for tests, one-shot scripts, and `cancel_and_wait`. NOT
    for the strategy main loop; its `timeout` is required (no default).
    """

    # Canonical terminal tokens. Substring-matched so vendor-decorated forms
    # (REJECTED_BY_RMS, AMO_CANCELLED, EXECUTED_PARTIAL_AMENDED, ...) all
    # normalise correctly. COMPLETED and EXECUTED are the same state under
    # two names — postback uses COMPLETED, client.orders() uses EXECUTED.
    _TERMINAL_TOKENS = ("REJECTED", "CANCELLED", "EXECUTED", "COMPLETED")

    TERMINAL = {"COMPLETED", "EXECUTED", "REJECTED", "CANCELLED"}
    SUCCESS = {"COMPLETED", "EXECUTED"}

    REFRESH_ON_TYPES = {
        "order", "trade", "sl_trigger", "gtt_order", "position_conversion",
    }

    # REST page size for orderbook / tradebook fetches. Retail accounts almost
    # never exceed this in a session; raise if you trade higher volume.
    _PAGE_LIMIT = 500

    def __init__(self, client, debounce_seconds: float = 0.5) -> None:
        self._client = client
        self._debounce = debounce_seconds

        self._lock = threading.Lock()
        self._dirty: set[str] = set()
        self._worker_running = False
        self._closed = False

        # Merged state from postbacks + REST refreshes. Terminal status comes
        # from whichever surface saw it first; fill quantities / prices come
        # from the orderbook refresh.
        self._orders: dict[str, dict] = {}
        self._trades: dict[str, list] = {}

        self._events: dict[str, threading.Event] = {}
        self._notified_terminal: set[str] = set()

        # callable(order_id: str, status: str) -> None.
        # Set BEFORE placing orders. Fires once per order_id.
        self.on_terminal: Optional[Callable[[str, str], None]] = None

    # ------- status / envelope helpers -------

    @classmethod
    def _terminal_token(cls, status: Optional[str]) -> Optional[str]:
        """Substring-match a status string against canonical terminal tokens.

        Returns the canonical token (`"REJECTED"`, `"CANCELLED"`, etc.) or
        `None` if `status` is non-terminal. Handles vendor-decorated forms
        like `"REJECTED_BY_RMS"`, `"AMO_CANCELLED"`, `"EXECUTED_PARTIAL"`.
        """
        if not status:
            return None
        s = status.upper()
        for tok in cls._TERMINAL_TOKENS:
            if tok in s:
                return tok
        return None

    @classmethod
    def _normalise_row(cls, row: dict) -> "tuple[dict, Optional[str]]":
        """If `row.status` is a terminal decorated form, rewrite `status` to
        the canonical token and preserve the original in `raw_status`.

        Returns (possibly-rewritten row, canonical token or None).
        """
        raw = row.get("status") or ""
        tok = cls._terminal_token(raw)
        if tok and raw != tok:
            return {**row, "status": tok, "raw_status": raw}, tok
        return row, tok

    @staticmethod
    def _orders_rows(book: dict) -> list:
        """Endpoint response envelope varies by API:

            client.orders()    → {"orders": [...]}
            client.holdings()  → {"data":   [...]}
            client.trades()    → {"trades": [...]}

        Try the common keys in order and return the first list found.
        """
        if not isinstance(book, dict):
            return []
        for key in ("orders", "data", "orderBook", "orderbook"):
            v = book.get(key)
            if isinstance(v, list):
                return v
        return []

    @staticmethod
    def _trades_rows(trades: dict) -> list:
        if not isinstance(trades, dict):
            return []
        for key in ("trades", "data", "tradeBook", "tradebook"):
            v = trades.get(key)
            if isinstance(v, list):
                return v
        return []

    def _fetch_orderbook(self) -> dict:
        """On current vortex-api, `client.orders(limit, offset)` are required
        positional args. On older releases the no-args form worked. Try the
        new form first, fall back on TypeError for forward / backward compat.
        """
        try:
            return self._client.orders(limit=self._PAGE_LIMIT, offset=0) or {}
        except TypeError:
            return self._client.orders() or {}

    def _fetch_tradebook(self) -> dict:
        try:
            return self._client.trades(limit=self._PAGE_LIMIT, offset=0) or {}
        except TypeError:
            return self._client.trades() or {}

    @staticmethod
    def _rejection_reason(row: dict) -> Optional[str]:
        """The rejection-reason field is named differently across surfaces:

            postback envelope    →  data.status_message
            REST orderbook row   →  error_reason
            place_order response →  message

        Returns the first non-empty value across the three.
        """
        return (
            row.get("status_message")
            or row.get("error_reason")
            or row.get("message")
        )

    # ------- one-time startup seeding -------

    def initialize(self) -> None:
        """Seed cache from today's orderbook + tradebook WITHOUT firing
        `on_terminal` for orders that are already terminal at startup.

        Call ONCE at startup, BEFORE setting `on_terminal` and BEFORE placing
        orders. Otherwise the first refresh fires `on_terminal` for every
        already-completed order from earlier in the day.
        """
        try:
            book = self._fetch_orderbook()
            trades = self._fetch_tradebook()
        except Exception as exc:
            logger.warning("OrderTracker.initialize() failed: %s", exc)
            return

        with self._lock:
            for row in self._orders_rows(book):
                oid = row.get("order_id")
                if not oid:
                    continue
                normalised, tok = self._normalise_row(row)
                self._orders[oid] = normalised
                if tok:
                    self._notified_terminal.add(oid)

            per_order: dict[str, list] = {}
            for tr in self._trades_rows(trades):
                oid = tr.get("order_id")
                if oid:
                    per_order.setdefault(oid, []).append(tr)
            for oid, lst in per_order.items():
                self._trades[oid] = lst

    # ------- postback entry point (WS reader thread) -------

    def on_update(self, ws, msg: dict) -> None:
        """Wire to `wire.on_order_update`. Must NOT block (runs on WS thread).

        Fast-path: if this is an `order` postback whose `status` is already
        terminal, mirror it into the cache and fire `on_terminal` synchronously.
        The REST orderbook can be tens of seconds behind a postback on real
        rejections — waiting for it would silently miss terminal transitions.
        """
        if msg.get("type") not in self.REFRESH_ON_TYPES:
            return
        payload = msg.get("data") or {}
        order_id = payload.get("order_id")
        if not order_id:
            return

        # Fast path for terminal `order` postbacks. The REST refresh still
        # runs (see schedule below) to populate fill quantities; we just
        # don't wait for it to learn the terminal state.
        if msg.get("type") == "order":
            normalised, tok = self._normalise_row(payload)
            if tok:
                self._record_terminal_from_postback(order_id, normalised, tok)

        # Schedule a coalesced REST refresh regardless — orderbook is still
        # authoritative for traded_quantity / traded_price after a fill.
        with self._lock:
            if self._closed:
                return
            self._dirty.add(order_id)
            if not self._worker_running:
                self._worker_running = True
                try:
                    threading.Thread(
                        target=self._refresh_loop,
                        daemon=True,
                        name="OrderTracker-refresh",
                    ).start()
                except Exception:
                    self._worker_running = False
                    raise

    def _record_terminal_from_postback(
        self, order_id: str, row: dict, token: str
    ) -> None:
        """Merge a terminal postback into the cache; fire wait Events + on_terminal.

        Runs on the WS reader thread — keep it fast (no REST, no slow user code).
        Idempotent: a second terminal postback for the same order_id is a no-op.
        """
        fire = None
        with self._lock:
            if order_id in self._notified_terminal:
                return
            existing = self._orders.get(order_id, {})
            # Postback payload layered on top of prior state; raw_status preserved.
            self._orders[order_id] = {**existing, **row}
            self._notified_terminal.add(order_id)
            ev = self._events.get(order_id)
            if ev is not None:
                ev.set()
            fire = (order_id, token)

        handler = self.on_terminal
        if handler is not None and fire is not None:
            try:
                handler(*fire)
            except Exception:
                logger.exception("on_terminal handler raised for %s", fire[0])

    # ------- public read API -------

    def wait(self, order_id: str, timeout: float) -> bool:
        """Block until terminal or `timeout` seconds. `timeout` is REQUIRED;
        pass `float("inf")` to wait forever.

        Script / test primitive. In a live strategy main loop use `on_terminal`.
        Returns True iff status is in SUCCESS. After a timeout, check `status()`
        — the order may still be working at the broker.
        """
        with self._lock:
            order = self._orders.get(order_id)
            if order and order.get("status") in self.TERMINAL:
                return order["status"] in self.SUCCESS
            ev = self._events.setdefault(order_id, threading.Event())
        ev.wait(timeout)
        with self._lock:
            return (self._orders.get(order_id) or {}).get("status") in self.SUCCESS

    def cancel_and_wait(
        self, order_id: str, timeout: float
    ) -> Optional[str]:
        """Cancel and block until terminal state confirmed. Returns the actual
        terminal status — `CANCELLED`, or `COMPLETED`/`EXECUTED` if a fill
        raced the cancel. ALWAYS check before placing a replacement.
        """
        cur = self.status(order_id)
        if cur in self.TERMINAL:
            return cur
        try:
            self._client.cancel_order(order_id=order_id)
        except Exception as exc:
            logger.info("cancel_order(%s) raised: %s", order_id, exc)
        self.wait(order_id, timeout=timeout)
        return self.status(order_id)

    def status(self, order_id: str) -> Optional[str]:
        with self._lock:
            return (self._orders.get(order_id) or {}).get("status")

    def order(self, order_id: str) -> dict:
        """Latest merged row for this order (postback + orderbook fields)."""
        with self._lock:
            return dict(self._orders.get(order_id, {}))

    def fills(self, order_id: str) -> list:
        """All tradebook rows seen for this order_id."""
        with self._lock:
            return list(self._trades.get(order_id, []))

    def avg_fill_price(self, order_id: str) -> Optional[float]:
        """Quantity-weighted average fill price.

        Prefers `client.orders()`'s `traded_price` (already qty-weighted).
        Falls back to recomputing from tradebook rows. Note the field-name
        difference between surfaces — orderbook uses `traded_*`, tradebook
        uses `trade_*`.
        """
        with self._lock:
            row = self._orders.get(order_id)
        if row:
            qty = row.get("traded_quantity") or 0
            px = row.get("traded_price") or 0
            if qty > 0 and px > 0:
                return float(px)
        with self._lock:
            trades = list(self._trades.get(order_id, []))
        qty = sum((t.get("trade_quantity") or 0) for t in trades)
        if qty == 0:
            return None
        notional = sum(
            (t.get("trade_price") or 0) * (t.get("trade_quantity") or 0)
            for t in trades
        )
        return notional / qty

    def rejection_reason(self, order_id: str) -> Optional[str]:
        """Most informative rejection-reason string we've seen for this
        order. The field name varies by surface: postback uses
        `status_message`, REST uses `error_reason`, place_order response
        uses `message`. Returns the first non-empty one.
        """
        with self._lock:
            row = self._orders.get(order_id, {})
        return self._rejection_reason(row)

    def close(self) -> None:
        """Stop accepting further refreshes."""
        with self._lock:
            self._closed = True

    # ------- worker -------

    def _refresh_loop(self) -> None:
        time.sleep(self._debounce)
        while True:
            with self._lock:
                if not self._dirty or self._closed:
                    self._worker_running = False
                    return
                self._dirty.clear()

            try:
                book = self._fetch_orderbook()
                trades = self._fetch_tradebook()
            except Exception as exc:
                logger.warning("OrderTracker refresh failed: %s", exc)
                with self._lock:
                    if not self._dirty:
                        self._worker_running = False
                        return
                continue

            self._apply(book, trades)
            # No extra sleep — if new postbacks arrived during the REST calls,
            # the next iteration sees them in _dirty and refreshes immediately.

    def _apply(self, book: dict, trades: dict) -> None:
        fire: list[tuple[str, str]] = []
        with self._lock:
            for raw_row in self._orders_rows(book):
                oid = raw_row.get("order_id")
                if not oid:
                    continue
                row, tok = self._normalise_row(raw_row)

                # DOWNGRADE GUARD: REST orderbook can return PENDING /
                # working status for tens of seconds AFTER a postback
                # already pushed the terminal state. Don't let stale REST
                # data clobber a terminal status the postback established.
                if oid in self._notified_terminal and tok is None:
                    existing = self._orders.get(oid, {})
                    fields_without_status = {
                        k: v for k, v in row.items() if k != "status"
                    }
                    self._orders[oid] = {**existing, **fields_without_status}
                    continue

                # Normal path: merge (preserve any earlier fields like
                # raw_status from the postback) and store.
                existing = self._orders.get(oid, {})
                self._orders[oid] = {**existing, **row}

                if tok and oid not in self._notified_terminal:
                    self._notified_terminal.add(oid)
                    ev = self._events.get(oid)
                    if ev is not None:
                        ev.set()
                    fire.append((oid, tok))

            per_order: dict[str, list] = {}
            for tr in self._trades_rows(trades):
                oid = tr.get("order_id")
                if oid:
                    per_order.setdefault(oid, []).append(tr)
            for oid, lst in per_order.items():
                self._trades[oid] = lst

        handler = self.on_terminal
        if handler is not None:
            for oid, status in fire:
                try:
                    handler(oid, status)
                except Exception:
                    logger.exception("on_terminal handler raised for %s", oid)
```

### Live strategy wiring

```python
client  = VortexAPI()
tracker = OrderTracker(client)
tracker.initialize()                              # seed cache with today's orderbook
                                                  # so historical orders don't fire on_terminal
strategy = Strategy(config, risk_manager, client, tracker)
tracker.on_terminal = strategy.on_order_terminal  # wire callback BEFORE placing orders

wire = VortexFeed(access_token=client.access_token)
wire.on_order_update = tracker.on_update
wire.connect(threaded=True)
time.sleep(1)

strategy.run()
```

### When to call `wait()`

Three legitimate uses:

```python
# 1. cancel_and_wait — block until a cancel confirms before replacing the order
final = tracker.cancel_and_wait(order_id, timeout=10)
if final != "CANCELLED":
    logger.warning("expected CANCELLED, got %s — DO NOT place replacement", final)

# 2. One-shot script (place one order, print outcome, exit)
oid = client.place_order(...)["data"]["order_id"]
filled = tracker.wait(oid, timeout=float("inf"))   # script can block; nothing else to do

# 3. Tests
def test_market_order_fills():
    oid = client.place_order(variety=Vc.VarietyTypes.REGULAR_MARKET_ORDER, ...)
    assert tracker.wait(oid["data"]["order_id"], timeout=5)
```

Inside `strategy.next(tick)` or signal-evaluation code, **don't call `wait()`** — react to fills via `on_order_terminal`.

## 7. Complete Example: Signal Generator Module

Here's a complete, production-quality signal generator demonstrating all practices:

```python
# strategy/signal_generator.py

import logging
from typing import Optional
from dataclasses import dataclass
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class Signal:
    """Trade signal output."""
    side: str  # "BUY" or "SELL"
    symbol: str
    quantity: int
    reason: str

class SignalGenerator:
    def __init__(self, client, config):
        self.client = client
        self.config = config
        self.logger = logging.getLogger(__name__)

    def analyze_market(
        self,
        symbol: str
    ) -> Optional[Signal]:
        """
        Analyze market conditions and generate buy/sell signal.

        This function combines multiple indicators (MA, RSI) to reduce
        false signals. Both conditions must be true to generate a signal.

        Args:
            symbol: Trading symbol (e.g., "RELIANCE")

        Returns:
            Signal if conditions met, None otherwise
        """
        try:
            # Fetch recent OHLCV data
            ohlcv = self._fetch_ohlcv(symbol, period=100)

            if ohlcv is None or len(ohlcv) < 50:
                self.logger.warning(
                    f"Insufficient data for {symbol}"
                )
                return None

            # Check moving average crossover
            ma_signal = self._check_ma_crossover(ohlcv)

            # Check RSI oversold
            rsi_signal = self._check_rsi_oversold(ohlcv)

            # Generate signal only if both conditions agree
            if ma_signal and rsi_signal:
                quantity = self._calculate_quantity(symbol)

                signal = Signal(
                    side="BUY",
                    symbol=symbol,
                    quantity=quantity,
                    reason="MA + RSI confirmation"
                )

                self.logger.info(
                    f"Signal: BUY {symbol} qty={quantity}"
                )
                return signal

        except Exception as e:
            self.logger.error(
                f"Error analyzing {symbol}: {e}",
                exc_info=True
            )

        return None

    def _fetch_ohlcv(
        self,
        symbol: str,
        period: int
    ) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data from broker."""
        try:
            data = self.client.get_historical_data(
                symbol=symbol,
                period=period
            )
            return pd.DataFrame(data)
        except Exception as e:
            self.logger.error(f"Failed to fetch {symbol}: {e}")
            return None

    def _check_ma_crossover(
        self,
        ohlcv: pd.DataFrame
    ) -> bool:
        """Check if fast MA crossed above slow MA."""
        close = ohlcv["close"].values

        ma_fast = np.mean(
            close[-self.config.ma_fast_period:]
        )
        ma_slow = np.mean(
            close[-self.config.ma_slow_period:]
        )

        # Bullish crossover: fast > slow and gap widening
        return ma_fast > ma_slow

    def _check_rsi_oversold(
        self,
        ohlcv: pd.DataFrame
    ) -> bool:
        """Check if RSI indicates oversold condition."""
        close = ohlcv["close"].values
        rsi = self._calculate_rsi(close, period=14)

        return rsi < self.config.rsi_oversold_threshold

    @staticmethod
    def _calculate_rsi(
        prices: np.ndarray,
        period: int = 14
    ) -> float:
        """Calculate RSI indicator."""
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _calculate_quantity(self, symbol: str) -> int:
        """Calculate trade quantity based on risk parameters."""
        # Fetch current price
        quotes = self.client.get_quotes(symbols=[symbol])
        price = quotes[symbol]["ltp"]

        # Position size = max_position / price
        quantity = int(self.config.max_position_size / price)

        return max(quantity, 1)  # At least 1 share
```

---

## Summary: Code Quality Checklist

Before deploying any trading strategy:

- [ ] Project is organized into modules (strategy, execution, risk, guardrails)
- [ ] All logging uses `logging` module, never `print()`
- [ ] Trade events logged in structured JSON format
- [ ] Configuration is dataclass-based, never hardcoded
- [ ] All function signatures have type hints
- [ ] Critical functions have docstrings explaining "why"
- [ ] Unit tests exist for signal generation in isolation
- [ ] Integration tests verify full signal-to-order pipeline
- [ ] Tests include fixtures for market data and mock broker
- [ ] Property-based tests verify invariants with Hypothesis
- [ ] Error handling matches patterns in `error-handling.md`
- [ ] Code passes linter (pylint, flake8) and type checker (mypy)
- [ ] README documents how to run, test, and configure strategy
