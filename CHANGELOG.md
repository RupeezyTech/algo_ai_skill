# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.1] - 2026-08-28

### Added

- **`market_session.py`, generated into every strategy — session rules as importable code rather than prose to be recalled.** The single biggest source of small-model error in this skill was asking the model to remember that continuous trading ends at 15:15 for a CAS scrip, 15:30 without F&O contracts and 15:40 for derivatives, and to apply the right one. It now writes `session.should_exit_now(self.segment)` instead. The module encodes the segment clocks, every CAS phase boundary, the +/-3% auction band, the stop-loss/GTT protection gap, runtime CAS-eligibility derivation, and a `pre_open_schedule()` that branches on the 7 Sep 2026 realignment date. `strategy.py` now resolves its segment in `init()` and exposes `must_square_off()`. Verified against the full CAS timeline: the three segments diverge at 15:05 / 15:20 / 15:30 with a 10-minute buffer, order entry is refused 15:15-15:20, market orders are refused from 15:25, and stop-loss protection reports false from 15:15.
- **`references/brokers/rupeezy-vortex-advanced.md`** — Backtesting, Common Patterns and Error Handling split out of the core broker reference (303 lines, ~2.2K tokens) so they load only on demand. The core keeps every section `validate_broker_adapter.py` requires and still reports 0 failures.

### Changed

- **Scaffolding is now the documented default, not an option.** Generated code already satisfies Rules 1, 2, 7, 8, 11, 15 and 16 by construction, so the model edits one function instead of authoring six files from memory. Stated in Strategy Output Format.
- **Rule 16 no longer restates the CAS timeline** — it leads with "import `market_session.py`, never hardcode a session time", keeps a three-row segment table, and retains only the traps no import can fix (stop-loss and GTT both dead from 15:15, the +/-3% band, the changed meaning of "the close", the missing 15:15-15:30 candles).
- **Routing guidance now tells the reader what NOT to load.** If a strategy was scaffolded, `code-quality.md` (~10.6K tokens) is not needed for order tracking — `order_tracker.py` is already on disk. This takes a typical live-Vortex task from ~45K tokens to **~36.4K on the scaffold path**.

### Fixed

- **The scaffolder emitted non-ASCII source, which the container rejects.** Six of the generated files (`main.py`, `strategy.py`, `config.py`, `auth.py`, `login.py`, `order_tracker.py`) contained em dashes. The broker reference documents this precise failure: non-ASCII "break the upload: the server rejects the bundle with `SyntaxError: unexpected character after line continuation character`" — so the repo's own sanctioned tool produced container bundles that fail on upload. Every generated file now goes through a `write_source()` helper that transliterates the usual offenders and then **hard-fails at scaffold time** if anything non-ASCII survives, rather than shipping a bundle that dies later. Verified: 42 generated files across all four type/deployment combinations, 0 non-ASCII, all compile.

- **Restored the loopback OAuth pattern to the Rupeezy broker reference — it had been silently lost.** SKILL.md Rule 8 mandates shipping `login.py` + `auth.py` and states "the full pattern is in `references/brokers/rupeezy-vortex.md`". It was not there: commit `1ef59cb` replaced that section (174 insertions / 205 deletions) with the **manual auth-code paste flow that Rule 8 explicitly forbids**, described self-hosted auth as "Manual OAuth authentication required", recommended `export VORTEX_ACCESS_TOKEN=...` under a heading reading "Environment variables (recommended)", and called the access token one that "persists across sessions". `scaffold_strategy.py:641` meanwhile emits "DO NOT add VORTEX_ACCESS_TOKEN here. The access_token is short-lived (~24h)". The flagship broker doc was contradicting both the skill's own rule and its own generated code. The pattern has been restored from commit `5f92809` and reconciled with what the scaffolder ships today (`client.login_url(callback_param=...)`, `127.0.0.1:8765/callback`, `.access_token.json`).
- **The manual-paste escape hatch is gone for real this time.** CHANGELOG 1.1.7 claimed the Self-Hosted section was "rewritten with full `login.py` + `auth.py` code listings" and 1.1.9 claimed the duplicate auth subsection was "collapsed" and the escape hatch "deleted" with an SSH port-forward recipe in its place. Neither was true of the shipped file — the port-forward recipe never landed in any commit. Headless boxes are now handled with an actual `ssh -L 8765:127.0.0.1:8765` recipe, per Rule 8's "headless is non-exempting".
- **Access-token lifetime is now stated in the broker reference** (~24h, session credential, cache to disk, never in `.env`), and the two deployment modes are presented as disjoint in a table: `VORTEX_ACCESS_TOKEN` is **platform-injected for containers** and **never set by hand for self-hosted**. Previously the doc listed it as a generic env var "optional, auto-generated on auth" for both.
- **Summary section contradicted Critical Rule 1.** It advised "Always look up tokens by symbol — never hardcode", the pre-2.1.8 doctrine, in a section readers quote. Replaced with the ticker-first rule plus the enum, auth, CAS and margin takeaways.
- **`validate_broker_adapter.py` reported a false SEBI registration.** The check was `"sebi" in content and re.search(r"IN[A-Z]\d+", content)` — satisfied by the word "SEBI" appearing anywhere plus `INE002`, the leading chunk of the Reliance ISIN used in an unrelated code example. A regulatory-disclosure check was silently green on a document with no registration number. It now requires the number to appear near the word "SEBI" and to carry at least six digits.

### Added

- `## Broker Identification` and `## Known Limitations` in the Rupeezy reference, plus a **Generic-to-Vortex constants mapping** (`EXCHANGE_MAP` / `PRODUCT_MAP` / `TRANSACTION_MAP` / `ORDER_TYPE_MAP` / `STATUS_MAP`) whose values are `Vc.*` **enum instances, not strings** — a string map would teach a Rule 15 violation. `STATUS_MAP` holds strings because statuses arrive as strings, and is documented as substring-matched.
- **CAS coverage in the broker reference**: deriving eligibility via `client.instruments.all_by_underlying("NSE_FO", underlying)` (Vortex exposes no CAS flag), a variety-by-time-window table for the closing auction, and the no-candles-3:15-to-3:30 warning on historical data.
- Section headings aligned to `BROKER_TEMPLATE.md` (`Authentication Pattern`, `Positions, Holdings, and Funds`, `Historical Data`, `Constants Mapping`, `Deployment Considerations`) — renames only, no content moved. `validate_broker_adapter.py` on the Rupeezy doc goes from **12 failures to 0**; the two surviving warnings (no SEBI number, SDK version not pinned) are left deliberately rather than papered over.

- **Rupeezy's confirmed closing-auction behaviour**, supplied by the maintainer and previously undocumented: Rupeezy **does not buffer** orders during the 3:15-3:20 transition — they are rejected, not queued and forwarded at 3:20; and **GTT orders stop triggering at 3:15 PM on CAS scrips**. Together these close the two workarounds a strategy would otherwise reach for, so the reference now states plainly that **no broker-side mechanism protects a cash position through the auction** on a CAS scrip. Recorded in the Rupeezy reference, in `indian-market.md` §1A's broker-layer section, and as a clause on Rule 3.
- **Order-endpoint rate limits** from `https://vortex.rupeezy.in/docs/latest/regular-order/`: place / modify / cancel / order book / order history / modify tags at 10/sec, and **cancel-multiple at 1/sec**. The 1/sec outlier is called out specifically because a SIGTERM handler cancelling every pending order at once walks straight into it — bulk cancels must be serialised and each confirmed, or shutdown reports success while live orders remain in the market. Also noted that order-book reads share the 10/sec budget with placement, reinforcing Rule 9's refresh-on-postback over polling.

- **Broker Identification now carries the real regulatory details** from `https://rupeezy.in`: registered entity Astha Credit & Securities Pvt Ltd, SEBI stockbroker registration **INZ000187932** (NSE, BSE, MCX), DP registration IN-DP-611-2021 (NSDL IN303420, CDSL 94500), exchange member codes NSE 12227 / BSE 6844 / MCX 40000, CIN, and registered office. With the regex fix above, `SEBI_REGISTRATION` now passes on the actual number rather than on a stray ISIN — the check is meaningful again.
- **`vortex-api>=2.1.8` stays a floor; pinning was considered and rejected.** Strategies should pick up SDK fixes without a docs change. The resulting `VERSION_NOT_PINNED` warning is knowingly accepted, and the Installation section now says so inline so a future contributor does not "fix" it to `==`.

### Notes

- Items still needing the maintainer, deliberately left as gaps rather than guessed: the public support contact, rate limits for non-order endpoints (trade book, positions, holdings, funds, quotes, historical candles, instrument master, margin — not published on the rate-limit page), request timeouts and retry semantics, and the specific CAS rejection code strings.
- `validate_broker_adapter.py` on the Rupeezy reference: **39/40 pass, 0 failures, 1 deliberately accepted warning.**

## [1.2.0] - 2026-08-28

### Added

- **Critical Rule 16 — "Cash-equity intraday exits must clear the Closing Auction Session."** SEBI's CAS framework went live in the cash segment on 3 August 2026 for securities with live derivative contracts. For those symbols continuous trading now ends at **3:15 PM**, not 3:30, and the closing price is set by a call auction: no order entry 3:15-3:20, limit + market 3:20-3:25, limit only from 3:25 to a system-driven random close between 3:28 and 3:30, matching 3:30-3:35, post-close moved to 3:50-4:00. The equity derivatives segment was **extended to 3:40 PM**. The skill had no awareness of any of this and would generate strategies that place exit orders into a book that no longer exists.
- **`references/indian-market.md` §1A "Closing Auction Session (CAS)"** — full phase timeline, the ±3% static reference-price band (VWAP of 3:00-3:15, a 15-minute window), order-type eligibility table, carry-forward and time-priority rules, equilibrium-price and matching-priority logic, per-exchange divergence, suspension cases, and an explicit broker-layer section. Sourced only to SEBI circular `SEBI/HO/47/11/11(3)2025-MRD-POD2/I/2765/2026` (16 Jan 2026), `NSE/CMTR/73362` (18 Mar 2026), NSE CAS FAQ v1.0 (May 2026) and BSE Notice 20260610-41 (10 Jun 2026) — several broker and news explainers published the wrong session length after go-live.
- Runtime CAS-eligibility derivation for Vortex (`client.instruments.all_by_underlying("NSE_FO", underlying)`), since the SDK exposes no CAS flag and the eligible list moves with SEBI's F&O reviews.
- **"Bar gaps on CAS scrips" (`indian-market.md` §1A) and CAS discontinuities in `backtesting.md`.** There are **no candles at all** for a CAS scrip between 3:15 and 3:30 PM — not empty bars, none — because no continuous matching occurs. Every consequence is a silent failure: `df.iloc[-1]` at 3:22 PM returns the 3:14 bar so "current price" is stale, "wait for the next bar" loops never fire, fixed bar-count lookbacks shift meaning, daily gap-detection alerts fire falsely, and `ffill()` fabricates prices that never traded. A CAS scrip yields ~360 one-minute bars a day against 375 for a non-CAS symbol, so multi-symbol panels must join on timestamp rather than position. The guidance is to drive all closing-window logic off `datetime.now(IST)`, never off bar arrival.
- **"Who You Are Talking To" section in `SKILL.md`** — states the reader's user is a trader, not a programmer, and derives the consequences (answerable questions, safe defaults instead of blocking, rupees not bare percentages, walk-throughs for anything the user must do themselves).
- **Mandatory pre-handover validation gate** — `scripts/validate_strategy.py` shipped since 1.0 and was referenced from nowhere in `SKILL.md`. It is now a required step in Strategy Output Format, with guidance on interpreting its per-file heuristics and a note that it does not cover the silent-until-live rules.
- **"Explaining the result" section** — what the README and the post-generation explanation must contain, since the README is the only artifact a non-programmer can read.

### Changed

- **Market hours are now segment-split everywhere.** `indian-market.md` (timings table, F&O bullet, segments table, DPR section, short-selling section, launch checklist, footer), `risk-management.md` (`should_exit_on_time` rewritten to take a `segment`, stop-loss section warning, key takeaways), `execution-alpha.md` (seasonality buckets, VWAP volume profile, iceberg warning, closing-window state machine), `strategy-patterns.md` (VWAP operating hours, IST market-hours block, stop-loss discipline).
- **Rules 3, 9, 10 and 12 gained CAS caveats.** Untriggered stop-loss and disclosed-quantity orders are cancelled by the exchange at 3:15 PM on CAS scrips, so a resting broker-side SL is not protection through the close (Rule 3) and the resulting burst of exchange-initiated `CANCELLED` postbacks must not be read as user cancellations (Rule 9). The auction's ±3% band is tighter than DPR and binds any auction-routed order (Rule 12).
- Rule 16 added to the silent-until-live list (now Rules 1, 11, 12, 13, 15, 16).
- Step 1 question 4 (deployment) rewritten in plain language with a default, so a non-programmer can answer it; question 5 (risk) now asks in rupees. Step 2 now requires confirming the strategy back to the user in plain English before writing code.
- Scaffolded `config.py`: the unused `market_close_time = "15:30"` replaced by `continuous_end_cash_cas` / `continuous_end_cash_non_cas` / `continuous_end_derivatives` plus `intraday_exit_buffer_minutes`.
- Graceful Shutdown now requires a session-aware square-off path that cannot report success on an unfilled exit.

### Fixed

- **Generated `main.py` crashed with `NameError` on every scaffold.** The template emitted `if "live" in LIVE:` — `LIVE` is a bare undefined name, produced by interpolating `strategy_type.upper()` into the generated source. **The branches were also inverted**: the `live` path called `strategy.backtest()` and vice versa. Replaced with a literal branch resolved at scaffold time. It passed `py_compile`, so `make test-scaffold` (which only checks that files exist) never caught it.
- **Scaffolded `Strategy.run()` / `.backtest()` exited silently.** Both stubs logged "not yet implemented" and returned, so `python main.py` completed with exit code 0 on a strategy that had no logic — indistinguishable from a working run for a non-programmer. They now raise `NotImplementedError` naming the fix.
- **The `.plugin` package shipped no `scripts/` directory at all.** `SKILL.md` instructs Claude to run `scripts/scaffold_strategy.py` (Rule 8) and `scripts/validate_strategy.py` (the new handover gate), and `CONTRIBUTING_BROKER.md` points at `scripts/validate_broker_adapter.py` — none of which existed for anyone who installed via the marketplace plugin, only for `.skill` installs. The Makefile's `plugin` target now stages `scripts/*.py`, and `SKILL_FILES` uses a wildcard so a newly added script can't silently fall out of both packages again.
- `BROKER_TEMPLATE.md` told broker contributors to validate their adapter with `validate_strategy.py` — the AST linter for generated strategy code, which cannot check a markdown adapter doc. Corrected to `scripts/validate_broker_adapter.py`.
- **`validate_strategy.py`'s timezone check passed on the exact bug Rule 7 warns about.** The condition was `'utc' in source.lower()`, so a strategy calling `datetime.utcnow()` — naive UTC, 5h30m off IST — satisfied the TIMEZONE check. It now looks for a real IST setup (`pytz` / `ZoneInfo` / `Asia/Kolkata` / `astimezone`) and adds a `NAIVE_DATETIME` check that flags `datetime.utcnow()`, `datetime.now()` and `date.today()` by name.
- `indian-market.md` claimed intraday positions are "forcibly closed by the exchange" at 3:29:59. Square-off is the broker's RMS on its own schedule; published cutoffs range from about 3:00 to 3:12 PM for CAS scrips and are policy, not regulation. Now documented as broker-specific and never to be hardcoded.
- `risk-management.md` stated a "4:00 PM NSE close". NSE continuous trading has never ended at 4:00 PM.
- `strategy-patterns.md` referred to "choppy 10-4 PM sessions" — no such session exists.
- Post-close session corrected from 3:40-4:00 to 3:50-4:00 (it moved for CAS and non-CAS securities alike).

### Notes

- The **Pre-Open Auction Session realignment is effective 7 September 2026** and is not yet in force. Documented in full as `indian-market.md` §1B: limit+market 9:00-9:05; limit only 9:05-9:10 with a system-driven random close in the last 2 minutes (9:08-9:10); matching 9:10-9:12; transition to CTS 9:12-9:15. It applies to the whole cash segment, not just CAS scrips, and it retires the 9:08 AM order-entry cutoff. Code touching pre-open must branch on the date; a backtest spanning the changeover needs both structures.
- Rupeezy/Vortex-specific CAS behaviour (order acceptance during 3:15-3:20, square-off timing, GTT triggers, rejection codes) is not covered by any circular and must be confirmed against Rupeezy's developer notes before live use.
- The auction print's exact timestamp, and whether the daily `close` field from a given historical API carries the equilibrium price, still vary by vendor — confirm against your own data source.
- Conflicts left deliberately hedged: NSE says IOC is not allowed in CAS while BSE's guidelines describe IOC orders inside CAS; the ±3% stock-futures band is NSE-sourced, not SEBI-sourced; the circuit-breaker CAS suspension and the "Buffer Period" label are BSE-only; the 3:10-3:40 derivatives closing VWAP comes from the NSE FAQ citing a circular that could not be retrieved.
- CHANGELOG gap: entries for 1.1.11 through 1.1.14 were never written; this entry follows 1.1.10.

## [1.1.10] - 2026-05-26

### Added

- **`OrderTracker` class** (canonical in `references/code-quality.md`; scaffolded as `order_tracker.py` for live strategies). Postback-driven, refreshes from orderbook + tradebook with 500 ms debounce, fires `on_terminal(order_id, status)` for every terminal transition. API: `initialize`, `on_update`, `on_terminal`, `wait(order_id, timeout)` (timeout required), `cancel_and_wait`, `status`/`order`/`fills`/`avg_fill_price`.
- **Scaffolder** generates `order_tracker.py` for `--type live`; wires it through `main.py` (`initialize` → `on_terminal` → connect feed) and adds an `on_order_terminal` method to `strategy.py` (replaces the empty `on_order_fill`/`on_order_cancel` stubs).

### Changed

- **Critical Rule 9 rewritten** — postback is a signal, orderbook is the truth. Names all five envelope types (`order`, `trade`, `sl_trigger`, `gtt_order`, `position_conversion`); strategy code refreshes from `client.orders()`/`client.trades()` instead of parsing `msg["data"]`; postbacks coalesced via 500 ms debounce. Live strategies use `on_terminal`; `wait()` reframed as a script/test primitive with required `timeout`.
- **Broker reference** Common Patterns rewritten around `OrderTracker.on_terminal` + `initialize()`; `orders()`/`order_history()` callouts now distinguish sleep-loop polling (anti-pattern) from postback-driven refresh (recommended).
- **SKILL.md halved** — 405 → 216 lines, ~5.5K → ~2.8K always-loaded tokens. No rules removed, only verbosity. Step-1, Code Architecture, Rule 8, Output Format, Backtesting Standards, and Proactive Suggestions rewritten as terse bullets.

### Fixed

- **Skill was teaching order-status polling.** `references/code-quality.md` shipped a `wait_for_order_fill()` that polled `broker.get_order_status()` in a `while time.sleep(0.5)` loop, with a docstring rationalising "polling instead of events to avoid callback hell". Rewritten as event-driven; Rule 9 and broker callouts now explicitly forbid sleep-loop polling.
- **Postback envelope shape.** Real payload is `{type, data, client_code}`; examples were reading the inner fields at the top level (would `KeyError` on real traffic). All examples now filter on `msg["type"]` and unwrap `msg["data"]`.
- **Thread-start race** in `OrderTracker.on_update` — `try/finally` resets `_worker_running` if `Thread.start()` raises, preventing silent permanent refresh stoppage.
- **`on_terminal` deduplication** via `_notified_terminal` set; an order staying terminal across multiple refreshes only fires the callback once.
- Stale `lookup_token(master, "RELIANCE", "NSE_EQ")` snippet in broker reference Common Patterns — now `ticker="NSE:RELIANCE"`.
- **`COMPLETED` vs `EXECUTED` alias** — same state under two names (postback envelope returns `COMPLETED`, `client.orders()` returns `EXECUTED`). `OrderTracker.TERMINAL` and `SUCCESS` now include both. Without this, the orderbook refresh would never fire `on_terminal` for filled orders.
- **Postback-vs-REST lag broke the reference `OrderTracker` on rejections** (field-test fix). Real-world: WS pushes `REJECTED` postbacks within ms of `place_order` returning, but `client.orders()` keeps returning `PENDING` for the same `order_id` for ~30 seconds. The previous "postback = signal, REST = truth" model missed rejections and let stale REST overwrite a terminal status. Reframed as **split authority**: postback `data.status` is authoritative for status transitions; REST is authoritative for fill quantities / prices. `OrderTracker.on_update` now fast-paths terminal `order` postbacks (mirrors payload into cache, fires `on_terminal` synchronously on the WS thread). `_apply` has a **downgrade guard**: once a terminal status is recorded, a later non-terminal REST row merges fill fields but does NOT overwrite `status`.
- **Substring terminal-status detection.** Brokers emit decorated forms (`REJECTED_BY_RMS`, `AMO_CANCELLED`, `EXECUTED_PARTIAL`). The previous strict set membership check missed these. `OrderTracker._terminal_token()` substring-matches against canonical tokens and normalises the stored `status` field; the original verbose form is preserved in `raw_status`.
- **Response envelope keys differ per endpoint** (field-test fix). `client.orders()` returns `{"orders": [...]}`, `client.trades()` returns `{"trades": [...]}` — NOT `{"data": [...]}` (which is the holdings/positions/funds shape). `OrderTracker._orders_rows()` / `_trades_rows()` chain through the common key names. Broker reference gains an explicit "Endpoint response envelope keys" table.
- **SDK signature drift since 2.1.8** (field-test fixes). `client.orders()` and `client.trades()` now require `(limit, offset)` positional args (raises `TypeError` if omitted); `OrderTracker._fetch_orderbook` / `_fetch_tradebook` try the new form and fall back to no-args on `TypeError`. `place_order`'s `disclosed_quantity` is REQUIRED (broker reference parameter table updated). `get_order_margin` response is flat (`{"required_margin", "available_margin", "status"}`) — not nested under `"data"`; broker reference example rewritten to use the flat shape and dropped the `funds()` double-call.
- **Rejection reason field name varies by surface** (field-test fix). Postback envelope uses `status_message`; REST orderbook row uses `error_reason`; `place_order` response uses `message`. Added `OrderTracker.rejection_reason(order_id)` accessor that walks the chain. Scaffolded `strategy.py.on_order_terminal` uses it. Broker reference Order Rejection section documents all three field names with a table.
- **Instrument master quirks** (field-test fix). `expiry_date` is `YYYYMMDD` in the master CSV, ISO in REST orderbook rows, and `"29May2026"` in postbacks for the same contract. Documented in the broker reference Instrument Master section with a recommendation to lexicographically compare master-CSV expiry strings instead of parsing. Futures rows use `option_type='XX'` (sometimes `'  '`), not `None`/`""` — documented the robust filter idiom.
- **`funds()` unreliable as a margin-availability source** (field-test fix). On some accounts it returned `{}` with no buckets — would `KeyError` on `funds()["data"]["equity"]["margin_available"]`. Broker reference Margin Check example rewritten to read `available_margin` directly from `get_order_margin`'s response (one round-trip, stable shape) and explicitly warn against the funds()-double-call pattern.
- **Scaffolded `config.py` now calls `load_dotenv()` at module top** (field-test fix). Previously a caller importing `config.py` before `auth.py` would read empty env vars. config.py uses a `try: from dotenv import load_dotenv` guard so it's harmless on container deployments. `auth.py` no longer duplicates the call; it just `import config` for the side-effect. `requirements.txt` keeps `python-dotenv` in both deployments so the import is always available. Documented that the PyPI package is `python-dotenv` (NOT `dotenv` — separate, unrelated package).
- **Typed-enum gotcha on `Vc.*` constants** (field-test fix). The Vortex SDK runtime-typechecks `transaction_type`, `product`, `variety`, `validity`, `mode`, `exchange`, `resolution` via strict `isinstance(value, EnumClass)` at `vortex_api/api.py:147`. Passing the string value (e.g. `"INTRADAY"`) raises `TypeError: product must be of type ProductTypes` even though the enum's `.value` IS `"INTRADAY"`. Silent until first live `place_order` / `get_order_margin` — `py_compile` and unit tests pass. Fixes: scaffolded `config.py` now stores `default_product` / `default_variety` / `default_validity` / `default_transaction` as `Vc.*` enum instances (typed annotations + correct defaults), so `client.place_order(product=config.default_product, ...)` works as-written. Added new **Critical Rule 15** to `SKILL.md` and a "Vc.* constants are runtime-typed enums" entry under broker reference "Field-format quirks" with the name-vs-value pitfall called out (`Vc.VarietyTypes.REGULAR_LIMIT_ORDER.value == "RL"` — name and value differ for many enums). Constants Reference table gained a "pass the enum, not the value" callout.

## [1.1.9] - 2026-05-26

### Changed

- **Eliminated five places where the skill contradicted itself on the loopback OAuth login.** A clean read by an LLM consumer could previously interpret the manual auth-code paste flow as compliant. Specifically:
  - Step 1 question 4 — "default to the loopback SSO pattern" rewritten as a hard `MUST` with an explicit decision tree ("self-hosted → ship login.py + auth.py" vs "container → don't"). Headless / SSH-only edge case is called out as non-exempting.
  - Code Architecture diagram — the `(self-hosted only)` parenthetical that read as "optional" replaced with two explicit deployment-keyed file lists labelled `REQUIRED`.
  - Critical Rule 8 — promoted from "use the loopback SSO login" (suggestion-flavoured) to "Self-hosted strategies MUST ship login.py + auth.py — no exceptions". Adds an explicit list of patterns that are forbidden (`input("auth code: ")`, `VORTEX_ACCESS_TOKEN` in `.env`, `broker.py` with a manual auth_code parameter) and rebuts three common edge-case excuses (headless box, "portal might not allow localhost", minimal-deps).
  - Strategy Output Format (the section LLMs use as the final file checklist) — was omitting `login.py` and `auth.py` entirely. Now shows two deployment-keyed file lists; container packages explicitly **must not** include `login.py`/`auth.py`.
  - `references/brokers/rupeezy-vortex.md` — deleted the "Advanced (only when the loopback server can't run)" escape hatch that explicitly told the LLM "headless → fall back to manual paste"; replaced with the SSH port-forward recipe. Collapsed the duplicate "Authentication / Self-Hosted OAuth Flow" subsection that was contradicting the Deployment Modes section above it.

## [1.1.7] - 2026-05-26

### Added

- **Loopback SSO login pattern for self-hosted strategies.** New critical Rule 8 in `SKILL.md` requires shipping a `login.py` that spins up a stdlib `HTTPServer` on `127.0.0.1:8765/callback`, opens the SSO URL in the browser, and exchanges the captured `auth_token` for an `access_token` automatically. End users never see either token. Strategies read the cached token via `auth.get_client()`. Eliminates the most common end-user bug (confusing `auth_token` with `access_token`).
- `scripts/scaffold_strategy.py` gained a `--deployment {self-hosted,container}` flag (default `self-hosted`). Self-hosted scaffolds ship `login.py` + `auth.py`; `main.py` calls `get_client()`; `.env.example` carries `VORTEX_API_KEY` + `VORTEX_APPLICATION_ID`; `requirements.txt` pulls in `python-dotenv`. Container scaffolds **skip** the login files entirely: `main.py` does zero-arg `VortexAPI()` (platform injects `VORTEX_ACCESS_TOKEN`), `.env.example` warns against putting broker credentials in `.env`, and `python-dotenv` is dropped from `requirements.txt`. "Next steps" output branches accordingly.
- `references/brokers/rupeezy-vortex.md` Self-Hosted section rewritten with full `login.py` + `auth.py` code listings; manual OAuth flow demoted to an "advanced/headless only" footnote.

### Changed

- **Ticker-first guidance for vortex-api >= 2.1.8.** Critical Rule 1 in `SKILL.md` and the entire `references/brokers/rupeezy-vortex.md` reference now teach identifying instruments by ticker (`"NSE:RELIANCE"`) instead of `(exchange, token)` pairs. Updated examples:
  - `place_order(ticker=...)`, `historical_candles(ticker=...)`, `get_order_margin(ticker=...)`
  - `client.quotes(instruments=["NSE:RELIANCE"], ...)` — tickers accepted directly
  - `wire.subscribe(ticker=..., mode=...)` and reading `tick["ticker"]` from VortexFeed updates
  - `client.instruments.get_by_ticker(...)` / `get_by_exchange_token` / `get_by_isin` / `all_by_underlying` / `filter` replace hand-rolled CSV scanning
- Replaced the broken `from vortex import Client` + `master[master['tradingsymbol']==…]` snippet in `references/backtesting.md` with a working ticker-form `historical_candles` call.
- `references/indian-market.md` tick-size lookup, data-sources table, and "Always download fresh instrument master" sections now point to `client.instruments` for Vortex while remaining broker-agnostic.
- `scripts/validate_strategy.py` — the "hardcoded token" violation message now recommends the ticker form first, with `client.instruments.get_by_ticker(...)` as the metadata-access path.
- Documented the IDX ticker convention for indices (`"NSE:NIFTYIDX"`, `"NSE:BANKNIFTYIDX"`, `"BSE:SENSEXIDX"`) — the suffix lives on the ticker, the underlying symbol stays bare.
- Bumped `requirements.txt` example from `vortex-api>=1.0.0` to `vortex-api>=2.1.8`.

### Notes

- Legacy `(exchange, token)` form is still accepted by the SDK but emits `FutureWarning`. One legacy example is retained per surface (orders, websocket) so users on older code can recognise the deprecated pattern.

## [1.1.4] - 2026-03-31

### Changed

- Restructured repo to native plugin layout (skill files under `skills/indian-algo-trading/`)
- Repo is now directly installable as a Cowork marketplace — no build step needed
- Updated Makefile for new directory structure

## [1.1.1] - 2026-03-31

### Added

- `marketplace.json` for plugin discoverability in marketplaces
- Dual packaging: `.skill` (platform-agnostic) and `.plugin` (Claude + Rupeezy MCP)
- `.mcp.json` bundling Rupeezy Trading and Strategy Platform MCP servers
- Makefile with `skill`, `plugin`, `all`, `release`, `validate`, and `test-scaffold` targets
- CONTRIBUTING_BROKER.md — step-by-step guide for adding broker adapters with AI prompt template
- `validate_broker_adapter.py` — automated broker adapter validation script

### Changed

- Removed MCP tool docs from `rupeezy-vortex.md` (auto-discovered via `.mcp.json`)

## [1.0.0] - 2026-03-31

### Added

**Core Skill**

- SKILL.md with pre-flight checklist, reference routing table, 13 critical rules, and code architecture patterns
- Progressive disclosure: 290-line brain routes to 16 reference files by context

**Reference Files (16)**

- `strategy-patterns.md` — 6 core + 5 advanced strategy patterns with code skeletons
- `risk-management.md` — position sizing (fixed fractional, ATR, Kelly Lite), drawdown controls, F&O margin monitoring
- `indian-market.md` — market timings, expiry calendar, STT rates FY 2025-26, circuit limits, auction risk, tick sizes, DPR, NSE no-API rule
- `backtesting.md` — library selection guide, realistic transaction costs, parameter optimization
- `error-handling.md` — order state machine, partial fills, graceful shutdown, state persistence
- `code-quality.md` — project structure, logging, pytest patterns, config management
- `options-greeks.md` — Black-Scholes, delta-neutral, gamma scalping, theta harvesting, IV vs RV
- `regime-detection.md` — HMM for 3 regimes, strategy decay via rolling Sharpe
- `india-data-edge.md` — FII/DII flows, OI analysis, PCR, max pain, delivery %, rollover, GIFT Nifty
- `execution-alpha.md` — TWAP, VWAP, iceberg, impact cost, NSE intraday timing patterns
- `robustness-testing.md` — walk-forward optimization, Monte Carlo, sensitivity analysis
- `portfolio-construction.md` — multi-strategy allocation, correlation-aware sizing, decay rotation
- `psychological-guardrails.md` — daily loss breaker, consecutive loss pause, weekly throttle, killswitch
- `tax-optimization.md` — STCG vs LTCG (20% vs 12.5%), tax-loss harvesting, F&O business income
- `python-performance.md` — vectorization, Numba JIT, Polars, async, profiling workflow

**Broker Support**

- `brokers/rupeezy-vortex.md` — full Vortex SDK reference (primary broker)
- `brokers/BROKER_TEMPLATE.md` — 12-section template for community broker adapters
- `brokers/CONTRIBUTING_BROKER.md` — step-by-step guide for adding a new broker with AI prompt template, verification checklist, and maintainer review process

**Scripts**

- `validate_strategy.py` — AST-based linter checking for hardcoded tokens, missing stop-loss, print statements, NSE scraping, tick size rounding
- `validate_broker_adapter.py` — validates broker adapter docs against template structure, checks for placeholders, constants completeness, OAuth flow documentation
- `scaffold_strategy.py` — generates best-practice project skeleton with main.py, strategy.py, risk_manager.py, guardrails.py, config.py, tests/

**Assets**

- `assets/strategy_template/` — 9 standalone template files matching scaffold output, browsable as reference

**Evals**

- `evals/evals.json` — 10 test prompts with 65 assertions covering all critical skill capabilities

**Governance**

- CONTRIBUTING.md with 6 contribution types, trust tiers, DCO, code of conduct
- Strategy patterns are core-team only (not open for community contribution)
- Apache 2.0 license
