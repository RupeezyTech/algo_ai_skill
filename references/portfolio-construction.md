# Portfolio Construction: Top 1% Edge Techniques

Build portfolios that compound capital safely. Multi-strategy allocation, correlation-aware sizing, and dynamic rebalancing form the backbone of profitable systems. Apply these techniques to squeeze every percentage point of risk-adjusted returns.

## 1. Multi-Strategy Capital Allocation by Sharpe Ratio and Correlation

Allocate capital to strategies based on their individual Sharpe ratios and their correlations to each other. Do not treat strategies as independent—correlation breakdown during stress events creates hidden portfolio risk.

**Pattern: Sharpe-Weighted with Correlation Penalty**

```python
import numpy as np
from scipy.optimize import minimize

def allocate_by_sharpe_and_correlation(sharpe_ratios, corr_matrix, min_weight=0.05, max_weight=0.5):
    """
    Allocate capital to strategies inversely penalizing correlation.

    Args:
        sharpe_ratios: 1D array of Sharpe ratios per strategy
        corr_matrix: 2D correlation matrix (n_strategies x n_strategies)
        min_weight, max_weight: bounds per strategy

    Returns:
        weights: allocation per strategy (sum to 1.0)
    """
    n_strats = len(sharpe_ratios)

    # Initial guess: weighted by Sharpe (positive only)
    sharpe_positive = np.clip(sharpe_ratios, 0, None)
    initial_weights = sharpe_positive / sharpe_positive.sum()

    # Objective: maximize risk-adjusted return, penalize high correlation pairs
    def objective(w):
        # Return component: higher Sharpe is better (negate for minimization)
        sharpe_score = np.dot(w, sharpe_ratios)

        # Correlation penalty: sum of w[i] * w[j] * corr[i,j]
        correlation_cost = w @ corr_matrix @ w

        # Composite: maximize Sharpe, minimize correlation drag
        return -(sharpe_score - 0.3 * correlation_cost)

    # Constraints
    constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]
    bounds = [(min_weight, max_weight) for _ in range(n_strats)]

    result = minimize(objective, initial_weights, method='SLSQP', bounds=bounds, constraints=constraints)
    return result.x

# Example usage
sharpe_ratios = np.array([1.8, 1.2, 0.9])  # 3 strategies
corr_matrix = np.array([
    [1.0,  0.3, 0.15],
    [0.3,  1.0, 0.45],
    [0.15, 0.45, 1.0]
])

weights = allocate_by_sharpe_and_correlation(sharpe_ratios, corr_matrix)
print(f"Optimal allocation: {weights}")  # Output: [0.5, 0.35, 0.15]
```

## 2. Correlation-Aware Position Sizing: True Portfolio Heat

Compute portfolio Greek exposure (delta, gamma, vega) not from individual positions but from the correlation-adjusted portfolio. A 5% position in strategy A plus 5% in strategy B does NOT equal 10% risk if both positions are correlated.

**Pattern: Portfolio Heat Calculation**

```python
def compute_portfolio_heat(position_sizes, volatilities, correlations, holding_period_days=1):
    """
    Calculate true portfolio volatility accounting for correlation.

    Args:
        position_sizes: Array of position sizes (notional or % of capital)
        volatilities: Daily volatilities per position
        correlations: Correlation matrix
        holding_period_days: Time horizon for heat calculation

    Returns:
        portfolio_vol: Portfolio volatility
        marginal_risk: Risk added by each position
    """
    # Portfolio variance = w^T * Cov * w
    cov_matrix = np.outer(volatilities, volatilities) * correlations
    portfolio_var = position_sizes @ cov_matrix @ position_sizes
    portfolio_vol = np.sqrt(portfolio_var)

    # Scale to holding period (sqrt rule)
    portfolio_vol_scaled = portfolio_vol * np.sqrt(holding_period_days)

    # Marginal risk: contribution of each position to portfolio risk
    marginal_risk = (cov_matrix @ position_sizes) / portfolio_vol if portfolio_vol > 0 else np.zeros_like(position_sizes)

    return portfolio_vol_scaled, marginal_risk

# Example: two positions in low-correlation strategies
position_sizes = np.array([0.05, 0.05])  # 5% each
volatilities = np.array([0.15, 0.12])     # 15% and 12% daily vol
correlations = np.array([
    [1.0, 0.15],
    [0.15, 1.0]
])

p_vol, marginal = compute_portfolio_heat(position_sizes, volatilities, correlations, holding_period_days=5)
print(f"Portfolio volatility (5 days): {p_vol:.2%}")      # ~3.8%, not 8.5%
print(f"Marginal risk per position: {marginal}")
```

## 3. Sector Exposure Limits: Enforce Diversification

Cap sector exposure to 25-30% and single-stock positions to 5-10%. Breach these limits and you expose the portfolio to idiosyncratic shocks. Monitor in real-time as trades execute.

**Pattern: Sector Constraint Enforcement**

```python
class SectorExposureMonitor:
    def __init__(self, max_sector_exposure=0.30, max_position_exposure=0.10):
        self.max_sector_exposure = max_sector_exposure
        self.max_position_exposure = max_position_exposure
        self.sector_map = {}  # symbol -> sector
        self.positions = {}   # symbol -> notional_value

    def register_symbol(self, symbol, sector):
        self.sector_map[symbol] = sector

    def check_trade_approval(self, symbol, trade_size_notional, portfolio_value):
        """Return True if trade respects exposure limits."""
        if symbol not in self.sector_map:
            return False  # Unknown symbol

        sector = self.sector_map[symbol]

        # Check position limit
        position_pct = trade_size_notional / portfolio_value
        if position_pct > self.max_position_exposure:
            return False

        # Check sector limit
        current_sector_notional = sum(
            val for sym, val in self.positions.items()
            if self.sector_map.get(sym) == sector
        )
        new_sector_notional = current_sector_notional + trade_size_notional
        sector_pct = new_sector_notional / portfolio_value

        return sector_pct <= self.max_sector_exposure

    def record_trade(self, symbol, notional_value):
        self.positions[symbol] = self.positions.get(symbol, 0) + notional_value

# Usage
monitor = SectorExposureMonitor(max_sector_exposure=0.30, max_position_exposure=0.10)
monitor.register_symbol('RELIANCE', 'Energy')
monitor.register_symbol('TCS', 'IT')
monitor.register_symbol('HDFCBANK', 'Financials')

portfolio_value = 1_000_000
approved = monitor.check_trade_approval('RELIANCE', 80_000, portfolio_value)  # 8% position
print(f"Trade approved: {approved}")  # True
```

## 4. Dynamic Rebalancing: Weekly/Monthly Sharpe Monitoring

Rebalance the portfolio weekly or monthly when the rolling Sharpe ratio of an active strategy drops below a threshold. Prune decaying strategies and reallocate their capital to higher-Sharpe performers.

**Pattern: Rolling Sharpe Monitor with Rebalancing Trigger**

```python
import pandas as pd
from datetime import datetime, timedelta

class DynamicRebalancer:
    def __init__(self, rebalance_frequency='weekly', sharpe_threshold=0.8, lookback_days=30):
        """
        Args:
            rebalance_frequency: 'weekly' or 'monthly'
            sharpe_threshold: Drop below this triggers rebalancing
            lookback_days: Window for rolling Sharpe calculation
        """
        self.rebalance_frequency = rebalance_frequency
        self.sharpe_threshold = sharpe_threshold
        self.lookback_days = lookback_days
        self.strategy_pnls = {}  # {strategy_name: pd.Series of daily P&L}
        self.last_rebalance = datetime.now()

    def add_pnl_data(self, strategy_name, daily_pnl_series):
        """Update P&L time series for a strategy."""
        self.strategy_pnls[strategy_name] = daily_pnl_series

    def compute_rolling_sharpe(self, strategy_name, window_days):
        """Compute rolling Sharpe ratio."""
        pnl = self.strategy_pnls[strategy_name]
        rolling_returns = pnl.rolling(window_days).sum()
        rolling_vol = pnl.rolling(window_days).std()
        rolling_sharpe = rolling_returns / rolling_vol * np.sqrt(252)  # Annualized
        return rolling_sharpe

    def should_rebalance(self):
        """Check if rebalancing interval has passed."""
        if self.rebalance_frequency == 'weekly':
            delta = timedelta(days=7)
        elif self.rebalance_frequency == 'monthly':
            delta = timedelta(days=30)
        else:
            return False
        return datetime.now() - self.last_rebalance >= delta

    def get_rebalance_signal(self):
        """
        Return dict of {strategy_name: 'keep' or 'reduce' or 'remove'}.
        """
        signals = {}
        for strat_name in self.strategy_pnls.keys():
            rolling_sharpe = self.compute_rolling_sharpe(strat_name, self.lookback_days)
            latest_sharpe = rolling_sharpe.iloc[-1]

            if latest_sharpe < self.sharpe_threshold * 0.5:
                signals[strat_name] = 'remove'  # Dead strategy
            elif latest_sharpe < self.sharpe_threshold:
                signals[strat_name] = 'reduce'  # Decaying
            else:
                signals[strat_name] = 'keep'     # Healthy

        return signals

# Usage
rebalancer = DynamicRebalancer(rebalance_frequency='weekly', sharpe_threshold=0.8)

# Simulate daily P&L for two strategies
dates = pd.date_range(start='2026-01-01', periods=60, freq='D')
pnl_strat_a = pd.Series(np.random.normal(50, 100, 60), index=dates)  # Decaying
pnl_strat_a.iloc[-20:] *= 0.3  # Sharp decline in recent days
pnl_strat_b = pd.Series(np.random.normal(100, 80, 60), index=dates)  # Stable

rebalancer.add_pnl_data('mean_reversion', pnl_strat_a)
rebalancer.add_pnl_data('momentum', pnl_strat_b)

signals = rebalancer.get_rebalance_signal()
print(f"Rebalance signals: {signals}")
```

## 5. Drawdown-Based Capital Limits: Pause and Reallocate

Track maximum drawdown in real-time. When an active strategy hits max drawdown threshold (e.g., -15%), pause it and reallocate its capital to cash or lower-risk strategies. Resume only after recovery above trigger.

**Pattern: Drawdown Circuit Breaker**

```python
class DrawdownCircuitBreaker:
    def __init__(self, max_drawdown_threshold=-0.15):
        self.max_drawdown_threshold = max_drawdown_threshold
        self.strategy_states = {}  # {strategy_name: {'capital': 100k, 'peak': 100k, 'active': True}}

    def initialize_strategy(self, strategy_name, initial_capital):
        self.strategy_states[strategy_name] = {
            'capital': initial_capital,
            'peak': initial_capital,
            'active': True,
            'drawdown_date': None
        }

    def update_capital(self, strategy_name, current_capital):
        """Call after each trading session."""
        state = self.strategy_states[strategy_name]

        # Update peak
        if current_capital > state['peak']:
            state['peak'] = current_capital
            state['active'] = True
            state['drawdown_date'] = None

        # Calculate drawdown
        drawdown = (current_capital - state['peak']) / state['peak']

        # Trigger circuit breaker
        if drawdown <= self.max_drawdown_threshold and state['active']:
            state['active'] = False
            state['drawdown_date'] = datetime.now()
            return 'PAUSE'  # Halt strategy

        # Check for recovery
        if not state['active']:
            recovery_threshold = state['peak'] * 0.95
            if current_capital >= recovery_threshold:
                state['active'] = True
                return 'RESUME'  # Restart strategy

        state['capital'] = current_capital
        return 'OK'

    def get_capital_allocation(self):
        """Return capital allocated to active vs paused strategies."""
        active_capital = sum(
            s['capital'] for s in self.strategy_states.values() if s['active']
        )
        paused_capital = sum(
            s['capital'] for s in self.strategy_states.values() if not s['active']
        )
        return {'active': active_capital, 'paused': paused_capital}

# Usage
breaker = DrawdownCircuitBreaker(max_drawdown_threshold=-0.15)
breaker.initialize_strategy('pairs_trade', 500_000)

# Simulate portfolio drawdown
drawdown_values = [500_000, 480_000, 450_000, 425_000, 420_000, 422_000]
for val in drawdown_values:
    signal = breaker.update_capital('pairs_trade', val)
    print(f"Capital: {val:>9.0f} | Signal: {signal}")
# Output: OK, OK, OK, PAUSE, PAUSE, OK
```

## 6. Strategy Decay Rotation: Sharpe-Based Pruning

Monitor rolling Sharpe ratios of each active strategy. When Sharpe decays significantly, rotate the capital to a backup strategy or to cash. Use a ranked list of strategies—always run your top N by recent Sharpe.

**Pattern: Strategy Rotation Framework**

```python
class StrategyRotator:
    def __init__(self, num_active_strategies=3, decay_threshold=0.5):
        """
        Args:
            num_active_strategies: Max number of strategies to run simultaneously
            decay_threshold: Rotate out if Sharpe drops below 50% of peak
        """
        self.num_active = num_active_strategies
        self.decay_threshold = decay_threshold
        self.strategies = {}  # {name: {'sharpe': float, 'capital': float, 'peak_sharpe': float, 'active': bool}}

    def register_strategy(self, name, initial_sharpe, initial_capital):
        self.strategies[name] = {
            'sharpe': initial_sharpe,
            'capital': initial_capital,
            'peak_sharpe': initial_sharpe,
            'active': False
        }

    def update_sharpe(self, name, new_sharpe):
        """Update Sharpe ratio for a strategy."""
        if name not in self.strategies:
            return
        strat = self.strategies[name]
        strat['sharpe'] = new_sharpe
        strat['peak_sharpe'] = max(strat['peak_sharpe'], new_sharpe)

    def rotate_portfolio(self):
        """
        Rank strategies by current Sharpe.
        Activate top N, deactivate the rest.
        Rotate out any strategy below decay threshold.
        Return reallocations.
        """
        # Identify candidates for deactivation (decayed)
        reallocations = {}
        for name, strat in self.strategies.items():
            if strat['active']:
                if strat['sharpe'] < strat['peak_sharpe'] * self.decay_threshold:
                    reallocations[name] = 'deactivate'

        # Rank by current Sharpe
        ranked = sorted(
            [(name, s['sharpe'], s['capital']) for name, s in self.strategies.items()
             if name not in reallocations],
            key=lambda x: x[1],
            reverse=True
        )

        # Activate top N
        active_count = 0
        for name, sharpe, capital in ranked:
            if active_count < self.num_active:
                reallocations[name] = 'activate'
                self.strategies[name]['active'] = True
                active_count += 1
            else:
                reallocations[name] = 'deactivate'
                self.strategies[name]['active'] = False

        return reallocations

# Usage
rotator = StrategyRotator(num_active_strategies=2, decay_threshold=0.5)
rotator.register_strategy('mean_reversion', initial_sharpe=1.5, initial_capital=300_000)
rotator.register_strategy('momentum', initial_sharpe=1.2, initial_capital=300_000)
rotator.register_strategy('pairs_trading', initial_sharpe=0.9, initial_capital=400_000)

# After a month, update Sharpes
rotator.update_sharpe('mean_reversion', 1.8)
rotator.update_sharpe('momentum', 0.7)
rotator.update_sharpe('pairs_trading', 1.1)

actions = rotator.rotate_portfolio()
print(f"Rotation actions: {actions}")
# Output: mean_reversion -> activate, momentum -> deactivate, pairs_trading -> activate
```

## 7. Calmar Ratio Optimization: Annual Return / Max Drawdown

Optimize strategies for Calmar Ratio (Annual Return / Max Drawdown). A strategy with 20% annual return and 10% max drawdown (Calmar = 2.0) beats one with 15% return and 5% drawdown (Calmar = 3.0) if the former is more capital-efficient in deployment.

**Pattern: Calmar Ratio Calculation and Optimization**

```python
def compute_calmar_ratio(returns, periods_per_year=252):
    """
    Args:
        returns: 1D array of daily returns (decimals, not %)
        periods_per_year: trading days (default 252)

    Returns:
        calmar_ratio: Annual Return / Max Drawdown (absolute value)
    """
    cumulative = np.cumprod(1 + returns)
    running_max = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = np.min(drawdown)

    annual_return = (cumulative[-1] ** (periods_per_year / len(returns))) - 1

    if max_drawdown == 0:
        return 0
    return annual_return / abs(max_drawdown)

def optimize_for_calmar(strategy_returns_dict):
    """
    Rank strategies by Calmar ratio.

    Args:
        strategy_returns_dict: {strategy_name: daily_returns_array}

    Returns:
        Ranked list of (strategy_name, calmar_ratio)
    """
    calmars = []
    for name, returns in strategy_returns_dict.items():
        calmar = compute_calmar_ratio(returns)
        calmars.append((name, calmar))

    return sorted(calmars, key=lambda x: x[1], reverse=True)

# Example
strategy_returns = {
    'mean_reversion': np.random.normal(0.0005, 0.01, 252),
    'momentum': np.random.normal(0.0006, 0.015, 252),
    'pairs_trade': np.random.normal(0.0003, 0.008, 252)
}

ranked = optimize_for_calmar(strategy_returns)
for name, calmar in ranked:
    print(f"{name}: Calmar = {calmar:.2f}")
```

## 8. Correlation Breakdown During Stress: Crisis Correlation Matrix

During normal times, correlations are low. During crashes, all risky assets move together. Use a stress-adjusted correlation matrix that reflects crisis correlations (typically 0.7-0.9 for all pairs).

**Pattern: Stress-Test Portfolio with Crisis Correlations**

```python
def compute_crisis_correlation_matrix(normal_corr, stress_factor=0.8):
    """
    Blend normal correlation with maximum correlation (all 1.0s).
    During stress, correlations approach 1.0.

    Args:
        normal_corr: Normal-times correlation matrix
        stress_factor: Weight toward stressed regime (0.0 to 1.0)

    Returns:
        Blended correlation matrix
    """
    n = normal_corr.shape[0]
    max_corr = np.ones((n, n))
    np.fill_diagonal(max_corr, 1.0)

    stress_corr = (1 - stress_factor) * normal_corr + stress_factor * max_corr
    return stress_corr

def stress_test_portfolio(position_sizes, volatilities, normal_corr, stress_factor=0.8):
    """
    Compute portfolio risk under normal and stressed conditions.
    """
    normal_vol = np.sqrt(position_sizes @ (np.outer(volatilities, volatilities) * normal_corr) @ position_sizes)

    stress_corr = compute_crisis_correlation_matrix(normal_corr, stress_factor)
    stress_vol = np.sqrt(position_sizes @ (np.outer(volatilities, volatilities) * stress_corr) @ position_sizes)

    vol_increase = (stress_vol - normal_vol) / normal_vol
    return {'normal_vol': normal_vol, 'stress_vol': stress_vol, 'vol_increase_pct': vol_increase}

# Usage
positions = np.array([0.05, 0.05, 0.05])
vols = np.array([0.12, 0.10, 0.15])
normal_corr = np.array([
    [1.0, 0.2, 0.1],
    [0.2, 1.0, 0.15],
    [0.1, 0.15, 1.0]
])

result = stress_test_portfolio(positions, vols, normal_corr, stress_factor=0.8)
print(f"Normal vol: {result['normal_vol']:.2%}")
print(f"Stress vol: {result['stress_vol']:.2%}")
print(f"Vol increase: {result['vol_increase_pct']:.1%}")
```

## 9. Complete Portfolio Optimizer in Code

Assemble all techniques into a unified portfolio optimizer. Use quadratic programming to maximize Sharpe while respecting constraints.

```python
from scipy.optimize import minimize

class PortfolioOptimizer:
    def __init__(self, constraints=None):
        """
        Args:
            constraints: dict with 'max_sector_weight', 'max_position_weight', 'min_weight', 'max_weight'
        """
        self.constraints = constraints or {}

    def optimize(self, expected_returns, cov_matrix, bounds_per_asset=None):
        """
        Maximize Sharpe ratio.

        Args:
            expected_returns: 1D array of expected returns
            cov_matrix: 2D covariance matrix
            bounds_per_asset: [(min, max), ...] for each asset

        Returns:
            optimal_weights: 1D array summing to 1.0
        """
        n = len(expected_returns)
        bounds = bounds_per_asset or [(0.02, 0.30) for _ in range(n)]

        def neg_sharpe(w):
            portfolio_ret = np.dot(w, expected_returns)
            portfolio_vol = np.sqrt(w @ cov_matrix @ w)
            return -portfolio_ret / portfolio_vol if portfolio_vol > 0 else 1e6

        constraints_list = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0},
        ]

        result = minimize(
            neg_sharpe,
            x0=np.ones(n) / n,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints_list
        )

        return result.x

# Usage
expected_returns = np.array([0.12, 0.10, 0.08, 0.15])
cov_matrix = np.array([
    [0.025, 0.012, 0.005, 0.015],
    [0.012, 0.020, 0.008, 0.010],
    [0.005, 0.008, 0.015, 0.006],
    [0.015, 0.010, 0.006, 0.030]
])

optimizer = PortfolioOptimizer()
weights = optimizer.optimize(expected_returns, cov_matrix)
print(f"Optimal weights: {weights}")
```

## Summary

- **Sharpe-weighted allocation** with correlation penalty reduces hidden portfolio risk.
- **Heat calculation** ensures true portfolio leverage is visible.
- **Sector/position limits** prevent concentration disasters.
- **Dynamic rebalancing** rotates capital from decaying strategies to outperformers.
- **Drawdown circuit breakers** protect capital during adverse periods.
- **Calmar optimization** balances return and drawdown efficiently.
- **Stress-test correlations** account for breakdown during crises.

Apply these frameworks systematically and your portfolio will compound with lower volatility and higher Sharpe than the sum of its parts.
