"""
Strategy class implementing the core trading logic for Indian algo trading.

This module contains the Strategy class which handles signal generation, order placement,
order tracking, and backtesting. All orders must be approved by the RiskManager before execution.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any

import pytz

from config import Config
from risk_manager import RiskManager
from guardrails import CircuitBreaker


IST = pytz.timezone("Asia/Kolkata")


@dataclass
class Order:
    """Represents a trading order."""

    order_id: str
    symbol: str
    transaction_type: str  # BUY or SELL
    quantity: int
    price: float
    timestamp: datetime
    status: str = "PENDING"  # PENDING, FILLED, PARTIALLY_FILLED, CANCELLED, REJECTED
    filled_quantity: int = 0
    filled_price: Optional[float] = None


@dataclass
class Tick:
    """Represents a market tick/candle with OHLCV data."""

    timestamp: datetime
    symbol: str
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None


class Strategy(ABC):
    """
    Abstract base class for trading strategies.

    This class defines the interface for strategy implementation and manages order lifecycle,
    risk checks, and backtesting capabilities. All orders are subject to RiskManager approval.
    """

    def __init__(
        self,
        config: Config,
        risk_manager: RiskManager,
        circuit_breaker: CircuitBreaker,
    ):
        """
        Initialize the strategy.

        Args:
            config: Configuration object with strategy parameters.
            risk_manager: RiskManager instance for order approval.
            circuit_breaker: CircuitBreaker instance for market health checks.
        """
        self.config = config
        self.risk_manager = risk_manager
        self.circuit_breaker = circuit_breaker
        self.logger = logging.getLogger(__name__)

        # Order tracking
        self.orders: Dict[str, Order] = {}
        self.positions: Dict[str, int] = {}  # symbol -> net quantity

        self.logger.info("Strategy initialized.")

    @abstractmethod
    def next(self, tick: Tick) -> None:
        """
        Generate trading signals based on incoming market tick.

        Called once per tick/candle. Subclasses should implement signal logic here.

        Args:
            tick: Current market tick with OHLCV data.

        TODO: Implement signal generation logic.
        """
        pass

    def place_order(
        self,
        symbol: str,
        transaction_type: str,
        quantity: int,
        price: float,
        order_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Place a trading order after risk checks.

        The order is submitted to RiskManager for approval. Only approved orders are placed.

        Args:
            symbol: Trading symbol (e.g., 'RELIANCE', 'NSE:NIFTY50').
            transaction_type: 'BUY' or 'SELL'.
            quantity: Number of shares/contracts.
            price: Order price.
            order_id: Optional custom order ID. Auto-generated if not provided.

        Returns:
            Order ID if approved and placed, None if rejected.
        """
        if order_id is None:
            order_id = f"{symbol}_{datetime.now(tz=IST).timestamp()}"

        order = Order(
            order_id=order_id,
            symbol=symbol,
            transaction_type=transaction_type,
            quantity=quantity,
            price=price,
            timestamp=datetime.now(tz=IST),
        )

        # Submit order to risk manager for approval
        if not self.risk_manager.approve(order):
            self.logger.warning(
                f"Order {order_id} rejected by risk manager: "
                f"{symbol} {transaction_type} {quantity} @ {price}"
            )
            return None

        # TODO: Place order with broker API
        self.orders[order_id] = order
        self.logger.info(
            f"Order placed: {order_id} | {symbol} {transaction_type} {quantity} @ {price}"
        )
        return order_id

    def on_order_fill(self, order_id: str, filled_quantity: int, filled_price: float):
        """
        Handle order fill event.

        Called when an order is filled (partially or fully).

        Args:
            order_id: ID of the filled order.
            filled_quantity: Quantity filled in this event.
            filled_price: Price at which the order was filled.
        """
        if order_id not in self.orders:
            self.logger.warning(f"Order fill received for unknown order: {order_id}")
            return

        order = self.orders[order_id]
        order.filled_quantity += filled_quantity
        order.filled_price = filled_price
        order.status = (
            "FILLED"
            if order.filled_quantity == order.quantity
            else "PARTIALLY_FILLED"
        )

        # Update positions
        symbol = order.symbol
        quantity_change = (
            filled_quantity
            if order.transaction_type == "BUY"
            else -filled_quantity
        )
        self.positions[symbol] = self.positions.get(symbol, 0) + quantity_change

        # Update P&L
        self.risk_manager.update_pnl(symbol, order.transaction_type, filled_quantity, filled_price)

        self.logger.info(
            f"Order fill: {order_id} | {symbol} | "
            f"{filled_quantity} @ {filled_price} | Status: {order.status}"
        )

    def on_order_cancel(self, order_id: str):
        """
        Handle order cancellation event.

        Called when an order is cancelled.

        Args:
            order_id: ID of the cancelled order.
        """
        if order_id not in self.orders:
            self.logger.warning(f"Cancel event for unknown order: {order_id}")
            return

        order = self.orders[order_id]
        order.status = "CANCELLED"
        self.logger.info(f"Order cancelled: {order_id} | {order.symbol}")

    def shutdown(self):
        """
        Perform graceful shutdown: cancel open orders, close positions.

        TODO: Implement order cancellation and position closure logic.
        """
        self.logger.info("Shutting down strategy...")
        # Cancel all pending orders
        for order_id, order in list(self.orders.items()):
            if order.status in ["PENDING", "PARTIALLY_FILLED"]:
                self.on_order_cancel(order_id)
        # TODO: Close all open positions
        self.logger.info("Strategy shutdown complete.")

    def backtest(
        self,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float,
    ) -> Dict[str, Any]:
        """
        Run backtest simulation on historical data.

        Args:
            start_date: Backtest start date (IST).
            end_date: Backtest end date (IST).
            initial_capital: Initial capital for backtest.

        Returns:
            Dictionary with backtest results (returns, Sharpe ratio, max drawdown, etc.)

        TODO: Implement backtest logic using historical market data.
        """
        self.logger.info(
            f"Backtest started: {start_date} to {end_date}, capital: {initial_capital}"
        )
        # TODO: Load historical data
        # TODO: Simulate strategy execution
        # TODO: Calculate metrics
        results = {
            "total_return": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "trades": 0,
        }
        return results

    def run(self):
        """
        Main strategy execution loop.

        Connects to market data, processes ticks, and handles graceful shutdown.

        TODO: Implement connection to real-time market data feed.
        """
        self.logger.info("Starting strategy execution loop...")
        try:
            # TODO: Connect to market data feed (WebSocket or polling)
            # TODO: Process each tick: next(tick) -> signal generation -> order placement
            # TODO: Handle order fills and cancellations
            pass
        except Exception as e:
            self.logger.error(f"Strategy execution error: {e}", exc_info=True)
            raise
        finally:
            self.shutdown()
