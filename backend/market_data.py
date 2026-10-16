import asyncio
import json
import time
import requests
import websockets
from typing import List, Dict, Any, Callable, Optional

BINANCE_REST_URL = "https://api.binance.com/api/v3"
BINANCE_WS_URL = "wss://stream.binance.com:9443/ws"

class MarketDataManager:
    def __init__(self):
        self.symbol = "SOLUSDT"
        self.latest_price = 0.0
        self.price_change_24h = 0.0
        self.high_24h = 0.0
        self.low_24h = 0.0
        self.klines_15m: List[Dict[str, Any]] = []
        self.is_connected = False
        self.listeners: List[Callable] = []
        self._running = False

    def add_listener(self, callback: Callable):
        self.listeners.append(callback)

    def notify_listeners(self, event_type: str, data: Any):
        for cb in self.listeners:
            try:
                cb(event_type, data)
            except Exception:
                pass

    def fetch_historical_klines(self, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            url = f"{BINANCE_REST_URL}/klines?symbol={self.symbol}&interval=15m&limit={limit}"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                raw_klines = resp.json()
                formatted = []
                for k in raw_klines:
                    formatted.append({
                        "time": int(k[0] / 1000),  # timestamp en segundos para Lightweight Charts
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[5])
                    })
                self.klines_15m = formatted
                if len(formatted) > 0:
                    self.latest_price = formatted[-1]["close"]
                return self.klines_15m
        except Exception as e:
            print(f"Error cargando velas iniciales: {e}")
        return self.klines_15m

    def fetch_24h_stats(self):
        try:
            url = f"{BINANCE_REST_URL}/ticker/24hr?symbol={self.symbol}"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                self.latest_price = float(data.get("lastPrice", self.latest_price))
                self.price_change_24h = float(data.get("priceChangePercent", 0.0))
                self.high_24h = float(data.get("highPrice", 0.0))
                self.low_24h = float(data.get("lowPrice", 0.0))
        except Exception:
            pass

    async def start_websocket(self):
        self._running = True
        self.fetch_historical_klines()
        self.fetch_24h_stats()

        ws_stream_url = f"{BINANCE_WS_URL}/solusdt@kline_15m/solusdt@ticker"

        while self._running:
            try:
                async with websockets.connect(ws_stream_url, ping_interval=20, ping_timeout=10) as ws:
                    self.is_connected = True
                    self.notify_listeners("connected", True)

                    while self._running:
                        msg_str = await ws.recv()
                        msg = json.loads(msg_str)

                        # Evento de Ticker (precio en vivo continuo)
                        if "e" in msg and msg["e"] == "24hrTicker":
                            self.latest_price = float(msg.get("c", self.latest_price))
                            self.price_change_24h = float(msg.get("P", self.price_change_24h))
                            self.high_24h = float(msg.get("h", self.high_24h))
                            self.low_24h = float(msg.get("l", self.low_24h))
                            self.notify_listeners("tick", {
                                "price": self.latest_price,
                                "change_24h": self.price_change_24h,
                                "high_24h": self.high_24h,
                                "low_24h": self.low_24h
                            })

                        # Evento de Vela 15M
                        elif "e" in msg and msg["e"] == "kline":
                            k = msg["k"]
                            candle = {
                                "time": int(k["t"] / 1000),
                                "open": float(k["o"]),
                                "high": float(k["h"]),
                                "low": float(k["l"]),
                                "close": float(k["c"]),
                                "volume": float(k["v"])
                            }
                            self.latest_price = candle["close"]

                            # Si la vela ya existe en el último índice, actualizarla; sino agregarla
                            if len(self.klines_15m) > 0 and self.klines_15m[-1]["time"] == candle["time"]:
                                self.klines_15m[-1] = candle
                            else:
                                self.klines_15m.append(candle)
                                if len(self.klines_15m) > 120:
                                    self.klines_15m.pop(0)

                            self.notify_listeners("candle", candle)

            except Exception as e:
                self.is_connected = False
                self.notify_listeners("connected", False)
                await asyncio.sleep(3)

    def stop(self):
        self._running = False
