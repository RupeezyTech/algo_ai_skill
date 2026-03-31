# Regime Detection: Hidden Markov Model Framework

## Overview
Implement a Hidden Markov Model (HMM) to identify three market regimes: trending, volatile, and sideways. Switch strategy logic conditionally on detected regime. Monitor regime probabilities for signal gating. Detect strategy decay via rolling Sharpe ratio degradation.

## The Three Regimes

**Trending Regime**: Strong directional bias, moderate-to-low volatility, persistent returns. Deploy momentum strategies. Entry: breakouts, trend-following signals.

**Volatile Regime**: High VIX, whipsaw moves, mean-reversion payoff structure. Avoid momentum. Deploy delta-neutral or hedged positions.

**Sideways Regime**: Low returns, oscillating price action, range-bound behavior. Deploy mean-reversion. Entry: extremes on RSI or Bollinger bands.

## HMM Feature Engineering

Use these two features for HMM observation sequences:

```python
# Daily features
def compute_hmm_features(ohlc_df, vix_series):
    """
    ohlc_df: DataFrame with OHLC prices
    vix_series: India VIX daily values
    Returns: (log_returns, volatility_scaled_vix)
    """
    log_returns = np.log(ohlc_df['Close'] / ohlc_df['Close'].shift(1))

    # Normalize VIX to 0-1 range for observation
    vix_min, vix_max = 10, 50
    vix_normalized = np.clip(vix_series, vix_min, vix_max)
    vix_scaled = (vix_normalized - vix_min) / (vix_max - vix_min)

    # Stack: (N, 2) array where N = number of days
    observations = np.column_stack([log_returns[1:], vix_scaled[1:]])

    return observations

# Example usage:
from hmmlearn import hmm
import numpy as np

obs = compute_hmm_features(nifty_ohlc, india_vix)

# Train 3-state Gaussian HMM
model = hmm.GaussianHMM(n_components=3, covariance_type="diag", n_iter=1000)
model.fit(obs)

# Assign regime labels
hidden_states = model.predict(obs)
# hidden_states: array of [0, 1, 2]
```

## Regime Identification & Labeling

After training, label the three regimes by analyzing state statistics:

```python
def label_regimes(model, obs):
    """
    Assign semantic labels to hidden states.
    State with high volatility = volatile
    State with high positive drift = trending
    State with low volatility = sideways
    """
    means = model.means_  # (3, 2) array
    covars = model.covars_  # (3, 2) array or shape depends on covariance_type

    regimes = {}

    for state in range(3):
        mean_log_return = means[state, 0]
        mean_vix = means[state, 1]

        # Heuristic labeling
        if mean_vix > 0.5:
            regimes[state] = 'VOLATILE'
        elif abs(mean_log_return) < 0.0005:
            regimes[state] = 'SIDEWAYS'
        else:
            regimes[state] = 'TRENDING'

    return regimes

regimes = label_regimes(model, obs)
print(regimes)
# Output: {0: 'TRENDING', 1: 'VOLATILE', 2: 'SIDEWAYS'}
```

## Regime Probability for Signal Gating

Extract the forward probability matrix to compute rolling regime probabilities:

```python
def compute_regime_probabilities(model, obs, window=20):
    """
    Compute rolling probability of being in each regime.
    Use as gate: only trade if regime_prob > threshold (e.g., 0.7)
    """
    posteriors = model.predict_proba(obs)
    # posteriors: (N, 3) array of probabilities for [state_0, state_1, state_2]

    # Rolling mean of posteriors (smoothing)
    prob_rolling = pd.DataFrame(posteriors).rolling(window=window, min_periods=1).mean()

    return prob_rolling

prob_df = compute_regime_probabilities(model, obs, window=20)

# Gating logic in live trading:
def apply_regime_gate(current_regime_prob, threshold=0.70):
    """
    Only generate signals if regime probability > threshold.
    Prevents whipsaw trades during regime uncertainty.
    """
    regime_idx = np.argmax(current_regime_prob)
    regime_prob = current_regime_prob[regime_idx]

    if regime_prob < threshold:
        return None, "UNCERTAIN_REGIME"

    regime_label = regimes[regime_idx]
    return regime_label, regime_prob
```

## Regime-Conditional Strategy Switching

Deploy different strategies per regime:

```python
def generate_signal_by_regime(regime, price_features, technical_indicators):
    """
    route to regime-specific signal function
    """
    if regime == 'TRENDING':
        return momentum_signal(technical_indicators, window=20)
    elif regime == 'SIDEWAYS':
        return mean_reversion_signal(technical_indicators, rsi_threshold=30)
    elif regime == 'VOLATILE':
        return flat_signal(0)  # Stay flat or delta-neutral
    else:
        return 0  # No signal

# Momentum strategy (trending)
def momentum_signal(indicators, window=20):
    ema_fast = indicators['ema_10']
    ema_slow = indicators['ema_50']
    rsi = indicators['rsi']

    if ema_fast > ema_slow and rsi < 70:
        return 1  # BUY
    elif ema_fast < ema_slow and rsi > 30:
        return -1  # SELL
    else:
        return 0

# Mean reversion (sideways)
def mean_reversion_signal(indicators, rsi_threshold=30):
    rsi = indicators['rsi']

    if rsi < rsi_threshold:
        return 1  # BUY oversold
    elif rsi > (100 - rsi_threshold):
        return -1  # SELL overbought
    else:
        return 0

# Flat/hedged (volatile)
def flat_signal(value):
    return 0
```

## Strategy Decay Detection: Rolling Sharpe Ratio

Monitor rolling Sharpe ratio to detect edge degradation:

```python
def detect_strategy_decay(pnl_series, window=30, threshold=1.0):
    """
    Calculate rolling Sharpe ratio.
    If rolling Sharpe < threshold, strategy edge is decaying.
    Trigger retraining or position reduction.
    """
    daily_returns = pnl_series.pct_change().dropna()

    rolling_sharpe = (
        daily_returns.rolling(window=window).mean() /
        daily_returns.rolling(window=window).std() *
        np.sqrt(252)  # Annualize
    )

    is_decaying = rolling_sharpe < threshold

    return rolling_sharpe, is_decaying

# Live monitoring:
rolling_sharpe, decay_flags = detect_strategy_decay(equity_curve, window=30, threshold=1.0)

if decay_flags.iloc[-1]:
    print("ALERT: Strategy edge is decaying. Reduce position size or retrain HMM.")
    # Actions: reduce position_size by 50%, or schedule HMM retraining
```

## Retraining Cadence

Retrain HMM weekly or monthly. Detect regime shift (state transition) as trigger:

```python
def check_regime_shift(old_regime, new_regime):
    """
    Detect if hidden state changed from previous day.
    If shift detected, mark for potential retraining.
    """
    if old_regime != new_regime:
        return True
    return False

# In live loop:
regime_shift_count = 0
for day in trading_days:
    obs_today = compute_hmm_features(ohlc_df, vix_series)
    regime_today = model.predict(obs_today[-1:])

    if check_regime_shift(regime_yesterday, regime_today):
        regime_shift_count += 1

    # Retrain if multiple shifts or every 21 trading days
    if regime_shift_count > 2 or day % 21 == 0:
        obs = compute_hmm_features(ohlc_df, vix_series)
        model = hmm.GaussianHMM(n_components=3, n_iter=1000)
        model.fit(obs)
        regime_shift_count = 0
```

## Summary

- Train 3-state HMM on Nifty log-returns + India VIX
- Label states: trending (momentum), volatile (flat/hedged), sideways (mean-reversion)
- Gate signals with regime probability (only trade if prob > 0.7)
- Switch strategy per regime
- Monitor rolling Sharpe for decay; retrain when it falls or regime shifts occur
- Rolling probability smoothing prevents whipsaw regime flips
