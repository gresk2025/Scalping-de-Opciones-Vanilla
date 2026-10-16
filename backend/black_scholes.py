import math
from typing import Dict, Any

def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def norm_pdf(x: float) -> float:
    return (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * x * x)

def calculate_option_price(
    spot_price: float,
    strike_price: float,
    time_to_expiry_days: float,
    option_type: str = "PUT",
    volatility: float = 0.65,
    risk_free_rate: float = 0.04
) -> Dict[str, Any]:
    option_type = option_type.upper()
    T = max(time_to_expiry_days / 365.0, 0.0001)
    S = max(spot_price, 0.01)
    K = max(strike_price, 0.01)
    r = risk_free_rate
    sigma = max(volatility, 0.05)

    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T

    if option_type == "CALL":
        price = S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
        delta = norm_cdf(d1)
        theta_annual = -(S * norm_pdf(d1) * sigma) / (2.0 * sqrt_T) - r * K * math.exp(-r * T) * norm_cdf(d2)
    else:  # PUT
        price = K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)
        delta = norm_cdf(d1) - 1.0
        theta_annual = -(S * norm_pdf(d1) * sigma) / (2.0 * sqrt_T) + r * K * math.exp(-r * T) * norm_cdf(-d2)

    theta_daily = theta_annual / 365.0
    gamma = norm_pdf(d1) / (S * sigma * sqrt_T)

    price = max(round(price, 4), 0.05)

    return {
        "price": price,
        "delta": round(delta, 3),
        "theta_daily": round(theta_daily, 4),
        "gamma": round(gamma, 5),
        "implied_volatility": sigma
    }
