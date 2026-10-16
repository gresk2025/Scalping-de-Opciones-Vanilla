import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode
from typing import Dict, Any, List, Optional

BASE_URL = "https://vapi.binance.com"

def generate_signature(secret: str, query_string: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

def test_binance_connection(api_key: str, api_secret: str) -> Dict[str, Any]:
    if not api_key or not api_secret:
        return {
            "success": False,
            "message": "Falta ingresar API Key o Secret Key.",
            "balance_usdt": 0.0
        }

    try:
        # 1. Probar ping / tiempo del servidor
        time_resp = requests.get(f"{BASE_URL}/vapi/v1/time", timeout=5)
        if time_resp.status_code != 200:
            return {
                "success": False,
                "message": f"Error conectando con el servidor de Binance Options: {time_resp.status_code}",
                "balance_usdt": 0.0
            }
        server_time = time_resp.json().get("serverTime", int(time.time() * 1000))

        # 2. Probar cuenta firmada con HMAC
        params = {
            "timestamp": server_time,
            "recvWindow": 5000
        }
        query_str = urlencode(params)
        signature = generate_signature(api_secret, query_str)
        full_url = f"{BASE_URL}/vapi/v1/account?{query_str}&signature={signature}"

        headers = {
            "X-MBX-APIKEY": api_key
        }

        acc_resp = requests.get(full_url, headers=headers, timeout=5)
        if acc_resp.status_code == 200:
            data = acc_resp.json()
            balance = 0.0
            # Extraer saldo USDT si está disponible
            for asset in data.get("asset", []):
                if asset.get("asset") == "USDT":
                    balance = float(asset.get("available", 0.0))
                    break

            return {
                "success": True,
                "message": f"Conexión exitosa a Binance Vanilla Options. Saldo disponible: ${balance:.2f} USDT",
                "balance_usdt": balance
            }
        else:
            err_data = acc_resp.json()
            msg = err_data.get("msg", acc_resp.text)
            return {
                "success": False,
                "message": f"Binance rechazó las credenciales: {msg} (código {acc_resp.status_code})",
                "balance_usdt": 0.0
            }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "message": f"Error de red al conectar con Binance Options: {str(e)}",
            "balance_usdt": 0.0
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error inesperado: {str(e)}",
            "balance_usdt": 0.0
        }

def get_available_sol_options() -> List[Dict[str, Any]]:
    try:
        resp = requests.get(f"{BASE_URL}/vapi/v1/optionInfo", timeout=6)
        if resp.status_code == 200:
            contracts = resp.json()
            sol_contracts = []
            for c in contracts:
                if c.get("underlying") == "SOLUSDT":
                    sol_contracts.append({
                        "symbol": c.get("symbol"),
                        "strike": float(c.get("strikePrice", 0)),
                        "type": "CALL" if c.get("side") == "CALL" else "PUT",
                        "expiry": c.get("expiryDate"),
                        "min_qty": float(c.get("minQty", 0.1))
                    })
            return sol_contracts
    except Exception:
        pass
    return []

def get_option_mark_price(symbol: str) -> Optional[float]:
    try:
        resp = requests.get(f"{BASE_URL}/vapi/v1/mark?symbol={symbol}", timeout=4)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                return float(data[0].get("markPrice", 0.0))
            elif isinstance(data, dict):
                return float(data.get("markPrice", 0.0))
    except Exception:
        pass
    return None

