"""
Risk management module for enforcing position sizing, daily loss limits, and exposure controls.

This module contains the RiskManager class which approves/rejects orders based on
risk parameters and tracks P&L for daily loss limit enforcement.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Optional

from config import Config


@dataclass
class PositionMetrics:
    """Tracks metrics for an open position."""

    symbol: str
    quantity: int = 0
    avg_entry_price: float = 0.0
    current_price: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0

    @property
    def total_pnl(self) -> float:
        """Calculate total P&L (realized + unrealized)."""
        return self.realized_pnl + self.unrealized_pnl


class RiskManager:
    """
    Manages risk by enforcing limits on position size, daily losses, and open positions.

    All orders must pass through the approve() method before being placed.
    """

    def __init__(self, config: Config):
        """
        Initialize the risk manager with configuration parameters.

        Args:
            config: Configuration object with risk parameters.
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Daily P&L tracking
        self.daily_realized_pnl: float = 0.0
        self.daily_unrealized_pnl: float = 0.0

        # Position tracking
        self.positions: Dict[str, PositionMetrics] = {}

        self.logger.info(
            f"RiskManager initialized: "
            f"max_loss={config.max_loss_per_day}, "
            f"max_position_value={config.max_position_value}, "
            f"max_open_positions={config.max_open_positions}"
        )

    def approve(self, order) -> bool:
        """
        Check if an order meets all risk criteria.

        An order is approved if it:
        1. Does not exceed daily loss limit
        2. Does not result in position size exceeding limit
        3. Does not exceed maximum number of open positions

        Args:
            order: Order object to evaluate.

        Returns:
            True if order is approved, False otherwise.
        """
        # Check daily loss limit
        if self._check_daily_loss_limit():
            self.logger.warning(
                f"Order {order.order_id} rejected: Daily loss limit reached. "
                f"Current loss: {self.daily_realized_pnl + self.daily_unrealized_pnl}"
            )
            return False

        # Check position size limit
        proposed_position_value = order.quantity * order.price
        if not self._check_position_size(proposed_position_value):
            self.logger.warning(
                f"Order {order.order_id} rejected: Proposed position value "
                f"({proposed_position_value}) exceeds limit ({self.config.max_position_value})"
            )
            return False

        # Check max open positions limit
        new_position = order.symbol not in self.positions
        current_open_positions = len(
            [p for p in self.positions.values() if p.quantity != 0]
        )
        if new_position and current_open_positions >= self.config.max_open_positions:
            self.logger.warning(
                f"Order {order.order_id} rejected: Maximum open positions "
                f"({self.config.max_open_positions}) reached"
            )
            return False

        self.logger.debug(f"Order {order.order_id} approved: {order.symbol} {order.transaction_type} {order.quantity}")
        return True

    def _check_daily_loss_limit(self) -> bool:
        """
        Check if daily loss limit has been reached.

        Returns:
            True if limit reached (further orders should be rejected), False otherwise.
        """
        total_daily_pnl = self.daily_realized_pnl + self.daily_unrealized_pnl
        if total_daily_pnl <= -self.config.max_loss_per_day:
            return True
        return False

    def _check_position_size(self, proposed_position_value: float) -> bool:
        """
        Check if proposed position would exceed size limit.

        Args:
            proposed_position_value: Total value (quantity * price) of the proposed position.

        Returns:
            True if within limit, False if exceeds limit.
        """
        return proposed_position_value <= self.config.max_position_value

    def update_pnl(
        self,
        symbol: str,
        transaction_type: str,
        quantity: int,
        price: float,
    ):
        """
        Update P&L tracking when an order is filled.

        Args:
            symbol: Trading symbol.
            transaction_type: 'BUY' or 'SELL'.
            quantity: Quantity filled.
            price: Execution price.
        """
        if symbol not in self.positions:
            self.positions[symbol] = PositionMetrics(symbol=symbol)

        position = self.positions[symbol]

        if transaction_type == "BUY":
            # Update average entry price
            total_cost = (
                position.quantity * position.avg_entry_price + quantity * price
            )
            position.quantity += quantity
            if position.quantity > 0:
                position.avg_entry_price = total_cost / position.quantity
        else:  # SELL
            # Calculate realized P&L only on the portion that closes the existing long.
            closing_quantity = min(quantity, position.quantity) if position.quantity > 0 else 0
            if closing_quantity > 0:
                pnl_per_unit = price - position.avg_entry_price
                realized_pnl = pnl_per_unit * closing_quantity
                self.daily_realized_pnl += realized_pnl
                position.realized_pnl += realized_pnl

            # This template is long-only: clamp at 0 instead of going short on
            # an oversell, which would otherwise leave a phantom short position
            # carrying the old long's avg_entry_price.
            oversold_quantity = quantity - closing_quantity
            if oversold_quantity > 0:
                self.logger.warning(
                    f"Oversold {symbol}: sell quantity {quantity} exceeds long "
                    f"position of {position.quantity}; {oversold_quantity} unit(s) "
                    f"ignored (long-only, no short positions supported)."
                )

            position.quantity = max(position.quantity - quantity, 0)
            if position.quantity == 0:
                position.avg_entry_price = 0.0

        self.logger.debug(
            f"P&L updated: {symbol} | qty={position.quantity} | "
            f"avg_price={position.avg_entry_price} | realized={self.daily_realized_pnl}"
        )

    def get_position(self, symbol: str) -> Optional[PositionMetrics]:
        """
        Get position metrics for a symbol.

        Args:
            symbol: Trading symbol.

        Returns:
            PositionMetrics object or None if no position exists.
        """
        return self.positions.get(symbol)

    def get_daily_pnl(self) -> float:
        """
        Get current daily P&L (realized + unrealized).

        Returns:
            Total daily P&L.
        """
        return self.daily_realized_pnl + self.daily_unrealized_pnl

    def reset_daily_pnl(self):
        """Reset daily P&L counters (typically at market close)."""
        self.daily_realized_pnl = 0.0
        self.daily_unrealized_pnl = 0.0
        self.logger.info("Daily P&L reset.")
