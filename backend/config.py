import os
import json
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
SETTINGS_FILE = DATA_DIR / "settings.json"

load_dotenv(BASE_DIR / ".env")

DEFAULT_SETTINGS = {
    "paper_trading": True,
    "binance_api_key": os.getenv("BINANCE_API_KEY", ""),
    "binance_api_secret": os.getenv("BINANCE_API_SECRET", ""),
    "max_daily_loss": 5.00,
    "default_contracts": 5,
    "stop_loss_pct": 0.35,
    "take_profit_pct": 0.75,
    "max_trade_duration_minutes": 90,
    "circuit_breaker_triggered": False,
    "bot_running": True,
    "timeframe": "15m",
    "min_confluence": 3,
    "dashboard_user": os.getenv("DASHBOARD_USERNAME", "admin"),
    "dashboard_pass": os.getenv("DASHBOARD_PASSWORD", "admin123"),
    "session_secret": "f3dc16ac8f067cfe0db9c3982fef3fdd004d15d926ce4dad37ab4d74a274cf12"
}

def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                merged = {**DEFAULT_SETTINGS, **saved}
                return merged
        except Exception:
            return DEFAULT_SETTINGS.copy()
    else:
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()

def save_settings(settings: dict) -> None:
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        print(f"Error guardando settings: {e}")

def update_setting(key: str, value) -> dict:
    current = load_settings()
    current[key] = value
    save_settings(current)
    return current

