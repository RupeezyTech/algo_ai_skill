#!/usr/bin/env python3
"""
Strategy Scaffolder

Generates a best-practice project skeleton for algo trading strategies.
Creates directory structure and starter templates following all skill rules.

Usage:
    # Self-hosted (default) — ships login.py for the loopback SSO flow
    python scaffold_strategy.py my_strategy --type live

    # Rupeezy container platform — credentials are injected, no login.py
    python scaffold_strategy.py my_strategy --type live --deployment container

    # Backtest-only skeleton
    python scaffold_strategy.py backtest_v2 --type backtest

Output structure (live, self-hosted):
    my_strategy/
        main.py              # Wires client + VortexFeed + OrderTracker; runs strategy
        login.py             # Loopback SSO login (run once per session)
        auth.py              # Credential helpers (get_client / save_token)
        order_tracker.py     # Postback-driven order tracker (see SKILL.md Rule 9)
        strategy.py
        risk_manager.py
        guardrails.py
        config.py
        requirements.txt
        .env.example         # VORTEX_API_KEY + VORTEX_APPLICATION_ID
        tests/
            __init__.py
            test_signals.py

Output structure (live, container):
    Same as above, MINUS login.py / auth.py. main.py uses zero-arg VortexAPI()
    because the Rupeezy platform injects VORTEX_ACCESS_TOKEN at runtime.

Output structure (backtest):
    No order_tracker.py / login.py / auth.py — backtests don't connect to the
    live feed or place real orders. They read historical OHLCV and use one of
    backtesting.py / vectorbt / backtrader.
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


def write_main_py(base_dir, strategy_type, deployment):
    """Generate main.py with proper initialization.

    Live strategies wire: client → VortexFeed → OrderTracker → Strategy.
    Backtest strategies skip the feed and tracker.
    """
    is_live = strategy_type != 'backtest'

    if deployment == 'container':
        client_import = "from vortex_api import VortexAPI"
        client_setup = '''# On the Rupeezy container platform, credentials are injected at runtime
# (VORTEX_ACCESS_TOKEN is set by the platform). No login flow needed.
client = VortexAPI()'''
    else:
        client_import = "from auth import get_client"
        client_setup = '''# Load the authenticated client — reads cached .access_token.json
# (run `python login.py` once to populate it).
client = get_client()'''

    if is_live:
        live_imports = '''from vortex_api import VortexFeed
import time
from order_tracker import OrderTracker'''
        live_setup = '''# Postback-driven order tracker (see SKILL.md Critical Rule 9).
# Refreshes from client.orders() + client.trades() on every postback, with a
# 500 ms debounce so a many-fill order doesn\\'t trip the REST rate limit.
tracker = OrderTracker(client)

# Seed the cache from today\\'s existing orderbook. This marks orders that
# were already terminal before we started as "already notified", so
# on_terminal doesn\\'t fire for historical fills when we start refreshing.
# Must be called BEFORE setting on_terminal and BEFORE placing orders.
tracker.initialize()

strategy = Strategy(config=config, risk_manager=risk_manager, client=client, tracker=tracker)

# Wire the terminal callback. Strategy.on_order_terminal fires once per order
# when it reaches COMPLETED / REJECTED / CANCELLED — even if no thread is
# blocked in tracker.wait(). This is the primary order-outcome path for live
# strategies; don\\'t call tracker.wait() inside Strategy.next().
tracker.on_terminal = strategy.on_order_terminal

# Connect the WebSocket. Postbacks now flow into the tracker, which refreshes
# orderbook+tradebook and fires on_terminal as orders complete.
wire = VortexFeed(access_token=client.access_token)
wire.on_order_update = tracker.on_update   # legacy SDK property name; receives all 5 types
wire.connect(threaded=True)
time.sleep(1)  # let the connection stabilise'''
    else:
        live_imports = ''
        live_setup = '''strategy = Strategy(config=config, risk_manager=risk_manager, client=client)'''

    content = '''#!/usr/bin/env python3
"""
Main strategy entry point.

Sets up logging, timezone, WebSocket connection, and SIGTERM handler.
Initializes risk manager and runs the trading loop.
"""

import sys
import signal
import logging
from datetime import datetime
import pytz
''' + client_import + '''
''' + live_imports + '''
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

''' + client_setup + '''

config = Config()
risk_manager = RiskManager(config=config)
''' + live_setup + '''

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


def write_strategy_py(base_dir, strategy_type):
    """Generate strategy.py with Strategy class. Live mode wires OrderTracker."""
    is_live = strategy_type != 'backtest'

    if is_live:
        tracker_import = "from order_tracker import OrderTracker\n"
        tracker_arg = ", tracker: OrderTracker"
        tracker_assign = "        self.tracker = tracker\n"
        # The terminal-status callback the strategy registers via
        # tracker.on_terminal = self.on_order_terminal in main.py.
        # Fires on the OrderTracker worker thread, NOT this thread.
        terminal_method = '''
    def on_order_terminal(self, order_id: str, status: str) -> None:
        """Called once per order_id when it first reaches a terminal status.

        Runs on the OrderTracker worker thread — if you mutate strategy state
        shared with the main loop (positions, P&L, etc.), use a threading.Lock
        or queue events for next() to drain.

        Do NOT call wait() or any long REST request from here — it blocks the
        refresh worker.
        """
        order = self.tracker.order(order_id)
        # COMPLETED (from postback) and EXECUTED (from orderbook) are the same
        # state — check SUCCESS set, not the literal string.
        if status in self.tracker.SUCCESS:
            avg = self.tracker.avg_fill_price(order_id)
            qty = order.get("traded_quantity")
            side = order.get("transaction_type")
            symbol = order.get("symbol")
            logger.info(
                "FILL %s %s qty=%s avg=%.2f", side, symbol, qty, avg or 0.0
            )
            # TODO: update self.positions, self.pnl, etc.
        elif status == "REJECTED":
            # rejection_reason walks the three field names the broker uses
            # across surfaces (status_message / error_reason / message).
            logger.warning(
                "REJECTED order_id=%s reason=%s",
                order_id, self.tracker.rejection_reason(order_id),
            )
            # TODO: react — maybe retry, maybe alert, maybe halt the strategy
        elif status == "CANCELLED":
            logger.info("CANCELLED order_id=%s", order_id)
'''
    else:
        tracker_import = ""
        tracker_arg = ""
        tracker_assign = ""
        terminal_method = ""

    content = '''"""
Trading strategy logic.

The Strategy class is split into two entry points (live mode):

  - next(tick):           called on every price tick. Place orders here,
                          but NEVER block (no tracker.wait() calls).
  - on_order_terminal():  called when one of your orders reaches a terminal
                          status (COMPLETED / REJECTED / CANCELLED). Update
                          self.positions / self.pnl from here.

Both entry points operate on shared self.* state. on_order_terminal runs on
the OrderTracker worker thread, so synchronise (lock or queue) if you mutate
state read by next().

All orders go through risk_manager.approve() before execution.
"""

import logging
from typing import Optional
from vortex_api import VortexAPI
''' + tracker_import + '''from config import Config
from risk_manager import RiskManager

logger = logging.getLogger(__name__)


class Strategy:
    """Base strategy implementation."""

    def __init__(self, config: Config, risk_manager: RiskManager, client: VortexAPI''' + tracker_arg + '''):
        """Initialize strategy with configuration, risk controls, and broker client."""
        self.config = config
        self.risk_manager = risk_manager
        self.client = client
''' + tracker_assign + '''        self.positions = {}

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

        Place orders here if signals fire — but DO NOT call self.tracker.wait()
        from this method. Order outcomes arrive asynchronously via
        self.on_order_terminal. Read self.tracker.status(order_id) /
        self.tracker.order(order_id) on subsequent ticks if you need current
        state of an in-flight order.
        """
        # TODO: Generate signals based on indicators
        # TODO: Check if we should enter/exit positions
        # TODO: Place orders through risk_manager
        pass
''' + terminal_method + '''
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
    """Generate config.py with risk parameters.

    Calls load_dotenv() at module top so any caller importing config.py
    (or modules that depend on it) gets .env-populated env vars regardless
    of import order. Without this, auth.py / login.py and any module that
    reads VORTEX_API_KEY at import time would race load_dotenv() and fail
    silently with empty creds. The PyPI package name is `python-dotenv`
    (NOT `dotenv` — that's a different, unrelated package).
    """
    content = '''"""
Configuration and defaults.

All strategy and risk parameters defined in one place.

Imports .env at module top so any downstream module reading os.environ
at import time sees populated values, regardless of import order.

SDK enum defaults (default_product, default_variety, default_validity,
default_transaction_type) are stored as `Vc.*` enum INSTANCES, not as
their string values. The Vortex SDK runtime-typechecks these arguments
via `isinstance` and rejects bare strings — e.g. passing "INTRADAY"
where `Vc.ProductTypes.INTRADAY` is expected raises
`TypeError: product must be of type ProductTypes`, even though the
enum\\'s `.value` IS "INTRADAY". The bug is silent until the first live
order. Storing the enum here makes strategy code that writes
`client.place_order(product=config.default_product, ...)` correct by
construction.
"""

from dataclasses import dataclass

# Load .env BEFORE anything else reads os.environ. python-dotenv is harmless
# on container deployments (no .env present; load_dotenv silently does nothing).
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv isn\\'t installed (e.g., container build with no .env file).
    # That\\'s fine — env vars are injected by the platform.
    pass

from vortex_api import Constants as Vc


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

    # Order parameters — Vc.* ENUM INSTANCES, not strings (see module docstring).
    # Pass these directly to client.place_order / client.get_order_margin.
    default_product:    Vc.ProductTypes     = Vc.ProductTypes.DELIVERY
    default_variety:    Vc.VarietyTypes     = Vc.VarietyTypes.REGULAR_LIMIT_ORDER
    default_validity:   Vc.ValidityTypes    = Vc.ValidityTypes.FULL_DAY
    default_transaction: Vc.TransactionSides = Vc.TransactionSides.BUY
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


def write_requirements_txt(base_dir, deployment):
    """Generate requirements.txt.

    python-dotenv is included for both deployments: self-hosted needs it to
    read .env; container doesn\\'t need .env but config.py has an
    `try: from dotenv import load_dotenv` guard so the import being present
    is harmless and keeps the import-order story identical across modes.
    """
    content = '''# Core trading API — ticker-first surface (client.instruments, place_order(ticker=...))
# 2.1.8 is the minimum that accepts ticker= on place_order / historical_candles /
# get_order_margin and supports client.instruments. Newer 2.1.x releases also
# require (limit, offset) positional args on client.orders() / client.trades();
# OrderTracker handles both signatures via TypeError fallback.
vortex-api>=2.1.8

# Loads VORTEX_API_KEY / VORTEX_APPLICATION_ID from .env. The PyPI package is
# `python-dotenv` (the import name is `dotenv`); a separate unrelated package
# `dotenv` exists on PyPI — DO NOT depend on that one.
python-dotenv>=1.0.0

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


def write_env_example(base_dir, deployment):
    """Generate .env.example template.

    Self-hosted strategies need VORTEX_API_KEY + VORTEX_APPLICATION_ID so login.py
    can run the OAuth flow. Container deployments don't need .env at all — Rupeezy
    injects everything at runtime — but we still ship the file for tunables like
    strategy parameters and logging.
    """
    if deployment == 'container':
        content = '''# Copy this file to .env and fill in any strategy-specific tunables.
# Never commit .env to version control.

# IMPORTANT: On the Rupeezy container platform, broker credentials
# (VORTEX_API_KEY, VORTEX_APPLICATION_ID, VORTEX_ACCESS_TOKEN) are injected
# automatically by the platform. DO NOT set them here — putting your own keys
# in .env will be ignored at best and conflict with the runtime values at worst.

# Strategy configuration
STRATEGY_NAME=my_strategy
STRATEGY_TYPE=live

# Logging — container platform aggregates these to the platform dashboard
LOG_LEVEL=INFO
'''
    else:
        content = '''# Copy this file to .env and fill in your credentials.
# Never commit .env to version control.

# Persistent Rupeezy credentials — from the API Center at https://vortex.rupeezy.in
# Get these once; they don't expire.
VORTEX_API_KEY=your_api_key_here
VORTEX_APPLICATION_ID=your_application_id_here

# DO NOT add VORTEX_ACCESS_TOKEN here. The access_token is short-lived (~24h)
# and is fetched via `python login.py`, which caches it to .access_token.json.
# Putting an access_token in .env will make it stale after a day.

# Strategy configuration
STRATEGY_NAME=my_strategy
STRATEGY_TYPE=live

# Logging
LOG_LEVEL=INFO
LOG_FILE=strategy.log
'''
    (base_dir / '.env.example').write_text(content)
    logger.info("Created .env.example")


def write_auth_py(base_dir):
    """Generate auth.py with VortexAPI client + token helpers."""
    content = '''"""
Credential helpers — keep auth concerns out of strategy code.

Loads VORTEX_API_KEY and VORTEX_APPLICATION_ID from .env (the persistent
credentials you get from the Rupeezy API Center). The access_token is cached
to .access_token.json after `python login.py`, so subsequent script runs are
non-interactive until the token expires (~24h).

Important — auth_token vs access_token:
    auth_token   = the short-lived `?auth=...` query param that lands on
                   the OAuth callback URL. NOT what you want to save.
    access_token = the long-lived bearer token returned by
                   client.exchange_token(auth_token). THIS is what you save.

login.py handles the exchange so you never have to think about the difference.
"""

import json
import os
from pathlib import Path

# config.py calls load_dotenv() at its module top, so importing it first
# guarantees .env is populated before we read os.environ — regardless of
# whether the caller imports auth.py or config.py first.
import config  # noqa: F401  (imported for its load_dotenv side-effect)

from vortex_api import VortexAPI

API_KEY = os.environ["VORTEX_API_KEY"]
APPLICATION_ID = os.environ["VORTEX_APPLICATION_ID"]
TOKEN_FILE = Path(__file__).parent / ".access_token.json"


def get_client() -> VortexAPI:
    """Return a VortexAPI client with the cached access_token loaded.

    Raises a clear error if the cache is missing — run `python login.py` first.
    """
    client = VortexAPI(API_KEY, APPLICATION_ID)
    if not TOKEN_FILE.exists():
        raise RuntimeError(
            "No cached access_token found. "
            "Run `python login.py` first to authenticate."
        )
    client.access_token = json.loads(TOKEN_FILE.read_text())["access_token"]
    return client


def save_token(access_token: str) -> None:
    """Cache an access_token to disk so future runs don't need to re-login."""
    TOKEN_FILE.write_text(json.dumps({"access_token": access_token}))
    print(f"Token cached to {TOKEN_FILE}")
'''
    (base_dir / 'auth.py').write_text(content)
    logger.info("Created auth.py")


def write_login_py(base_dir):
    """Generate login.py — loopback SSO callback server."""
    content = '''#!/usr/bin/env python3
"""
SSO login — hands-free, no copy/paste.

Spins up a tiny local HTTP server on 127.0.0.1:8765/callback, opens the SSO
URL in your browser, catches the redirect, exchanges the auth_token for an
access_token, and caches it to .access_token.json.

One-time setup: in your Rupeezy API Center app config, set the redirect URL to
    http://127.0.0.1:8765/callback

After that, just run `python login.py` whenever your token expires (~24h).
Strategy code reads the cached token via auth.get_client().
"""

import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from vortex_api import VortexAPI

from auth import API_KEY, APPLICATION_ID, save_token

HOST, PORT = "127.0.0.1", 8765
PATH = "/callback"


class CallbackHandler(BaseHTTPRequestHandler):
    """One-shot handler that captures the ?auth=... query param."""

    auth_token = None

    def do_GET(self):  # noqa: N802 (stdlib signature)
        parsed = urlparse(self.path)
        if parsed.path != PATH:
            self.send_response(404)
            self.end_headers()
            return

        params = parse_qs(parsed.query)
        token = params.get("auth", [None])[0]

        if token:
            CallbackHandler.auth_token = token
            body = b"<h2>Login received. You can close this tab.</h2>"
            self.send_response(200)
        else:
            body = b"<h2>Missing auth in callback.</h2>"
            self.send_response(400)

        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):  # silence default access logs
        pass


def wait_for_auth_token() -> str:
    """Block until the callback fires, then return the auth_token."""
    server = HTTPServer((HOST, PORT), CallbackHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        while CallbackHandler.auth_token is None:
            thread.join(0.2)
    finally:
        server.shutdown()
    return CallbackHandler.auth_token


def main() -> None:
    client = VortexAPI(API_KEY, APPLICATION_ID)

    url = client.login_url(callback_param="strategy-login")
    print(f"Listening on http://{HOST}:{PORT}{PATH}")
    print(f"Opening browser: {url}\\n")
    webbrowser.open(url)

    auth_token = wait_for_auth_token()
    print("Received auth_token, exchanging for access_token...")

    client.exchange_token(auth_token)
    save_token(client.access_token)
    print("\\nLogged in. You can now run `python main.py`.")


if __name__ == "__main__":
    main()
'''
    (base_dir / 'login.py').write_text(content)
    logger.info("Created login.py")


def write_order_tracker_py(base_dir):
    """Generate order_tracker.py — postback-driven OrderTracker class.

    Same pattern documented in references/code-quality.md. Live strategies
    instantiate this, wire `tracker.on_update` to `wire.on_order_update`, and
    call `tracker.wait(order_id)` instead of polling.
    """
    content = '''"""
Postback-driven order tracker. See SKILL.md Critical Rule 9 and
references/code-quality.md for the full design rationale.

The Vortex SDK\\'s `VortexFeed.on_order_update` callback fires for FIVE
envelope types (order, trade, sl_trigger, gtt_order, position_conversion).
Each one is treated as a SIGNAL that something changed for an order_id; we
never trust `msg["data"]` as the new state. Instead, we refresh from
`client.orders()` and `client.trades()` — the canonical source of truth.

Coalescing: first postback starts a 500 ms debounce; further postbacks
within the window accumulate for free. One REST refresh covers every dirty
order_id. After the refresh, if more postbacks arrived during the REST
calls, we refresh again immediately (no extra debounce). Prevents a
many-fill order from melting the REST rate limit.

Threading note: `on_terminal` fires on the refresh worker thread, NOT the
strategy main thread. If your handler mutates shared state (positions, P&L,
etc.), use a lock or queue events for the main loop to drain.
"""

import logging
import threading
import time
from typing import Callable, Optional


logger = logging.getLogger(__name__)


class OrderTracker:
    """Split-authority order tracker.

    - Postback `data.status` is authoritative for STATUS TRANSITIONS (REST
      orderbook can lag postbacks by tens of seconds on the same order).
    - REST orderbook / tradebook are authoritative for FILL QUANTITIES and
      avg traded price.
    - Once terminal is recorded, a later non-terminal REST row must NOT
      overwrite it (downgrade guard).
    - Terminal-status detection uses substring match — broker may decorate
      canonical tokens ("REJECTED_BY_RMS", "AMO_CANCELLED").
    """

    # Substring tokens. Broker may emit decorated forms; we normalise.
    _TERMINAL_TOKENS = ("REJECTED", "CANCELLED", "EXECUTED", "COMPLETED")

    TERMINAL = {"COMPLETED", "EXECUTED", "REJECTED", "CANCELLED"}
    SUCCESS = {"COMPLETED", "EXECUTED"}
    REFRESH_ON_TYPES = {
        "order", "trade", "sl_trigger", "gtt_order", "position_conversion",
    }

    # REST page size; raise if your account exceeds this many orders/day.
    _PAGE_LIMIT = 500

    def __init__(self, client, debounce_seconds: float = 0.5):
        self._client = client
        self._debounce = debounce_seconds
        self._lock = threading.Lock()
        self._dirty = set()
        self._worker_running = False
        self._closed = False
        self._orders = {}             # order_id -> merged postback+REST row
        self._trades = {}             # order_id -> list of tradebook rows
        self._events = {}             # order_id -> threading.Event for wait()
        self._notified_terminal = set()

        # callable(order_id: str, status: str) -> None.
        # Set AFTER initialize() and BEFORE placing orders.
        self.on_terminal: Optional[Callable[[str, str], None]] = None

    # ---- status / envelope helpers ----

    @classmethod
    def _terminal_token(cls, status):
        """Substring-match a status string against canonical terminal tokens."""
        if not status:
            return None
        s = status.upper()
        for tok in cls._TERMINAL_TOKENS:
            if tok in s:
                return tok
        return None

    @classmethod
    def _normalise_row(cls, row):
        """Rewrite vendor-decorated terminal status to its canonical token;
        preserve the original verbose form in `raw_status`.
        Returns (row, terminal_token_or_None)."""
        raw = row.get("status") or ""
        tok = cls._terminal_token(raw)
        if tok and raw != tok:
            return {**row, "status": tok, "raw_status": raw}, tok
        return row, tok

    @staticmethod
    def _orders_rows(book):
        """Envelope key varies by endpoint:
            client.orders()   -> {"orders": [...]}
            client.holdings() -> {"data":   [...]}
        Try the common keys and return the first list found."""
        if not isinstance(book, dict):
            return []
        for key in ("orders", "data", "orderBook", "orderbook"):
            v = book.get(key)
            if isinstance(v, list):
                return v
        return []

    @staticmethod
    def _trades_rows(trades):
        if not isinstance(trades, dict):
            return []
        for key in ("trades", "data", "tradeBook", "tradebook"):
            v = trades.get(key)
            if isinstance(v, list):
                return v
        return []

    def _fetch_orderbook(self):
        """Current vortex-api requires client.orders(limit, offset); fall back
        to the no-args form for older releases."""
        try:
            return self._client.orders(limit=self._PAGE_LIMIT, offset=0) or {}
        except TypeError:
            return self._client.orders() or {}

    def _fetch_tradebook(self):
        try:
            return self._client.trades(limit=self._PAGE_LIMIT, offset=0) or {}
        except TypeError:
            return self._client.trades() or {}

    @staticmethod
    def _rejection_reason(row):
        """Rejection-reason field name varies by surface:
            postback envelope    -> data.status_message
            REST orderbook row   -> error_reason
            place_order response -> message
        Returns first non-empty value."""
        return (
            row.get("status_message")
            or row.get("error_reason")
            or row.get("message")
        )

    # ---- one-time startup seeding ----

    def initialize(self):
        """Seed cache from today\\'s orderbook + tradebook WITHOUT firing
        on_terminal for already-terminal orders. Call ONCE at startup,
        BEFORE setting on_terminal and BEFORE placing orders."""
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
            per_order = {}
            for tr in self._trades_rows(trades):
                oid = tr.get("order_id")
                if oid:
                    per_order.setdefault(oid, []).append(tr)
            for oid, lst in per_order.items():
                self._trades[oid] = lst

    # ---- postback entry point (WS reader thread) ----

    def on_update(self, ws, msg):
        """Wire to wire.on_order_update. Must NOT block.

        Fast-path: terminal `order` postbacks are mirrored into the cache
        and fire on_terminal synchronously, BEFORE the REST refresh runs.
        REST can be tens of seconds behind on rejections — waiting for it
        would silently miss real terminal transitions.
        """
        if msg.get("type") not in self.REFRESH_ON_TYPES:
            return
        payload = msg.get("data") or {}
        order_id = payload.get("order_id")
        if not order_id:
            return

        if msg.get("type") == "order":
            normalised, tok = self._normalise_row(payload)
            if tok:
                self._record_terminal_from_postback(order_id, normalised, tok)

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

    def _record_terminal_from_postback(self, order_id, row, token):
        """Merge terminal postback into cache; fire wait Events + on_terminal.
        Runs on the WS reader thread — keep it fast. Idempotent."""
        fire = None
        with self._lock:
            if order_id in self._notified_terminal:
                return
            existing = self._orders.get(order_id, {})
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

    # ---- public read API ----

    def wait(self, order_id, timeout):
        """Block until terminal or `timeout` seconds. `timeout` is REQUIRED;
        pass float("inf") to wait forever.

        Script / test primitive. In a live strategy main loop use on_terminal.
        After a timeout, the order may still be working at the broker."""
        with self._lock:
            order = self._orders.get(order_id)
            if order and order.get("status") in self.TERMINAL:
                return order["status"] in self.SUCCESS
            ev = self._events.setdefault(order_id, threading.Event())
        ev.wait(timeout)
        with self._lock:
            return (self._orders.get(order_id) or {}).get("status") in self.SUCCESS

    def cancel_and_wait(self, order_id, timeout):
        """Cancel and block until terminal confirmed. Returns the actual
        terminal status — could be COMPLETED/EXECUTED if a fill races the
        cancel. ALWAYS check before placing a replacement."""
        cur = self.status(order_id)
        if cur in self.TERMINAL:
            return cur
        try:
            self._client.cancel_order(order_id=order_id)
        except Exception as exc:
            logger.info("cancel_order(%s) raised: %s", order_id, exc)
        self.wait(order_id, timeout=timeout)
        return self.status(order_id)

    def status(self, order_id):
        with self._lock:
            return (self._orders.get(order_id) or {}).get("status")

    def order(self, order_id):
        with self._lock:
            return dict(self._orders.get(order_id, {}))

    def fills(self, order_id):
        with self._lock:
            return list(self._trades.get(order_id, []))

    def avg_fill_price(self, order_id):
        """Orderbook traded_price (qty-weighted) preferred; fall back to
        recomputing from tradebook rows. Note: orderbook uses traded_*,
        tradebook uses trade_* — different field names for the same concept."""
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
            (t.get("trade_price") or 0) * (t.get("trade_quantity") or 0) for t in trades
        )
        return notional / qty

    def rejection_reason(self, order_id):
        """Best-available rejection reason string. Field name varies by
        surface — see _rejection_reason()."""
        with self._lock:
            row = self._orders.get(order_id, {})
        return self._rejection_reason(row)

    def close(self):
        with self._lock:
            self._closed = True

    # ---- worker ----

    def _refresh_loop(self):
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

    def _apply(self, book, trades):
        fire = []
        with self._lock:
            for raw_row in self._orders_rows(book):
                oid = raw_row.get("order_id")
                if not oid:
                    continue
                row, tok = self._normalise_row(raw_row)

                # DOWNGRADE GUARD: if a postback already established
                # terminal and REST is still lagging (non-terminal), merge
                # fill data but keep the terminal status.
                if oid in self._notified_terminal and tok is None:
                    existing = self._orders.get(oid, {})
                    fields_without_status = {
                        k: v for k, v in row.items() if k != "status"
                    }
                    self._orders[oid] = {**existing, **fields_without_status}
                    continue

                existing = self._orders.get(oid, {})
                self._orders[oid] = {**existing, **row}

                if tok and oid not in self._notified_terminal:
                    self._notified_terminal.add(oid)
                    ev = self._events.get(oid)
                    if ev is not None:
                        ev.set()
                    fire.append((oid, tok))

            per_order = {}
            for tr in self._trades_rows(trades):
                oid = tr.get("order_id")
                if oid:
                    per_order.setdefault(oid, []).append(tr)
            for oid, lst in per_order.items():
                self._trades[oid] = lst

        # Outside lock so user code in on_terminal can\\'t deadlock us.
        handler = self.on_terminal
        if handler is not None:
            for oid, status in fire:
                try:
                    handler(oid, status)
                except Exception:
                    logger.exception("on_terminal handler raised for %s", oid)
'''
    (base_dir / 'order_tracker.py').write_text(content)
    logger.info("Created order_tracker.py")


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
    parser.add_argument(
        '--deployment',
        choices=['self-hosted', 'container'],
        default='self-hosted',
        help=(
            'Where this strategy will run: '
            '"self-hosted" (default) ships login.py + auth.py for the loopback SSO flow; '
            '"container" targets the Rupeezy platform (credentials injected, no login flow).'
        ),
    )

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
    )

    logger.info(f"Creating strategy scaffold: {args.name}")
    logger.info(f"Type:       {args.type}")
    logger.info(f"Deployment: {args.deployment}")

    # Create directory structure
    base_dir = scaffold_directory(args.name, args.type)

    # Generate all files. login.py and auth.py are self-hosted only — the
    # container platform injects credentials and has no browser/disk for the
    # OAuth loopback dance. order_tracker.py is live only — backtests don't
    # connect to the live feed or place real orders.
    write_main_py(base_dir, args.type, args.deployment)
    if args.deployment == 'self-hosted':
        write_auth_py(base_dir)
        write_login_py(base_dir)
    if args.type != 'backtest':
        write_order_tracker_py(base_dir)
    write_strategy_py(base_dir, args.type)
    write_risk_manager_py(base_dir)
    write_guardrails_py(base_dir)
    write_config_py(base_dir)
    write_requirements_txt(base_dir, args.deployment)
    write_env_example(base_dir, args.deployment)
    write_test_signals_py(base_dir)
    write_tests_init(base_dir)

    logger.info("")
    logger.info("=" * 60)
    logger.info(f"Strategy scaffold created: {base_dir}")
    logger.info("=" * 60)
    logger.info("Next steps:")
    logger.info(f"  1. cd {args.name}")
    logger.info("  2. pip install -r requirements.txt")
    if args.deployment == 'self-hosted':
        logger.info("  3. cp .env.example .env  # fill in VORTEX_API_KEY + VORTEX_APPLICATION_ID")
        logger.info("  4. In the Rupeezy API Center, set your app's redirect URL to:")
        logger.info("       http://127.0.0.1:8765/callback")
        logger.info("  5. python login.py  # one-time SSO flow, caches access_token to disk")
        logger.info("  6. Edit config.py with your risk parameters")
        logger.info("  7. Implement signal logic in strategy.py")
        logger.info("  8. Run tests: pytest tests/")
        logger.info("  9. Start strategy: python main.py")
    else:
        logger.info("  3. cp .env.example .env  # strategy tunables only (NOT broker credentials)")
        logger.info("  4. Edit config.py with your risk parameters")
        logger.info("  5. Implement signal logic in strategy.py")
        logger.info("  6. Run tests: pytest tests/")
        logger.info("  7. Zip the project (main.py + requirements.txt at root) and upload")
        logger.info("       via the Rupeezy MCP `create_strategy` / `deploy_strategy` tools.")
        logger.info("       The platform injects VORTEX_ACCESS_TOKEN automatically — no login needed.")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
