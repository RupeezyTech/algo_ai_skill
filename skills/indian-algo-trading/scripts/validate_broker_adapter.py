#!/usr/bin/env python3
"""
Broker Adapter Validator

Validates a broker adapter markdown file against the BROKER_TEMPLATE structure.
Checks for completeness, unresolved placeholders, and required sections.

Usage:
    python validate_broker_adapter.py references/brokers/angelone.md
    python validate_broker_adapter.py references/brokers/angelone.md --test-file tests/test_angelone_adapter.py
"""

import sys
import re
import argparse
from pathlib import Path


# All 12 required sections from BROKER_TEMPLATE.md
REQUIRED_SECTIONS = [
    "Broker Identification",
    "Installation",
    "Authentication Pattern",
    "Instrument Master",
    "Order Placement",
    "Order Management",
    "Positions, Holdings, and Funds",
    "WebSocket",
    "Historical Data",
    "Constants Mapping",
    "Deployment Considerations",
    "Known Limitations",
]

# Required keys in the constants mapping section
REQUIRED_CONSTANT_MAPS = [
    "EXCHANGE_MAP",
    "PRODUCT_MAP",
    "TRANSACTION_MAP",
    "ORDER_TYPE_MAP",
    "STATUS_MAP",
]

# Required exchange codes
REQUIRED_EXCHANGES = ["NSE_EQ", "NSE_FO", "BSE_EQ", "MCX_FO"]

# Required product types
REQUIRED_PRODUCTS = ["DELIVERY", "INTRADAY"]

# Required order types
REQUIRED_ORDER_TYPES = ["MARKET", "LIMIT", "STOPLOSS", "STOPLOSS_LIMIT"]

# Required transaction types
REQUIRED_TRANSACTIONS = ["BUY", "SELL"]

# OAuth flow steps that must be documented
OAUTH_KEYWORDS = [
    "developer portal",
    "authorization",
    "callback",
    "access token",
    "token validity",
]


class ValidationResult:
    """Stores validation pass/fail/warn results."""

    def __init__(self):
        self.passes = []
        self.failures = []
        self.warnings = []

    def pass_(self, check, detail=""):
        self.passes.append((check, detail))

    def fail(self, check, detail=""):
        self.failures.append((check, detail))

    def warn(self, check, detail=""):
        self.warnings.append((check, detail))

    @property
    def ok(self):
        return len(self.failures) == 0


def read_file(path):
    """Read file contents."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: File not found: {path}")
        sys.exit(1)


def check_sections(content, result):
    """Check that all 12 required sections are present."""
    for section in REQUIRED_SECTIONS:
        # Match section headers flexibly (## 1. Broker Identification, ## Broker Identification, etc.)
        pattern = rf"##\s+\d*\.?\s*{re.escape(section)}"
        if re.search(pattern, content, re.IGNORECASE):
            result.pass_("SECTION_PRESENT", section)
        else:
            # Try a looser match
            words = section.split()
            loose_pattern = r"##.*" + r".*".join(re.escape(w) for w in words)
            if re.search(loose_pattern, content, re.IGNORECASE):
                result.pass_("SECTION_PRESENT", f"{section} (loose match)")
            else:
                result.fail("SECTION_MISSING", f"Missing section: {section}")


def check_placeholders(content, result):
    """Check for unresolved [PLACEHOLDER] and [NEEDS VERIFICATION] text."""
    placeholder_matches = re.findall(r"\[PLACEHOLDER[^\]]*\]", content)
    verification_matches = re.findall(r"\[NEEDS VERIFICATION[^\]]*\]", content)

    if placeholder_matches:
        result.fail(
            "UNRESOLVED_PLACEHOLDER",
            f"{len(placeholder_matches)} unresolved [PLACEHOLDER] entries: "
            + ", ".join(placeholder_matches[:5]),
        )
    else:
        result.pass_("NO_PLACEHOLDERS")

    if verification_matches:
        result.warn(
            "NEEDS_VERIFICATION",
            f"{len(verification_matches)} [NEEDS VERIFICATION] entries remain",
        )
    else:
        result.pass_("NO_VERIFICATION_NEEDED")


def check_constants(content, result):
    """Check that constants mapping table has all required keys."""
    for map_name in REQUIRED_CONSTANT_MAPS:
        if map_name in content:
            result.pass_("CONSTANT_MAP_PRESENT", map_name)
        else:
            result.fail("CONSTANT_MAP_MISSING", f"Missing: {map_name}")

    # Check for required exchange codes
    for exchange in REQUIRED_EXCHANGES:
        if f'"{exchange}"' in content or f"'{exchange}'" in content:
            result.pass_("EXCHANGE_CODE", exchange)
        else:
            result.warn("EXCHANGE_CODE_MISSING", f"Exchange code not found: {exchange}")

    # Check for required product types
    for product in REQUIRED_PRODUCTS:
        if f'"{product}"' in content or f"'{product}'" in content:
            result.pass_("PRODUCT_TYPE", product)
        else:
            result.warn("PRODUCT_TYPE_MISSING", f"Product type not found: {product}")

    # Check for required order types
    for order_type in REQUIRED_ORDER_TYPES:
        if f'"{order_type}"' in content or f"'{order_type}'" in content:
            result.pass_("ORDER_TYPE", order_type)
        else:
            result.warn("ORDER_TYPE_MISSING", f"Order type not found: {order_type}")


def check_oauth(content, result):
    """Check that OAuth 2.0 flow is properly documented."""
    content_lower = content.lower()

    for keyword in OAUTH_KEYWORDS:
        if keyword in content_lower:
            result.pass_("OAUTH_DOCUMENTED", keyword)
        else:
            result.warn("OAUTH_MISSING", f"OAuth detail not found: {keyword}")

    # Check for the 5-step flow
    flow_steps = [
        r"(register|create).*app",
        r"redirect.*login|authorization.*url|login.*url",
        r"callback.*url|redirect.*back|auth.*code",
        r"exchange.*token|access.*token",
        r"token.*valid|expir|refresh",
    ]

    documented_steps = sum(
        1 for step in flow_steps if re.search(step, content_lower)
    )
    if documented_steps >= 4:
        result.pass_("OAUTH_FLOW_COMPLETE", f"{documented_steps}/5 steps documented")
    else:
        result.fail(
            "OAUTH_FLOW_INCOMPLETE",
            f"Only {documented_steps}/5 OAuth flow steps documented",
        )


def check_code_examples(content, result):
    """Check that code examples are present in key sections."""
    code_blocks = re.findall(r"```python(.*?)```", content, re.DOTALL)

    if len(code_blocks) >= 5:
        result.pass_("CODE_EXAMPLES", f"{len(code_blocks)} Python code blocks found")
    elif len(code_blocks) >= 3:
        result.warn(
            "FEW_CODE_EXAMPLES",
            f"Only {len(code_blocks)} code blocks — aim for 5+",
        )
    else:
        result.fail(
            "MISSING_CODE_EXAMPLES",
            f"Only {len(code_blocks)} code blocks — need at least 5",
        )

    # Check for import statements (indicates real SDK usage)
    has_imports = any("import" in block for block in code_blocks)
    if has_imports:
        result.pass_("SDK_IMPORTS", "Code blocks contain import statements")
    else:
        result.warn("NO_SDK_IMPORTS", "No import statements found — are SDK methods documented?")


def check_broker_info(content, result):
    """Check that broker identification is complete."""
    content_lower = content.lower()

    # SEBI registration
    if "sebi" in content_lower and re.search(r"IN[A-Z]\d+", content):
        result.pass_("SEBI_REGISTRATION", "SEBI registration number found")
    else:
        result.warn("NO_SEBI_NUMBER", "No SEBI registration number found (format: INxNNNNNN)")

    # SDK name and version
    if re.search(r"pip install\s+[\w-]+", content):
        result.pass_("PIP_INSTALL", "pip install command found")
    else:
        result.fail("NO_PIP_INSTALL", "No pip install command found")

    # Version pinned
    if re.search(r"==\d+\.\d+", content):
        result.pass_("VERSION_PINNED", "SDK version is pinned")
    else:
        result.warn("VERSION_NOT_PINNED", "SDK version not pinned in requirements")


def check_test_file(test_path, result):
    """Check that test file exists and has required test classes."""
    if not Path(test_path).exists():
        result.fail("TEST_FILE_MISSING", f"Test file not found: {test_path}")
        return

    test_content = read_file(test_path)

    # Check for pytest imports
    if "import pytest" in test_content or "from pytest" in test_content:
        result.pass_("PYTEST_IMPORT", "pytest imported")
    else:
        result.warn("NO_PYTEST", "pytest not imported in test file")

    # Check for mock usage
    if "mock" in test_content.lower() or "Mock" in test_content:
        result.pass_("USES_MOCKS", "Tests use mocking")
    else:
        result.fail("NO_MOCKS", "Tests don't use mocking — may make real API calls")

    # Check for required test areas
    test_areas = {
        "authentication": r"(test.*auth|test.*login|test.*token|test.*oauth)",
        "order_placement": r"(test.*order|test.*place)",
        "positions": r"(test.*position|test.*holding)",
        "instrument_master": r"(test.*instrument|test.*master|test.*symbol)",
    }

    for area, pattern in test_areas.items():
        if re.search(pattern, test_content, re.IGNORECASE):
            result.pass_("TEST_COVERAGE", f"Tests cover: {area}")
        else:
            result.warn("TEST_GAP", f"No tests found for: {area}")

    # Check no real API calls
    dangerous_patterns = [
        (r"requests\.(get|post|put|delete)\(", "Direct HTTP calls (use mocks)"),
        (r"http(s)?://api\.", "Hardcoded API URLs in tests"),
    ]

    for pattern, desc in dangerous_patterns:
        if re.search(pattern, test_content):
            result.warn("REAL_API_CALL", f"Potential real API call: {desc}")


def print_results(result, file_path):
    """Print validation results."""
    print(f"\nValidating: {file_path}")
    print("-" * 60)

    for check, detail in result.passes:
        detail_str = f" — {detail}" if detail else ""
        print(f"  PASS: {check}{detail_str}")

    for check, detail in result.warnings:
        detail_str = f" — {detail}" if detail else ""
        print(f"  WARN: {check}{detail_str}")

    for check, detail in result.failures:
        detail_str = f" — {detail}" if detail else ""
        print(f"  FAIL: {check}{detail_str}")

    print()
    print("=" * 60)
    total = len(result.passes) + len(result.warnings) + len(result.failures)
    print(f"  Passed: {len(result.passes)}/{total}")
    print(f"  Warnings: {len(result.warnings)}/{total}")
    print(f"  Failures: {len(result.failures)}/{total}")
    print()

    if result.failures:
        print("RESULT: FAILED — address failures before merging")
        print("=" * 60)
        return 1
    elif result.warnings:
        print("RESULT: WARNINGS — review manually before merging")
        print("=" * 60)
        return 0
    else:
        print("RESULT: PASSED")
        print("=" * 60)
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="Validate a broker adapter markdown file"
    )
    parser.add_argument(
        "adapter_file",
        help="Path to the broker adapter .md file",
    )
    parser.add_argument(
        "--test-file",
        help="Path to the corresponding test file (optional)",
        default=None,
    )

    args = parser.parse_args()

    content = read_file(args.adapter_file)
    result = ValidationResult()

    # Run all checks
    check_sections(content, result)
    check_placeholders(content, result)
    check_constants(content, result)
    check_oauth(content, result)
    check_code_examples(content, result)
    check_broker_info(content, result)

    if args.test_file:
        check_test_file(args.test_file, result)

    exit_code = print_results(result, args.adapter_file)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
