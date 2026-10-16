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
            "suggested_type": "NONE",
            "pending_setup": None,
            "trading_setups": None
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

    # 6. Determinar Nivel / Precio Objetivo en Espera (Setup Acechado)
    target_price = round(current_price, 2)
    target_reason = ""
    target_action = "BUY_CALL" if trend == "BULLISH" else "BUY_PUT"
    target_type = "CALL" if trend == "BULLISH" else "PUT"
    target_strike = math.ceil(current_price + 1.0) if trend == "BULLISH" else math.floor(current_price - 1.0)

    if trend == "BULLISH":
        bull_obs = [ob for ob in active_obs if ob["type"] == "BULLISH"]
        bull_fvgs = [f for f in active_fvgs if f["type"] == "BULLISH"]
        if bull_obs:
            best_ob = max(bull_obs, key=lambda x: x["top"])
            target_price = round(best_ob["top"], 2)
            target_reason = f"Order Block Alcista (${best_ob['bottom']:.2f} - ${best_ob['top']:.2f})"
        elif bull_fvgs:
            best_fvg = max(bull_fvgs, key=lambda x: x["top"])
            target_price = round(best_fvg["top"], 2)
            target_reason = f"FVG Alcista (${best_fvg['bottom']:.2f} - ${best_fvg['top']:.2f})"
        else:
            target_price = round(fib_levels["0.618"], 2)
            target_reason = f"Zona Dorada Fib 0.618 (${fib_levels['0.618']:.2f})"
    else:
        bear_obs = [ob for ob in active_obs if ob["type"] == "BEARISH"]
        bear_fvgs = [f for f in active_fvgs if f["type"] == "BEARISH"]
        if bear_obs:
            best_ob = min(bear_obs, key=lambda x: x["bottom"])
            target_price = round(best_ob["bottom"], 2)
            target_reason = f"Order Block Bajista (${best_ob['bottom']:.2f} - ${best_ob['top']:.2f})"
        elif bear_fvgs:
            best_fvg = min(bear_fvgs, key=lambda x: x["bottom"])
            target_price = round(best_fvg["bottom"], 2)
            target_reason = f"FVG Bajista (${best_fvg['bottom']:.2f} - ${best_fvg['top']:.2f})"
        else:
            target_price = round(fib_levels["0.618"], 2)
            target_reason = f"Zona Dorada Fib 0.618 (${fib_levels['0.618']:.2f})"

    dist_usd = round(abs(current_price - target_price), 2)
    dist_pct = round((dist_usd / current_price) * 100, 2) if current_price > 0 else 0.0

    # Calcular confluencia proyectada del setup objetivo
    target_confluence = 70
    target_factors = []
    if "Order Block" in target_reason:
        target_confluence = 70
        target_factors = ["Order Block Institucional (35%)", "Fair Value Gap / Descuento (25%)", "Estructura Institucional (10%)"]
    elif "FVG" in target_reason:
        target_confluence = 65
        target_factors = ["Fair Value Gap (25%)", "Zona de Retroceso (30%)", "Estructura (10%)"]
    else:
        target_confluence = 65
        target_factors = ["Nivel Dorado Fib 0.618 (30%)", "FVG Imbalance (25%)", "Estructura (10%)"]

    display_confidence = confluence_score if confluence_score > 0 else target_confluence

    pending_setup = {
        "status": "WAITING_PRICE",
        "target_price": target_price,
        "target_action": target_action,
        "target_type": target_type,
        "target_strike": target_strike,
        "current_sol": round(current_price, 2),
        "distance_usd": dist_usd,
        "distance_pct": dist_pct,
        "zone_name": target_reason,
        "confluence": target_confluence,
        "min_confluence": 65,
        "rationale": f"Acechando nivel ${target_price:.2f} ({target_reason}). Distancia: ${dist_usd:.2f} ({dist_pct:.2f}%). Confluencia calculada del setup: {target_confluence}% ({' + '.join(target_factors)}). Gatillará {target_type} al mitigar este nivel."
    }

    # 7. Razón Explicativa en lenguaje humano
    if signal == "BUY_PUT":
        rationale = f"Confluencia Bajista ({confluence_score}%): {' + '.join(confluence_factors)}. Zona propicia para comprar opción PUT strike ${suggested_strike} esperando rechazo rápido."
    elif signal == "BUY_CALL":
        rationale = f"Confluencia Alcista ({confluence_score}%): {' + '.join(confluence_factors)}. Zona de soporte institucional para opción CALL strike ${suggested_strike} buscando impulso rápido."
    else:
        rationale = f"Acechando ${target_price:.2f} ({target_reason}). Distancia: ${dist_usd:.2f} ({dist_pct:.2f}%). Confluencia proyectada del setup: {target_confluence}% (Supera el 65% requerido). Al mitigar la zona disparará automáticamente."

    # 8. Generar Analisis y Setups de Trading para SPOT y FUTUROS
    bull_obs = [ob for ob in active_obs if ob["type"] == "BULLISH"]
    bear_obs = [ob for ob in active_obs if ob["type"] == "BEARISH"]

    # --- SETUP SPOT (Acumulacion / Swing sin apalancamiento) ---
    if bull_obs:
        best_bull_ob = max(bull_obs, key=lambda x: x["top"])
        spot_entry_opt = best_bull_ob["top"]
        spot_entry_sec = best_bull_ob["bottom"]
    else:
        spot_entry_opt = fib_levels["0.618"]
        spot_entry_sec = fib_levels["0.50"]

    spot_sl = round(min(recent_low, spot_entry_sec) * 0.992, 2)
    spot_risk = max(current_price - spot_sl, 0.5)

    spot_tp1 = round(max(recent_high, current_price + spot_risk * 1.5), 2)
    spot_tp2 = round(current_price + spot_risk * 2.8, 2)
    spot_tp3 = round(current_price + spot_risk * 4.5, 2)

    spot_setup = {
        "status": "ZONA DE COMPRA" if trend == "BULLISH" else "ZONA DE ESPERA / DCA",
        "action": "COMPRA_SPOT",
        "entry_optimal": round(spot_entry_opt, 2),
        "entry_secondary": round(spot_entry_sec, 2),
        "tp1": round(spot_tp1, 2),
        "tp1_pct": round(max((spot_tp1 - current_price) / current_price * 100, 0.5), 2),
        "tp2": round(spot_tp2, 2),
        "tp2_pct": round(max((spot_tp2 - current_price) / current_price * 100, 1.0), 2),
        "tp3": round(spot_tp3, 2),
        "tp3_pct": round(max((spot_tp3 - current_price) / current_price * 100, 2.0), 2),
        "risk_reward": "1:2.8",
        "allocation_tip": "Sin Stop Loss requerido: el comercio Spot no tiene liquidación. Compras escalonadas en DCA (60% Entrada 1, 40% Entrada 2) para toma de beneficios en TP1, TP2 y TP3.",
        "invalidation_reason": "Sin liquidación. En caso de retroceso mayor, se acumula DCA en zonas de descuento institucional."
    }

    # --- SETUP FUTUROS (Long o Short con Apalancamiento) ---
    fut_dir = "LONG" if trend == "BULLISH" else "SHORT"
    if fut_dir == "LONG":
        fut_entry = spot_entry_opt
        fut_sl = round(spot_entry_sec * 0.994, 2)
        fut_risk = max(fut_entry - fut_sl, 0.4)
        fut_tp1 = round(fut_entry + fut_risk * 1.5, 2)
        fut_tp2 = round(fut_entry + fut_risk * 3.0, 2)
        fut_tp3 = round(fut_entry + fut_risk * 5.0, 2)
    else:  # SHORT
        if bear_obs:
            best_bear_ob = min(bear_obs, key=lambda x: x["bottom"])
            fut_entry = best_bear_ob["bottom"]
            fut_sl = round(best_bear_ob["top"] * 1.006, 2)
        else:
            fut_entry = fib_levels["0.618"]
            fut_sl = round(fib_levels["0.705"] * 1.006, 2)
        fut_risk = max(fut_sl - fut_entry, 0.4)
        fut_tp1 = round(fut_entry - fut_risk * 1.5, 2)
        fut_tp2 = round(fut_entry - fut_risk * 3.0, 2)
        fut_tp3 = round(fut_entry - fut_risk * 5.0, 2)

    fut_sl_pct = round(abs(fut_entry - fut_sl) / fut_entry * 100, 2)
    fut_setup = {
        "direction": fut_dir,
        "status": f"SENAL {fut_dir} ACTIVA" if confluence_score >= 50 else f"ACECHANDO {fut_dir}",
        "entry_trigger": round(fut_entry, 2),
        "entry_distance_usd": round(abs(current_price - fut_entry), 2),
        "entry_distance_pct": round(abs(current_price - fut_entry) / current_price * 100, 2),
        "leverage_recommended": "5x - 10x (Aislado)",
        "stop_loss": round(fut_sl, 2),
        "sl_distance_usd": round(abs(fut_entry - fut_sl), 2),
        "sl_distance_pct": fut_sl_pct,
        "tp1": round(fut_tp1, 2),
        "tp1_pct": round(abs(fut_tp1 - fut_entry) / fut_entry * 100, 2),
        "tp1_action": "Cerrar 50% de posicion + mover SL a Breakeven",
        "tp2": round(fut_tp2, 2),
        "tp2_pct": round(abs(fut_tp2 - fut_entry) / fut_entry * 100, 2),
        "tp2_action": "Toma parcial 30% en siguiente resistencia/soporte",
        "tp3": round(fut_tp3, 2),
        "tp3_pct": round(abs(fut_tp3 - fut_entry) / fut_entry * 100, 2),
        "tp3_action": "Dejar correr 20% residual con Trailing Stop",
        "risk_reward": "1:3.0",
        "est_liq_5x": round(fut_entry * (0.81 if fut_dir == "LONG" else 1.19), 2),
        "est_liq_10x": round(fut_entry * (0.91 if fut_dir == "LONG" else 1.09), 2),
        "risk_rule": "Riesgo maximo: 1% a 2% del balance de futuros por trade. Usar siempre Margen Aislado."
    }

    trading_setups = {
        "spot": spot_setup,
        "futures": fut_setup
    }

    return {
        "signal": signal,
        "confidence": display_confidence,
        "rationale": rationale,
        "order_blocks": active_obs,
        "fvgs": active_fvgs,
        "fib_levels": fib_levels,
        "trend": trend,
        "sma20": round(sma20, 2),
        "suggested_strike": suggested_strike,
        "suggested_type": suggested_type,
        "pending_setup": pending_setup,
        "trading_setups": trading_setups
    }


