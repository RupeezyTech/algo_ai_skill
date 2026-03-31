# How to Contribute a Broker Adapter

Step-by-step guide for adding support for a new Indian broker. This guide assumes you'll use an AI assistant to help fill out the template, but the verification steps are your responsibility.

---

## Before You Start

### Prerequisites

- You are an **active user** of the broker you're adding (you can test API calls)
- The broker has a **documented Python SDK** or REST API
- The broker is **SEBI-registered** with a public registration number
- The broker supports **OAuth 2.0** for authentication (all Indian brokers do)

### What you'll produce

1. `references/brokers/<broker-name>.md` — filled-out BROKER_TEMPLATE
2. `tests/test_<broker-name>_adapter.py` — pytest suite with mocked API responses
3. Both reviewed and tested before submitting PR

---

## Step 1: Collect Raw Material (You, Not AI)

Before touching any AI tool, gather these from the broker's official documentation. This is the most important step — AI models hallucinate API method names, parameter codes, and constant values. You need the ground truth.

### Must-have documentation

| What | Where to find it | Why it matters |
|------|-------------------|----------------|
| Python SDK package name + version | PyPI page or broker's developer docs | Wrong package name = nothing works |
| OAuth 2.0 flow details | Developer portal / API docs | Auth URL, callback mechanism, token validity, refresh behavior |
| Instrument master download method | API reference | Exact method name, return format, column names |
| Order placement API | API reference | Method signature, parameter names, required vs optional fields |
| Order type constants | API reference or SDK source | The exact string/int codes: "MARKET" vs "MKT" vs 1 |
| Exchange constants | API reference or SDK source | "NSE" vs "NSE_EQ" vs "nse_cm" vs 1 |
| Product type constants | API reference or SDK source | "CNC" vs "DELIVERY" vs "C" |
| Order status values | API reference | What string the API returns for filled, rejected, etc. |
| WebSocket setup | API reference | Connection method, subscription modes, tick data format |
| Historical data API | API reference | Supported intervals, max lookback period, return format |
| Rate limits | API reference or terms of service | Requests per second, per minute |
| Known limitations | Community forums, GitHub issues | Gotchas that aren't in official docs |

### Nice-to-have

- Sandbox/paper trading endpoint URL
- Sample API responses (copy from docs or your own test calls)
- The broker's GitHub repo for the SDK (to check actual method signatures)

### Pro tip: get real API responses

Run a few real API calls and save the responses. This is gold for your AI and for writing test mocks:

```python
import json

# After authenticating with the broker SDK
master = client.get_instruments()
print(json.dumps(master[:3], indent=2))  # first 3 instruments

order = client.place_order(...)  # paper/sandbox if available
print(json.dumps(order, indent=2))

positions = client.get_positions()
print(json.dumps(positions, indent=2))
```

Save these outputs — you'll paste them into your AI prompt and use them as mock data in tests.

---

## Step 2: Feed to AI with the Template

### The prompt

Copy-paste this prompt to your AI assistant. Replace the bracketed sections with your actual data.

```
I'm contributing a broker adapter for [BROKER NAME] to the indian-algo-trading
open-source skill.

Here is the BROKER_TEMPLATE.md I need to fill out:

---
[PASTE THE ENTIRE CONTENTS OF references/brokers/BROKER_TEMPLATE.md]
---

Here is the broker's official Python SDK documentation:

---
[PASTE THE SDK DOCS — auth flow, order APIs, WebSocket, historical data,
instrument master, constants/enums]
---

Here are some real API responses I captured:

---
[PASTE YOUR SAVED API RESPONSES FROM STEP 1]
---

Instructions:
1. Fill out every section of the BROKER_TEMPLATE with this broker's specifics.
2. Use EXACT method names, parameter names, and constant values from the
   documentation I provided.
3. Do NOT guess or invent any API method names, parameter codes, or constant
   values. If something is unclear from the docs I provided, write
   [NEEDS VERIFICATION] instead of guessing.
4. For the Constants Mapping Table (section 10), use the exact enum/string
   values from the SDK — these are the #1 source of bugs.
5. For the OAuth flow (section 3), document the specific URLs and token
   lifetime for this broker.
6. Include the real API response format in each section where applicable.

After filling the template, also generate:
- A pytest test file `test_<broker>_adapter.py` with mocked API responses
  covering: authentication, order placement, order cancellation, position
  fetching, and instrument master download. Use the real API responses I
  provided as mock data. Target >80% code coverage.
```

### What to paste as "SDK documentation"

The more concrete material you give the AI, the less it hallucinates. Prioritize:

1. **The SDK's README or quickstart** — has the import paths and basic usage
2. **API reference pages** for each endpoint (place_order, get_positions, etc.)
3. **Constants/enums page** — the exact codes the API uses
4. **WebSocket documentation** — connection and subscription format
5. **Your real API responses** from Step 1

If the docs are too large, prioritize the constants/enums page and order placement API — these are where AI makes the most mistakes.

---

## Step 3: Verify (You, Not AI)

This is non-negotiable. AI will get subtle things wrong, and in trading, subtle things cost money.

### Verification checklist

**Authentication (Section 3):**
- [ ] Developer portal URL is correct and accessible
- [ ] Authorization URL matches what the SDK actually uses
- [ ] Token validity matches real behavior (test: authenticate, wait, check if token still works)
- [ ] Refresh token behavior is accurate (some brokers don't support refresh — you re-auth daily)

**Constants (Section 10) — the #1 source of adapter bugs:**
- [ ] Exchange codes match SDK exactly (test: `client.place_order(exchange=YOUR_CODE)`)
- [ ] Product type codes match SDK exactly (test: place a CNC order, then an MIS order)
- [ ] Order type codes match SDK exactly (test: place MARKET, LIMIT, SL orders)
- [ ] Order status strings match what the API actually returns (test: check a filled order's status field)

**Instrument Master (Section 4):**
- [ ] Method name is correct
- [ ] Column names match the actual DataFrame/dict columns returned
- [ ] Token/symbol format is accurate (some brokers use int tokens, some use string)

**Order Placement (Section 5):**
- [ ] Parameter names match SDK exactly (some use `qty` not `quantity`, `txn_type` not `transaction_type`)
- [ ] All required parameters are documented
- [ ] Return value format is accurate (some return `{"order_id": "123"}`, others return just `"123"`)

**WebSocket (Section 8):**
- [ ] Connection method and subscription format are correct
- [ ] Tick data fields match what's actually received
- [ ] Reconnection behavior is documented accurately

**Historical Data (Section 9):**
- [ ] Supported intervals are correct
- [ ] Max lookback period is accurate (test: request 2 years of minute data — does it work?)
- [ ] Return format matches actual response

### Quick smoke test

After filling out the template, try to write a minimal working script from ONLY the information in your adapter doc:

```python
# Can you authenticate using only the info in Section 3?
# Can you download instruments using only Section 4?
# Can you place a paper order using only Section 5?
# Can you connect to WebSocket using only Section 8?
```

If any step requires information not in your adapter doc, the doc is incomplete.

---

## Step 4: Write Tests

Your test file should use **mocked API responses** — never call the live broker in tests. Use the real responses you captured in Step 1 as mock data.

### Required test coverage (>80%)

| Test area | What to test |
|-----------|-------------|
| Authentication | OAuth flow initiates correctly, token exchange works, expired token handled |
| Instrument master | Download returns expected format, symbol lookup works, empty result handled |
| Order placement | Market/limit/SL orders place correctly, invalid params rejected, response parsed |
| Order management | Cancel works, modify works, get_order returns correct status |
| Positions | Open positions returned correctly, empty portfolio handled |
| WebSocket | Subscribe formats message correctly, tick data parsed, disconnect handled |

### Test file structure

```python
"""Tests for [Broker] adapter - all API calls mocked."""

import pytest
from unittest.mock import patch, MagicMock

# Mock responses based on real API data captured in Step 1
MOCK_ORDER_RESPONSE = {  # paste your real response here
    "order_id": "220303000012345",
    "status": "COMPLETE"
}

MOCK_POSITIONS_RESPONSE = [  # paste your real response here
    {"symbol": "RELIANCE-EQ", "qty": 10, "avg_price": 2450.50}
]

class TestAuthentication:
    def test_oauth_flow(self):
        """Test OAuth login URL generation and token exchange."""
        ...

class TestOrderPlacement:
    def test_place_market_order(self):
        """Test market order with correct exchange/product codes."""
        ...

    def test_place_limit_order_with_tick_rounding(self):
        """Test that limit price is rounded to tick size."""
        ...

class TestInstrumentMaster:
    def test_download_and_lookup(self):
        """Test master download and symbol token lookup."""
        ...
```

---

## Step 5: Submit PR

### PR checklist

- [ ] Adapter doc fills every section of BROKER_TEMPLATE (no remaining `[PLACEHOLDER]` text)
- [ ] Any `[NEEDS VERIFICATION]` items have been resolved
- [ ] Constants verified against live SDK (not just docs)
- [ ] Test suite passes: `pytest tests/test_<broker>_adapter.py -v --cov`
- [ ] Coverage >80%
- [ ] No hardcoded API keys or credentials anywhere
- [ ] No `[PLACEHOLDER]` text remaining
- [ ] DCO sign-off on commits (`git commit -s`)

### PR title format

```
Add [BrokerName] adapter (SmartAPI v2.1)
```

### Expected review timeline

2 maintainer reviews required. Typical turnaround: 2–3 weeks. Maintainers will check:
- Constants accuracy (they may test against their own broker accounts)
- Test quality and coverage
- Documentation completeness
- Compliance with template structure

---

## For Maintainers: How to Review a Broker Adapter PR

You can't just read the code and approve. Broker adapters have a unique problem: the code looks correct but uses the wrong constant for an exchange code, and now orders go to the wrong segment. Here's the review process.

### Automated checks (run first)

Run the adapter validation script against the submitted doc:

```bash
python scripts/validate_broker_adapter.py references/brokers/<broker-name>.md
```

This checks:
- All 12 sections are present and filled (no `[PLACEHOLDER]` remaining)
- No `[NEEDS VERIFICATION]` left unresolved
- Constants mapping table has all required keys
- OAuth section documents all 5 required flow steps
- Test file exists and passes with >80% coverage

### Manual verification (the critical part)

**Level 1: Documentation cross-check (30 min)**

1. Open the broker's official Python SDK docs in your browser
2. For each API method in the adapter doc, verify the method signature matches the official docs
3. Pay special attention to:
   - Parameter names (is it `qty` or `quantity`? `txn_type` or `transaction_type`?)
   - Return value format (does place_order return `{"order_id": "123"}` or just `"123"`?)
   - Required vs optional parameters

**Level 2: Constants verification (most important, 20 min)**

This is where 80% of adapter bugs hide. For each constants table entry:

1. Open the broker's SDK source on GitHub/PyPI
2. Find the actual enum/constant definitions
3. Verify every single mapping:
   - Exchange codes: "NSE" vs "NSE_EQ" vs "nse_cm" vs 1
   - Product types: "CNC" vs "DELIVERY" vs "C"
   - Order types: "MARKET" vs "MKT" vs "MARKET_ORDER"
   - Transaction types: "BUY" vs "B" vs "buy"
   - Order statuses: "COMPLETE" vs "FILLED" vs "executed"

**If you have an account with this broker:**

Best case — run these smoke tests yourself:

```python
# 1. Can you authenticate with the documented flow?
# 2. Does download_master() return the documented columns?
# 3. Place a paper order — do the exchange/product/order_type codes work?
# 4. Check a filled order — does the status string match the STATUS_MAP?
```

**If you don't have an account:**

Ask the contributor to provide:
- Screenshot of a real API response for instrument master (first 3 rows)
- Screenshot of a real order placement response
- Screenshot of a real get_positions response
- Output of: `pip show <broker-sdk-name>` (confirms version)

These screenshots prove the adapter was tested against the real API, not just the docs.

**Level 3: Test quality review (15 min)**

1. Run the test suite: `pytest tests/test_<broker>_adapter.py -v --cov`
2. Check that mock data looks realistic (not placeholder values)
3. Verify tests cover error cases (expired token, rejected order, API timeout)
4. Confirm no test makes real API calls (grep for `requests.get`, `requests.post`, no network calls)

### Review decision matrix

| Situation | Decision |
|-----------|----------|
| All constants verified, tests pass, docs match SDK | Approve |
| Constants look right but reviewer has no account to verify | Request screenshots from contributor |
| One or two minor issues (typo, missing optional param) | Request changes, fast-track re-review |
| Constants don't match SDK source | Reject with specifics, ask contributor to re-verify |
| Test coverage <80% | Request additional tests |
| Any `[PLACEHOLDER]` or `[NEEDS VERIFICATION]` remaining | Reject immediately |
| Adapter for broker with no public SDK docs | Reject — can't maintain what we can't verify |

### After merge

- Add the broker to the README's supported brokers section
- Update CHANGELOG.md
- Tag the contributor in the release notes

---

## Common Mistakes

| Mistake | Why it happens | How to avoid |
|---------|---------------|--------------|
| Wrong constant codes | AI guesses "NSE" when SDK uses "NSE_EQ" or 1 | Always verify against live SDK, not docs alone |
| Wrong method names | AI confuses similar brokers' SDKs | Paste the exact import path and method signature |
| Missing required params | AI omits params that aren't in basic examples | Check the SDK source or try a real API call |
| Incorrect token format | Some brokers use int tokens, some use strings | Check the type of `master['token'].iloc[0]` |
| Wrong order status strings | AI assumes "FILLED" when API returns "COMPLETE" | Check a real filled order's status field |
| Stale SDK version | Docs reference old version | Pin and test against the specific version you document |
| Incorrect tick data format | WebSocket returns different fields than REST API | Log actual WebSocket ticks and verify field names |

---

## Example: What a Contributor Prompt Looks Like (Angel One)

For reference, here's approximately what the AI prompt would look like for adding Angel One:

```
I'm contributing a broker adapter for Angel One (SmartAPI) to the
indian-algo-trading open-source skill.

Here is the BROKER_TEMPLATE.md I need to fill out:
[... full template ...]

Here is Angel One's SmartAPI Python SDK documentation:

Package: smartapi-python (pip install smartapi-python)
Version: 1.4.1

Authentication:
- Developer portal: https://smartapi.angelbroking.com/
- Uses TOTP-based 2FA + API key
- Method: SmartConnect(api_key).generateSession(clientCode, password, totp)
- Token validity: until midnight IST

Instrument master:
- URL: https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json
- Returns: JSON array with token, symbol, name, expiry, strike, lotsize, instrumenttype, exch_seg

Order placement:
- Method: obj.placeOrder(orderparams)
- orderparams = {
    "variety": "NORMAL",
    "tradingsymbol": "RELIANCE-EQ",
    "symboltoken": "2885",
    "transactiontype": "BUY",
    "exchange": "NSE",
    "ordertype": "LIMIT",
    "producttype": "DELIVERY",
    "duration": "DAY",
    "price": "2450",
    "quantity": "1"
  }

[... WebSocket, historical data, positions, etc. ...]

Real API responses I captured:
[... paste actual JSON responses ...]

[... rest of the prompt template from Step 2 ...]
```

Notice how specific the raw material is — exact method names, exact parameter keys, exact constant values. That's what makes the AI output trustworthy.

---

**Last updated**: March 2026
