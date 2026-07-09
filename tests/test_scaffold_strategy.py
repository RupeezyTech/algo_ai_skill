"""
Tests for scaffold_strategy.py -- verify BUG-A/B/C/D fixes in the code it
GENERATES (not in this test file itself).

Both scaffold types are generated once (module-scoped fixture) via the same
CLI invocation a user would run, into a pytest tmp_path -- which pytest
always places under the system temp directory, i.e. outside this repo
worktree, so nothing generated here gets committed.

BUG-C/BUG-D tests exec the generated risk_manager.py / guardrails.py source
directly (with a stubbed `config` module for risk_manager.py) instead of
importing the generated project as real modules. This deliberately avoids
needing the vortex-api package (not installed, and not required to be) and
avoids a separate, pre-existing, out-of-scope issue: generated files that
carry the scaffolder's non-ASCII punctuation (em dashes) fail to import via
Python's normal UTF-8 source decoding on a Windows box whose default text
encoding isn't UTF-8, because Path.write_text() defaults to the locale
encoding. Reading the source with matching-default read_text() and exec()-ing
the decoded string sidesteps that entirely, so these tests probe exactly
BUG-A/B/C/D, nothing else.
"""

import ast
import logging
import subprocess
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCAFFOLD_SCRIPT = (
    REPO_ROOT
    / "plugins"
    / "indian-algo-trading"
    / "skills"
    / "indian-algo-trading"
    / "scripts"
    / "scaffold_strategy.py"
)

PYTHON = sys.executable


def _scaffold(cwd: Path, name: str, strategy_type: str) -> Path:
    """Run the scaffolder exactly as a user would from the CLI."""
    result = subprocess.run(
        [PYTHON, str(SCAFFOLD_SCRIPT), name, "--type", strategy_type],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return cwd / name


@pytest.fixture(scope="module")
def scaffolded(tmp_path_factory):
    """Scaffold one backtest and one live project into a tmp dir outside
    the repo worktree (tmp_path_factory always resolves under the system
    temp directory)."""
    base = tmp_path_factory.mktemp("scaffold-verify")
    return {
        "backtest": _scaffold(base, "t1", "backtest"),
        "live": _scaffold(base, "t2", "live"),
    }


def _exec_generated(path: Path, module_name: str, stub_modules: dict):
    """Exec a generated file's source in an isolated namespace, with fake
    modules installed in sys.modules for the duration (restored after)."""
    source = path.read_text()
    code = compile(source, str(path), "exec")
    namespace = {"__name__": module_name, "__file__": str(path)}

    saved = {name: sys.modules.get(name) for name in stub_modules}
    sys.modules.update(stub_modules)
    try:
        exec(code, namespace)
    finally:
        for name, mod in saved.items():
            if mod is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = mod

    return namespace


# ---------------------------------------------------------------------------
# BUG-A: generated main.py must resolve backtest-vs-live at GENERATION time
# and call strategy.backtest()/strategy.run() directly -- no runtime
# `if "..." in BACKTEST:` membership test against a bare, undefined name.
# ---------------------------------------------------------------------------


class TestBugAMainPy:
    @pytest.mark.parametrize("kind", ["backtest", "live"])
    def test_no_bare_backtest_or_live_name_nodes(self, scaffolded, kind):
        main_py = scaffolded[kind] / "main.py"
        tree = ast.parse(main_py.read_text(), filename=str(main_py))
        bare_names = {
            node.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Name) and node.id in ("BACKTEST", "LIVE")
        }
        assert bare_names == set()

    @pytest.mark.parametrize("kind", ["backtest", "live"])
    def test_main_py_compiles(self, scaffolded, kind):
        main_py = scaffolded[kind] / "main.py"
        result = subprocess.run(
            [PYTHON, "-m", "py_compile", str(main_py)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr

    def test_backtest_main_calls_backtest_only(self, scaffolded):
        source = (scaffolded["backtest"] / "main.py").read_text()
        assert "strategy.backtest()" in source
        assert "strategy.run()" not in source

    def test_live_main_calls_run_only(self, scaffolded):
        source = (scaffolded["live"] / "main.py").read_text()
        assert "strategy.run()" in source
        assert "strategy.backtest()" not in source


# ---------------------------------------------------------------------------
# BUG-B: the generated tests/test_signals.py `strategy` fixture must call
# Strategy(...) with kwargs that are a subset of the generated
# Strategy.__init__ params, for both scaffold types.
# ---------------------------------------------------------------------------


def _get_init_params(strategy_py: Path):
    tree = ast.parse(strategy_py.read_text(), filename=str(strategy_py))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Strategy":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                    args = item.args
                    names = [a.arg for a in args.args if a.arg != "self"]
                    names += [a.arg for a in args.kwonlyargs]
                    return names
    raise AssertionError(f"Strategy.__init__ not found in {strategy_py}")


def _get_fixture_kwargs(test_signals_py: Path):
    tree = ast.parse(test_signals_py.read_text(), filename=str(test_signals_py))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "strategy":
            for call in ast.walk(node):
                if (
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Name)
                    and call.func.id == "Strategy"
                ):
                    return [kw.arg for kw in call.keywords]
    raise AssertionError(f"strategy fixture Strategy(...) call not found in {test_signals_py}")


class TestBugBFixtureSignature:
    @pytest.mark.parametrize("kind", ["backtest", "live"])
    def test_fixture_kwargs_subset_of_init_params(self, scaffolded, kind):
        init_params = set(_get_init_params(scaffolded[kind] / "strategy.py"))
        fixture_kwargs = set(
            _get_fixture_kwargs(scaffolded[kind] / "tests" / "test_signals.py")
        )

        assert fixture_kwargs, "fixture should pass at least one kwarg"
        assert fixture_kwargs <= init_params, (
            f"[{kind}] fixture kwargs {fixture_kwargs} are not a subset of "
            f"Strategy.__init__ params {init_params}"
        )

    def test_backtest_init_requires_client_not_tracker(self, scaffolded):
        params = set(_get_init_params(scaffolded["backtest"] / "strategy.py"))
        assert "client" in params
        assert "tracker" not in params

    def test_live_init_requires_client_and_tracker(self, scaffolded):
        params = set(_get_init_params(scaffolded["live"] / "strategy.py"))
        assert "client" in params
        assert "tracker" in params

    def test_live_fixture_passes_tracker(self, scaffolded):
        fixture_kwargs = set(
            _get_fixture_kwargs(scaffolded["live"] / "tests" / "test_signals.py")
        )
        assert "tracker" in fixture_kwargs


# ---------------------------------------------------------------------------
# BUG-C: generated risk_manager.py must reject an order with a missing or
# zero price/quantity instead of letting notional_value silently become 0
# and bypass the position-size check.
# ---------------------------------------------------------------------------


class TestBugCRiskManager:
    @pytest.fixture
    def risk_manager_ns(self, scaffolded):
        risk_manager_py = scaffolded["backtest"] / "risk_manager.py"

        # Stub `config` so `from config import Config` resolves without
        # needing the real config.py (which imports vortex_api).
        fake_config_module = types.ModuleType("config")

        class _Config:  # only needs to exist for the type annotation
            pass

        fake_config_module.Config = _Config
        return _exec_generated(
            risk_manager_py, "risk_manager", {"config": fake_config_module}
        )

    @staticmethod
    def _make_risk_manager(ns, **overrides):
        cfg = SimpleNamespace(
            max_loss_per_day=5000.0,
            max_position_value=100000.0,
            max_open_positions=5,
        )
        for key, value in overrides.items():
            setattr(cfg, key, value)
        return ns["RiskManager"](config=cfg)

    def test_missing_price_key_rejected_with_warning(self, risk_manager_ns, caplog):
        rm = self._make_risk_manager(risk_manager_ns)
        order = {"symbol": "RELIANCE", "quantity": 100}  # market order, no price
        with caplog.at_level(logging.WARNING):
            approved = rm.approve(order)
        assert approved is False
        assert any("quantity/price" in r.message for r in caplog.records)

    def test_zero_price_rejected(self, risk_manager_ns):
        rm = self._make_risk_manager(risk_manager_ns)
        order = {"symbol": "RELIANCE", "quantity": 100, "price": 0}
        assert rm.approve(order) is False

    def test_zero_quantity_rejected(self, risk_manager_ns):
        rm = self._make_risk_manager(risk_manager_ns)
        order = {"symbol": "RELIANCE", "quantity": 0, "price": 2500}
        assert rm.approve(order) is False

    def test_missing_quantity_and_price_rejected(self, risk_manager_ns):
        rm = self._make_risk_manager(risk_manager_ns)
        assert rm.approve({"symbol": "RELIANCE"}) is False

    def test_normal_order_still_approved(self, risk_manager_ns):
        rm = self._make_risk_manager(risk_manager_ns)
        order = {"symbol": "RELIANCE", "quantity": 10, "price": 2500}  # 25k notional
        assert rm.approve(order) is True

    def test_oversized_order_still_rejected(self, risk_manager_ns):
        rm = self._make_risk_manager(risk_manager_ns)
        order = {"symbol": "RELIANCE", "quantity": 1000, "price": 2500}  # 2.5M notional
        assert rm.approve(order) is False

    def test_daily_loss_limit_still_enforced(self, risk_manager_ns):
        rm = self._make_risk_manager(risk_manager_ns)
        rm.daily_pnl = -rm.config.max_loss_per_day - 1
        assert rm.approve({"quantity": 1, "price": 2500}) is False


# ---------------------------------------------------------------------------
# BUG-D: generated guardrails.py must treat missing/None/0 bid, ask, or ltp
# as unhealthy (returning False) instead of raising TypeError/KeyError.
# ---------------------------------------------------------------------------


class TestBugDGuardrails:
    @pytest.fixture
    def guardrails_ns(self, scaffolded):
        guardrails_py = scaffolded["backtest"] / "guardrails.py"
        return _exec_generated(guardrails_py, "guardrails", {})

    @staticmethod
    def _breaker(ns):
        return ns["CircuitBreaker"]()

    def test_missing_bid_key_is_unhealthy_no_exception(self, guardrails_ns, caplog):
        cb = self._breaker(guardrails_ns)
        tick = {"ask": 100.5, "ltp": 100.0}  # 'bid' key absent entirely
        with caplog.at_level(logging.ERROR):
            assert cb.check_market_health(tick) is False
        assert caplog.records

    def test_none_bid_is_unhealthy(self, guardrails_ns):
        cb = self._breaker(guardrails_ns)
        tick = {"bid": None, "ask": 100.5, "ltp": 100.0}
        assert cb.check_market_health(tick) is False

    def test_zero_ask_is_unhealthy(self, guardrails_ns):
        cb = self._breaker(guardrails_ns)
        tick = {"bid": 99.5, "ask": 0, "ltp": 100.0}
        assert cb.check_market_health(tick) is False

    def test_missing_ltp_key_no_keyerror(self, guardrails_ns):
        cb = self._breaker(guardrails_ns)
        tick = {"bid": 99.5, "ask": 100.5}  # 'ltp' key absent entirely
        assert cb.check_market_health(tick) is False

    def test_zero_ltp_is_unhealthy(self, guardrails_ns):
        cb = self._breaker(guardrails_ns)
        tick = {"bid": 99.5, "ask": 100.5, "ltp": 0}
        assert cb.check_market_health(tick) is False

    def test_healthy_tick_passes(self, guardrails_ns):
        cb = self._breaker(guardrails_ns)
        tick = {"bid": 99.9, "ask": 100.1, "ltp": 100.0}
        assert cb.check_market_health(tick) is True

    def test_wide_spread_still_rejected(self, guardrails_ns):
        cb = self._breaker(guardrails_ns)
        tick = {"bid": 90.0, "ask": 110.0, "ltp": 100.0}  # 20% spread
        assert cb.check_market_health(tick) is False
