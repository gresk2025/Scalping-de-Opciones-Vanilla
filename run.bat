@echo off
title Scalping de Opciones Vanilla - SOL/USDT
echo ========================================================
echo    INICIANDO BOT DE SCALPING DE OPCIONES VANILLA
echo ========================================================
echo.

cd /d "%~dp0"

echo [1/2] Verificando dependencias...
pip install -r requirements.txt --quiet

echo [2/2] Abriendo panel de control en el navegador...
start http://localhost:8000

echo.
echo ========================================================
echo  Dashboard activo en: http://localhost:8000
echo  Para detener el bot presiona Ctrl + C en esta ventana
echo ========================================================
echo.

python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
pause
