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

3. **Módulo Gráfico SMC Pro (`/grafico`)**:
   - Apartado dedicado exclusivamente a la visualización gráfica de alta resolución.
   - Dibuja en tiempo real las cajas sombreadas de Order Blocks (alcistas y bajistas), vacíos de liquidez FVG, banda del Golden Pocket de Fibonacci y media móvil de tendencia dinámica (SMA 20).
   - Interruptores interactivos para encender/apagar capas visuales en vivo.

4. **Scalping Rápido contra el Theta Decay**:
   - Compra de contratos diarios o a 1-2 días de vencimiento (0DTE / Daily Options).
   - Entradas en compresión y salidas rápidas (**Take Profit +75%**, **Stop Loss -35%**, o límite de tiempo de **90 minutos** para evitar que el paso de las horas degrade la prima).
   - Reventa directa del contrato en el mercado de opciones (sin tocar Spot ni comprar la moneda).

5. **Dos Modos de Operación (Conmutables en 1 Clic)**:
   - 🧪 **MODO PAPER TRADING (SIMULACIÓN)**: Activo por defecto. Se conecta a Binance en tiempo real vía WebSockets públicos, detecta velas reales y simula la compra/venta y PnL de las opciones con el modelo Black-Scholes sin arriesgar dinero.
   - ⚠️ **MODO REAL**: Activado únicamente cuando tú lo decidas y configures tus API Keys desde el Dashboard.

6. **Configuración de Binance desde la Web**:
   - No necesitas editar archivos de código.
   - En el Dashboard, haz clic en **'Configurar API'**, pega tu API Key y Secret, y haz clic en **'Probar y Guardar'**. El sistema valida la conexión con `vapi.binance.com`, verifica tus permisos y muestra tu saldo disponible.

7. **Protección de Acceso y Gestión de Credenciales**:
   - Acceso restringido al Dashboard mediante autenticación con cookies firmadas criptográficamente (HMAC-SHA256).
   - Posibilidad de cambiar usuario y contraseña directamente desde la interfaz web.

---

## 🔑 Guía Paso a Paso: Cómo Crear y Conectar tus Claves API de Binance

Sigue estos pasos dentro de tu cuenta de Binance cuando decidas pasar a **Modo Real**:

1. **Entrar a Binance**: Inicia sesión en tu cuenta de [Binance](https://www.binance.com).
2. **Ir a Gestión de API**: Haz clic en el ícono de tu perfil (esquina superior derecha) ➔ **Gestión de API** (*API Management*).
3. **Crear API**: Haz clic en el botón amarillo **"Crear API"** ➔ Selecciona la opción **"Generada por el sistema"** (*System generated*).
4. **Asignar Nombre**: Ponle un nombre descriptivo a la API (por ejemplo: `Bot-Opciones-Solana`).
5. **Verificación de Seguridad**: Completa los códigos de seguridad (código por correo / 2FA / Google Authenticator / Passkey).
6. **Restricción de IP (REQUERIDO Y RECOMENDADO)**:
   - Haz clic en el botón **"Editar restricciones"** (*Edit restrictions*).
   - En la sección inferior, selecciona: **"Restringir el acceso solo a IPs de confianza"** (*Restrict access to trusted IPs only*).
   - Introduce la **IP fija de tu servidor VPS**.
   - 💡 *Por qué es vital*: Al colocar la IP de tu VPS, blindas la API para que nadie pueda usarla fuera de tu servidor y además **Binance desbloquea los permisos de trading de opciones y evita que la clave expire a los 90 días**.
7. **Permisos a Activar**:
   - ✅ **Habilitar Lectura** (*Enable Reading*) — viene activo por defecto.
   - ✅ **Habilitar Opciones / Trading de Opciones Vanilla** (*Enable Vanilla Options Trading*).
   - ⛔ **REGLA DE SEGURIDAD CRÍTICA**: **NUNCA marques la casilla "Habilitar retiros" (*Enable Withdrawals*)**. Tu dinero jamás podrá salir de tu cuenta; el bot únicamente necesita comprar y vender contratos de opciones.
8. **Copiar Claves Inmediatamente**:
   - Copia de inmediato tanto la **API Key** como la **Secret Key** en un lugar seguro.
   - ⚠️ *Atención*: Binance **solo muestra la Secret Key esta única vez**. Si recargas la página o sales sin copiarla, quedará oculta permanentemente con asteriscos (`***`) y tendrás que eliminarla y crear otra.
9. **Transferir Fondos a la Billetera de Opciones**:
   - En Binance, las opciones tienen su propia billetera separada de Spot y Futuros.
   - Dirígete a **Billetera** ➔ **Transferir** ➔ De **Spot** a **Opciones** (*Options Wallet*), e ingresa tu asignación (ej: $10 a $30 USD). La transferencia interna es gratuita e inmediata.
10. **Conectar en el Dashboard**:
    - Abre tu Dashboard, haz clic en **'Configurar API'**, pega tu API Key y Secret Key, y haz clic en **'Probar y Guardar'**. El bot testeará la conexión en vivo con `vapi.binance.com`, verificará tus permisos y confirmará tu saldo USDT disponible.

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
