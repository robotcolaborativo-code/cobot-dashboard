from flask import Flask, jsonify, render_template_string, request
import mysql.connector
import os
import time
from datetime import datetime

app = Flask(__name__)

# ======================= CONEXIÓN MYSQL =======================
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=os.environ.get('MYSQL_HOST', 'turntable.proxy.rlwy.net'),
            user=os.environ.get('MYSQL_USER', 'root'),
            password=os.environ.get('MYSQL_PASSWORD', 'QttFmgSWJcoJfFKJNFwuscHPWPSESxWs'),
            database=os.environ.get('MYSQL_DATABASE', 'railway'),
            port=int(os.environ.get('MYSQL_PORT', 57488)),
            connect_timeout=10
        )
        return conn
    except Exception as e:
        print(f"❌ Error conectando a MySQL: {e}")
        return None

# ======================= CONFIGURACIÓN INICIAL =======================
def setup_database():
    try:
        conn = get_db_connection()
        if conn is None:
            return False
            
        cursor = conn.cursor()
        
        # Tabla de comandos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comandos_robot (
                id INT AUTO_INCREMENT PRIMARY KEY,
                esp32_id VARCHAR(50),
                comando VARCHAR(100),
                parametros TEXT,
                motor_num INT,
                pasos INT,
                velocidad INT,
                direccion VARCHAR(10),
                grados FLOAT,
                ejecutado BOOLEAN DEFAULT FALSE,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de estado del robot (ESP32 actualizará esta tabla)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS estado_robot (
                id INT AUTO_INCREMENT PRIMARY KEY,
                esp32_id VARCHAR(50),
                conectado BOOLEAN DEFAULT FALSE,
                wifi_conectado BOOLEAN DEFAULT FALSE,
                posicion_m1 FLOAT DEFAULT 0,
                posicion_m2 FLOAT DEFAULT 0,
                posicion_m3 FLOAT DEFAULT 0,
                posicion_m4 FLOAT DEFAULT 0,
                garra_abierta BOOLEAN DEFAULT TRUE,
                velocidad_actual INT DEFAULT 500,
                emergency_stop BOOLEAN DEFAULT FALSE,
                terminal_log TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de posiciones guardadas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posiciones_guardadas (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(100),
                posicion_m1 FLOAT,
                posicion_m2 FLOAT,
                posicion_m3 FLOAT,
                posicion_m4 FLOAT,
                garra_estado VARCHAR(10),
                velocidad INT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insertar estado inicial
        cursor.execute("SELECT * FROM estado_robot WHERE esp32_id = 'cobot_01'")
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO estado_robot 
                (esp32_id, conectado, wifi_conectado, posicion_m1, posicion_m2, posicion_m3, posicion_m4, garra_abierta, velocidad_actual) 
                VALUES 
                ('cobot_01', 0, 0, 0, 0, 0, 0, 1, 500)
            ''')
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ BASE DE DATOS CONFIGURADA")
        return True
        
    except Exception as e:
        print(f"❌ Error configurando BD: {e}")
        return False

# Configurar BD al inicio
setup_database()

# ======================= HTML DASHBOARD MEJORADO =======================
HTML_DASHBOARD = '''
<!DOCTYPE html>
<html>
<head>
    <title>🤖 Dashboard Control Robot 4DOF</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        body { background: linear-gradient(135deg, #1e3c72, #2a5298); color: white; min-height: 100vh; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        
        /* Header */
        .header { 
            text-align: center; 
            margin-bottom: 20px; 
            padding: 20px; 
            background: rgba(255, 255, 255, 0.1); 
            border-radius: 15px; 
            border: 1px solid rgba(255, 255, 255, 0.2); 
        }
        .header h1 { 
            font-size: 2.5em; 
            margin-bottom: 10px; 
            background: linear-gradient(45deg, #00b4db, #0083b0); 
            -webkit-background-clip: text; 
            -webkit-text-fill-color: transparent; 
        }
        
        /* Grid Principal */
        .main-grid { 
            display: grid; 
            grid-template-columns: 1fr 1fr; 
            gap: 20px; 
            margin-bottom: 20px; 
        }
        @media (max-width: 1024px) { 
            .main-grid { grid-template-columns: 1fr; } 
        }
        
        /* Paneles */
        .panel { 
            background: rgba(255, 255, 255, 0.1); 
            border-radius: 15px; 
            padding: 20px; 
            border: 1px solid rgba(255, 255, 255, 0.2); 
        }
        .panel h2 { 
            font-size: 1.5em; 
            margin-bottom: 15px; 
            color: #00b4db; 
            border-bottom: 2px solid #00b4db; 
            padding-bottom: 8px; 
        }
        
        /* Conexión */
        .connection-status { 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            margin-bottom: 15px; 
        }
        .status-badge { 
            padding: 8px 15px; 
            border-radius: 20px; 
            font-weight: bold; 
        }
        .status-connected { background: #00C851; color: white; }
        .status-disconnected { background: #ff4444; color: white; }
        
        /* Posiciones */
        .positions-grid { 
            display: grid; 
            grid-template-columns: repeat(2, 1fr); 
            gap: 10px; 
            margin-bottom: 15px; 
        }
        .position-item { 
            background: rgba(0, 0, 0, 0.3); 
            padding: 12px; 
            border-radius: 8px; 
            text-align: center; 
        }
        .position-label { font-size: 0.9em; opacity: 0.8; }
        .position-value { font-size: 1.2em; font-weight: bold; color: #00b4db; }
        
        /* Botones */
        .btn-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); 
            gap: 8px; 
            margin-bottom: 15px; 
        }
        .btn { 
            padding: 10px 15px; 
            border: none; 
            border-radius: 8px; 
            font-size: 0.9em; 
            font-weight: bold; 
            cursor: pointer; 
            text-align: center; 
            transition: all 0.3s; 
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.2); }
        .btn-primary { background: linear-gradient(45deg, #00b4db, #0083b0); color: white; }
        .btn-success { background: linear-gradient(45deg, #00C851, #007E33); color: white; }
        .btn-danger { background: linear-gradient(45deg, #ff4444, #cc0000); color: white; }
        .btn-warning { background: linear-gradient(45deg, #ffbb33, #FF8800); color: white; }
        
        /* Control de Motores */
        .motor-control { 
            background: rgba(0, 0, 0, 0.2); 
            padding: 15px; 
            border-radius: 10px; 
            margin-bottom: 15px; 
        }
        .control-row { 
            display: flex; 
            gap: 10px; 
            margin-bottom: 10px; 
            align-items: center; 
        }
        .control-input { 
            flex: 1; 
            padding: 8px; 
            border-radius: 5px; 
            background: rgba(255,255,255,0.1); 
            color: white; 
            border: 1px solid rgba(255,255,255,0.3); 
        }
        
        /* Terminal */
        .terminal { 
            background: #1a1a1a; 
            color: #00ff00; 
            padding: 15px; 
            border-radius: 8px; 
            font-family: 'Courier New', monospace; 
            height: 200px; 
            overflow-y: auto; 
            margin-top: 15px; 
        }
        .terminal-line { margin-bottom: 5px; }
        .terminal-time { color: #888; }
        .terminal-message { color: #00ff00; }
        .terminal-error { color: #ff4444; }
        
        /* Alertas */
        .alert { 
            padding: 12px; 
            margin: 10px 0; 
            border-radius: 5px; 
            font-weight: bold; 
            text-align: center; 
        }
        .alert-success { background: rgba(0, 200, 81, 0.2); border: 1px solid #00C851; color: #00C851; }
        .alert-error { background: rgba(255, 68, 68, 0.2); border: 1px solid #ff4444; color: #ff4444; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 DASHBOARD CONTROL ROBOT 4DOF</h1>
            <p>Control completo del robot colaborativo - Versión Mejorada</p>
        </div>

        <div id="alert-container"></div>

        <div class="main-grid">
            <!-- PANEL IZQUIERDO: CONTROL Y ESTADO -->
            <div class="panel">
                <h2>🔗 CONEXIÓN</h2>
                <div class="connection-status">
                    <div>
                        <strong>Serial:</strong>
                        <button class="btn btn-primary" onclick="conectarSerial()">Conectar</button>
                        <button class="btn btn-warning" onclick="desconectarSerial()">Desconectar</button>
                    </div>
                    <div class="status-badge status-disconnected" id="status-conexion">Desconectado</div>
                </div>
                <div class="status-badge" id="status-wifi">WIFI: Desconectado</div>

                <h2>📍 POSICIONES (GRADOS)</h2>
                <div class="positions-grid">
                    <div class="position-item">
                        <div class="position-label">M1</div>
                        <div class="position-value" id="pos-m1">0°</div>
                    </div>
                    <div class="position-item">
                        <div class="position-label">M2</div>
                        <div class="position-value" id="pos-m2">0°</div>
                    </div>
                    <div class="position-item">
                        <div class="position-label">M3</div>
                        <div class="position-value" id="pos-m3">0°</div>
                    </div>
                    <div class="position-item">
                        <div class="position-label">M4</div>
                        <div class="position-value" id="pos-m4">0°</div>
                    </div>
                </div>

                <h2>🦾 GARRA</h2>
                <div class="btn-grid">
                    <button class="btn btn-success" onclick="controlGarra('ABRIR')">ABRIR</button>
                    <button class="btn btn-danger" onclick="controlGarra('CERRAR')">CERRAR</button>
                </div>

                <h2>⚡ VELOCIDAD (1-1000 RPM)</h2>
                <div class="control-row">
                    <input type="number" id="velocidad-global" value="500" min="1" max="1000" class="control-input">
                    <button class="btn btn-primary" onclick="cambiarVelocidad()">ACTUALIZAR</button>
                </div>

                <h2>🎮 CONTROL DIRECTO</h2>
                <div class="btn-grid">
                    <button class="btn btn-success" onclick="sendCommand('ON')">ON (ENERGIZAR)</button>
                    <button class="btn btn-warning" onclick="sendCommand('OFF')">OFF (APAGAR)</button>
                    <button class="btn btn-danger" onclick="sendCommand('STOP')">PARO EMERGENCIA</button>
                    <button class="btn btn-primary" onclick="sendCommand('RESET')">REINICIAR</button>
                </div>
            </div>

            <!-- PANEL DERECHO: CONTROL AVANZADO -->
            <div class="panel">
                <h2>🔧 CONTROL DE MOTORES</h2>
                
                <div class="motor-control">
                    <div class="control-row">
                        <select id="motor-select" class="control-input">
                            <option value="1">M1 - Motor 1</option>
                            <option value="2">M2 - Motor 2</option>
                            <option value="3">M3 - Motor 3</option>
                            <option value="4">M4 - Motor 4</option>
                        </select>
                    </div>
                    
                    <div class="control-row">
                        <input type="number" id="grados-input" value="90" min="1" max="360" placeholder="Grados" class="control-input">
                        <input type="number" id="velocidad-motor" value="500" min="1" max="1000" placeholder="Velocidad" class="control-input">
                    </div>
                    
                    <div class="btn-grid">
                        <button class="btn btn-primary" onclick="moverMotorGrados('H')">HORARIO</button>
                        <button class="btn btn-primary" onclick="moverMotorGrados('A')">ANTIHORARIO</button>
                    </div>
                </div>

                <h2>💾 SISTEMA DE POSICIONES</h2>
                <div class="control-row">
                    <input type="text" id="nombre-posicion" placeholder="Nombre posición" class="control-input">
                    <button class="btn btn-success" onclick="guardarPosicion()">GUARDAR</button>
                </div>
                
                <div class="control-row">
                    <select id="posiciones-guardadas" class="control-input">
                        <option value="">Seleccionar posición...</option>
                    </select>
                    <button class="btn btn-primary" onclick="cargarPosicion()">CARGAR</button>
                    <button class="btn btn-danger" onclick="eliminarPosicion()">ELIMINAR</button>
                </div>

                <h2>📊 SECUENCIAS</h2>
                <div class="btn-grid">
                    <button class="btn btn-primary" onclick="moverSecuencia()">MOVER SECUENCIA</button>
                    <button class="btn btn-warning" onclick="limpiarTerminal()">LIMPIAR TERMINAL</button>
                </div>

                <h2>📟 TERMINAL</h2>
                <div class="terminal" id="terminal">
                    <div class="terminal-line">
                        <span class="terminal-time">[00:00:00]</span>
                        <span class="terminal-message">Sistema inicializado</span>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // ======================= FUNCIONES PRINCIPALES =======================
        function showAlert(message, type = 'success') {
            const alertContainer = document.getElementById('alert-container');
            const alert = document.createElement('div');
            alert.className = `alert ${type === 'success' ? 'alert-success' : 'alert-error'}`;
            alert.textContent = message;
            alertContainer.appendChild(alert);
            setTimeout(() => { alert.remove(); }, 5000);
        }

        function addTerminalLine(message, isError = false) {
            const terminal = document.getElementById('terminal');
            const now = new Date();
            const timeString = `[${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}]`;
            
            const line = document.createElement('div');
            line.className = 'terminal-line';
            line.innerHTML = `<span class="terminal-time">${timeString}</span> <span class="${isError ? 'terminal-error' : 'terminal-message'}">${message}</span>`;
            
            terminal.appendChild(line);
            terminal.scrollTop = terminal.scrollHeight;
        }

        // ======================= CONEXIÓN SERIAL =======================
        async function conectarSerial() {
            try {
                const response = await fetch('/api/conectar_serial');
                const result = await response.json();
                if (result.status === 'success') {
                    showAlert('✅ Conectado vía Serial');
                    document.getElementById('status-conexion').textContent = 'Conectado';
                    document.getElementById('status-conexion').className = 'status-badge status-connected';
                    addTerminalLine('Conectado vía Serial');
                } else {
                    showAlert('❌ Error al conectar', 'error');
                    addTerminalLine('Error al conectar: ' + result.error, true);
                }
            } catch (error) {
                showAlert('❌ Error de conexión', 'error');
                addTerminalLine('Error de conexión: ' + error.message, true);
            }
        }

        async function desconectarSerial() {
            try {
                const response = await fetch('/api/desconectar_serial');
                const result = await response.json();
                if (result.status === 'success') {
                    showAlert('🔌 Desconectado');
                    document.getElementById('status-conexion').textContent = 'Desconectado';
                    document.getElementById('status-conexion').className = 'status-badge status-disconnected';
                    addTerminalLine('Desconectado vía Serial');
                }
            } catch (error) {
                showAlert('❌ Error al desconectar', 'error');
            }
        }

        // ======================= COMANDOS GENERALES =======================
        async function sendCommand(comando) {
            try {
                const response = await fetch(`/api/comando/${comando}`);
                const result = await response.json();
                if (result.status === 'success') {
                    showAlert(`✅ Comando ${comando} enviado`);
                    addTerminalLine(`Comando enviado: ${comando}`);
                    actualizarEstado();
                } else {
                    showAlert(`❌ Error: ${result.error}`, 'error');
                    addTerminalLine(`Error en comando ${comando}: ${result.error}`, true);
                }
            } catch (error) {
                showAlert('❌ Error de conexión', 'error');
                addTerminalLine('Error de conexión al enviar comando', true);
            }
        }

        async function controlGarra(estado) {
            await sendCommand(estado);
        }

        // ======================= CONTROL DE MOTORES =======================
        async function moverMotorGrados(direccion) {
            const motor = document.getElementById('motor-select').value;
            const grados = document.getElementById('grados-input').value;
            const velocidad = document.getElementById('velocidad-motor').value;
            
            if (!grados || grados < 1) {
                showAlert('⚠️ Ingresa grados válidos', 'error');
                return;
            }

            try {
                const response = await fetch('/api/mover_motor_grados', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        motor: parseInt(motor),
                        grados: parseFloat(grados),
                        velocidad: parseInt(velocidad),
                        direccion: direccion
                    })
                });
                const result = await response.json();
                if (result.status === 'success') {
                    showAlert(`✅ Motor M${motor} movido ${grados}°`);
                    addTerminalLine(`Motor M${motor} movido ${grados}° ${direccion === 'H' ? 'horario' : 'antihorario'} (vel=${velocidad})`);
                } else {
                    showAlert(`❌ Error: ${result.error}`, 'error');
                    addTerminalLine(`Error moviendo motor: ${result.error}`, true);
                }
            } catch (error) {
                showAlert('❌ Error de conexión', 'error');
                addTerminalLine('Error de conexión al mover motor', true);
            }
        }

        // ======================= SISTEMA DE POSICIONES =======================
        async function guardarPosicion() {
            const nombre = document.getElementById('nombre-posicion').value;
            if (!nombre) {
                showAlert('⚠️ Ingresa un nombre para la posición', 'error');
                return;
            }

            try {
                const response = await fetch('/api/guardar_posicion', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ nombre: nombre })
                });
                const result = await response.json();
                if (result.status === 'success') {
                    showAlert(`✅ Posición "${nombre}" guardada`);
                    addTerminalLine(`Posición guardada: ${nombre}`);
                    cargarListaPosiciones();
                    document.getElementById('nombre-posicion').value = '';
                } else {
                    showAlert(`❌ Error: ${result.error}`, 'error');
                }
            } catch (error) {
                showAlert('❌ Error de conexión', 'error');
            }
        }

        async function cargarListaPosiciones() {
            try {
                const response = await fetch('/api/obtener_posiciones');
                const result = await response.json();
                if (result.status === 'success') {
                    const select = document.getElementById('posiciones-guardadas');
                    select.innerHTML = '<option value="">Seleccionar posición...</option>';
                    
                    result.posiciones.forEach(pos => {
                        const option = document.createElement('option');
                        option.value = pos.id;
                        option.textContent = pos.nombre;
                        select.appendChild(option);
                    });
                }
            } catch (error) {
                console.error('Error cargando posiciones:', error);
            }
        }

        async function cargarPosicion() {
            const select = document.getElementById('posiciones-guardadas');
            const posicionId = select.value;
            
            if (!posicionId) {
                showAlert('⚠️ Selecciona una posición', 'error');
                return;
            }

            try {
                const response = await fetch(`/api/cargar_posicion/${posicionId}`);
                const result = await response.json();
                if (result.status === 'success') {
                    showAlert(`✅ Posición "${result.posicion.nombre}" cargada`);
                    addTerminalLine(`Posición cargada: ${result.posicion.nombre}`);
                } else {
                    showAlert(`❌ Error: ${result.error}`, 'error');
                }
            } catch (error) {
                showAlert('❌ Error de conexión', 'error');
            }
        }

        async function eliminarPosicion() {
            const select = document.getElementById('posiciones-guardadas');
            const posicionId = select.value;
            
            if (!posicionId) {
                showAlert('⚠️ Selecciona una posición', 'error');
                return;
            }

            if (!confirm('¿Estás seguro de eliminar esta posición?')) return;

            try {
                const response = await fetch(`/api/eliminar_posicion/${posicionId}`, { method: 'DELETE' });
                const result = await response.json();
                if (result.status === 'success') {
                    showAlert('✅ Posición eliminada');
                    addTerminalLine('Posición eliminada');
                    cargarListaPosiciones();
                } else {
                    showAlert(`❌ Error: ${result.error}`, 'error');
                }
            } catch (error) {
                showAlert('❌ Error de conexión', 'error');
            }
        }

        // ======================= FUNCIONES AUXILIARES =======================
        async function cambiarVelocidad() {
            const velocidad = document.getElementById('velocidad-global').value;
            await sendCommand(`VELOCIDAD_${velocidad}`);
        }

        async function moverSecuencia() {
            await sendCommand('SECUENCIA');
        }

        function limpiarTerminal() {
            document.getElementById('terminal').innerHTML = '';
            addTerminalLine('Terminal limpiada');
        }

        // ======================= ACTUALIZACIÓN DE ESTADO =======================
        async function actualizarEstado() {
            try {
                const response = await fetch('/api/estado');
                const estado = await response.json();
                
                if (estado.error) {
                    console.error('Error actualizando estado:', estado.error);
                    return;
                }

                // Actualizar conexión
                document.getElementById('status-conexion').textContent = estado.conectado ? 'Conectado' : 'Desconectado';
                document.getElementById('status-conexion').className = estado.conectado ? 'status-badge status-connected' : 'status-badge status-disconnected';
                document.getElementById('status-wifi').textContent = estado.wifi_conectado ? 'WIFI: Conectado' : 'WIFI: Desconectado';

                // Actualizar posiciones
                document.getElementById('pos-m1').textContent = estado.posicion_m1 + '°';
                document.getElementById('pos-m2').textContent = estado.posicion_m2 + '°';
                document.getElementById('pos-m3').textContent = estado.posicion_m3 + '°';
                document.getElementById('pos-m4').textContent = estado.posicion_m4 + '°';

                // Actualizar velocidad
                document.getElementById('velocidad-global').value = estado.velocidad_actual;

            } catch (error) {
                console.error('Error actualizando estado:', error);
            }
        }

        // ======================= INICIALIZACIÓN =======================
        document.addEventListener('DOMContentLoaded', function() {
            actualizarEstado();
            cargarListaPosiciones();
            
            // Actualizar cada 2 segundos
            setInterval(actualizarEstado, 2000);
            setInterval(cargarListaPosiciones, 5000);
            
            addTerminalLine('Dashboard inicializado correctamente');
        });
    </script>
</body>
</html>
'''

# ======================= RUTAS PARA EL ESP32 =======================
@app.route('/api/conectar_serial')
def conectar_serial():
    """Simular conexión serial (luego se integra con ESP32 real)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Actualizar estado como conectado
        cursor.execute(
            "UPDATE estado_robot SET conectado = TRUE WHERE esp32_id = 'cobot_01'"
        )
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"status": "success", "message": "Conectado vía serial"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/desconectar_serial')
def desconectar_serial():
    """Simular desconexión serial"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE estado_robot SET conectado = FALSE WHERE esp32_id = 'cobot_01'"
        )
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"status": "success", "message": "Desconectado"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/mover_motor_grados', methods=['POST'])
def mover_motor_grados():
    """Mover motor por grados específicos"""
    try:
        data = request.json
        motor = data.get('motor')
        grados = data.get('grados')
        velocidad = data.get('velocidad')
        direccion = data.get('direccion')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """INSERT INTO comandos_robot 
            (esp32_id, comando, motor_num, grados, velocidad, direccion) 
            VALUES (%s, %s, %s, %s, %s, %s)""",
            ('cobot_01', 'MOVER_GRADOS', motor, grados, velocidad, direccion)
        )
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "status": "success", 
            "message": f"Motor M{motor} programado: {grados}° {direccion}"
        })
        
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/guardar_posicion', methods=['POST'])
def guardar_posicion():
    """Guardar posición actual"""
    try:
        data = request.json
        nombre = data.get('nombre')
        
        # Obtener estado actual
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM estado_robot WHERE esp32_id = 'cobot_01' ORDER BY timestamp DESC LIMIT 1")
        estado = cursor.fetchone()
        
        if estado:
            cursor.execute(
                """INSERT INTO posiciones_guardadas 
                (nombre, posicion_m1, posicion_m2, posicion_m3, posicion_m4, garra_estado, velocidad) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (nombre, estado[4], estado[5], estado[6], estado[7], 'ABIERTA' if estado[8] else 'CERRADA', estado[9])
            )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"status": "success", "message": f"Posición '{nombre}' guardada"})
        
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/obtener_posiciones')
def obtener_posiciones():
    """Obtener lista de posiciones guardadas"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, nombre FROM posiciones_guardadas ORDER BY timestamp DESC")
        posiciones = cursor.fetchall()
        
        posiciones_list = []
        for pos in posiciones:
            posiciones_list.append({"id": pos[0], "nombre": pos[1]})
        
        cursor.close()
        conn.close()
        
        return jsonify({"status": "success", "posiciones": posiciones_list})
        
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/cargar_posicion/<int:posicion_id>')
def cargar_posicion(posicion_id):
    """Cargar posición específica"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM posiciones_guardadas WHERE id = %s", (posicion_id,))
        posicion = cursor.fetchone()
        
        if posicion:
            # Guardar como comando para mover a esa posición
            cursor.execute(
                """INSERT INTO comandos_robot 
                (esp32_id, comando, posicion_m1, posicion_m2, posicion_m3, posicion_m4, garra_estado, velocidad) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                ('cobot_01', 'MOVER_POSICION', posicion[2], posicion[3], posicion[4], posicion[5], posicion[6], posicion[7])
            )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({
                "status": "success", 
                "posicion": {"nombre": posicion[1]}
            })
        else:
            return jsonify({"status": "error", "error": "Posición no encontrada"}), 404
            
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/eliminar_posicion/<int:posicion_id>', methods=['DELETE'])
def eliminar_posicion(posicion_id):
    """Eliminar posición guardada"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM posiciones_guardadas WHERE id = %s", (posicion_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"status": "success", "message": "Posición eliminada"})
        
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

# ======================= RUTAS EXISTENTES (mantener compatibilidad) =======================
@app.route('/')
def dashboard():
    return render_template_string(HTML_DASHBOARD)

@app.route('/api/comando/<accion>')
def enviar_comando(accion):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO comandos_robot (esp32_id, comando) VALUES (%s, %s)",
            ('cobot_01', accion.upper())
        )
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"status": "success", "comando": accion})
        
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/estado')
def obtener_estado():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM estado_robot WHERE esp32_id = 'cobot_01' ORDER BY timestamp DESC LIMIT 1")
        estado = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if estado:
            return jsonify({
                "conectado": bool(estado[2]),
                "wifi_conectado": bool(estado[3]),
                "posicion_m1": float(estado[4]),
                "posicion_m2": float(estado[5]),
                "posicion_m3": float(estado[6]),
                "posicion_m4": float(estado[7]),
                "garra_abierta": bool(estado[8]),
                "velocidad_actual": int(estado[9]),
                "emergency_stop": bool(estado[10])
            })
        else:
            return jsonify({"error": "No se encontró estado del robot"})
            
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/test_db')
def test_db():
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"status": "error", "error": "No se pudo conectar"})
            
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return jsonify({"status": "success", "message": "Conexión exitosa a MySQL"})
        
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

@app.route('/api/comandos_pendientes/<esp32_id>')
def obtener_comandos_pendientes(esp32_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM comandos_robot WHERE esp32_id = %s AND (ejecutado IS NULL OR ejecutado = FALSE) ORDER BY timestamp ASC LIMIT 10",
            (esp32_id,)
        )
        comandos = cursor.fetchall()
        
        comandos_list = []
        for cmd in comandos:
            comando_data = {
                "id": cmd[0],
                "comando": cmd[2],
                "motor_num": cmd[4],
                "pasos": cmd[5],
                "velocidad": cmd[6],
                "direccion": cmd[7],
                "grados": cmd[8]
            }
            comandos_list.append(comando_data)
        
        cursor.close()
        conn.close()
        
        return jsonify({"status": "success", "comandos": comandos_list})
        
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "cobot-dashboard-mejorado",
        "timestamp": time.time(),
        "database": "connected" if get_db_connection() else "disconnected"
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Iniciando Dashboard Cobot MEJORADO en puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
