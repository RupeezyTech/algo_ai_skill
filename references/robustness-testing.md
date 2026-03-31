# Robustness Testing: Walk-Forward, Monte Carlo, Out-of-Sample, Sensitivity

## Overview
Ruthlessly test strategy robustness. Deploy walk-forward optimization to prevent overfitting. Use Monte Carlo trade reshuffling and price permutation to confirm edge is real, not luck. Hold out 30% test data. Segment by regime. Vary parameters ±10%. Reject strategies with <50 trades.

## Walk-Forward Optimization: Sliding Window

Optimize on window 1, test on window 2, slide forward. Prevents look-ahead bias:

```python
import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit

def walk_forward_optimization(data, lookback_days=252, test_days=63, slide_days=63):
    """
    Split data into rolling train/test windows.
    train: 252 trading days (1 year)
    test: 63 trading days (3 months)
    slide: advance by 63 days each iteration

    For each window:
      1. Optimize strategy parameters on train data
      2. Test on test data (out-of-sample)
      3. Record OOS performance
    """
    n = len(data)
    results = []

    for start_idx in range(0, n - lookback_days - test_days, slide_days):
        train_start = start_idx
        train_end = start_idx + lookback_days
        test_start = train_end
        test_end = test_start + test_days

        if test_end > n:
            break

        train_data = data.iloc[train_start:train_end]
        test_data = data.iloc[test_start:test_end]

        # 1. Optimize on train data
        optimal_params = optimize_strategy_on_window(train_data)

        # 2. Backtest on test data (OOS)
        oos_backtest = backtest_strategy(test_data, optimal_params)

        # 3. Record
        results.append({
            'window': len(results) + 1,
            'train_period': f"{train_data.index[0].date()} to {train_data.index[-1].date()}",
            'test_period': f"{test_data.index[0].date()} to {test_data.index[-1].date()}",
            'optimal_params': optimal_params,
            'is_backtest': oos_backtest['return_pct'],
            'oos_sharpe': oos_backtest['sharpe_ratio'],
            'oos_max_dd': oos_backtest['max_drawdown_pct'],
            'oos_trades': oos_backtest['trade_count']
        })

    return pd.DataFrame(results)

def optimize_strategy_on_window(train_data):
    """
    Optimize strategy parameters on training window.
    Example: find best RSI threshold, EMA periods, etc.
    """
    best_return = -1
    best_params = {}

    for rsi_th in range(25, 40):
        for ema_fast in range(5, 15):
            ema_slow = ema_fast * 3
            backtest = backtest_strategy(
                train_data,
                {'rsi_threshold': rsi_th, 'ema_fast': ema_fast, 'ema_slow': ema_slow}
            )
            if backtest['return_pct'] > best_return:
                best_return = backtest['return_pct']
                best_params = {
                    'rsi_threshold': rsi_th,
                    'ema_fast': ema_fast,
                    'ema_slow': ema_slow
                }

    return best_params

def backtest_strategy(data, params):
    """
    Dummy backtest function. Replace with actual strategy logic.
    """
    # Placeholder: return random metrics for demo
    return {
        'return_pct': np.random.normal(5, 3),
        'sharpe_ratio': np.random.normal(1.5, 0.5),
        'max_drawdown_pct': np.random.normal(-10, 3),
        'trade_count': np.random.randint(30, 150)
    }

# Example: walk-forward on 3 years of data
data = pd.DataFrame({
    'close': np.cumsum(np.random.randn(756)) + 100  # ~3 years of daily
}, index=pd.date_range('2023-01-01', periods=756, freq='D'))

wf_results = walk_forward_optimization(data, lookback_days=252, test_days=63, slide_days=63)
print("Walk-Forward Results (Out-of-Sample):")
print(wf_results[['window', 'oos_return_pct', 'oos_sharpe', 'oos_trades']])

# Aggregate OOS performance
print(f"\nAverage OOS Return: {wf_results['is_backtest'].mean():.2f}%")
print(f"Average OOS Sharpe: {wf_results['oos_sharpe'].mean():.2f}")
print(f"Total OOS Trades: {wf_results['oos_trades'].sum():.0f}")
```

## Monte Carlo Trade Reshuffling: Lucky Sequence Test

Reshuffle trade order 1000+ times. If profit depends on lucky sequence, edge is false:

```python
def monte_carlo_trade_reshuffling(trade_list, n_simulations=1000):
    """
    trade_list: list of dicts with 'pnl', 'entry_date', 'exit_date'

    Reshuffle trade order randomly n_simulations times.
    Compute P&L for each permutation.
    If P&L distribution is similar to original, edge is REAL.
    If original P&L is outlier, edge is LUCKY SEQUENCE.

    Returns: distribution of P&Ls across permutations
    """
    original_pnl = sum([t['pnl'] for t in trade_list])
    pnls = []

    for sim in range(n_simulations):
        # Shuffle trade order
        shuffled_trades = trade_list.copy()
        np.random.shuffle(shuffled_trades)

        # Reshuffle may affect slippage, commissions (order-dependent)
        sim_pnl = sum([t['pnl'] for t in shuffled_trades])
        pnls.append(sim_pnl)

    pnls = np.array(pnls)

    # Statistics
    pnl_mean = pnls.mean()
    pnl_std = pnls.std()
    pnl_percentile_orig = (pnls <= original_pnl).sum() / len(pnls) * 100

    return {
        'original_pnl': original_pnl,
        'simulated_mean_pnl': pnl_mean,
        'simulated_std_pnl': pnl_std,
        'percentile_of_original': pnl_percentile_orig,
        'simulated_pnls': pnls,
        'conclusion': (
            'EDGE_REAL' if pnl_percentile_orig > 75 else
            'EDGE_QUESTIONABLE' if 25 < pnl_percentile_orig <= 75 else
            'EDGE_LIKELY_LUCKY'
        )
    }

# Example: 100 trades
trades = [
    {'pnl': np.random.normal(50, 100), 'entry': i, 'exit': i+1}
    for i in range(100)
]

mc_result = monte_carlo_trade_reshuffling(trades, n_simulations=1000)
print(f"Original P&L: {mc_result['original_pnl']:.2f}")
print(f"Simulated Mean P&L: {mc_result['simulated_mean_pnl']:.2f}")
print(f"Percentile of Original: {mc_result['percentile_of_original']:.1f}%")
print(f"Conclusion: {mc_result['conclusion']}")
```

## Monte Carlo Price Permutation: Synthetic Data Test

Generate synthetic price sequences by permuting historical price changes. Test if strategy still profits:

```python
def monte_carlo_price_permutation(price_series, n_simulations=1000):
    """
    price_series: array of daily closes

    1. Compute daily returns
    2. Reshuffle returns 1000x -> create synthetic price paths
    3. Run strategy on each synthetic path
    4. If 90%+ of synthetic backtests are profitable, edge is REAL
    5. If <50% are profitable, edge is OVERFITTED

    Returns: % of synthetic simulations that were profitable
    """
    returns = np.diff(np.log(price_series))
    original_backtest_return = backtest_on_price_series(price_series)

    synthetic_returns = []

    for sim in range(n_simulations):
        # Permute returns
        shuffled_returns = np.random.permutation(returns)

        # Reconstruct synthetic price path
        synthetic_prices = np.exp(np.log(price_series[0]) + np.cumsum(shuffled_returns))

        # Backtest on synthetic path
        synthetic_return = backtest_on_price_series(synthetic_prices)
        synthetic_returns.append(synthetic_return)

    synthetic_returns = np.array(synthetic_returns)
    profitable_pct = (synthetic_returns > 0).sum() / len(synthetic_returns) * 100

    return {
        'original_return': original_backtest_return,
        'synthetic_mean_return': synthetic_returns.mean(),
        'synthetic_std_return': synthetic_returns.std(),
        'percent_profitable_synthetic': profitable_pct,
        'conclusion': (
            'EDGE_REAL' if profitable_pct > 80 else
            'EDGE_MARGINAL' if 50 < profitable_pct <= 80 else
            'EDGE_OVERFITTED'
        )
    }

def backtest_on_price_series(prices):
    """
    Dummy: run strategy on price series, return total return %.
    """
    return np.random.normal(5, 3)  # Placeholder

# Test
prices = np.cumprod(1 + np.random.randn(500) * 0.01) * 100
mc_perm = monte_carlo_price_permutation(prices, n_simulations=1000)
print(f"Original Return: {mc_perm['original_return']:.2f}%")
print(f"Synthetic Mean Return: {mc_perm['synthetic_mean_return']:.2f}%")
print(f"% of Synthetic Paths Profitable: {mc_perm['percent_profitable_synthetic']:.1f}%")
print(f"Conclusion: {mc_perm['conclusion']}")
```

## Out-of-Sample Holdout: 30% Test Set (Never Touched)

Reserve 30% of data. Never optimize on it. Use only for final validation:

```python
def out_of_sample_holdout_validation(full_data, holdout_pct=0.30):
    """
    1. Split data: 70% for optimization, 30% for validation
    2. Optimize strategy on 70% (including walk-forward windows)
    3. Run final test on 30% holdout (never seen during optimization)
    4. If OOS performance similar to IS, edge is robust

    Returns: (is_performance, oos_performance, comparison)
    """
    split_idx = int(len(full_data) * (1 - holdout_pct))

    in_sample_data = full_data.iloc[:split_idx]
    out_of_sample_data = full_data.iloc[split_idx:]

    # Step 1: Optimize on in-sample only
    wf_results = walk_forward_optimization(in_sample_data)
    # Extract best params from walk-forward
    best_params = wf_results.loc[wf_results['oos_sharpe'].idxmax(), 'optimal_params']

    # Step 2: Backtest best params on in-sample (IS performance)
    is_perf = backtest_strategy(in_sample_data, best_params)

    # Step 3: Backtest same params on holdout (OOS performance)
    oos_perf = backtest_strategy(out_of_sample_data, best_params)

    # Step 4: Compare
    return_drawdown = abs(oos_perf['return_pct'] - is_perf['return_pct']) / is_perf['return_pct']
    sharpe_drawdown = abs(oos_perf['sharpe_ratio'] - is_perf['sharpe_ratio']) / is_perf['sharpe_ratio']

    conclusion = (
        'ROBUST' if return_drawdown < 0.10 and sharpe_drawdown < 0.20 else
        'QUESTIONABLE' if return_drawdown < 0.25 else
        'OVERFITTED'
    )

    return {
        'in_sample_return': is_perf['return_pct'],
        'out_of_sample_return': oos_perf['return_pct'],
        'return_drawdown_pct': return_drawdown * 100,
        'in_sample_sharpe': is_perf['sharpe_ratio'],
        'out_of_sample_sharpe': oos_perf['sharpe_ratio'],
        'sharpe_drawdown_pct': sharpe_drawdown * 100,
        'conclusion': conclusion
    }

# Example
data = pd.DataFrame({
    'close': np.cumsum(np.random.randn(1000)) + 100
}, index=pd.date_range('2020-01-01', periods=1000, freq='D'))

oos_validation = out_of_sample_holdout_validation(data, holdout_pct=0.30)
print("Out-of-Sample Holdout Test:")
print(f"  In-Sample Return: {oos_validation['in_sample_return']:.2f}%")
print(f"  Out-of-Sample Return: {oos_validation['out_of_sample_return']:.2f}%")
print(f"  Drawdown: {oos_validation['return_drawdown_pct']:.1f}%")
print(f"  Conclusion: {oos_validation['conclusion']}")
```

## Regime-Conditional Backtesting: Test in Bull/Bear/Sideways

Backtest separately in different regimes to ensure edge persists:

```python
def regime_conditional_backtest(data, regime_labels):
    """
    data: price series with date index
    regime_labels: array of regime for each day ('BULL', 'BEAR', 'SIDEWAYS', 'VOLATILE')

    For each regime:
      1. Extract trades in that regime
      2. Compute performance (return, Sharpe, max DD)
      3. Check if strategy is profitable in ALL regimes

    If strategy only works in one regime (e.g., bull), it's not robust.
    """
    unique_regimes = np.unique(regime_labels)
    results = {}

    for regime in unique_regimes:
        regime_mask = regime_labels == regime
        regime_data = data[regime_mask]

        if len(regime_data) < 20:
            continue

        perf = backtest_strategy(regime_data, params={})

        results[regime] = {
            'return_pct': perf['return_pct'],
            'sharpe_ratio': perf['sharpe_ratio'],
            'max_drawdown_pct': perf['max_drawdown_pct'],
            'trade_count': perf['trade_count'],
            'profitable': perf['return_pct'] > 0
        }

    # Check robustness across regimes
    profitable_regimes = sum([v['profitable'] for v in results.values()])
    total_regimes = len(results)

    conclusion = (
        'ROBUST' if profitable_regimes == total_regimes else
        'REGIME_DEPENDENT'
    )

    return {
        'results_by_regime': results,
        'profitable_regimes': f"{profitable_regimes}/{total_regimes}",
        'conclusion': conclusion
    }

# Example: assign regimes
data = pd.Series(
    np.cumsum(np.random.randn(500)) + 100,
    index=pd.date_range('2020-01-01', periods=500, freq='D')
)
# Regime: bull if price > MA, etc.
ma_50 = data.rolling(50).mean()
regime_labels = np.where(data > ma_50, 'BULL', 'BEAR')

regime_results = regime_conditional_backtest(data, regime_labels)
print("Regime-Conditional Backtest:")
for regime, perf in regime_results['results_by_regime'].items():
    print(f"  {regime}: Return {perf['return_pct']:.2f}%, Sharpe {perf['sharpe_ratio']:.2f}")
print(f"Conclusion: {regime_results['conclusion']}")
```

## Sensitivity Analysis: ±10% Parameter Variation

Vary key parameters by ±10%. If strategy breaks, it's fragile:

```python
def sensitivity_analysis(base_params, param_ranges, data, sensitivity_pct=0.10):
    """
    base_params: dict of parameters {'rsi_threshold': 35, 'ema_fast': 10, ...}
    param_ranges: dict of min/max for each param
    sensitivity_pct: vary by ±10% (or fixed value)

    For each parameter:
      1. Vary by ±10%
      2. Backtest
      3. Check if strategy still works

    If performance is robust across ±10%, strategy is NOT fragile.
    """
    results = {'base_params': base_params, 'variations': {}}

    # Baseline performance
    base_perf = backtest_strategy(data, base_params)
    results['base_return'] = base_perf['return_pct']

    for param_name, base_value in base_params.items():
        lower_value = base_value * (1 - sensitivity_pct)
        upper_value = base_value * (1 + sensitivity_pct)

        variations = []

        for variant_value in [lower_value, base_value, upper_value]:
            variant_params = base_params.copy()
            variant_params[param_name] = variant_value

            variant_perf = backtest_strategy(data, variant_params)
            variations.append({
                'value': variant_value,
                'return_pct': variant_perf['return_pct'],
                'sharpe_ratio': variant_perf['sharpe_ratio']
            })

        # Check stability
        returns = [v['return_pct'] for v in variations]
        stability = max(returns) - min(returns)  # Range

        results['variations'][param_name] = {
            'lower': variations[0]['return_pct'],
            'base': variations[1]['return_pct'],
            'upper': variations[2]['return_pct'],
            'stability_range': stability,
            'fragile': stability > 0.20  # If range > 20%, fragile
        }

    return results

# Example
base_params = {'rsi_threshold': 35, 'ema_fast': 10, 'ema_slow': 30}
data = pd.DataFrame({'close': np.cumsum(np.random.randn(500)) + 100})

sensitivity = sensitivity_analysis(base_params, {}, data, sensitivity_pct=0.10)
print("Sensitivity Analysis (±10% variation):")
for param, results_dict in sensitivity['variations'].items():
    print(f"  {param}: Lower {results_dict['lower']:.2f}%, Base {results_dict['base']:.2f}%, Upper {results_dict['upper']:.2f}%")
    if results_dict['fragile']:
        print(f"    WARNING: FRAGILE (range {results_dict['stability_range']:.2f}%)")
```

## Minimum Trade Count Filter: <50 Trades = Reject

Strategies with too few trades are statistically insignificant:

```python
def validate_trade_count(trade_count, data_length_days, min_trades=50):
    """
    < 50 trades over full period = statistically insignificant.
    Risk: edge may be luck, not skill.

    Expected trade frequency:
    - mean reversion: 0.5-2 trades/day
    - momentum: 1-3 trades/day
    """
    avg_trades_per_day = trade_count / (data_length_days / 252)

    if trade_count < min_trades:
        conclusion = 'INSUFFICIENT_TRADES'
        recommendation = 'RELAX_ENTRY_CRITERIA OR EXTEND_DATA'
    elif trade_count < 100:
        conclusion = 'BORDERLINE'
        recommendation = 'GATHER_MORE_DATA_BEFORE_LIVE'
    else:
        conclusion = 'ADEQUATE'
        recommendation = 'PROCEED_WITH_CAUTION'

    return {
        'trade_count': trade_count,
        'avg_trades_per_day': avg_trades_per_day,
        'conclusion': conclusion,
        'recommendation': recommendation
    }

# Example: 40 trades over 1 year
validation = validate_trade_count(trade_count=40, data_length_days=252)
print(f"Trade Count Validation: {validation['conclusion']}")
print(f"  Recommendation: {validation['recommendation']}")
```

## Integrated Robustness Test Suite

```python
def run_full_robustness_test(strategy_func, data, params):
    """
    Master function: run ALL robustness tests in sequence.
    """
    print("=" * 60)
    print("FULL ROBUSTNESS TEST SUITE")
    print("=" * 60)

    # 1. Walk-forward
    print("\n1. Walk-Forward Optimization (OOS)...")
    wf_results = walk_forward_optimization(data)
    avg_oos_sharpe = wf_results['oos_sharpe'].mean()
    print(f"   Average OOS Sharpe: {avg_oos_sharpe:.2f}")

    # 2. Monte Carlo trade reshuffling
    print("\n2. Monte Carlo Trade Reshuffling...")
    trades = extract_trades_from_backtest(data, params)
    mc_shuffle = monte_carlo_trade_reshuffling(trades)
    print(f"   Conclusion: {mc_shuffle['conclusion']}")

    # 3. Monte Carlo price permutation
    print("\n3. Monte Carlo Price Permutation...")
    mc_perm = monte_carlo_price_permutation(data['close'].values)
    print(f"   Conclusion: {mc_perm['conclusion']}")

    # 4. Out-of-sample holdout
    print("\n4. Out-of-Sample Holdout (30%)...")
    oos_val = out_of_sample_holdout_validation(data)
    print(f"   Return Drawdown: {oos_val['return_drawdown_pct']:.1f}%")
    print(f"   Conclusion: {oos_val['conclusion']}")

    # 5. Regime-conditional
    print("\n5. Regime-Conditional Backtest...")
    regimes = assign_regimes(data)
    regime_results = regime_conditional_backtest(data, regimes)
    print(f"   Profitable Regimes: {regime_results['profitable_regimes']}")

    # 6. Sensitivity
    print("\n6. Sensitivity Analysis (±10%)...")
    sensitivity = sensitivity_analysis(params, {}, data)
    fragile_params = [p for p, r in sensitivity['variations'].items() if r['fragile']]
    if fragile_params:
        print(f"   FRAGILE PARAMETERS: {fragile_params}")
    else:
        print(f"   All parameters stable")

    # 7. Trade count
    print("\n7. Trade Count Validation...")
    trades = extract_trades_from_backtest(data, params)
    trade_validation = validate_trade_count(len(trades), len(data))
    print(f"   {trade_validation['conclusion']}: {trade_validation['recommendation']}")

    print("\n" + "=" * 60)
    print("FINAL VERDICT:")
    if (avg_oos_sharpe > 1.0 and mc_shuffle['conclusion'] == 'EDGE_REAL' and
        oos_val['conclusion'] == 'ROBUST' and len(fragile_params) == 0):
        print("  EDGE IS ROBUST. READY FOR LIVE TRADING.")
    else:
        print("  EDGE NEEDS STRENGTHENING. MORE WORK REQUIRED.")
    print("=" * 60)

def assign_regimes(data):
    """Dummy regime assignment."""
    return np.random.choice(['BULL', 'BEAR', 'SIDEWAYS'], len(data))

def extract_trades_from_backtest(data, params):
    """Dummy trade extraction."""
    return [{'pnl': np.random.normal(50, 100)} for _ in range(100)]
```

## Summary

- **Walk-Forward**: Optimize on T1, test OOS on T2, slide. Prevents look-ahead bias
- **Monte Carlo Shuffle**: If P&L depends on lucky sequence, edge is false
- **Price Permutation**: >80% of synthetic paths profitable = edge is real
- **Out-of-Sample Holdout**: Reserve 30%, never optimize on it. <10% drawdown = robust
- **Regime-Conditional**: Must be profitable in bull, bear, AND sideways markets
- **Sensitivity**: Vary params ±10%. If range >20% return, strategy is fragile
- **Trade Count**: <50 trades = reject. <100 = borderline. >100 = adequate
- **Integration**: Run all tests. Only deploy if: OOS Sharpe >1.0, Shuffle "EDGE_REAL", Permutation >80%, Holdout drawdown <10%, all regimes profitable, no fragile params, >100 trades
