# Options Greeks: Delta-Neutral Portfolio & Volatility Harvesting

## Overview
Master delta-neutral portfolio construction. Harvest volatility via gamma scalping and theta collection. Scale exposure based on India VIX. Sell vol when implied > realized; buy when implied < realized. Compute Greeks in real-time. Warn on expiry-day gamma risk.

## Black-Scholes Greeks Computation

Implement canonical Greek calculations for European options:

```python
import numpy as np
from scipy.stats import norm

def black_scholes_greeks(S, K, T, r, sigma, option_type='call'):
    """
    Compute Greeks using Black-Scholes formula.
    S: current spot price
    K: strike price
    T: time to expiry (years, e.g., 7/365 for 7 days)
    r: risk-free rate (annual)
    sigma: volatility (annual)
    option_type: 'call' or 'put'

    Returns: (price, delta, gamma, theta, vega, rho)
    """
    d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
    d2 = d1 - sigma*np.sqrt(T)

    N_d1 = norm.cdf(d1)
    n_d1 = norm.pdf(d1)  # standard normal PDF
    N_minus_d1 = norm.cdf(-d1)
    N_minus_d2 = norm.cdf(-d2)

    if option_type == 'call':
        price = S * N_d1 - K * np.exp(-r*T) * norm.cdf(d2)
        delta = N_d1
        theta = (
            -(S * n_d1 * sigma) / (2 * np.sqrt(T)) -
            r * K * np.exp(-r*T) * norm.cdf(d2)
        ) / 365  # per day
    else:  # put
        price = K * np.exp(-r*T) * N_minus_d2 - S * N_minus_d1
        delta = N_d1 - 1
        theta = (
            -(S * n_d1 * sigma) / (2 * np.sqrt(T)) +
            r * K * np.exp(-r*T) * N_minus_d2
        ) / 365  # per day

    gamma = n_d1 / (S * sigma * np.sqrt(T))
    vega = S * n_d1 * np.sqrt(T) / 100  # per 1% vol change
    rho = K * T * np.exp(-r*T) * (norm.cdf(d2) if option_type == 'call' else -N_minus_d2) / 100

    return price, delta, gamma, theta, vega, rho

# Example: Nifty Call, 7 DTE
S = 23500
K = 23500
T = 7 / 365
r = 0.06
sigma = 0.18

price, delta, gamma, theta, vega, rho = black_scholes_greeks(S, K, T, r, sigma, 'call')
print(f"Call Price: {price:.2f}")
print(f"Delta: {delta:.4f}, Gamma: {gamma:.6f}, Theta: {theta:.4f}")
print(f"Vega: {vega:.4f}, Rho: {rho:.4f}")
```

## Delta-Neutral Portfolio Construction

Build a hedged position by matching longs and shorts:

```python
def build_delta_neutral_portfolio(positions):
    """
    positions: list of dicts, each with:
      - 'instrument': 'NIFTY 23500 CE' etc.
      - 'quantity': signed int (positive = long, negative = short)
      - 'delta': Greek value
      - 'price': current mark-to-market price
      - 'type': 'underlying' or 'option'

    Returns: portfolio dict with total Greeks and rehedge signals
    """
    portfolio = {
        'positions': positions,
        'total_delta': 0,
        'total_gamma': 0,
        'total_theta': 0,
        'total_vega': 0,
        'hedge_action': None
    }

    for pos in positions:
        if pos['type'] == 'underlying':
            # Underlying has delta = 1
            portfolio['total_delta'] += pos['quantity'] * 1
        else:
            # Option
            portfolio['total_delta'] += pos['quantity'] * pos['delta']
            portfolio['total_gamma'] += pos['quantity'] * pos.get('gamma', 0)
            portfolio['total_theta'] += pos['quantity'] * pos.get('theta', 0)
            portfolio['total_vega'] += pos['quantity'] * pos.get('vega', 0)

    # Rehedge trigger: if |delta| > 0.05 (5% exposure)
    if abs(portfolio['total_delta']) > 0.05:
        if portfolio['total_delta'] > 0:
            portfolio['hedge_action'] = f"SELL {abs(portfolio['total_delta']):.2f} delta hedge"
        else:
            portfolio['hedge_action'] = f"BUY {abs(portfolio['total_delta']):.2f} delta hedge"

    return portfolio

# Example: long 100 ATM calls, short 50 shares
positions = [
    {
        'instrument': 'NIFTY 23500 CE',
        'quantity': 100,
        'delta': 0.52,
        'gamma': 0.00015,
        'theta': -0.08,
        'vega': 0.45,
        'type': 'option'
    },
    {
        'instrument': 'NIFTY Spot',
        'quantity': -50,
        'delta': 1.0,
        'type': 'underlying'
    }
]

portfolio = build_delta_neutral_portfolio(positions)
print(f"Net Delta: {portfolio['total_delta']:.4f}")
print(f"Action: {portfolio['hedge_action']}")
```

## Gamma Scalping: Harvest Realized Volatility

Buy long gamma (long ATM calls or puts), delta-hedge, and profit from vol:

```python
def gamma_scalp_pnl(S_entry, S_exit, gamma, T_held_days):
    """
    Realized P&L from gamma scalping.
    Profit = 0.5 * gamma * (dS)^2
    where dS = price move and gamma is the average gamma held.

    S_entry: entry price
    S_exit: exit price
    gamma: portfolio gamma
    T_held_days: days held (for theta drag)
    """
    dS = S_exit - S_entry
    gamma_pnl = 0.5 * gamma * (dS ** 2)

    # Subtract theta decay
    theta_daily = -0.08  # theta per day (example)
    theta_pnl = theta_daily * T_held_days

    return gamma_pnl, theta_pnl, gamma_pnl + theta_pnl

# Example
gamma = 0.00015
S_prices = [23500, 23510, 23495, 23520, 23505]  # mark-to-market prices

total_gamma_pnl = 0
for i in range(len(S_prices) - 1):
    g_pnl, theta_pnl, net = gamma_scalp_pnl(S_prices[i], S_prices[i+1], gamma, T_held_days=1)
    total_gamma_pnl += net
    print(f"Gamma P&L: {g_pnl:.2f}, Theta: {theta_pnl:.2f}, Net: {net:.2f}")

print(f"Total Gamma Scalp P&L: {total_gamma_pnl:.2f}")
```

## Theta Harvesting: Short Strangles & Iron Condors

Sell premium via strangles (short OTM call + put) or iron condors (4-leg spreads):

```python
def theta_harvest_position(S, K_call, K_put, T, r, sigma):
    """
    Strangle: short call + short put
    K_call: short call strike (OTM, e.g., S * 1.02)
    K_put: short put strike (OTM, e.g., S * 0.98)

    Returns: position Greeks and break-even levels
    """
    # Short call
    call_price, call_delta, call_gamma, call_theta, call_vega, _ = black_scholes_greeks(
        S, K_call, T, r, sigma, 'call'
    )
    # Short put
    put_price, put_delta, put_gamma, put_theta, put_vega, _ = black_scholes_greeks(
        S, K_put, T, r, sigma, 'put'
    )

    strangle = {
        'credit': call_price + put_price,  # premium received
        'delta': -(call_delta + put_delta),  # delta is short
        'gamma': -(call_gamma + put_gamma),  # short gamma
        'theta': call_theta + put_theta,  # positive theta (time decay benefit)
        'vega': -(call_vega + put_vega),  # short vega exposure
        'max_loss': max(K_call - K_put - (call_price + put_price), 100),
        'breakeven_up': K_call + (call_price + put_price),
        'breakeven_down': K_put - (call_price + put_price)
    }

    return strangle

# Example: NSE Nifty, 7 DTE
strangle = theta_harvest_position(S=23500, K_call=24000, K_put=23000, T=7/365, r=0.06, sigma=0.18)
print(f"Credit Received: {strangle['credit']:.2f}")
print(f"Theta (daily): {strangle['theta']:.4f}")
print(f"Max Loss: {strangle['max_loss']:.2f}")
print(f"Breakeven: {strangle['breakeven_down']:.2f} / {strangle['breakeven_up']:.2f}")
```

## IV vs RV Spread: Sell When IV > RV

Compare implied volatility (option prices) to realized volatility (price moves):

```python
def compute_realized_volatility(prices, window=20):
    """
    Compute realized volatility from historical price moves.
    window: lookback period in days
    """
    log_returns = np.log(prices / prices.shift(1)).dropna()
    rv = log_returns.rolling(window=window).std() * np.sqrt(252)  # annualize
    return rv

def iv_rv_signal(iv, rv, threshold=0.02):
    """
    Compare implied vol to realized vol.
    If IV > RV + threshold: sell vol (short strangles)
    If IV < RV - threshold: buy vol (long strangles)
    """
    spread = iv - rv

    if spread > threshold:
        return 'SELL_VOL'
    elif spread < -threshold:
        return 'BUY_VOL'
    else:
        return 'NEUTRAL'

# Live usage
nifty_prices = ... # historical daily closes
iv_current = 0.22  # from option chain
rv = compute_realized_volatility(nifty_prices, window=20).iloc[-1]

signal = iv_rv_signal(iv_current, rv, threshold=0.02)
print(f"IV: {iv_current:.2%}, RV: {rv:.2%}, Spread: {iv_current - rv:.2%}")
print(f"Signal: {signal}")
```

## Vega Management: Scale by India VIX

Scale position size inversely to VIX level (trade smaller when VIX is high):

```python
def calculate_position_size_by_vega(base_size, india_vix, vega_nominal_target=50):
    """
    Scale position based on India VIX.
    High VIX = smaller size (vega is more volatile, expensive)
    Low VIX = larger size (vega is cheap, stable)

    india_vix: current India VIX level (e.g., 20)
    vega_nominal_target: target vega notional in Rs (e.g., 50k)
    """
    vix_reference = 20  # baseline VIX

    # Inverse scaling
    size_multiplier = vix_reference / india_vix

    # Cap at 0.5x to 2x
    size_multiplier = np.clip(size_multiplier, 0.5, 2.0)

    adjusted_size = base_size * size_multiplier

    return adjusted_size, size_multiplier

# Example
base_size = 100  # 100 contracts
india_vix = 25

adjusted_size, multiplier = calculate_position_size_by_vega(base_size, india_vix)
print(f"VIX: {india_vix}, Multiplier: {multiplier:.2f}, Adjusted Size: {adjusted_size:.0f} contracts")
```

## Expiry-Day Gamma Risk Warning

Flag high gamma exposure near expiry to avoid gap risk:

```python
def expiry_gamma_warning(portfolio_gamma, T_days, spot_price):
    """
    Warning system for expiry day gamma.
    High gamma + low T = extreme moves possible.
    """
    if T_days <= 1:
        if abs(portfolio_gamma) > 0.0005:
            gamma_dollar_notional = portfolio_gamma * (spot_price ** 2) / spot_price
            return {
                'alert': 'CRITICAL',
                'message': f'High gamma ({portfolio_gamma:.6f}) with {T_days} DTE. Risk of >2% move.',
                'gamma_notional': gamma_dollar_notional
            }
        elif abs(portfolio_gamma) > 0.0002:
            return {
                'alert': 'MEDIUM',
                'message': f'Moderate gamma ({portfolio_gamma:.6f}) with {T_days} DTE.',
                'gamma_notional': portfolio_gamma * (spot_price ** 2) / spot_price
            }
    return {'alert': 'LOW', 'message': 'Safe gamma levels', 'gamma_notional': 0}

# Use in daily monitoring
warning = expiry_gamma_warning(portfolio_gamma=0.0008, T_days=1, spot_price=23500)
if warning['alert'] != 'LOW':
    print(f"ALERT: {warning['message']}")
    print(f"Action: Close or hedge high-gamma positions immediately")
```

## Real-Time Greeks Update Loop

Refresh Greeks as market prices move:

```python
def update_portfolio_greeks_live(positions, spot_price, india_vix, seconds_to_expiry):
    """
    Called every tick or minute. Recompute Greeks.
    Update delta hedge ratio, check vega exposure, flag warnings.
    """
    T = seconds_to_expiry / (365 * 24 * 3600)
    r = 0.06
    sigma = india_vix / 100  # Use VIX as proxy for ATM vol

    updated_positions = []
    total_delta = 0
    total_gamma = 0
    total_vega = 0

    for pos in positions:
        if pos['type'] == 'option':
            price, delta, gamma, theta, vega, _ = black_scholes_greeks(
                spot_price, pos['strike'], T, r, sigma, pos['option_type']
            )
            pos['delta'] = delta * pos['quantity']
            pos['gamma'] = gamma * pos['quantity']
            pos['vega'] = vega * pos['quantity']
            pos['theta'] = theta * pos['quantity']
            pos['mark_price'] = price

            total_delta += pos['delta']
            total_gamma += pos['gamma']
            total_vega += pos['vega']

        updated_positions.append(pos)

    return {
        'positions': updated_positions,
        'total_delta': total_delta,
        'total_gamma': total_gamma,
        'total_vega': total_vega
    }
```

## Summary

- Compute Greeks using Black-Scholes: price, delta, gamma, theta, vega, rho
- Build delta-neutral: rehedge when |delta| > 0.05
- Gamma scalping: long gamma + hedge, profit from moves
- Theta harvesting: short strangles, collect decay
- IV vs RV spread: sell vol when IV > RV, buy when IV < RV
- Scale by VIX: smaller positions when IV high
- Monitor expiry-day gamma; close if portfolio gamma > 0.0005 with < 1 DTE
- Update Greeks every minute in live trading loop
