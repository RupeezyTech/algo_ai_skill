"""Tests for the strategy validation linter.

Covers the ERROR_HANDLING try/body-range fix (BUG-A/BUG-B), removal of the
dead visit_TryExcept path (BUG-C), and the tightened NSE-scrape substring
check (BUG-D).
"""

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "indian-algo-trading"
    / "skills"
    / "indian-algo-trading"
    / "scripts"
    / "validate_strategy.py"
)

spec = importlib.util.spec_from_file_location("validate_strategy", SCRIPT_PATH)
validate_strategy = importlib.util.module_from_spec(spec)
sys.modules["validate_strategy"] = validate_strategy
spec.loader.exec_module(validate_strategy)

validate_file = validate_strategy.validate_file


def _write(tmp_path, source):
    filepath = tmp_path / "strategy.py"
    filepath.write_text(source, encoding="utf-8")
    return filepath


def test_wrapped_place_order_passes_error_handling(tmp_path, capsys):
    source = """
def run(client):
    try:
        client.place_order(symbol="NSE:RELIANCE", qty=1)
    except Exception as e:
        pass
"""
    filepath = _write(tmp_path, source)
    validate_file(str(filepath))
    out = capsys.readouterr().out
    assert "PASS: ERROR_HANDLING" in out
    assert "WARN: ERROR_HANDLING" not in out


def test_unwrapped_place_order_is_flagged(tmp_path, capsys):
    source = """
def run(client):
    client.place_order(symbol="NSE:RELIANCE", qty=1)
"""
    filepath = _write(tmp_path, source)
    exit_code = validate_file(str(filepath))
    out = capsys.readouterr().out
    assert "WARN: ERROR_HANDLING" in out
    assert "Missing try/except around place_order" in out
    assert exit_code == 1


def test_place_order_in_except_handler_is_flagged(tmp_path, capsys):
    # place_order sits in the *except* block, not the try body -- must not
    # be treated as protected.
    source = """
def run(client):
    try:
        pass
    except Exception:
        client.place_order(symbol="NSE:RELIANCE", qty=1)
"""
    filepath = _write(tmp_path, source)
    exit_code = validate_file(str(filepath))
    out = capsys.readouterr().out
    assert "WARN: ERROR_HANDLING" in out
    assert "Missing try/except around place_order" in out
    assert exit_code == 1


def test_no_place_order_calls_passes(tmp_path, capsys):
    # Plain backtest file with zero place_order calls: nothing to wrap.
    source = """
def run():
    total = 1 + 1
    return total
"""
    filepath = _write(tmp_path, source)
    validate_file(str(filepath))
    out = capsys.readouterr().out
    assert "PASS: ERROR_HANDLING" in out


def test_one_wrapped_one_unwrapped_flags_correct_line(tmp_path, capsys):
    source = """
def run(client):
    try:
        client.place_order(symbol="NSE:RELIANCE", qty=1)
    except Exception:
        pass

    client.place_order(symbol="NSE:TCS", qty=1)
"""
    filepath = _write(tmp_path, source)
    exit_code = validate_file(str(filepath))
    out = capsys.readouterr().out
    assert "WARN: ERROR_HANDLING" in out
    # Line 8 is the unwrapped second call; line 4's wrapped call must not be
    # reported.
    assert "Line 8: Missing try/except around place_order" in out
    assert "Line 4: Missing try/except around place_order" not in out
    assert exit_code == 1


def test_print_statement_still_detected(tmp_path, capsys):
    source = """
def run():
    print("hello")
"""
    filepath = _write(tmp_path, source)
    validate_file(str(filepath))
    out = capsys.readouterr().out
    assert "WARN: PRINT_STATEMENT" in out
    assert "Use logging instead of print()" in out


def test_hardcoded_token_still_detected(tmp_path, capsys):
    source = """
instrument_token = 12345
"""
    filepath = _write(tmp_path, source)
    exit_code = validate_file(str(filepath))
    out = capsys.readouterr().out
    assert "FAIL: HARDCODED_TOKEN" in out
    assert exit_code == 2


def test_license_and_requests_get_without_nse_passes_nse_scrape(tmp_path, capsys):
    # 'license' contains the bare substring 'nse'; must not trip NSE_SCRAPE
    # when there is no actual NSE reference.
    source = """
import requests

def run():
    license_text = "check the license"
    r = requests.get("https://example.com/data")
    return r
"""
    filepath = _write(tmp_path, source)
    validate_file(str(filepath))
    out = capsys.readouterr().out
    assert "PASS: NSE_SCRAPE" in out
    assert "FAIL: NSE_SCRAPE" not in out


def test_nseindia_scrape_still_flagged(tmp_path, capsys):
    source = """
import requests

def run():
    r = requests.get("https://www.nseindia.com/api/quote")
    return r
"""
    filepath = _write(tmp_path, source)
    exit_code = validate_file(str(filepath))
    out = capsys.readouterr().out
    assert "FAIL: NSE_SCRAPE" in out
    assert exit_code == 2
