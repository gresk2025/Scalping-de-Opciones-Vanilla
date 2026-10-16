import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from .config import load_settings, update_setting
from .database import (
    create_trade, close_trade, get_open_trade,
    get_daily_pnl, get_total_stats, add_log, get_recent_logs
)
from .smc_engine import analyze_smc
from .black_scholes import calculate_option_price
from .binance_options import test_binance_connection, get_option_mark_price
from .market_data import MarketDataManager

class TradingBot:
    def __init__(self, market_data: MarketDataManager):
        self.md = market_data
        self.settings = load_settings()
        self.current_analysis: Dict[str, Any] = {
            "signal": "WAIT",
            "confidence": 0,
            "rationale": "Inicializando motor de análisis SMC...",
            "order_blocks": [],
            "fvgs": [],
            "fib_levels": {},
            "trend": "NEUTRAL"
        }
        self.active_trade: Optional[Dict[str, Any]] = None
        self._running = False
        self.last_trade_time = 0
        self.last_scan_log = 0

    async def initialize(self):
        self.settings = load_settings()
        self.active_trade = get_open_trade()
        # Verificar estado diario de pérdidas
        daily_pnl = get_daily_pnl()
        if daily_pnl <= -self.settings['max_daily_loss']:
            self.settings["circuit_breaker_triggered"] = True
            update_setting("circuit_breaker_triggered", True)
            add_log("WARN", f"CIRCUIT BREAKER PREVIO ACTIVO: Pérdida de ${daily_pnl:.2f} hoy. Bot pausado.")

    def reload_settings(self):
        self.settings = load_settings()

    def toggle_pause(self) -> Dict[str, Any]:
        self.reload_settings()
        # Si estaba disparado el circuit breaker, este toggle lo resetea
        if self.settings.get("circuit_breaker_triggered", False):
            self.settings["circuit_breaker_triggered"] = False
            update_setting("circuit_breaker_triggered", False)
            self.settings["bot_running"] = True
            update_setting("bot_running", True)
            add_log("SUCCESS", "Circuit Breaker reseteado manualmente por el usuario. Bot reactivado.")
            return {"status": "RUNNING", "message": "Circuit breaker reseteado. Bot activo."}

        new_state = not self.settings.get("bot_running", True)
        self.settings["bot_running"] = new_state
        update_setting("bot_running", new_state)
        state_str = "REANUDADO" if new_state else "PAUSADO"
        add_log("INFO", f"Bot {state_str} manualmente desde el dashboard.")
        return {"status": "RUNNING" if new_state else "PAUSED", "message": f"Bot {state_str}."}

    def set_mode(self, paper: bool) -> Dict[str, Any]:
        self.settings["paper_trading"] = paper
        update_setting("paper_trading", paper)
        mode_str = "PAPER TRADING (Simulación)" if paper else "MODO REAL (Dinero Real)"
        add_log("WARN", f"Modo cambiado a: {mode_str}")
        return {"paper_trading": paper, "message": f"Modo configurado en {mode_str}."}

    def manual_close_trade(self) -> Optional[Dict[str, Any]]:
        self.active_trade = get_open_trade()
        if not self.active_trade:
            return None

        current_sol = self.md.latest_price
        current_premium = self._calculate_current_premium(self.active_trade, current_sol)
        closed = close_trade(
            trade_id=self.active_trade["id"],
            exit_sol_price=current_sol,
            exit_premium=current_premium,
            exit_reason="MANUAL"
        )
        self.active_trade = None
        return closed

    def _calculate_current_premium(self, trade: Dict[str, Any], current_sol: float) -> float:
        entry_time_str = trade.get("entry_time")
        elapsed_hours = 0.5
        if entry_time_str:
            try:
                entry_dt = datetime.fromisoformat(entry_time_str)
                now_dt = datetime.now(timezone.utc)
                elapsed_hours = (now_dt - entry_dt).total_seconds() / 3600.0
            except Exception:
                pass

        time_left_days = max(1.5 - (elapsed_hours / 24.0), 0.1)

        # Usar Black-Scholes para la prima dinámica realista
        bs_res = calculate_option_price(
            spot_price=current_sol,
            strike_price=trade["strike"],
            time_to_expiry_days=time_left_days,
            option_type=trade["option_type"]
        )
        return bs_res["price"]

    async def run_loop(self):
        self._running = True
        await self.initialize()

        while self._running:
            try:
                self.reload_settings()
                current_sol = self.md.latest_price

                if current_sol > 0 and len(self.md.klines_15m) >= 20:
                    # 1. Ejecutar análisis SMC continuo
                    self.current_analysis = analyze_smc(self.md.klines_15m, current_sol)
                    if time.time() - self.last_scan_log >= 300 and not self.active_trade:
                        tr_name = self.current_analysis.get('trend', 'NEUTRAL')
                        conf_sc = self.current_analysis.get('confidence', 0)
                        add_log('INFO', f"Scanner 15m activo: SOL ${current_sol:.2f} | Tendencia {tr_name} | Confluencia SMC {conf_sc}% | Monitoreando")
                        self.last_scan_log = time.time()

                    # 2. Verificar Circuit Breaker diario
                    daily_pnl = get_daily_pnl()
                    if daily_pnl <= -self.settings['max_daily_loss'] and not self.settings.get("circuit_breaker_triggered"):
                        self.settings["circuit_breaker_triggered"] = True
                        update_setting("circuit_breaker_triggered", True)
                        self.settings["bot_running"] = False
                        update_setting("bot_running", False)
                        add_log("WARN", f"CIRCUIT BREAKER DISPARADO: Pérdida diaria de ${daily_pnl:.2f} alcanzó el límite de -${self.settings['max_daily_loss']:.2f}. Operaciones detenidas.")

                    # 3. Monitorear operación abierta existente
                    self.active_trade = get_open_trade()
                    if self.active_trade:
                        current_premium = self._calculate_current_premium(self.active_trade, current_sol)
                        entry_premium = self.active_trade["entry_premium"]
                        pnl_pct = ((current_premium - entry_premium) / entry_premium) * 100 if entry_premium > 0 else 0.0

                        # Calcular tiempo transcurrido en minutos
                        elapsed_min = 0.0
                        entry_time_str = self.active_trade.get("entry_time")
                        if entry_time_str:
                            try:
                                entry_dt = datetime.fromisoformat(entry_time_str)
                                elapsed_min = (datetime.now(timezone.utc) - entry_dt).total_seconds() / 60.0
                            except Exception:
                                pass

                        # a) Take Profit alcanzado
                        tp_target = self.settings.get("take_profit_pct", 0.75) * 100.0
                        if pnl_pct >= tp_target:
                            close_trade(self.active_trade["id"], current_sol, current_premium, "TAKE_PROFIT")
                            self.active_trade = None

                        # b) Stop Loss alcanzado
                        elif pnl_pct <= -(self.settings.get("stop_loss_pct", 0.35) * 100.0):
                            close_trade(self.active_trade["id"], current_sol, current_premium, "STOP_LOSS")
                            self.active_trade = None

                        # c) Time Stop (Evitar desgaste por Theta Decay)
                        elif elapsed_min >= self.settings.get("max_trade_duration_minutes", 90):
                            close_trade(self.active_trade["id"], current_sol, current_premium, "TIME_STOP")
                            self.active_trade = None

                    # 4. Si NO hay operación abierta y el bot está ACTIVO, buscar entradas
                    elif self.settings.get("bot_running") and not self.settings.get("circuit_breaker_triggered"):
                        sig = self.current_analysis["signal"]
                        conf = self.current_analysis["confidence"]

                        if sig in ["BUY_CALL", "BUY_PUT"] and conf >= 65:
                            opt_type = self.current_analysis["suggested_type"]
                            strike = self.current_analysis["suggested_strike"]
                            contracts = int(self.settings.get("default_contracts", 5))

                            # Calcular prima inicial
                            bs_init = calculate_option_price(
                                spot_price=current_sol,
                                strike_price=strike,
                                time_to_expiry_days=1.5,
                                option_type=opt_type
                            )
                            entry_premium = bs_init["price"]
                            symbol_name = f"SOL-{opt_type[0]}-{strike}"
                            is_paper = self.settings.get("paper_trading", True)

                            trade_id = create_trade(
                                symbol=symbol_name,
                                option_type=opt_type,
                                strike=strike,
                                contracts=contracts,
                                entry_sol_price=current_sol,
                                entry_premium=entry_premium,
                                is_paper=is_paper,
                                rationale=self.current_analysis["rationale"]
                            )
                            self.active_trade = get_open_trade()

            except Exception as e:
                print(f"Error en bucle del bot: {e}")

            await asyncio.sleep(1.0)

    def get_dashboard_state(self) -> Dict[str, Any]:
        stats = get_total_stats()
        current_sol = self.md.latest_price
        active_info = None

        if self.active_trade:
            cur_prem = self._calculate_current_premium(self.active_trade, current_sol)
            ent_prem = self.active_trade["entry_premium"]
            contracts = self.active_trade["contracts"]
            pnl_usd = round((cur_prem - ent_prem) * contracts, 3)
            pnl_pct = round(((cur_prem - ent_prem) / ent_prem) * 100, 2) if ent_prem > 0 else 0.0

            elapsed_min = 0.0
            entry_time_str = self.active_trade.get("entry_time")
            if entry_time_str:
                try:
                    entry_dt = datetime.fromisoformat(entry_time_str)
                    elapsed_min = round((datetime.now(timezone.utc) - entry_dt).total_seconds() / 60.0, 1)
                except Exception:
                    pass

            entry_sol = self.active_trade.get("entry_sol_price", current_sol)

            active_info = {
                **self.active_trade,
                "current_sol": current_sol,
                "entry_sol_price": entry_sol,
                "current_premium": cur_prem,
                "unrealized_pnl_usd": pnl_usd,
                "unrealized_pnl_pct": pnl_pct,
                "elapsed_minutes": elapsed_min,
                "max_minutes": self.settings.get("max_trade_duration_minutes", 90),
                "take_profit_target_pct": self.settings.get("take_profit_pct", 0.75) * 100,
                "stop_loss_target_pct": -self.settings.get("stop_loss_pct", 0.35) * 100,
                "log": f"Operación en curso iniciada en SOL ${entry_sol:.2f}. Monitoreando TP (+75%), SL (-35%) o cierre temporal a los 90 min."
            }

        status_text = "RUNNING"
        if self.settings.get("circuit_breaker_triggered"):
            status_text = "CIRCUIT_BREAKER"
        elif not self.settings.get("bot_running"):
            status_text = "PAUSED"

        pending_setup = self.current_analysis.get("pending_setup") if self.current_analysis else None

        return {
            "status": status_text,
            "current_user": self.settings.get("dashboard_user", "admin"),
            "paper_trading": self.settings.get("paper_trading", True),
            "sol_price": current_sol,
            "price_change_24h": self.md.price_change_24h,
            "high_24h": self.md.high_24h,
            "low_24h": self.md.low_24h,
            "ws_connected": self.md.is_connected,
            "analysis": self.current_analysis,
            "active_trade": active_info,
            "pending_setup": pending_setup,
            "recent_trades": get_trades_history(50),
            "stats": stats,
            "settings": {
                "max_daily_loss": self.settings.get("max_daily_loss", 5.0),
                "default_contracts": self.settings.get("default_contracts", 5),
                "stop_loss_pct": self.settings.get("stop_loss_pct", 0.35),
                "take_profit_pct": self.settings.get("take_profit_pct", 0.75),
                "has_api_key": bool(self.settings.get("binance_api_key"))
            },
            "recent_logs": get_recent_logs(25)
        }


