# Scalping de Opciones Vanilla - SOL/USDT

Bot cuantitativo institucional de scalping para opciones vanilla en Binance, operando con la estrategia de **Smart Money Concepts (SMC)** y gestión de riesgo estricta.

---

## 🚀 Características Principales

1. **Gestión de Capital Estricta ($10 USD)**:
   - Diseñado específicamente para operar con una asignación de **$10 USD**.
   - **Circuit Breaker Automático (-$5.00 USD)**: Si el bot acumula una pérdida de -$5.00 en un solo día, se apaga automáticamente y **no vuelve a operar** hasta que tú lo reactives manualmente desde el Dashboard.

2. **Estrategia Smart Money Concepts (15M)**:
   - Detección algorítmica de **Order Blocks (OB)** institucionales.
   - Identificación de **Fair Value Gaps (FVG)** o vacíos de liquidez.
   - Retrocesos dorados de **Fibonacci (0.618 y 0.705)**.
   - Confluencia mínima del 65% requerida para gatillar una entrada.

3. **Scalping Rápido contra el Theta Decay**:
   - Compra de contratos diarios o a 1-2 días de vencimiento (0DTE / Daily Options).
   - Entradas en compresión y salidas rápidas (**Take Profit +75%**, **Stop Loss -35%**, o límite de tiempo de **90 minutos** para evitar que el paso de las horas degrade la prima).
   - Reventa directa del contrato en el mercado de opciones (sin tocar Spot ni comprar la moneda).

4. **Dos Modos de Operación (Conmutables en 1 Clic)**:
   - 🧪 **MODO PAPER TRADING (SIMULACIÓN)**: Activo por defecto. Se conecta a Binance en tiempo real vía WebSockets públicos, detecta velas reales y simula la compra/venta y PnL de las opciones con el modelo Black-Scholes sin arriesgar dinero.
   - ⚠️ **MODO REAL**: Activado únicamente cuando tú lo decidas y configures tus API Keys desde el Dashboard.

5. **Configuración de Binance desde la Web**:
   - No necesitas editar archivos de código.
   - En el Dashboard, haz clic en **'Configurar API'**, pega tu API Key y Secret, y haz clic en **'Probar y Guardar'**. El sistema valida la conexión con `vapi.binance.com`, verifica tus permisos y muestra tu saldo disponible.

6. **Protección de Acceso y Gestión de Credenciales**:
   - Acceso restringido al Dashboard mediante autenticación con cookies firmadas criptográficamente (HMAC-SHA256).
   - Posibilidad de cambiar usuario y contraseña directamente desde la interfaz web.

---

## 🔐 Acceso al Dashboard y Seguridad

- **Credenciales por defecto para nuevas instalaciones**:
  - **Usuario**: `admin`
  - **Contraseña**: `admin123`
- **Cambio de credenciales**: En la barra superior del Dashboard, haz clic sobre el botón de tu usuario para abrir el modal de seguridad y actualizar tus credenciales ingresando tu contraseña actual para confirmar.
- **Persistencia**: La sesión se mantiene activa de forma segura y sobrevive a reinicios del servidor.

---

## 💻 Cómo Iniciar el Bot

### En tu PC local (Windows):
Haz doble clic en el archivo:
`run.bat`

O ejecuta en la terminal dentro de esta carpeta:
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
Y abre en tu navegador:
👉 **http://localhost:8000**

---

## ☁️ Cómo Desplegarlo en tu Servidor VPS (Linux / Ubuntu)

Para desplegarlo en un servidor en la nube y mantenerlo corriendo 24/7:

```bash
# 1. Conectarte a tu VPS por SSH
ssh -i /ruta/a/tu/clave.key usuario@ip_de_tu_servidor

# 2. Clonar el repositorio
git clone https://github.com/gresk2025/Scalping-de-Opciones-Vanilla.git
cd Scalping-de-Opciones-Vanilla

# 3. Crear entorno virtual e instalar dependencias
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# 4. Iniciar servicio
sudo ./venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 80
```

---

## 🛡️ Seguridad de las Claves de API de Binance
- Permisos requeridos: **Lectura** y **Habilitar Trading de Opciones Vanilla**.
- **NUNCA actives el permiso de Retiros (Withdrawals)**.
- Opcional: En Binance, restringe el acceso de la API únicamente a la IP fija de tu servidor VPS.
