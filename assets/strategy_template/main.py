"""
Main strategy entry point with graceful shutdown, logging, and IST timezone support.

This module initializes the trading strategy, sets up signal handlers for graceful shutdown,
configures logging with IST timestamps, and orchestrates the overall strategy lifecycle.
"""

import signal
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Optional

import pytz

from config import Config
from strategy import Strategy
from risk_manager import RiskManager
from guardrails import CircuitBreaker


# Configure IST timezone
IST = pytz.timezone("Asia/Kolkata")

# Configure logging with IST timestamps
class ISTFormatter(logging.Formatter):
    """Custom formatter to use IST timestamps in logs."""

    def formatTime(self, record, datefmt=None):
        """Format timestamp in IST."""
        ct = datetime.fromtimestamp(record.created, tz=IST)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            t = ct.strftime("%Y-%m-%d %H:%M:%S")
            s = f"{t}.{int(ct.microsecond / 1000):03d}"
        return s


def setup_logging(config: Config) -> logging.Logger:
    """
    Set up logging with both file and console handlers, using IST timestamps.

    Args:
        config: Configuration object containing log settings.

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(getattr(logging, config.log_level))

    # Create formatters
    formatter = ISTFormatter(
        "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, config.log_level))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    log_dir = Path(config.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"strategy_{datetime.now(tz=IST).strftime('%Y%m%d_%H%M%S')}.log"

    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setLevel(getattr(logging, config.log_level))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.info(f"Logging initialized. Log file: {log_file}")
    return logger


class StrategyRunner:
    """Manages strategy lifecycle including initialization, execution, and graceful shutdown."""

    def __init__(self, config: Config):
        """
        Initialize the strategy runner.

        Args:
            config: Configuration object containing strategy and risk parameters.
        """
        self.config = config
        self.logger = setup_logging(config)
        self.strategy: Optional[Strategy] = None
        self.running = False

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """
        Handle shutdown signals (SIGTERM, SIGINT) gracefully.

        Args:
            signum: Signal number.
            frame: Current stack frame.
        """
        self.logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
        self.running = False
        if self.strategy:
            self.strategy.shutdown()
        self.logger.info("Strategy shutdown complete.")
        exit(0)

    def run(self):
        """
        Initialize and run the strategy.

        Raises:
            ValueError: If configuration validation fails.
        """
        try:
            # Validate configuration
            self.config.validate()
            self.logger.info("Configuration validated successfully.")

            # Initialize risk manager and circuit breaker
            risk_manager = RiskManager(self.config)
            circuit_breaker = CircuitBreaker(self.config)
            self.logger.info("Risk manager and circuit breaker initialized.")

            # Initialize strategy
            self.strategy = Strategy(self.config, risk_manager, circuit_breaker)
            self.logger.info("Strategy initialized.")

            # Run strategy
            self.running = True
            self.logger.info("Starting strategy execution...")
            self.strategy.run()

        except Exception as e:
            self.logger.error(f"Strategy execution failed: {e}", exc_info=True)
            raise


def main():
    """Main entry point for the strategy."""
    # TODO: Load configuration from environment or config file
    config = Config()

    runner = StrategyRunner(config)
    runner.run()


if __name__ == "__main__":
    main()
