#!/usr/bin/env python3
"""
Strategy Validation Linter

Checks strategy code for common mistakes and best practices.
Validates hardcoded tokens, missing error handling, logging, timezone, etc.

Usage:
    python validate_strategy.py path/to/strategy/
    python validate_strategy.py /home/user/my_strategy/main.py

Exit codes:
    0: All checks passed
    1: Warnings found (non-blocking)
    2: Failures found (blocking issues)
"""

import ast
import sys
from pathlib import Path
from collections import defaultdict


class StrategyValidator(ast.NodeVisitor):
    """AST visitor to check for anti-patterns in strategy code."""

    def __init__(self, filename):
        self.filename = filename
        self.issues = defaultdict(list)
        self.has_timezone = False
        self.has_error_handling_orders = False
        self.has_logging = False
        self.has_stop_loss = False
        self.has_nseindia_scrape = False

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name == 'logging':
                self.has_logging = True
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module == 'logging':
            self.has_logging = True
        self.generic_visit(node)

    def visit_Assign(self, node):
        # Check for hardcoded tokens
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id.lower()
                if any(x in var_name for x in ['token', 'instrument_token', 'lot_size']):
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, int):
                        self.issues['HARDCODED_TOKEN'].append({
                            'line': node.lineno,
                            'var': target.id,
                            'value': node.value.value,
                            'msg': f'Line {node.lineno}: Hardcoded {target.id} = {node.value.value}. Use client.download_master() to look up tokens dynamically.'
                        })
        self.generic_visit(node)

    def visit_Call(self, node):
        # Check for place_order without try/except
        if isinstance(node.func, ast.Attribute):
            func_name = node.func.attr.lower()

            if 'place_order' in func_name:
                self.has_error_handling_orders = False  # Will check if inside try block

            if 'round_to_tick' in func_name or 'round_price' in func_name:
                # Mark that we found tick rounding
                pass

            if 'nseindia.com' in ast.unparse(node):
                self.has_nseindia_scrape = True

        # Check for print statements
        if isinstance(node.func, ast.Name) and node.func.id == 'print':
            self.issues['PRINT_STATEMENT'].append({
                'line': node.lineno,
                'msg': f'Line {node.lineno}: Use logging instead of print(). Change to logger.info(...)'
            })

        self.generic_visit(node)

    def visit_TryExcept(self, node):
        # Check if place_order calls are wrapped in try/except
        for child in ast.walk(node.body[0] if node.body else node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    if 'place_order' in child.func.attr.lower():
                        self.has_error_handling_orders = True
        self.generic_visit(node)

    def visit_Try(self, node):
        # Python 3.8+ uses Try node
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    if 'place_order' in child.func.attr.lower():
                        self.has_error_handling_orders = True
        self.generic_visit(node)

    def check_string_content(self, tree):
        """Check string content for specific patterns."""
        source = ast.unparse(tree)

        if 'pytz' in source or 'timezone' in source.lower() or 'utc' in source.lower():
            self.has_timezone = True

        if 'stop' in source.lower() and 'loss' in source.lower():
            self.has_stop_loss = True

        if 'nseindia.com' in source or 'requests.get' in source and 'nse' in source.lower():
            self.has_nseindia_scrape = True


def validate_file(filepath):
    """Validate a single Python file."""
    print(f"\nValidating: {filepath}")
    print("-" * 60)

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
    except FileNotFoundError:
        print(f"FAIL: File not found: {filepath}")
        return 2
    except Exception as e:
        print(f"FAIL: Cannot read file: {e}")
        return 2

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        print(f"FAIL: Syntax error in {filepath}: {e}")
        return 2

    validator = StrategyValidator(str(filepath))
    validator.visit(tree)
    validator.check_string_content(tree)

    # Aggregated results
    checks = {
        'HARDCODED_TOKEN': ('FAIL', validator.issues.get('HARDCODED_TOKEN', [])),
        'PRINT_STATEMENT': ('WARN', validator.issues.get('PRINT_STATEMENT', [])),
        'TIMEZONE': ('WARN', [] if validator.has_timezone else ['No timezone configuration found']),
        'STOP_LOSS': ('WARN', [] if validator.has_stop_loss else ['No stop-loss logic detected']),
        'ERROR_HANDLING': ('WARN', [] if validator.has_error_handling_orders else ['Missing try/except around place_order']),
        'LOGGING': ('WARN', [] if validator.has_logging else ['No logging import found']),
        'NSE_SCRAPE': ('FAIL', ['NSE website scraping detected - use APIs instead'] if validator.has_nseindia_scrape else []),
    }

    has_failures = False
    has_warnings = False

    for check_name, (severity, issues) in checks.items():
        if issues:
            print(f"{severity}: {check_name}")
            for issue in issues:
                if isinstance(issue, dict):
                    print(f"  -> {issue.get('msg', str(issue))}")
                else:
                    print(f"  -> {issue}")
            if severity == 'FAIL':
                has_failures = True
            else:
                has_warnings = True
        else:
            print(f"PASS: {check_name}")

    if has_failures:
        return 2
    elif has_warnings:
        return 1
    else:
        return 0


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_strategy.py <file_or_directory>")
        print("Examples:")
        print("  python validate_strategy.py main.py")
        print("  python validate_strategy.py /home/user/strategy/")
        sys.exit(1)

    path = Path(sys.argv[1])

    if not path.exists():
        print(f"Error: Path does not exist: {path}")
        sys.exit(2)

    if path.is_file():
        files = [path]
    else:
        files = sorted(path.glob('**/*.py'))

    if not files:
        print(f"No Python files found in {path}")
        sys.exit(1)

    exit_code = 0

    for filepath in files:
        file_exit = validate_file(str(filepath))
        exit_code = max(exit_code, file_exit)

    print("\n" + "=" * 60)
    if exit_code == 0:
        print("RESULT: All checks passed")
    elif exit_code == 1:
        print("RESULT: Warnings found (review recommended)")
    else:
        print("RESULT: Failures found (fix before deployment)")
    print("=" * 60)

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
