# Error Handling for Live Trading Systems

This reference covers critical error handling patterns for algorithmic trading strategies. Implement these patterns to build resilient systems that recover gracefully from transient failures and maintain system integrity under adverse conditions.

## 1. Network Failures: Exponential Backoff and Circuit Breaker

Network requests to the broker API may fail due to transient issues (timeouts, packet loss) or sustained outages. Use exponential backoff to avoid overwhelming a struggling broker, and implement a circuit breaker to halt requests if failures persist.

### Exponential Backoff Pattern

```python
import time
from typing import Optional, Any, Callable

def with_exponential_backoff(
    func: Callable,
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0
) -> Any:
    """
    Retry a function with exponential backoff.

    Args:
        func: Function to call
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay between retries

    Returns:
        Result of the function call

    Raises:
        Exception: If all retries exhausted
    """
    attempt = 0
    delay = base_delay

    while attempt < max_retries:
        try:
            return func()
        except Exception as e:
            attempt += 1
            if attempt >= max_retries:
                raise

            # Calculate delay: base_delay * 2^attempt, capped at max_delay
            delay = min(base_delay * (2 ** attempt), max_delay)
            # Add jitter to prevent thundering herd
            jitter = delay * 0.1
            actual_delay = delay + (random.random() * jitter)

            logging.warning(
                f"Attempt {attempt}/{max_retries} failed: {e}. "
                f"Retrying in {actual_delay:.2f}s"
            )
            time.sleep(actual_delay)

# Usage example
def place_order():
    return client.place_order(symbol="RELIANCE", quantity=1, price=2500)

try:
    response = with_exponential_backoff(place_order, max_retries=3)
except Exception as e:
    logging.error(f"Order placement failed after retries: {e}")
```

### Circuit Breaker Pattern

The circuit breaker stops attempting requests when failures exceed a threshold, allowing the broker to recover. It has three states: closed (normal), open (failing), and half-open (testing recovery).

```python
import time
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"        # Normal operation
    OPEN = "open"            # Too many failures, block requests
    HALF_OPEN = "half_open"  # Testing if broker has recovered

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                # Try recovery
                self.state = CircuitState.HALF_OPEN
                logging.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise RuntimeError(
                    f"Circuit breaker is OPEN. "
                    f"Broker may be down. Retry in "
                    f"{self.recovery_timeout}s"
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """Reset on successful call."""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logging.info("Circuit breaker CLOSED: broker recovered")

    def _on_failure(self):
        """Increment failure count and open circuit if threshold exceeded."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logging.error(
                f"Circuit breaker OPEN after {self.failure_count} failures. "
                f"Broker may be experiencing issues."
            )

# Usage
breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)

def fetch_market_data():
    return client.get_quotes(symbols=["RELIANCE"])

try:
    quotes = breaker.call(fetch_market_data)
except RuntimeError as e:
    logging.warning(f"Cannot fetch data: {e}")
```

## 2. Order State Machine

Orders transition through distinct states: pending (awaiting broker acknowledgment), accepted (broker confirmed), partial fill (partial execution), filled (fully executed), rejected (broker refused), or cancelled (user cancelled). Track state explicitly to avoid duplicate orders or incorrect position records.

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class OrderState(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    PARTIAL_FILL = "partial_fill"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

@dataclass
class OrderRecord:
    order_id: str
    symbol: str
    quantity: int
    filled_quantity: int = 0
    state: OrderState = OrderState.PENDING
    price: float = 0.0
    timestamp: Optional[float] = None

class OrderManager:
    def __init__(self):
        self.orders: dict[str, OrderRecord] = {}
        self.state_transitions = {
            OrderState.PENDING: [
                OrderState.ACCEPTED,
                OrderState.REJECTED,
                OrderState.CANCELLED
            ],
            OrderState.ACCEPTED: [
                OrderState.PARTIAL_FILL,
                OrderState.FILLED,
                OrderState.REJECTED,
                OrderState.CANCELLED
            ],
            OrderState.PARTIAL_FILL: [
                OrderState.PARTIAL_FILL,
                OrderState.FILLED,
                OrderState.CANCELLED
            ],
        }

    def place_order(
        self,
        symbol: str,
        quantity: int,
        price: float
    ) -> str:
        """Create and track a new order."""
        order_id = str(uuid.uuid4())
        order = OrderRecord(
            order_id=order_id,
            symbol=symbol,
            quantity=quantity,
            price=price,
            timestamp=time.time()
        )
        self.orders[order_id] = order
        logging.info(f"Order {order_id} created: {symbol} qty={quantity}")
        return order_id

    def update_order_state(
        self,
        order_id: str,
        new_state: OrderState,
        filled_qty: Optional[int] = None
    ) -> bool:
        """Update order state with validation."""
        if order_id not in self.orders:
            logging.error(f"Order {order_id} not found")
            return False

        order = self.orders[order_id]

        # Validate state transition
        allowed_states = self.state_transitions.get(order.state, [])
        if new_state not in allowed_states and new_state != order.state:
            logging.error(
                f"Invalid transition: {order.state} -> {new_state}"
            )
            return False

        old_state = order.state
        order.state = new_state

        if filled_qty is not None:
            order.filled_quantity = filled_qty

        logging.info(
            f"Order {order_id}: {old_state} -> {new_state} "
            f"(filled: {order.filled_quantity}/{order.quantity})"
        )
        return True

    def is_order_live(self, order_id: str) -> bool:
        """Check if order is still active."""
        if order_id not in self.orders:
            return False

        state = self.orders[order_id].state
        return state in [
            OrderState.PENDING,
            OrderState.ACCEPTED,
            OrderState.PARTIAL_FILL
        ]

# Usage
manager = OrderManager()
order_id = manager.place_order(symbol="INFY", quantity=100, price=1500)
manager.update_order_state(order_id, OrderState.ACCEPTED)
manager.update_order_state(
    order_id,
    OrderState.PARTIAL_FILL,
    filled_qty=50
)
manager.update_order_state(
    order_id,
    OrderState.FILLED,
    filled_qty=100
)
```

## 3. Partial Fill Management

When an order fills partially, track remaining quantity separately. Reconcile positions by comparing broker reports with local order records. Always validate that positions match before executing new trades.

```python
@dataclass
class Position:
    symbol: str
    quantity: int
    average_price: float
    last_update: float

class PositionTracker:
    def __init__(self):
        self.positions: dict[str, Position] = {}

    def update_from_fill(
        self,
        symbol: str,
        quantity: int,
        fill_price: float
    ) -> None:
        """Update position from order fill (buy or sell)."""
        if symbol not in self.positions:
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                average_price=fill_price,
                last_update=time.time()
            )
        else:
            pos = self.positions[symbol]

            # Update average price using weighted average
            total_qty = pos.quantity + quantity
            if total_qty != 0:
                pos.average_price = (
                    (pos.quantity * pos.average_price +
                     quantity * fill_price) / total_qty
                )

            pos.quantity = total_qty
            pos.last_update = time.time()

        logging.info(
            f"Position updated: {symbol} qty={quantity} "
            f"avg_price={self.positions[symbol].average_price:.2f}"
        )

    def reconcile_with_broker(
        self,
        broker_positions: dict[str, int]
    ) -> dict[str, int]:
        """
        Reconcile local positions with broker holdings.

        Returns:
            dict of mismatches {symbol: (local_qty, broker_qty)}
        """
        mismatches = {}

        for symbol, qty in broker_positions.items():
            local_qty = (
                self.positions[symbol].quantity
                if symbol in self.positions else 0
            )

            if local_qty != qty:
                mismatches[symbol] = (local_qty, qty)
                logging.warning(
                    f"Position mismatch {symbol}: "
                    f"local={local_qty}, broker={qty}"
                )

        return mismatches

    def get_remaining_quantity(
        self,
        order_id: str,
        order: OrderRecord
    ) -> int:
        """Get quantity remaining to be filled."""
        return order.quantity - order.filled_quantity

# Usage
tracker = PositionTracker()
tracker.update_from_fill(symbol="TCS", quantity=50, fill_price=3500)

broker_holdings = {"TCS": 50, "RELIANCE": 100}
mismatches = tracker.reconcile_with_broker(broker_holdings)
if mismatches:
    logging.critical(f"Critical mismatch detected: {mismatches}")
```

## 4. Order Rejections and Retry Logic

Orders are rejected for specific reasons: insufficient margin, price outside exchange bands, invalid quantity, or exchange downtime. Classify rejections and implement conditional retry logic.

```python
from enum import Enum

class RejectionReason(Enum):
    INSUFFICIENT_MARGIN = "insufficient_margin"
    PRICE_OUTSIDE_BAND = "price_outside_band"
    INVALID_QUANTITY = "invalid_quantity"
    EXCHANGE_DOWNTIME = "exchange_downtime"
    UNKNOWN = "unknown"

def classify_rejection(error_message: str) -> RejectionReason:
    """Classify broker error message to reason."""
    message = error_message.lower()

    if "margin" in message or "balance" in message:
        return RejectionReason.INSUFFICIENT_MARGIN
    elif "price" in message or "band" in message:
        return RejectionReason.PRICE_OUTSIDE_BAND
    elif "quantity" in message or "qty" in message:
        return RejectionReason.INVALID_QUANTITY
    elif "exchange" in message or "down" in message or "halt" in message:
        return RejectionReason.EXCHANGE_DOWNTIME
    else:
        return RejectionReason.UNKNOWN

def should_retry_order(reason: RejectionReason) -> bool:
    """Determine if order should be retried."""
    retryable = {
        RejectionReason.EXCHANGE_DOWNTIME,
        RejectionReason.INSUFFICIENT_MARGIN,  # If more margin available
    }
    return reason in retryable

class OrderRejectionHandler:
    def __init__(self):
        self.rejection_count: dict[str, int] = {}

    def handle_rejection(
        self,
        order_id: str,
        error_message: str
    ) -> bool:
        """
        Handle order rejection.

        Returns:
            True if retry should be attempted, False otherwise
        """
        reason = classify_rejection(error_message)

        if not should_retry_order(reason):
            logging.error(
                f"Order {order_id} rejected (non-retryable): "
                f"{reason.value}: {error_message}"
            )
            return False

        # Track retry attempts
        attempts = self.rejection_count.get(order_id, 0) + 1
        self.rejection_count[order_id] = attempts

        if attempts > 3:
            logging.error(
                f"Order {order_id} exceeded max retries ({attempts}). "
                f"Reason: {reason.value}"
            )
            return False

        logging.warning(
            f"Order {order_id} rejected (retryable): "
            f"{reason.value}. Attempt {attempts}/3"
        )
        return True

# Usage
handler = OrderRejectionHandler()
try:
    client.place_order(symbol="RELIANCE", quantity=1, price=2500)
except Exception as e:
    should_retry = handler.handle_rejection("order-123", str(e))
    if should_retry:
        time.sleep(5)
        # Retry order
```

## 5. WebSocket Disconnection Handling

The SDK automatically reconnects WebSocket connections when disconnected. Do not implement custom reconnection logic. Instead, pass `reconnect=True` when initializing the wire connection and let the SDK handle recovery.

```python
from vortex import Client

# Initialize with auto-reconnect enabled
wire = vortex.wire.connect(
    threaded=True,
    reconnect=True,  # SDK handles reconnection automatically
    max_reconnect_attempts=10
)

def on_order_update(order_data):
    """Callback invoked when order updates arrive (after reconnect too)."""
    logging.info(f"Order update: {order_data}")

# Register callback
wire.on_order_update(on_order_update)

# SDK will automatically reconnect on network failure
# Callbacks continue to work after reconnect without manual intervention
```

## 6. Exchange Downtime and Market Halts

Detect circuit breaker halts and exchange downtime. Pause strategy execution until markets resume normal operation.

```python
class MarketHaltDetector:
    def __init__(self):
        self.is_halted = False
        self.halt_start_time: Optional[float] = None

    def check_market_status(self, client: Client) -> bool:
        """
        Check if exchange has triggered circuit breaker.

        Returns:
            True if market is normal, False if halted
        """
        try:
            # Attempt to fetch market data
            quotes = client.get_quotes(
                identifiers=[{"exchange": "NSE_EQ", "token": 1}]
            )

            if not quotes:
                self._mark_halt("No market data received")
                return False

            # If we receive data, market is normal
            if self.is_halted:
                duration = time.time() - self.halt_start_time
                logging.info(
                    f"Market resumed after {duration:.0f}s halt"
                )
                self.is_halted = False

            return True

        except Exception as e:
            self._mark_halt(str(e))
            return False

    def _mark_halt(self, reason: str):
        """Record that market is halted."""
        if not self.is_halted:
            self.is_halted = True
            self.halt_start_time = time.time()
            logging.critical(f"Market halt detected: {reason}")

def strategy_main_loop(halt_detector: MarketHaltDetector):
    """Main trading loop that respects market halts."""
    while True:
        # Check market status every 30 seconds
        if not halt_detector.check_market_status(client):
            logging.warning("Market halted. Pausing strategy execution.")
            time.sleep(30)
            continue

        # Execute strategy when market is normal
        execute_strategy()
        time.sleep(1)
```

## 7. Graceful Shutdown

Implement a SIGTERM handler to clean up resources when the strategy terminates. Cancel pending orders, optionally square off open positions, and persist state for recovery.

```python
import signal
from typing import Optional

class GracefulShutdown:
    def __init__(self, client: Client):
        self.client = client
        self.is_shutting_down = False
        signal.signal(signal.SIGTERM, self._on_sigterm)
        signal.signal(signal.SIGINT, self._on_sigterm)

    def _on_sigterm(self, signum, frame):
        """Handle SIGTERM signal."""
        logging.warning("SIGTERM received. Starting graceful shutdown...")
        self.is_shutting_down = True

    def shutdown(self, order_manager: OrderManager, force: bool = False):
        """
        Graceful shutdown: cancel orders and optionally square off.

        Args:
            order_manager: OrderManager instance tracking live orders
            force: If True, immediately terminate without squaring positions
        """
        logging.info("Initiating graceful shutdown")

        # Step 1: Cancel all pending orders
        live_orders = [
            (oid, o) for oid, o in order_manager.orders.items()
            if order_manager.is_order_live(oid)
        ]

        for order_id, order in live_orders:
            try:
                self.client.cancel_order(order_id=order_id)
                logging.info(f"Cancelled order {order_id}")
            except Exception as e:
                logging.error(f"Failed to cancel order {order_id}: {e}")

        # Step 2: Square off positions (optional, only if not forced)
        if not force:
            try:
                positions = self.client.get_positions()
                for pos in positions.get("net", []):
                    if pos["quantity"] != 0:
                        side = "SELL" if pos["quantity"] > 0 else "BUY"
                        qty = abs(pos["quantity"])
                        logging.info(
                            f"Squaring off {pos['symbol']}: {side} {qty}"
                        )
                        self.client.place_order(
                            symbol=pos["symbol"],
                            quantity=qty,
                            side=side,
                            product="INTRADAY"
                        )
            except Exception as e:
                logging.error(f"Failed to square off positions: {e}")

        # Step 3: Save state for recovery
        self._save_state(order_manager)
        logging.info("Shutdown complete")

    def _save_state(self, order_manager: OrderManager):
        """Persist strategy state to JSON."""
        state = {
            "orders": {
                oid: {
                    "symbol": o.symbol,
                    "quantity": o.quantity,
                    "filled_quantity": o.filled_quantity,
                    "state": o.state.value,
                    "price": o.price,
                }
                for oid, o in order_manager.orders.items()
            },
            "timestamp": time.time()
        }

        with open("strategy_state.json", "w") as f:
            json.dump(state, f, indent=2)

        logging.info("Strategy state saved to strategy_state.json")

# Usage
shutdown_handler = GracefulShutdown(client)

try:
    while not shutdown_handler.is_shutting_down:
        execute_strategy()
except KeyboardInterrupt:
    pass
finally:
    shutdown_handler.shutdown(order_manager, force=False)
```

## 8. State Persistence for Recovery

Save strategy state to JSON periodically. On restart, load state to resume from the last checkpoint without losing order information.

```python
import json
from datetime import datetime

class StateCheckpointer:
    def __init__(self, checkpoint_file: str = "checkpoint.json"):
        self.checkpoint_file = checkpoint_file

    def save_checkpoint(
        self,
        order_manager: OrderManager,
        position_tracker: PositionTracker
    ) -> None:
        """Save orders and positions to checkpoint file."""
        checkpoint = {
            "timestamp": datetime.utcnow().isoformat(),
            "orders": {
                oid: {
                    "symbol": o.symbol,
                    "quantity": o.quantity,
                    "filled_quantity": o.filled_quantity,
                    "state": o.state.value,
                    "price": o.price,
                }
                for oid, o in order_manager.orders.items()
            },
            "positions": {
                symbol: {
                    "quantity": pos.quantity,
                    "average_price": pos.average_price,
                    "last_update": pos.last_update,
                }
                for symbol, pos in position_tracker.positions.items()
            }
        }

        with open(self.checkpoint_file, "w") as f:
            json.dump(checkpoint, f, indent=2)

        logging.info(
            f"Checkpoint saved with {len(checkpoint['orders'])} orders"
        )

    def load_checkpoint(
        self,
        order_manager: OrderManager,
        position_tracker: PositionTracker
    ) -> bool:
        """
        Load orders and positions from checkpoint.

        Returns:
            True if checkpoint loaded, False if file not found
        """
        if not os.path.exists(self.checkpoint_file):
            logging.info("No checkpoint found. Starting fresh.")
            return False

        with open(self.checkpoint_file, "r") as f:
            checkpoint = json.load(f)

        # Restore orders
        for order_id, order_data in checkpoint["orders"].items():
            order = OrderRecord(
                order_id=order_id,
                symbol=order_data["symbol"],
                quantity=order_data["quantity"],
                filled_quantity=order_data["filled_quantity"],
                state=OrderState(order_data["state"]),
                price=order_data["price"],
            )
            order_manager.orders[order_id] = order

        # Restore positions
        for symbol, pos_data in checkpoint["positions"].items():
            position_tracker.positions[symbol] = Position(
                symbol=symbol,
                quantity=pos_data["quantity"],
                average_price=pos_data["average_price"],
                last_update=pos_data["last_update"],
            )

        logging.info(
            f"Checkpoint loaded: "
            f"{len(checkpoint['orders'])} orders, "
            f"{len(checkpoint['positions'])} positions"
        )
        return True

# Usage
checkpointer = StateCheckpointer()

# On startup
order_manager = OrderManager()
position_tracker = PositionTracker()
checkpointer.load_checkpoint(order_manager, position_tracker)

# During execution, save periodically
def periodic_checkpoint():
    while True:
        time.sleep(300)  # Every 5 minutes
        checkpointer.save_checkpoint(order_manager, position_tracker)
```

## 9. Rate Limiting and Request Batching

Respect API rate limits by batching requests and implementing request throttling. Most brokers impose limits on requests per minute.

```python
import threading
from collections import deque

class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.request_times: deque = deque()
        self.lock = threading.Lock()

    def acquire(self) -> None:
        """Wait if necessary to maintain rate limit."""
        with self.lock:
            now = time.time()

            # Remove timestamps older than 1 minute
            while self.request_times and self.request_times[0] < now - 60:
                self.request_times.popleft()

            # If at limit, wait
            if len(self.request_times) >= self.requests_per_minute:
                sleep_time = 60 - (now - self.request_times[0]) + 0.1
                logging.debug(f"Rate limit reached. Sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
                self.request_times.clear()

            self.request_times.append(time.time())

class BatchedQuotesFetcher:
    def __init__(self, client: Client, rate_limiter: RateLimiter):
        self.client = client
        self.rate_limiter = rate_limiter

    def get_quotes_batched(
        self,
        symbols: list[str],
        batch_size: int = 20
    ) -> dict:
        """
        Fetch quotes in batches to respect rate limits.

        Args:
            symbols: List of symbol strings
            batch_size: Max symbols per request

        Returns:
            Dict of symbol -> quote data
        """
        all_quotes = {}

        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]

            self.rate_limiter.acquire()

            try:
                quotes = self.client.get_quotes(
                    symbols=batch,
                    mode="ohlcv"
                )
                all_quotes.update(quotes)
            except Exception as e:
                logging.error(f"Failed to fetch quotes for batch: {e}")

        return all_quotes

# Usage
rate_limiter = RateLimiter(requests_per_minute=60)
fetcher = BatchedQuotesFetcher(client, rate_limiter)

symbols = ["RELIANCE", "TCS", "INFY", "WIPRO", "LT"]
quotes = fetcher.get_quotes_batched(symbols)
```

---

## Summary

Implement these patterns to build production-grade error handling:

1. Use exponential backoff with jitter for transient failures
2. Deploy circuit breaker pattern for sustained outages
3. Track explicit order state machines to prevent duplicates
4. Reconcile positions regularly against broker holdings
5. Classify rejections and retry only appropriate cases
6. Rely on SDK auto-reconnect for WebSocket failures
7. Detect market halts and pause strategy execution
8. Handle SIGTERM gracefully: cancel orders, square positions, save state
9. Checkpoint state regularly for recovery after restart
10. Batch API requests and throttle to respect rate limits
