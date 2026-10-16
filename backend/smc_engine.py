import math
from typing import List, Dict, Any, Optional

def analyze_smc(klines: List[Dict[str, Any]], current_price: float) -> Dict[str, Any]:
    if len(klines) < 20:
        return {
            "signal": "WAIT",
            "confidence": 0,
            "rationale": "Cargando suficientes velas históricas para análisis SMC...",
            "order_blocks": [],
            "fvgs": [],
            "fib_levels": {},
            "trend": "NEUTRAL",
            "suggested_strike": round(current_price),
            "suggested_type": "NONE"
        }

    # 1. Detectar Swing Highs y Swing Lows
    swing_highs = []
    swing_lows = []
    lookback = 2

    for i in range(lookback, len(klines) - lookback):
        h = klines[i]["high"]
        l = klines[i]["low"]

        # Pivot High
        is_high = True
        for j in range(1, lookback + 1):
            if klines[i - j]["high"] >= h or klines[i + j]["high"] > h:
                is_high = False
                break
        if is_high:
            swing_highs.append({"index": i, "price": h, "time": klines[i]["time"]})

        # Pivot Low
        is_low = True
        for j in range(1, lookback + 1):
            if klines[i - j]["low"] <= l or klines[i + j]["low"] < l:
                is_low = False
                break
        if is_low:
            swing_lows.append({"index": i, "price": l, "time": klines[i]["time"]})

    # 2. Detectar Fair Value Gaps (FVG)
    fvgs = []
    for i in range(2, len(klines)):
        c1 = klines[i - 2]
        c3 = klines[i]

        # Bullish FVG: Low de vela 3 > High de vela 1
        if c3["low"] > c1["high"]:
            gap_size = c3["low"] - c1["high"]
            if gap_size > (current_price * 0.001):  # Min 0.1% gap
                fvgs.append({
                    "type": "BULLISH",
                    "top": c3["low"],
                    "bottom": c1["high"],
                    "time": klines[i - 1]["time"],
                    "mitigated": False
                })

        # Bearish FVG: High de vela 3 < Low de vela 1
        elif c3["high"] < c1["low"]:
            gap_size = c1["low"] - c3["high"]
            if gap_size > (current_price * 0.001):
                fvgs.append({
                    "type": "BEARISH",
                    "top": c1["low"],
                    "bottom": c3["high"],
                    "time": klines[i - 1]["time"],
                    "mitigated": False
                })

    # Verificar mitigación de FVGs con velas posteriores
    for fvg in fvgs:
        for k in klines[-10:]:
            if fvg["type"] == "BULLISH" and k["low"] <= fvg["bottom"]:
                fvg["mitigated"] = True
            elif fvg["type"] == "BEARISH" and k["high"] >= fvg["top"]:
                fvg["mitigated"] = True

    active_fvgs = [f for f in fvgs if not f["mitigated"]][-5:]

    # 3. Detectar Order Blocks (OB)
    order_blocks = []
    # Buscar últimos quiebres de estructura (BOS)
    for i in range(5, len(klines)):
        close = klines[i]["close"]
        prev_close = klines[i - 1]["close"]

        # Bullish BOS: quiebre alcista con vela fuerte
        if close > prev_close and (close - klines[i]["open"]) > (current_price * 0.006):
            # Buscar la última vela bajista antes del impulso
            for j in range(i - 1, max(0, i - 6), -1):
                if klines[j]["close"] < klines[j]["open"]:
                    order_blocks.append({
                        "type": "BULLISH",
                        "top": max(klines[j]["open"], klines[j]["close"]),
                        "bottom": klines[j]["low"],
                        "time": klines[j]["time"],
                        "mitigated": False
                    })
                    break

        # Bearish BOS: quiebre bajista con vela fuerte
        elif close < prev_close and (klines[i]["open"] - close) > (current_price * 0.006):
            # Buscar la última vela alcista antes del impulso
            for j in range(i - 1, max(0, i - 6), -1):
                if klines[j]["close"] > klines[j]["open"]:
                    order_blocks.append({
                        "type": "BEARISH",
                        "top": klines[j]["high"],
                        "bottom": min(klines[j]["open"], klines[j]["close"]),
                        "time": klines[j]["time"],
                        "mitigated": False
                    })
                    break

    # Filtrar OBs mitigados recientemente
    for ob in order_blocks:
        for k in klines[-6:]:
            if ob["type"] == "BULLISH" and k["close"] < ob["bottom"]:
                ob["mitigated"] = True
            elif ob["type"] == "BEARISH" and k["close"] > ob["top"]:
                ob["mitigated"] = True

    active_obs = [ob for ob in order_blocks if not ob["mitigated"]][-4:]

    # 4. Niveles Fibonacci sobre la estructura reciente
    recent_high = max(k["high"] for k in klines[-30:])
    recent_low = min(k["low"] for k in klines[-30:])
    diff = max(recent_high - recent_low, 0.01)

    # Determinar tendencia por posición relativa del precio
    sma20 = sum(k["close"] for k in klines[-20:]) / 20.0
    trend = "BULLISH" if current_price > sma20 else "BEARISH"

    fib_levels = {
        "0.0": round(recent_low, 2),
        "0.50": round(recent_low + diff * 0.50, 2),
        "0.618": round(recent_low + diff * 0.618, 2),
        "0.705": round(recent_low + diff * 0.705, 2),
        "1.0": round(recent_high, 2)
    }

    # 5. Evaluación de Confluencia para señal
    confluence_score = 0
    confluence_factors = []
    signal = "WAIT"
    suggested_type = "NONE"
    suggested_strike = round(current_price)

    # Evaluar confluencia bajista (PUT)
    in_bearish_ob = any(ob["bottom"] <= current_price <= ob["top"] * 1.003 for ob in active_obs if ob["type"] == "BEARISH")
    near_fib_bear = abs(current_price - fib_levels["0.618"]) / current_price < 0.005 or abs(current_price - fib_levels["0.705"]) / current_price < 0.005
    has_bearish_fvg = any(fvg["bottom"] <= current_price <= fvg["top"] * 1.002 for fvg in active_fvgs if fvg["type"] == "BEARISH")

    # Evaluar confluencia alcista (CALL)
    in_bullish_ob = any(ob["bottom"] * 0.997 <= current_price <= ob["top"] for ob in active_obs if ob["type"] == "BULLISH")
    near_fib_bull = abs(current_price - fib_levels["0.50"]) / current_price < 0.005 or abs(current_price - fib_levels["0.618"]) / current_price < 0.005
    has_bullish_fvg = any(fvg["bottom"] * 0.998 <= current_price <= fvg["top"] for fvg in active_fvgs if fvg["type"] == "BULLISH")

    if in_bearish_ob or (near_fib_bear and trend == "BEARISH"):
        if in_bearish_ob:
            confluence_score += 35
            confluence_factors.append("Order Block Institucional Bajista")
        if near_fib_bear:
            confluence_score += 30
            confluence_factors.append("Zona Dorada Fibonacci (0.618 - 0.705)")
        if has_bearish_fvg:
            confluence_score += 25
            confluence_factors.append("Fair Value Gap (FVG) 15m")
        if trend == "BEARISH":
            confluence_score += 10
            confluence_factors.append("Estructura de Mercado a Favor")

        if confluence_score >= 65:
            signal = "BUY_PUT"
            suggested_type = "PUT"
            # Strike ligeramente OTM para scalping barato
            suggested_strike = math.floor(current_price - 1.0)

    elif in_bullish_ob or (near_fib_bull and trend == "BULLISH"):
        if in_bullish_ob:
            confluence_score += 35
            confluence_factors.append("Order Block Institucional Alcista")
        if near_fib_bull:
            confluence_score += 30
            confluence_factors.append("Zona de Retroceso Fib (0.618)")
        if has_bullish_fvg:
            confluence_score += 25
            confluence_factors.append("Fair Value Gap Alcista 15m")
        if trend == "BULLISH":
            confluence_score += 10
            confluence_factors.append("Estructura Alcista a Favor")

        if confluence_score >= 65:
            signal = "BUY_CALL"
            suggested_type = "CALL"
            suggested_strike = math.ceil(current_price + 1.0)

    # 6. Razón Explicativa en lenguaje humano
    if signal == "BUY_PUT":
        rationale = f"Confluencia Bajista ({confluence_score}%): {' + '.join(confluence_factors)}. Zona propicia para comprar opción PUT strike  esperando rechazo rápido."
    elif signal == "BUY_CALL":
        rationale = f"Confluencia Alcista ({confluence_score}%): {' + '.join(confluence_factors)}. Zona de soporte institucional para opción CALL strike  buscando impulso rápido."
    else:
        active_ob_count = len(active_obs)
        active_fvg_count = len(active_fvgs)
        rationale = f"Esperando confluencia en niveles clave. Monitorizando {active_ob_count} Order Blocks y {active_fvg_count} FVGs activos. Tendencia actual: {trend} (SMA20: ${sma20:.2f})."

    return {
        "signal": signal,
        "confidence": confluence_score,
        "rationale": rationale,
        "order_blocks": active_obs,
        "fvgs": active_fvgs,
        "fib_levels": fib_levels,
        "trend": trend,
        "suggested_strike": suggested_strike,
        "suggested_type": suggested_type
    }


