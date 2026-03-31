#!/usr/bin/env python3
"""
Strategy Scaffolder

Generates a best-practice project skeleton for algo trading strategies.
Creates directory structure and starter templates following all skill rules.

Usage:
    python scaffold_strategy.py my_strategy --type live
    python scaffold_strategy.py backtest_v2 --type backtest

Output structure:
    my_strategy/
        main.py
        strategy.py
        risk_manager.py
        guardrails.py
        config.py
        requirements.txt
        .env.example
        tests/
            __init__.py
            test_signals.py
"""

import sys
import logging
from pathlib import Path
import argparse

logger = logging.getLogger(__name__)


def scaffold_directory(name, strategy_type):
    """Create directory structure."""
    base_dir = Path(name)

    if base_dir.exists():
        print(f"Error: Directory '{name}' already exists")
        sys.exit(1)

    base_dir.mkdir(parents=True)
    tests_dir = base_dir / 'tests'
    tests_dir.mkdir()

    print(f"Created directory structure: {base_dir}")

    return base_dir


def write_main_py(base_dir, strategy_type):
    """Generate main.py with proper initialization."""
    content = '''#!/usr/bin/env python3
"""
Main strategy entry point.

Sets up logging, timezone, WebSocket connection, and SIGTERM handler.
Initializes risk manager and runs the trading loop.
"""

import sys
import signal
import logging
import os
from datetime import datetime
import pytz
from config import Config
from strategy import Strategy
from risk_manager import RiskManager

# Configure logging with timezone
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Set timezone to IST (Indian Standard Time)
IST = pytz.timezone('Asia/Kolkata')

config = Config()
risk_manager = RiskManager(config=config)
strategy = Strategy(config=config, risk_manager=risk_manager)

shutdown_event = False


def handle_sigterm(signum, frame):
    """Graceful shutdown on SIGTERM."""
    global shutdown_event
    logger.info("SIGTERM received. Starting graceful shutdown...")
    shutdown_event = True


def main():
    """Initialize and run strategy."""
    logger.info(f"Strategy starting at {datetime.now(IST)}")
    logger.info(f"Strategy type: ''' + strategy_type + '''")
    logger.info(f"Max position size: {config.max_position_value}")
    logger.info(f"Max loss per day: {config.max_loss_per_day}")

    signal.signal(signal.SIGTERM, handle_sigterm)

    try:
        if ''' + ('"backtest"' if strategy_type == 'backtest' else '"live"') + ''' in ''' + strategy_type.upper() + ''':
            logger.info("Running backtest mode")
            strategy.backtest()
        else:
            logger.info("Running live mode")
            strategy.run()

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.exception(f"Unhandled exception: {e}")
        return 1
    finally:
        logger.info("Strategy shutdown complete")

    return 0


if __name__ == '__main__':
    sys.exit(main())
'''
    (base_dir / 'main.py').write_text(content)
    logger.info("Created main.py")


def write_strategy_py(base_dir):
    """Generate strategy.py with Strategy class."""
    content = '''"""
Trading strategy logic.

The Strategy class encapsulates signal generation and order placement logic.
All orders go through risk_manager.approve() before execution.
"""

import logging
from typing import Optional
from config import Config
from risk_manager import RiskManager

logger = logging.getLogger(__name__)


class Strategy:
    """Base strategy implementation."""

    def __init__(self, config: Config, risk_manager: RiskManager):
        """Initialize strategy with configuration and risk controls."""
        self.config = config
        self.risk_manager = risk_manager
        self.positions = {}

    def init(self):
        """Initialize strategy state (called once at startup).

        Load historical data, set up subscriptions, warm up indicators.
        """
        logger.info("Initializing strategy")
        # TODO: Load master data, set up WebSocket subscriptions

    def next(self, tick):
        """Process each market tick.

        Args:
            tick: Market data with symbol, ltp, bid, ask, volume, timestamp
        """
        # TODO: Generate signals based on indicators
        # TODO: Check if we should enter/exit positions
        # TODO: Place orders through risk_manager
        pass

    def on_order_fill(self, order):
        """Callback when an order is filled."""
        logger.info(f"Order filled: {order}")
        # TODO: Update position tracking

    def on_order_cancel(self, order):
        """Callback when an order is cancelled."""
        logger.info(f"Order cancelled: {order}")

    def backtest(self):
        """Run strategy in backtest mode (paper trading)."""
        logger.info("Backtest mode not yet implemented")
        # TODO: Load historical data and run signal generation

    def run(self):
        """Run strategy in live mode."""
        logger.info("Live mode not yet implemented")
        # TODO: Connect to WebSocket, listen to ticks, place orders
'''
    (base_dir / 'strategy.py').write_text(content)
    logger.info("Created strategy.py")


def write_risk_manager_py(base_dir):
    """Generate risk_manager.py with risk controls."""
    content = '''"""
Risk management and order approval.

All orders must pass through approve() before execution.
Enforces position limits, loss limits, and margin checks.
"""

import logging
from config import Config

logger = logging.getLogger(__name__)


class RiskManager:
    """Risk management and order approval engine."""

    def __init__(self, config: Config):
        """Initialize with risk configuration."""
        self.config = config
        self.daily_pnl = 0
        self.open_positions = {}

    def approve(self, order: dict) -> bool:
        """Approve or reject an order based on risk rules.

        Args:
            order: Order dict with symbol, quantity, price, type, etc.

        Returns:
            True if order is approved, False otherwise.
        """
        # Check 1: Max loss per day
        if self.daily_pnl < -self.config.max_loss_per_day:
            logger.warning(
                f"Daily loss limit exceeded: {self.daily_pnl:.2f} "
                f"< -{self.config.max_loss_per_day}"
            )
            return False

        # Check 2: Position size limit
        notional_value = order.get('quantity', 0) * order.get('price', 0)
        if notional_value > self.config.max_position_value:
            logger.warning(
                f"Position too large: {notional_value:.2f} "
                f"> {self.config.max_position_value}"
            )
            return False

        # Check 3: Max open positions
        if len(self.open_positions) >= self.config.max_open_positions:
            logger.warning(
                f"Too many open positions: {len(self.open_positions)} "
                f">= {self.config.max_open_positions}"
            )
            return False

        logger.info(f"Order approved: {order}")
        return True

    def update_pnl(self, pnl: float):
        """Update daily P&L (called after order fills)."""
        self.daily_pnl += pnl
        logger.info(f"Daily P&L: {self.daily_pnl:.2f}")
'''
    (base_dir / 'risk_manager.py').write_text(content)
    logger.info("Created risk_manager.py")


def write_guardrails_py(base_dir):
    """Generate guardrails.py with safety checks."""
    content = '''"""
Trading guardrails and circuit breakers.

Hard stops to prevent runaway trading or catastrophic losses.
These cannot be overridden by strategy logic.
"""

import logging

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Emergency stop if market conditions are extreme."""

    def __init__(self, max_slippage_pct=2.0, max_spread_pct=0.5):
        """Initialize circuit breaker thresholds.

        Args:
            max_slippage_pct: Max acceptable slippage in percent
            max_spread_pct: Max acceptable bid-ask spread in percent
        """
        self.max_slippage_pct = max_slippage_pct
        self.max_spread_pct = max_spread_pct

    def check_market_health(self, tick: dict) -> bool:
        """Check if market conditions are normal.

        Args:
            tick: Market data tick

        Returns:
            False if market is unhealthy (circuit broken)
        """
        if tick.get('bid') == 0 or tick.get('ask') == 0:
            logger.error("Zero bid/ask detected. Circuit breaker triggered.")
            return False

        spread = tick['ask'] - tick['bid']
        spread_pct = (spread / tick['ltp']) * 100 if tick['ltp'] > 0 else 0

        if spread_pct > self.max_spread_pct:
            logger.error(
                f"Extreme spread detected: {spread_pct:.2f}% > {self.max_spread_pct}%. "
                f"Circuit breaker triggered."
            )
            return False

        return True

    def check_slippage(self, expected_price: float, actual_price: float) -> bool:
        """Check if order fill slippage is acceptable."""
        slippage_pct = abs(
            (actual_price - expected_price) / expected_price * 100
        )

        if slippage_pct > self.max_slippage_pct:
            logger.error(
                f"Excessive slippage: {slippage_pct:.2f}% > {self.max_slippage_pct}%"
            )
            return False

        return True
'''
    (base_dir / 'guardrails.py').write_text(content)
    logger.info("Created guardrails.py")


def write_config_py(base_dir):
    """Generate config.py with risk parameters."""
    content = '''"""
Configuration and defaults.

All strategy and risk parameters defined in one place.
"""

from dataclasses import dataclass


@dataclass
class Config:
    """Trading strategy configuration."""

    # Risk parameters
    max_loss_per_day: float = 5000.0  # Stop if cumulative loss exceeds this
    max_position_value: float = 100000.0  # Max notional value per trade
    max_open_positions: int = 5  # Max concurrent open positions

    # Market parameters
    exchange: str = "NSE"
    market_open_time: str = "09:15"  # IST
    market_close_time: str = "15:30"  # IST

    # Order parameters
    default_product: str = "DELIVERY"  # or INTRADAY, MTF, BTST
    slippage_pct: float = 0.5  # Expected slippage tolerance

    # Backtest parameters
    backtest_start_date: str = "2024-01-01"
    backtest_end_date: str = "2024-12-31"
    initial_capital: float = 1000000.0

    def validate(self) -> bool:
        """Validate configuration parameters."""
        assert self.max_loss_per_day > 0, "max_loss_per_day must be positive"
        assert self.max_position_value > 0, "max_position_value must be positive"
        assert self.max_open_positions > 0, "max_open_positions must be positive"
        return True
'''
    (base_dir / 'config.py').write_text(content)
    logger.info("Created config.py")


def write_requirements_txt(base_dir):
    """Generate requirements.txt."""
    content = '''# Core trading API
vortex-api>=2.0.0

# Data processing
pandas>=1.3.0
numpy>=1.21.0

# Date/time handling
pytz>=2021.3

# Testing
pytest>=6.2.0
pytest-cov>=2.12.0

# Development
black>=21.0
flake8>=3.9.0
mypy>=0.910
'''
    (base_dir / 'requirements.txt').write_text(content)
    logger.info("Created requirements.txt")


def write_env_example(base_dir):
    """Generate .env.example template."""
    content = '''# Copy this file to .env and fill in your credentials
# Never commit .env to version control

# Broker API credentials
BROKER_API_KEY=your_api_key_here
BROKER_CLIENT_ID=your_client_id_here
BROKER_ACCESS_TOKEN=your_access_token_here

# Strategy configuration
STRATEGY_NAME=my_strategy
STRATEGY_TYPE=live

# Logging
LOG_LEVEL=INFO
LOG_FILE=strategy.log

# Market data
MASTER_DATA_PATH=./data/master.csv
TICK_BUFFER_SIZE=1000
'''
    (base_dir / '.env.example').write_text(content)
    logger.info("Created .env.example")


def write_test_signals_py(base_dir):
    """Generate tests/test_signals.py with pytest fixture example."""
    content = '''"""
Unit tests for strategy signals.

Test indicator calculations and signal generation in isolation.
"""

import pytest
from config import Config
from strategy import Strategy
from risk_manager import RiskManager


@pytest.fixture
def config():
    """Fixture: default configuration for tests."""
    return Config(
        max_loss_per_day=5000,
        max_position_value=100000,
        max_open_positions=5,
    )


@pytest.fixture
def risk_manager(config):
    """Fixture: risk manager instance."""
    return RiskManager(config=config)


@pytest.fixture
def strategy(config, risk_manager):
    """Fixture: strategy instance."""
    return Strategy(config=config, risk_manager=risk_manager)


class TestSignalGeneration:
    """Test cases for signal generation."""

    def test_strategy_initializes(self, strategy):
        """Test that strategy initializes without errors."""
        strategy.init()
        assert strategy is not None

    def test_risk_manager_rejects_oversized_order(self, risk_manager):
        """Test that risk manager rejects oversized orders."""
        oversized_order = {
            'symbol': 'RELIANCE',
            'quantity': 1000,
            'price': 2500,  # 2.5M notional
        }
        result = risk_manager.approve(oversized_order)
        assert result is False

    def test_risk_manager_approves_normal_order(self, risk_manager):
        """Test that risk manager approves normal orders."""
        normal_order = {
            'symbol': 'RELIANCE',
            'quantity': 10,
            'price': 2500,  # 25k notional
        }
        result = risk_manager.approve(normal_order)
        assert result is True

    def test_daily_loss_limit(self, risk_manager, config):
        """Test that daily loss limit is enforced."""
        risk_manager.daily_pnl = -config.max_loss_per_day - 1
        order = {'symbol': 'RELIANCE', 'quantity': 1, 'price': 2500}
        result = risk_manager.approve(order)
        assert result is False


class TestOrderExecution:
    """Test cases for order execution flow."""

    def test_order_flow(self, strategy, risk_manager):
        """Test complete order flow: generate -> approve -> execute."""
        # TODO: Add integration test with mock broker
        pass
'''
    (base_dir / 'tests' / 'test_signals.py').write_text(content)
    logger.info("Created tests/test_signals.py")


def write_tests_init(base_dir):
    """Generate tests/__init__.py."""
    content = '"""Test suite for trading strategy."""\n'
    (base_dir / 'tests' / '__init__.py').write_text(content)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Generate a best-practice algo trading strategy skeleton'
    )
    parser.add_argument(
        'name',
        help='Strategy project name (e.g., my_strategy)'
    )
    parser.add_argument(
        '--type',
        choices=['live', 'backtest'],
        default='live',
        help='Strategy type: live (default) or backtest'
    )

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
    )

    logger.info(f"Creating strategy scaffold: {args.name}")
    logger.info(f"Type: {args.type}")

    # Create directory structure
    base_dir = scaffold_directory(args.name, args.type)

    # Generate all files
    write_main_py(base_dir, args.type)
    write_strategy_py(base_dir)
    write_risk_manager_py(base_dir)
    write_guardrails_py(base_dir)
    write_config_py(base_dir)
    write_requirements_txt(base_dir)
    write_env_example(base_dir)
    write_test_signals_py(base_dir)
    write_tests_init(base_dir)

    logger.info("")
    logger.info("=" * 60)
    logger.info(f"Strategy scaffold created: {base_dir}")
    logger.info("=" * 60)
    logger.info("Next steps:")
    logger.info(f"  1. cd {args.name}")
    logger.info("  2. pip install -r requirements.txt")
    logger.info("  3. cp .env.example .env")
    logger.info("  4. Edit config.py with your risk parameters")
    logger.info("  5. Implement signal logic in strategy.py")
    logger.info("  6. Run tests: pytest tests/")
    logger.info(f"  7. Start strategy: python main.py")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
