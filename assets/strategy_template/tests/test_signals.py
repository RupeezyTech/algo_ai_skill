"""
Test suite for strategy signal generation, order execution, and risk management.

Tests cover:
- Signal generation logic
- Order placement and risk checks
- Risk manager approval/rejection
- Daily loss limit enforcement
- Position size limits
- Open position limits
"""

import pytest
from datetime import datetime, time
from typing import Generator

import pytz

from config import Config
from strategy import Strategy, Order, Tick
from risk_manager import RiskManager
from guardrails import CircuitBreaker


IST = pytz.timezone("Asia/Kolkata")


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def config() -> Config:
    """Provide a test configuration."""
    return Config(
        strategy_name="Test Strategy",
        max_loss_per_day=5000.0,
        max_position_value=100000.0,
        max_open_positions=5,
        symbols=["RELIANCE", "TCS", "INFY"],
        enable_backtest=False,
        enable_paper_trading=True,
        enable_live_trading=False,
    )


@pytest.fixture
def risk_manager(config: Config) -> RiskManager:
    """Provide a risk manager instance."""
    return RiskManager(config)


@pytest.fixture
def circuit_breaker(config: Config) -> CircuitBreaker:
    """Provide a circuit breaker instance."""
    return CircuitBreaker(config)


@pytest.fixture
def strategy(
    config: Config, risk_manager: RiskManager, circuit_breaker: CircuitBreaker
) -> "TestStrategy":
    """Provide a concrete strategy implementation for testing."""
    return TestStrategy(config, risk_manager, circuit_breaker)


# ============================================================================
# Test Strategy Implementation (for testing)
# ============================================================================


class TestStrategy(Strategy):
    """Concrete strategy implementation for unit testing."""

    def next(self, tick: Tick) -> None:
        """Simple signal generation for testing."""
        if tick.close_price > tick.open_price:
            # Simple buy signal on up candle
            self.place_order(tick.symbol, "BUY", 10, tick.close_price)


# ============================================================================
# Tests: Order Initialization
# ============================================================================


class TestOrderInitialization:
    """Tests for Order initialization and defaults."""

    def test_order_creation_with_defaults(self):
        """Test that Order is created with correct defaults."""
        order = Order(
            order_id="test_001",
            symbol="RELIANCE",
            transaction_type="BUY",
            quantity=10,
            price=2500.0,
            timestamp=datetime.now(tz=IST),
        )

        assert order.order_id == "test_001"
        assert order.symbol == "RELIANCE"
        assert order.transaction_type == "BUY"
        assert order.quantity == 10
        assert order.price == 2500.0
        assert order.status == "PENDING"
        assert order.filled_quantity == 0
        assert order.filled_price is None

    def test_order_creation_with_custom_status(self):
        """Test Order creation with custom initial status."""
        order = Order(
            order_id="test_002",
            symbol="TCS",
            transaction_type="SELL",
            quantity=5,
            price=3500.0,
            timestamp=datetime.now(tz=IST),
            status="FILLED",
            filled_quantity=5,
            filled_price=3500.0,
        )

        assert order.status == "FILLED"
        assert order.filled_quantity == 5


# ============================================================================
# Tests: Risk Manager Approval Logic
# ============================================================================


class TestRiskManagerApproval:
    """Tests for RiskManager order approval logic."""

    def test_approve_normal_order(
        self, config: Config, risk_manager: RiskManager
    ):
        """Test that a normal order is approved."""
        order = Order(
            order_id="test_001",
            symbol="RELIANCE",
            transaction_type="BUY",
            quantity=10,
            price=2500.0,
            timestamp=datetime.now(tz=IST),
        )

        assert risk_manager.approve(order) is True

    def test_reject_oversized_order(
        self, config: Config, risk_manager: RiskManager
    ):
        """Test that oversized orders are rejected."""
        order = Order(
            order_id="test_002",
            symbol="RELIANCE",
            transaction_type="BUY",
            quantity=1000,  # 1000 * 2500 = 2,500,000 > 100,000 limit
            price=2500.0,
            timestamp=datetime.now(tz=IST),
        )

        assert risk_manager.approve(order) is False

    def test_reject_order_exceeding_max_positions(
        self, config: Config, risk_manager: RiskManager
    ):
        """Test that orders are rejected when max open positions reached."""
        # Fill up max positions
        for i in range(config.max_open_positions):
            order = Order(
                order_id=f"test_{i:03d}",
                symbol=f"SYM_{i}",
                transaction_type="BUY",
                quantity=10,
                price=1000.0,
                timestamp=datetime.now(tz=IST),
            )
            # Approve first N orders
            assert risk_manager.approve(order) is True
            # Simulate position opening
            risk_manager.update_pnl(f"SYM_{i}", "BUY", 10, 1000.0)

        # Next order should be rejected
        new_order = Order(
            order_id="test_overflow",
            symbol="NEW_SYMBOL",
            transaction_type="BUY",
            quantity=10,
            price=1000.0,
            timestamp=datetime.now(tz=IST),
        )

        assert risk_manager.approve(new_order) is False

    def test_approve_order_new_symbol_within_limits(
        self, config: Config, risk_manager: RiskManager
    ):
        """Test that new position is approved when within limits."""
        # Open a position
        order1 = Order(
            order_id="test_001",
            symbol="RELIANCE",
            transaction_type="BUY",
            quantity=10,
            price=1000.0,
            timestamp=datetime.now(tz=IST),
        )
        assert risk_manager.approve(order1) is True
        risk_manager.update_pnl("RELIANCE", "BUY", 10, 1000.0)

        # Open another position (still within limits)
        order2 = Order(
            order_id="test_002",
            symbol="TCS",
            transaction_type="BUY",
            quantity=20,
            price=1000.0,
            timestamp=datetime.now(tz=IST),
        )
        assert risk_manager.approve(order2) is True


# ============================================================================
# Tests: Daily Loss Limit
# ============================================================================


class TestDailyLossLimit:
    """Tests for daily loss limit enforcement."""

    def test_daily_loss_limit_not_exceeded(
        self, config: Config, risk_manager: RiskManager
    ):
        """Test that orders are approved when loss is within limit."""
        # Simulate a small loss
        risk_manager.daily_realized_pnl = -2000.0

        order = Order(
            order_id="test_001",
            symbol="RELIANCE",
            transaction_type="BUY",
            quantity=10,
            price=1000.0,
            timestamp=datetime.now(tz=IST),
        )

        assert risk_manager.approve(order) is True

    def test_daily_loss_limit_exceeded(
        self, config: Config, risk_manager: RiskManager
    ):
        """Test that orders are rejected when daily loss limit is exceeded."""
        # Simulate loss exceeding limit
        risk_manager.daily_realized_pnl = -5500.0  # > 5000 limit

        order = Order(
            order_id="test_002",
            symbol="RELIANCE",
            transaction_type="BUY",
            quantity=10,
            price=1000.0,
            timestamp=datetime.now(tz=IST),
        )

        assert risk_manager.approve(order) is False

    def test_daily_loss_exactly_at_limit(
        self, config: Config, risk_manager: RiskManager
    ):
        """Test behavior when daily loss exactly equals limit."""
        risk_manager.daily_realized_pnl = -5000.0  # Exactly at limit

        order = Order(
            order_id="test_003",
            symbol="RELIANCE",
            transaction_type="BUY",
            quantity=10,
            price=1000.0,
            timestamp=datetime.now(tz=IST),
        )

        # Should be rejected (at limit means no more orders)
        assert risk_manager.approve(order) is False


# ============================================================================
# Tests: P&L Tracking
# ============================================================================


class TestPnlTracking:
    """Tests for P&L calculation and tracking."""

    def test_update_pnl_buy_order(
        self, config: Config, risk_manager: RiskManager
    ):
        """Test P&L update on buy order."""
        risk_manager.update_pnl("RELIANCE", "BUY", 10, 2500.0)

        position = risk_manager.get_position("RELIANCE")
        assert position.quantity == 10
        assert position.avg_entry_price == 2500.0

    def test_update_pnl_sell_order_with_profit(
        self, config: Config, risk_manager: RiskManager
    ):
        """Test P&L calculation on sell order with profit."""
        # Buy 10 at 2500
        risk_manager.update_pnl("RELIANCE", "BUY", 10, 2500.0)

        # Sell 5 at 2600 (profit: 5 * 100 = 500)
        risk_manager.update_pnl("RELIANCE", "SELL", 5, 2600.0)

        position = risk_manager.get_position("RELIANCE")
        assert position.quantity == 5
        assert position.realized_pnl == 500.0
        assert risk_manager.daily_realized_pnl == 500.0

    def test_update_pnl_sell_order_with_loss(
        self, config: Config, risk_manager: RiskManager
    ):
        """Test P&L calculation on sell order with loss."""
        # Buy 10 at 2500
        risk_manager.update_pnl("RELIANCE", "BUY", 10, 2500.0)

        # Sell 10 at 2400 (loss: 10 * -100 = -1000)
        risk_manager.update_pnl("RELIANCE", "SELL", 10, 2400.0)

        position = risk_manager.get_position("RELIANCE")
        assert position.quantity == 0
        assert position.realized_pnl == -1000.0
        assert risk_manager.daily_realized_pnl == -1000.0

    def test_get_daily_pnl(self, config: Config, risk_manager: RiskManager):
        """Test daily P&L aggregation."""
        risk_manager.daily_realized_pnl = 5000.0
        risk_manager.daily_unrealized_pnl = -1000.0

        assert risk_manager.get_daily_pnl() == 4000.0


# ============================================================================
# Tests: Strategy Order Placement
# ============================================================================


class TestStrategyOrderPlacement:
    """Tests for strategy order placement and approval."""

    def test_place_normal_order(
        self, strategy: TestStrategy, risk_manager: RiskManager
    ):
        """Test placing a normal order through strategy."""
        order_id = strategy.place_order(
            symbol="RELIANCE",
            transaction_type="BUY",
            quantity=10,
            price=2500.0,
        )

        assert order_id is not None
        assert order_id in strategy.orders
        assert strategy.orders[order_id].status == "PENDING"

    def test_place_rejected_order(
        self, strategy: TestStrategy, risk_manager: RiskManager
    ):
        """Test that rejected orders are not added to strategy."""
        # Set daily loss to trigger rejection
        risk_manager.daily_realized_pnl = -5500.0

        order_id = strategy.place_order(
            symbol="RELIANCE",
            transaction_type="BUY",
            quantity=10,
            price=2500.0,
        )

        assert order_id is None

    def test_place_oversized_order(
        self, strategy: TestStrategy, risk_manager: RiskManager
    ):
        """Test that oversized orders are rejected."""
        order_id = strategy.place_order(
            symbol="RELIANCE",
            transaction_type="BUY",
            quantity=1000,  # Exceeds max_position_value
            price=2500.0,
        )

        assert order_id is None


# ============================================================================
# Tests: Configuration Validation
# ============================================================================


class TestConfigValidation:
    """Tests for configuration validation."""

    def test_config_validate_passes(self, config: Config):
        """Test that valid config passes validation."""
        config.validate()  # Should not raise

    def test_config_validate_negative_max_loss(self, config: Config):
        """Test that negative max_loss_per_day raises error."""
        config.max_loss_per_day = -1000.0
        with pytest.raises(ValueError):
            config.validate()

    def test_config_validate_invalid_exchange(self, config: Config):
        """Test that invalid exchange raises error."""
        config.exchange = "INVALID"
        with pytest.raises(ValueError):
            config.validate()

    def test_config_validate_empty_symbols(self, config: Config):
        """Test that empty symbols list raises error."""
        config.symbols = []
        with pytest.raises(ValueError):
            config.validate()

    def test_config_validate_market_hours(self, config: Config):
        """Test that invalid market hours raise error."""
        config.market_open_time = time(15, 30)  # 3:30 PM
        config.market_close_time = time(9, 15)  # 9:15 AM
        with pytest.raises(ValueError):
            config.validate()


# ============================================================================
# Tests: Order Lifecycle
# ============================================================================


class TestOrderLifecycle:
    """Tests for order state transitions."""

    def test_order_fill_update(self, strategy: TestStrategy):
        """Test order state update on fill."""
        order_id = strategy.place_order(
            symbol="RELIANCE",
            transaction_type="BUY",
            quantity=10,
            price=2500.0,
        )

        strategy.on_order_fill(order_id, filled_quantity=10, filled_price=2500.0)

        order = strategy.orders[order_id]
        assert order.status == "FILLED"
        assert order.filled_quantity == 10
        assert order.filled_price == 2500.0

    def test_order_partial_fill_update(self, strategy: TestStrategy):
        """Test order state update on partial fill."""
        order_id = strategy.place_order(
            symbol="RELIANCE",
            transaction_type="BUY",
            quantity=10,
            price=2500.0,
        )

        strategy.on_order_fill(order_id, filled_quantity=5, filled_price=2500.0)

        order = strategy.orders[order_id]
        assert order.status == "PARTIALLY_FILLED"
        assert order.filled_quantity == 5

        strategy.on_order_fill(order_id, filled_quantity=5, filled_price=2500.0)

        assert order.status == "FILLED"
        assert order.filled_quantity == 10

    def test_order_cancel(self, strategy: TestStrategy):
        """Test order cancellation."""
        order_id = strategy.place_order(
            symbol="RELIANCE",
            transaction_type="BUY",
            quantity=10,
            price=2500.0,
        )

        strategy.on_order_cancel(order_id)

        order = strategy.orders[order_id]
        assert order.status == "CANCELLED"
