import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "trading.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        option_type TEXT NOT NULL,
        strike REAL NOT NULL,
        contracts INTEGER NOT NULL,
        entry_sol_price REAL NOT NULL,
        exit_sol_price REAL,
        entry_premium REAL NOT NULL,
        exit_premium REAL,
        cost_usd REAL NOT NULL,
        revenue_usd REAL,
        pnl_usd REAL,
        pnl_pct REAL,
        status TEXT NOT NULL,
        exit_reason TEXT,
        is_paper INTEGER NOT NULL,
        rationale TEXT,
        entry_time TEXT NOT NULL,
        exit_time TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        level TEXT NOT NULL,
        message TEXT NOT NULL
    );
    """)
    conn.commit()
    conn.close()

def add_log(level: str, message: str):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).strftime("%H:%M:%S")
    cursor.execute("INSERT INTO logs (timestamp, level, message) VALUES (?, ?, ?)", (now, level.upper(), message))
    conn.commit()
    conn.close()

def get_recent_logs(limit: int = 40) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp, level, message FROM logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]

def create_trade(symbol: str, option_type: str, strike: float, contracts: int,
                 entry_sol_price: float, entry_premium: float, is_paper: bool, rationale: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cost_usd = round(contracts * entry_premium, 4)
    now = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
        INSERT INTO trades (
            symbol, option_type, strike, contracts, entry_sol_price, entry_premium,
            cost_usd, status, is_paper, rationale, entry_time
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?, ?)
    """, (symbol, option_type.upper(), strike, contracts, entry_sol_price, entry_premium,
          cost_usd, 1 if is_paper else 0, rationale, now))
    trade_id = cursor.lastrowid
    conn.commit()
    conn.close()
    add_log("SUCCESS", f"Operación abierta: {option_type} {contracts} contratos @ prima ${entry_premium:.2f} (Inversión: ${cost_usd:.2f})")
    return trade_id

def close_trade(trade_id: int, exit_sol_price: float, exit_premium: float, exit_reason: str) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
    trade = cursor.fetchone()
    if not trade:
        conn.close()
        return {}

    contracts = trade["contracts"]
    entry_premium = trade["entry_premium"]
    cost_usd = trade["cost_usd"]

    revenue_usd = round(contracts * exit_premium, 4)
    pnl_usd = round(revenue_usd - cost_usd, 4)
    pnl_pct = round(((exit_premium - entry_premium) / entry_premium) * 100, 2) if entry_premium > 0 else 0.0

    now = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
        UPDATE trades SET
            exit_sol_price = ?,
            exit_premium = ?,
            revenue_usd = ?,
            pnl_usd = ?,
            pnl_pct = ?,
            status = 'CLOSED',
            exit_reason = ?,
            exit_time = ?
        WHERE id = ?
    """, (exit_sol_price, exit_premium, revenue_usd, pnl_usd, pnl_pct, exit_reason, now, trade_id))
    conn.commit()

    cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
    updated = dict(cursor.fetchone())
    conn.close()

    sign = "+" if pnl_usd >= 0 else ""
    log_level = "SUCCESS" if pnl_usd >= 0 else "WARN"
    add_log(log_level, f"Operación cerrada ({exit_reason}): Prima ${exit_premium:.2f} | PnL: {sign}${pnl_usd:.2f} ({sign}{pnl_pct:.1f}%)")
    return updated

def get_open_trade() -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trades WHERE status = 'OPEN' ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_trades_history(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trades WHERE status = 'CLOSED' ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_daily_pnl() -> float:
    conn = get_connection()
    cursor = conn.cursor()
    today_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT SUM(pnl_usd) as daily_total
        FROM trades
        WHERE status = 'CLOSED' AND exit_time LIKE ?
    """, (f"{today_prefix}%",))
    res = cursor.fetchone()
    conn.close()
    total = res["daily_total"] if res and res["daily_total"] is not None else 0.0
    return round(total, 4)

def get_total_stats() -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            COUNT(*) as total_trades,
            SUM(pnl_usd) as total_pnl,
            SUM(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN pnl_usd <= 0 THEN 1 ELSE 0 END) as losses
        FROM trades
        WHERE status = 'CLOSED'
    """)
    res = cursor.fetchone()
    conn.close()

    total = res["total_trades"] if res and res["total_trades"] else 0
    pnl = round(res["total_pnl"], 4) if res and res["total_pnl"] is not None else 0.0
    wins = res["wins"] if res and res["wins"] else 0
    losses = res["losses"] if res and res["losses"] else 0
    win_rate = round((wins / total) * 100, 1) if total > 0 else 0.0

    return {
        "total_trades": total,
        "total_pnl": pnl,
        "daily_pnl": get_daily_pnl(),
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate
    }

