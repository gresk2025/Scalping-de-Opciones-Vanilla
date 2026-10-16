import time
import hmac
import hashlib
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, Response
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .database import init_db, get_trades_history, add_log, get_open_trade
from .config import update_setting, load_settings
from .market_data import MarketDataManager
from .trading_bot import TradingBot
from .binance_options import test_binance_connection

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

market_data = MarketDataManager()
bot = TradingBot(market_data)

def get_secret_key() -> str:
    settings = load_settings()
    return settings.get("session_secret", "fallback_secret_key_scalping_options_2026")

def generate_auth_token(username: str) -> str:
    ts = str(int(time.time()))
    secret = get_secret_key().encode("utf-8")
    payload = f"{username}:{ts}".encode("utf-8")
    sig = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    return f"{username}.{ts}.{sig}"

def verify_auth_token(token: Optional[str]) -> bool:
    if not token or "." not in token:
        return False
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return False
        username, ts_str, sig = parts
        secret = get_secret_key().encode("utf-8")
        payload = f"{username}:{ts_str}".encode("utf-8")
        expected_sig = hmac.new(secret, payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return False
        # Validez de 30 días
        ts = int(ts_str)
        if time.time() - ts > (86400 * 30):
            return False
        settings = load_settings()
        return username == settings.get("dashboard_user", "admin")
    except Exception:
        return False

def is_user_authenticated(request: Request) -> bool:
    token = request.cookies.get("auth_session")
    return verify_auth_token(token)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    settings = load_settings()
    open_trade = get_open_trade()

    if open_trade:
        trade_msg = f"Reanudando posición abierta {open_trade['symbol']} ({open_trade['contracts']} contratos)"
    else:
        trade_msg = "Sin operaciones previas pendientes"

    add_log("INFO", f"Sistema de Scalping de Opciones iniciado. Estado persistente: {trade_msg}")

    ws_task = asyncio.create_task(market_data.start_websocket())
    bot_task = asyncio.create_task(bot.run_loop())

    yield

    market_data.stop()
    bot._running = False
    ws_task.cancel()
    bot_task.cancel()

app = FastAPI(title="Scalping de Opciones Vanilla", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LoginPayload(BaseModel):
    username: str
    password: str

class ChangeCredentialsPayload(BaseModel):
    current_password: str
    new_username: str
    new_password: str

class ModePayload(BaseModel):
    paper: bool

class SettingsPayload(BaseModel):
    default_contracts: Optional[int] = None
    max_daily_loss: Optional[float] = None
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None

class BinanceCredentialsPayload(BaseModel):
    api_key: str
    api_secret: str

@app.get("/login")
async def serve_login(request: Request):
    if is_user_authenticated(request):
        return RedirectResponse(url="/")
    login_file = FRONTEND_DIR / "login.html"
    if login_file.exists():
        return FileResponse(login_file)
    return {"message": "Página de login no encontrada."}

@app.post("/api/auth/login")
async def login(payload: LoginPayload, response: Response):
    settings = load_settings()
    expected_user = settings.get("dashboard_user", "admin")
    expected_pass = settings.get("dashboard_pass", "admin123")

    if payload.username == expected_user and payload.password == expected_pass:
        token = generate_auth_token(payload.username)
        response.set_cookie(
            key="auth_session",
            value=token,
            max_age=86400 * 30,  # 30 días persistente
            httponly=True,
            samesite="lax"
        )
        add_log("SUCCESS", f"Sesión iniciada con éxito por {payload.username}")
        return {"success": True}

    add_log("WARN", f"Intento de acceso fallido con usuario: {payload.username}")
    raise HTTPException(status_code=401, detail="Credenciales incorrectas")

@app.post("/api/auth/logout")
async def logout(response: Response):
    response.delete_cookie("auth_session")
    return {"success": True}

@app.post("/api/auth/change-credentials")
async def change_credentials(payload: ChangeCredentialsPayload, request: Request, response: Response):
    if not is_user_authenticated(request):
        raise HTTPException(status_code=401, detail="No autorizado")

    settings = load_settings()
    current_expected_pass = settings.get("dashboard_pass", "admin123")

    if payload.current_password != current_expected_pass:
        raise HTTPException(status_code=400, detail="La contraseña actual no coincide")

    new_user = payload.new_username.strip()
    new_pass = payload.new_password.strip()

    if not new_user or len(new_user) < 3:
        raise HTTPException(status_code=400, detail="El nuevo usuario debe tener al menos 3 caracteres")
    if not new_pass or len(new_pass) < 6:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe tener al menos 6 caracteres")

    update_setting("dashboard_user", new_user)
    update_setting("dashboard_pass", new_pass)
    bot.reload_settings()

    token = generate_auth_token(new_user)
    response.set_cookie(
        key="auth_session",
        value=token,
        max_age=86400 * 30,
        httponly=True,
        samesite="lax"
    )
    add_log("SUCCESS", f"Credenciales actualizadas para el usuario: {new_user}")
    return {"success": True, "message": "Credenciales actualizadas correctamente", "username": new_user}

@app.get("/")
async def serve_index(request: Request):
    if not is_user_authenticated(request):
        return RedirectResponse(url="/login")
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Frontend no encontrado."}

@app.get("/api/state")
async def get_state(request: Request):
    if not is_user_authenticated(request):
        raise HTTPException(status_code=401, detail="No autorizado")
    return bot.get_dashboard_state()

@app.get("/api/klines")
async def get_klines(request: Request):
    if not is_user_authenticated(request):
        raise HTTPException(status_code=401, detail="No autorizado")
    return market_data.klines_15m

@app.get("/api/history")
async def get_history(request: Request):
    if not is_user_authenticated(request):
        raise HTTPException(status_code=401, detail="No autorizado")
    return get_trades_history(50)

@app.post("/api/control/toggle")
async def toggle_bot(request: Request):
    if not is_user_authenticated(request):
        raise HTTPException(status_code=401, detail="No autorizado")
    return bot.toggle_pause()

@app.post("/api/control/mode")
async def set_mode(payload: ModePayload, request: Request):
    if not is_user_authenticated(request):
        raise HTTPException(status_code=401, detail="No autorizado")
    return bot.set_mode(payload.paper)

@app.post("/api/control/close_active")
async def close_active(request: Request):
    if not is_user_authenticated(request):
        raise HTTPException(status_code=401, detail="No autorizado")
    res = bot.manual_close_trade()
    if res:
        return {"success": True, "trade": res}
    return {"success": False, "message": "No hay operación abierta."}

@app.post("/api/control/settings")
async def update_bot_settings(payload: SettingsPayload, request: Request):
    if not is_user_authenticated(request):
        raise HTTPException(status_code=401, detail="No autorizado")

    if payload.default_contracts is not None:
        update_setting("default_contracts", max(1, min(10, payload.default_contracts)))
    if payload.max_daily_loss is not None:
        update_setting("max_daily_loss", max(1.0, payload.max_daily_loss))
    if payload.stop_loss_pct is not None:
        update_setting("stop_loss_pct", max(0.1, min(0.8, payload.stop_loss_pct)))
    if payload.take_profit_pct is not None:
        update_setting("take_profit_pct", max(0.2, min(2.0, payload.take_profit_pct)))

    bot.reload_settings()
    add_log("INFO", "Parámetros actualizados desde el panel.")
    return {"success": True, "settings": bot.settings}

@app.post("/api/config/binance")
async def config_binance(payload: BinanceCredentialsPayload, request: Request):
    if not is_user_authenticated(request):
        raise HTTPException(status_code=401, detail="No autorizado")

    key = payload.api_key.strip()
    secret = payload.api_secret.strip()

    test_result = test_binance_connection(key, secret)

    if test_result["success"]:
        update_setting("binance_api_key", key)
        update_setting("binance_api_secret", secret)
        bot.reload_settings()
        add_log("SUCCESS", f"API de Binance conectada correctamente. Saldo: ${test_result['balance_usdt']:.2f} USDT")
    else:
        add_log("ERROR", f"Fallo en prueba de API de Binance: {test_result['message']}")

    return test_result

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.cookies.get("auth_session")
    if not verify_auth_token(token):
        await websocket.close(code=1008)
        return

    await websocket.accept()
    try:
        while True:
            state = bot.get_dashboard_state()
            await websocket.send_json(state)
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass

