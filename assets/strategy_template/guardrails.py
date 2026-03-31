"""
Guardrails module implementing market health checks and slippage detection.

This module contains the CircuitBreaker class which monitors market conditions
and can halt trading if anomalies are detected.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from config import Config


@dataclass
class MarketHealth:
    """Represents current market health status."""

    is_healthy: bool
    bid_ask_valid: bool
    spread_within_limit: bool
    halted: bool = False
    reason: str = ""


class CircuitBreaker:
    """
    Monitors market conditions and implements circuit breaker logic.

    Detects anomalies such as zero bid/ask spreads, extreme spreads, or market halts.
    """

    def __init__(self, config: Config):
        """
        Initialize the circuit breaker.

        Args:
            config: Configuration object with guardrail parameters.
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.halted = False
        self.halt_reason = ""

        self.logger.info("CircuitBreaker initialized.")

    def check_market_health(self, tick) -> MarketHealth:
        """
        Check overall market health based on current tick.

        Validates:
        - Bid/ask prices are non-zero
        - Bid price < ask price
        - Spread is within acceptable limits

        Args:
            tick: Current market tick with bid/ask data.

        Returns:
            MarketHealth object indicating health status.
        """
        health = MarketHealth(is_healthy=True, bid_ask_valid=True, spread_within_limit=True)

        # Check if bid/ask are valid (non-zero and bid < ask)
        if not tick.bid_price or not tick.ask_price:
            health.bid_ask_valid = False
            health.is_healthy = False
            health.reason = "Invalid bid/ask prices (zero or missing)"
            self.logger.warning(f"Market health check failed: {health.reason} for {tick.symbol}")
            return health

        if tick.bid_price >= tick.ask_price:
            health.bid_ask_valid = False
            health.is_healthy = False
            health.reason = f"Invalid bid/ask: bid({tick.bid_price}) >= ask({tick.ask_price})"
            self.logger.warning(f"Market health check failed: {health.reason} for {tick.symbol}")
            return health

        # Check if spread is within limits
        if not self._check_spread_limit(tick):
            health.spread_within_limit = False
            health.is_healthy = False
            spread = tick.ask_price - tick.bid_price
            health.reason = f"Spread exceeded: {spread} for {tick.symbol}"
            self.logger.warning(f"Market health check failed: {health.reason}")
            return health

        self.logger.debug(f"Market health OK for {tick.symbol}")
        return health

    def _check_spread_limit(self, tick) -> bool:
        """
        Check if bid-ask spread is within acceptable limits.

        Spread limit is typically defined as percentage of mid price.

        Args:
            tick: Current market tick.

        Returns:
            True if spread is within limit, False otherwise.
        """
        # TODO: Get spread limit from config
        max_spread_percent = 0.5  # 0.5% of mid price

        mid_price = (tick.bid_price + tick.ask_price) / 2
        spread = tick.ask_price - tick.bid_price
        spread_percent = (spread / mid_price) * 100

        return spread_percent <= max_spread_percent

    def check_slippage(
        self,
        symbol: str,
        expected_price: float,
        actual_price: float,
        max_slippage_percent: float = 0.1,
    ) -> bool:
        """
        Check if actual execution price has excessive slippage.

        Args:
            symbol: Trading symbol.
            expected_price: Expected execution price.
            actual_price: Actual execution price.
            max_slippage_percent: Maximum acceptable slippage as percentage. Default 0.1%.

        Returns:
            True if slippage is within limit, False if excessive.
        """
        if expected_price == 0:
            self.logger.warning(f"Cannot check slippage for {symbol}: expected_price is 0")
            return True

        slippage_percent = abs((actual_price - expected_price) / expected_price) * 100

        if slippage_percent > max_slippage_percent:
            self.logger.warning(
                f"Excessive slippage detected for {symbol}: "
                f"expected={expected_price}, actual={actual_price}, "
                f"slippage={slippage_percent:.4f}%"
            )
            return False

        self.logger.debug(
            f"Slippage acceptable for {symbol}: {slippage_percent:.4f}% "
            f"(limit: {max_slippage_percent}%)"
        )
        return True

    def halt_trading(self, reason: str):
        """
        Halt all trading activity.

        Args:
            reason: Reason for halt (logged for audit trail).
        """
        self.halted = True
        self.halt_reason = reason
        self.logger.error(f"TRADING HALTED: {reason}")

    def resume_trading(self):
        """Resume trading activity after halt."""
        self.halted = False
        self.halt_reason = ""
        self.logger.info("Trading resumed.")

    def is_trading_halted(self) -> bool:
        """
        Check if trading is currently halted.

        Returns:
            True if halted, False otherwise.
        """
        return self.halted
