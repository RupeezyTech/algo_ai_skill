# Contributing to Indian Algo Trading Skill

**Thank you for considering a contribution!** This is a high-stakes project—trading strategies and market data directly impact people's finances. All contributions require review and testing.

## Contribution Types & Review Requirements

### 1. Market Data Updates (STT rates, lot sizes, expiry rules)
- **Scope**: Updates to compliance rules, regulatory changes, broker-specific limits
- **Requirements**:
  - Include direct link to SEBI/exchange circular or official announcement
  - Update reference file + CHANGELOG.md with date and source
  - 1 maintainer review ✓
- **Fast-tracked**: Regulatory changes approved within 48 hours

> **This skill does not ship pre-built strategies.** The skill's purpose is to help end users create their own strategies with best practices baked in. The `references/strategy-patterns.md` file contains educational patterns and code skeletons that teach the AI how to help users — it is not a library of ready-to-deploy strategies. Strategy-related content is maintained by the core team only and is not open for community contribution. If you have ideas for improving the educational patterns, open a GitHub Discussion.

### 2. New Broker Adapters
- **Scope**: Integration with new brokers or APIs
- **Start here**: [How to Contribute a Broker Adapter](references/brokers/CONTRIBUTING_BROKER.md) — step-by-step guide with AI prompt template
- **Requirements**:
  - Follow `BROKER_TEMPLATE.md` exactly
  - Unit tests covering authentication, order placement, position fetching, order cancellation (>80% code coverage)
  - Test suite must run with mock API (no live broker calls)
  - Documentation with connection example
  - 2 maintainer reviews ✓
- **Time to approve**: 2–3 weeks

### 3. Core Skill Changes (SKILL.md)
- **Scope**: Changes to skill instruction, default behavior, or teaching philosophy
- **Requirements**:
  - Open GitHub Discussion with RFC (Request for Comments)
  - 7-day community feedback period
  - 2 maintainer reviews + 1 core team review ✓
- **Time to approve**: 3–4 weeks minimum

### 4. Reference File Updates
- **Scope**: Corrections, clarifications, new sections in existing reference files
- **Requirements**:
  - Source citation if factual
  - Clear changelog entry
  - 1 maintainer review ✓
- **Time to approve**: 1 week

### 5. Scripts & Tooling
- **Scope**: Backtesting scripts, analysis tools, data utilities
- **Requirements**:
  - Unit tests with >80% code coverage
  - Documented usage with examples
  - 1 maintainer review ✓
- **Time to approve**: 1–2 weeks

### 6. Documentation & Examples
- **Scope**: Tutorials, READMEs, example strategies, explanations
- **Requirements**:
  - Clear, accurate, beginner-friendly
  - Example code tested and runnable
  - 1 maintainer review ✓
- **Time to approve**: 1 week

## Trust Tiers & Path to Maintainer

```
Contributor
    ↓ (5+ merged PRs, consistent quality)
Reviewer (can approve most PRs, needs 1 core team sign-off)
    ↓ (Invited by core team)
Maintainer (can approve PRs independently, manages releases)
    ↓ (Founders only)
Core Team (sets strategy, RFC decisions)
```

## What We Will NOT Accept

### Hard Rejections (instant close):
- **Strategy contributions**: Pre-built strategies, new strategy patterns, or modifications to strategy logic (core-team only)
- **Return guarantees**: "This strategy makes X% CAGR guaranteed" or similar claims
- **Strategies without risk management**: No stop-loss, position sizing, or drawdown limits
- **Hardcoded credentials**: API keys, passwords, tokens (even masked with `****`)
- **Unverified market data**: Lot sizes, STT rates, or rules without official source
- **Platform-specific language**: "Claude will..." or "ChatGPT should..." (use "the AI" or "the user")
- **NSE/BSE web scraping code**: Use official APIs or licensed data providers only
- **Discriminatory or harassing content**: See Code of Conduct below

### High-Scrutiny Items (may reject after review):
- Strategies with Sharpe < 0.5 or max drawdown > 30%
- Adapters for brokers without clear API documentation
- Code with >20% code duplication
- Documentation without examples

## Submission Process

### For All Contributions:

1. **Fork** the repository
2. **Create a feature branch**: `git checkout -b add/momentum-strategy` or `fix/lot-size-nse`
3. **Make changes** and commit with clear messages:
   ```bash
   git commit -m "Add momentum strategy with mean-reversion filter (backtest: 2020–2024, Sharpe 1.2)"
   ```
4. **Run tests** (if applicable):
   ```bash
   pytest tests/ -v --cov=adapters,examples
   pylint adapters/ examples/
   ```
5. **Push** to your fork and **open a Pull Request**

### PR Template

```markdown
## Description
[What does this change do? Why is it needed?]

## Type of Change
- [ ] Market data update (requires source link)
- [ ] New broker adapter (requires tests)
- [ ] Core skill change (requires RFC discussion)
- [ ] Reference file update
- [ ] Script/tooling
- [ ] Documentation/example

## Testing
[For strategies]: Backtest period, Sharpe ratio, max drawdown, win rate
[For adapters]: How to test (mock API, test broker, etc.)
[For other]: How did you validate this change?

## Checklist
- [ ] Code follows project style (see STYLE.md)
- [ ] Tests pass locally (`pytest tests/ -v`)
- [ ] No hardcoded credentials
- [ ] Documentation updated (if applicable)
- [ ] No return guarantees or unsupported claims
- [ ] Source links included (if data/regulatory)

## Reviewer Notes
[Any specific guidance for reviewers?]
```

## Issue Template

```markdown
## Issue Type
- [ ] Bug report
- [ ] Feature request
- [ ] Question
- [ ] Data correction

## Description
[What's the problem or idea?]

## Expected Behavior
[What should happen?]

## Actual Behavior (if bug)
[What happens instead?]

## Steps to Reproduce (if bug)
1.
2.
3.

## Environment (if applicable)
- Python version:
- Broker:
- OS:

## Additional Context
[Backtest link, error stack trace, reference, etc.]
```

## Developer Certificate of Origin (DCO)

By contributing, you certify that you wrote the code or have the right to submit it under the Apache 2.0 license. Sign commits with `-s`:

```bash
git commit -s -m "Add momentum strategy"
```

This adds: `Signed-off-by: Your Name <email@example.com>`

**No DCO = PR will not be merged.** It protects us legally and ensures code ownership is clear.

## Code of Conduct

We are committed to a welcoming and inclusive community. By participating, you agree to:

- Treat all participants with respect, regardless of background, identity, or experience level
- Give and receive constructive feedback gracefully
- Report harassment or discrimination to maintainers immediately
- Assume good faith; ask clarifying questions rather than making accusations

**Unacceptable behavior** includes:
- Harassment, discrimination, or abusive language
- Deliberate misinformation or manipulation
- Spamming or commercial solicitation
- Doxxing or sharing personal information without consent

**Enforcement**: Violations may result in warning, PR rejection, or banning from the project.

See [Contributor Covenant 2.1](https://www.contributor-covenant.org/version/2-1/code_of_conduct/) for full details.

## Reviewer Expectations

Reviewers (trust tier 2+) are expected to:
- Review within 7 days of submission
- Check code quality, test coverage, and documentation
- Verify claims with citations (for regulatory changes, backtest metrics)
- Run tests locally when applicable
- Be respectful and constructive in feedback
- Escalate high-risk PRs (new strategies, adapter changes) to 2+ reviewers

## Release Cycle

- **Patch** (0.0.x): Bug fixes, documentation updates, market data corrections
- **Minor** (0.x.0): New broker adapters, reference improvements, scripts
- **Major** (x.0.0): Core skill changes, major API refactors, architecture shifts

Releases tagged with semantic versioning; changelog maintained in `CHANGELOG.md`.

## Questions?

- **Regulatory/compliance**: Open a Discussion or contact maintainers@opentrading.dev
- **Strategy feedback**: Backtest results forum (GitHub Discussions)
- **Technical help**: GitHub Issues with `[help-wanted]` tag

## Attribution

Contributors are credited in `CONTRIBUTORS.md` and README.md milestone notes.

Thank you for making Indian Algo Trading safer and better for everyone.

---

**Last updated**: March 2026 | Maintained by @opentrading/core-team
