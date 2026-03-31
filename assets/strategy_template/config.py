"""
Configuration module for strategy parameters.

This module contains the Config dataclass which holds all strategy parameters
including risk limits, market parameters, and backtest settings. Uses IST timezone.
"""

import os
from dataclasses import dataclass, field
from datetime import time
from typing import Optional

import pytz


IST = pytz.timezone("Asia/Kolkata")


@dataclass
class Config:
    """
    Central configuration for the trading strategy.

    Contains risk parameters, market schedule, backtest settings, and logging configuration.
    """

    # Strategy identification
    strategy_name: str = "Indian Algo Trading Strategy"
    strategy_type: str = "Mean Reversion"

    # Risk parameters
    max_loss_per_day: float = 5000.0  # Maximum daily loss in rupees
    max_position_value: float = 100000.0  # Maximum single position value in rupees
    max_open_positions: int = 5  # Maximum number of simultaneous open positions

    # Market parameters (all times in IST)
    exchange: str = "NSE"  # NSE or BSE
    market_open_time: time = field(default_factory=lambda: time(9, 15))  # 9:15 AM IST
    market_close_time: time = field(default_factory=lambda: time(15, 30))  # 3:30 PM IST
    symbols: list = field(default_factory=lambda: ["RELIANCE", "TCS", "INFY"])

    # Backtest parameters
    backtest_start_date: str = "2023-01-01"
    backtest_end_date: str = "2023-12-31"
    backtest_initial_capital: float = 500000.0  # 5 lakh initial capital

    # Data parameters
    data_feed: str = "vortex-api"  # Data provider
    market_data_path: Optional[str] = None  # Path to historical data if using file-based
    candle_interval: str = "1"  # Candle interval in minutes

    # Logging parameters
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    log_dir: str = "./logs"

    # Broker/API parameters (loaded from environment)
    broker_api_key: Optional[str] = field(default_factory=lambda: os.getenv("BROKER_API_KEY"))
    broker_api_secret: Optional[str] = field(
        default_factory=lambda: os.getenv("BROKER_API_SECRET")
    )
    broker_name: str = "Rupeezy"

    # Feature flags
    enable_backtest: bool = False
    enable_paper_trading: bool = True
    enable_live_trading: bool = False

    def validate(self) -> None:
        """
        Validate configuration parameters.

        Raises:
            ValueError: If configuration is invalid.
        """
        # Validate risk parameters
        if self.max_loss_per_day <= 0:
            raise ValueError("max_loss_per_day must be positive")

        if self.max_position_value <= 0:
            raise ValueError("max_position_value must be positive")

        if self.max_open_positions <= 0:
            raise ValueError("max_open_positions must be positive")

        # Validate market hours
        if self.market_open_time >= self.market_close_time:
            raise ValueError("market_open_time must be before market_close_time")

        # Validate exchange
        if self.exchange not in ["NSE", "BSE", "MCX"]:
            raise ValueError(f"Invalid exchange: {self.exchange}")

        # Validate symbols list
        if not self.symbols or len(self.symbols) == 0:
            raise ValueError("symbols list cannot be empty")

        # Validate backtest parameters
        if self.backtest_initial_capital <= 0:
            raise ValueError("backtest_initial_capital must be positive")

        # Validate candle interval
        try:
            interval_int = int(self.candle_interval)
            if interval_int <= 0:
                raise ValueError("candle_interval must be positive")
        except ValueError:
            raise ValueError("candle_interval must be a valid integer")

        # Validate logging level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level not in valid_log_levels:
            raise ValueError(f"Invalid log_level: {self.log_level}")

        # Warn if live trading is enabled without proper setup
        if self.enable_live_trading and not (
            self.broker_api_key and self.broker_api_secret
        ):
            raise ValueError(
                "Live trading enabled but broker credentials not configured. "
                "Set BROKER_API_KEY and BROKER_API_SECRET environment variables."
            )

    @classmethod
    def from_env(cls) -> "Config":
        """
        Create Config instance from environment variables.

        Environment variables:
        - STRATEGY_NAME
        - MAX_LOSS_PER_DAY
        - MAX_POSITION_VALUE
        - MAX_OPEN_POSITIONS
        - EXCHANGE
        - SYMBOLS (comma-separated)
        - LOG_LEVEL
        - ENABLE_LIVE_TRADING
        - BROKER_API_KEY
        - BROKER_API_SECRET

        Returns:
            Config instance with values from environment.
        """
        symbols = os.getenv("SYMBOLS", "RELIANCE,TCS,INFY").split(",")
        symbols = [s.strip() for s in symbols]

        return cls(
            strategy_name=os.getenv("STRATEGY_NAME", cls.strategy_name),
            max_loss_per_day=float(
                os.getenv("MAX_LOSS_PER_DAY", cls.max_loss_per_day)
            ),
            max_position_value=float(
                os.getenv("MAX_POSITION_VALUE", cls.max_position_value)
            ),
            max_open_positions=int(
                os.getenv("MAX_OPEN_POSITIONS", cls.max_open_positions)
            ),
            exchange=os.getenv("EXCHANGE", cls.exchange),
            symbols=symbols,
            log_level=os.getenv("LOG_LEVEL", cls.log_level),
            enable_live_trading=os.getenv(
                "ENABLE_LIVE_TRADING", "false"
            ).lower() == "true",
        )

    def get_market_hours(self) -> tuple:
        """
        Get market open and close times for IST.

        Returns:
            Tuple of (open_time, close_time) as time objects.
        """
        return (self.market_open_time, self.market_close_time)

    def __str__(self) -> str:
        """Return string representation of config."""
        return (
            f"Config(strategy={self.strategy_name}, "
            f"max_loss={self.max_loss_per_day}, "
            f"max_position={self.max_position_value}, "
            f"max_positions={self.max_open_positions}, "
            f"exchange={self.exchange}, "
            f"symbols={self.symbols}, "
            f"live_trading={self.enable_live_trading})"
        )
