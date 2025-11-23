from flask import Flask, jsonify, render_template_string, request
import mysql.connector
import os
import time
from datetime import datetime

app = Flask(__name__)
# Eliminada la línea: CORS(app) - No es esencial para funcionalidad básica

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
            print("❌ No se pudo conectar a la base de datos")
            return False
            
        cursor = conn.cursor()
        
        # Crear tablas si no existen
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
                posicion_m1 FLOAT,
                posicion_m2 FLOAT,
                posicion_m3 FLOAT,
                posicion_m4 FLOAT,
                garra_estado VARCHAR(10),
                modo_conexion VARCHAR(20),
                ejecutado BOOLEAN DEFAULT FALSE,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS moduls_tellis (
                id INT AUTO_INCREMENT PRIMARY KEY,
                esp32_id VARCHAR(50),
                motores_activos BOOLEAN,
                emergency_stop BOOLEAN,
                posicion_m1 FLOAT,
                posicion_m2 FLOAT,
                posicion_m3 FLOAT,
                posicion_m4 FLOAT,
                garra_abierta BOOLEAN,
                garra_grados FLOAT,
                velocidad_actual INT,
                conexion_wifi BOOLEAN,
                senal_wifi INT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
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
        
        # Insertar estado inicial si no existe
        cursor.execute("SELECT * FROM moduls_tellis WHERE esp32_id = 'cobot_01'")
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO moduls_tellis 
                (esp32_id, motores_activos, emergency_stop, posicion_m1, posicion_m2, posicion_m3, posicion_m4, garra_abierta, garra_grados, velocidad_actual, conexion_wifi, senal_wifi) 
                VALUES 
                ('cobot_01', 0, 0, 0, 0, 0, 0, 1, 100, 500, 0, 0)
            ''')
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ BASE DE DATOS CONFIGURADA CORRECTAMENTE")
        return True
        
    except Exception as e:
        print(f"❌ Error configurando BD: {e}")
        return False

# Configurar base de datos al inicio
setup_database()

# ======================= HTML DASHBOARD (VERSIÓN SIMPLIFICADA) =======================
HTML_DASHBOARD = '''
<!DOCTYPE html>
<html>
<head>
    <title>🤖 Dashboard Control Robot</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        body { background: linear-gradient(135deg, #0f2027, #203a43, #2c5364); color: white; min-height: 100vh; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; padding: 20px; background: rgba(255, 255, 255, 0.1); border-radius: 15px; border: 1px solid rgba(255, 255, 255, 0.2); }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; background: linear-gradient(45deg, #00b4db, #0083b0); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .dashboard-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
        @media (max-width: 1024px) { .dashboard-grid { grid-template-columns: 1fr; } }
        .panel { background: rgba(255, 255, 255, 0.1); border-radius: 15px; padding: 25px; border: 1px solid rgba(255, 255, 255, 0.2); }
        .panel h2 { font-size: 1.8em; margin-bottom: 20px; color: #00b4db; border-bottom: 2px solid #00b4db; padding-bottom: 10px; }
        .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .status-item { background: rgba(0, 0, 0, 0.3); padding: 15px; border-radius: 10px; text-align: center; border-left: 4px solid #00b4db; }
        .status-item .label { font-size: 0.9em; opacity: 0.8; margin-bottom: 5px; }
        .status-item .value { font-size: 1.3em; font-weight: bold; color: #00b4db; }
        .status-item.emergency .value { color: #ff4444; }
        .status-item.active .value { color: #00C851; }
        .btn-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; margin-bottom: 15px; }
        .btn { padding: 12px 20px; border: none; border-radius: 8px; font-size: 1em; font-weight: bold; cursor: pointer; text-align: center; background: linear-gradient(45deg, #00b4db, #0083b0); color: white; }
        .btn:hover { transform: translateY(-2px); }
        .btn-emergency { background: linear-gradient(45deg, #ff4444, #cc0000); }
        .btn-success { background: linear-gradient(45deg, #00C851, #007E33); }
        .btn-warning { background: linear-gradient(45deg, #ffbb33, #FF8800); }
        .alert { padding: 15px; margin: 10px 0; border-radius: 5px; font-weight: bold; text-align: center; }
        .alert.success { background: rgba(0, 200, 81, 0.2); border: 1px solid #00C851; color: #00C851; }
        .alert.error { background: rgba(255, 68, 68, 0.2); border: 1px solid #ff4444; color: #ff4444; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 DASHBOARD CONTROL ROBOT 4DOF</h1>
            <p>Control completo del robot colaborativo</p>
        </div>

        <div id="alert-container"></div>

        <div class="dashboard-grid">
            <!-- PANEL IZQUIERDO: ESTADO Y CONTROL BÁSICO -->
            <div class="panel">
                <h2>📊 Estado del Robot</h2>
                
                <div class="status-grid" id="estado-container">
                    <div class="status-item">
                        <div class="label">🏃 Motores</div>
                        <div class="value" id="motores-activos">Cargando...</div>
                    </div>
                    <div class="status-item emergency">
                        <div class="label">🛑 Emergencia</div>
                        <div class="value" id="emergency-stop">Cargando...</div>
                    </div>
                    <div class="status-item">
                        <div class="label">🤖 Garra</div>
                        <div class="value" id="garra-estado">Cargando...</div>
                    </div>
                    <div class="status-item">
                        <div class="label">⚡ Velocidad</div>
                        <div class="value" id="velocidad-actual">Cargando...</div>
                    </div>
                </div>

                <div class="status-grid">
                    <div class="status-item">
                        <div class="label">📍 M1 Posición</div>
                        <div class="value" id="posicion-m1">0°</div>
                    </div>
                    <div class="status-item">
                        <div class="label">📍 M2 Posición</div>
                        <div class="value" id="posicion-m2">0°</div>
                    </div>
                    <div class="status-item">
                        <div class="label">📍 M3 Posición</div>
                        <div class="value" id="posicion-m3">0°</div>
                    </div>
                    <div class="status-item">
                        <div class="label">📍 M4 Posición</div>
                        <div class="value" id="posicion-m4">0°</div>
                    </div>
                </div>

                <h3>🎮 Control General</h3>
                <div class="btn-grid">
                    <button class="btn btn-success" onclick="sendCommand('ON')">🔌 ENERGIZAR</button>
                    <button class="btn btn-warning" onclick="sendCommand('OFF')">⚙️ APAGAR</button>
                    <button class="btn btn-emergency" onclick="sendCommand('STOP')">🛑 PARADA EMERGENCIA</button>
                    <button class="btn" onclick="sendCommand('RESET')">🔄 REINICIAR</button>
                </div>

                <h3>🦾 Control de Garra</h3>
                <div class="btn-grid">
                    <button class="btn" onclick="controlGarra('ABRIR')">🔓 ABRIR GARRA</button>
                    <button class="btn" onclick="controlGarra('CERRAR')">🔒 CERRAR GARRA</button>
                </div>
            </div>

            <!-- PANEL DERECHO: CONTROL AVANZADO -->
            <div class="panel">
                <h2>⚙️ Control Avanzado</h2>

                <h3>🔧 Control Directo por Motor</h3>
                <select id="motor-select" style="padding: 10px; margin: 10px 0; width: 100%; border-radius: 5px; background: rgba(255,255,255,0.1); color: white; border: 1px solid rgba(255,255,255,0.3);">
                    <option value="1">M1 - Motor 1</option>
                    <option value="2">M2 - Motor 2</option>
                    <option value="3">M3 - Motor 3</option>
                    <option value="4">M4 - Motor 4</option>
                </select>
                <input type="number" id="pasos-input" value="200" min="1" max="10000" style="padding: 10px; margin: 10px 0; width: 100%; border-radius: 5px; background: rgba(255,255,255,0.1); color: white; border: 1px solid rgba(255,255,255,0.3);">
                <input type="number" id="velocidad-input" value="500" min="1" max="1000" style="padding: 10px; margin: 10px 0; width: 100%; border-radius: 5px; background: rgba(255,255,255,0.1); color: white; border: 1px solid rgba(255,255,255,0.3);">
                <div class="btn-grid">
                    <button class="btn" onclick="moverMotorDirecto('H')">⟳ HORARIO</button>
                    <button class="btn" onclick="moverMotorDirecto('A')">⟲ ANTIHORARIO</button>
                </div>

                <h3>💾 Sistema de Comandos</h3>
                <div class="btn-grid">
                    <button class="btn" onclick="testDatabase()">🧪 Probar Base de Datos</button>
                    <button class="btn" onclick="verComandos()">📋 Ver Comandos</button>
                </div>

                <div id="info" style="margin-top: 20px; padding: 15px; background: rgba(0,0,0,0.3); border-radius: 10px;">
                    <strong>Información del Sistema:</strong><br>
                    <span id="db-status">Base de datos: Probando...</span>
                </div>
            </div>
        </div>
    </div>

    <script>
        function showAlert(message, type = 'success') {
            const alertContainer = document.getElementById('alert-container');
            const alert = document.createElement('div');
            alert.className = `alert ${type}`;
            alert.textContent = message;
            alertContainer.appendChild(alert);
            setTimeout(() => { alert.remove(); }, 5000);
        }

        async function sendCommand(comando) {
            try {
                const response = await fetch(`/api/comando/${comando}`);
                const result = await response.json();
                if (result.status === 'success') {
                    showAlert(`✅ Comando ${comando} enviado`);
                    actualizarEstado();
                } else {
                    showAlert(`❌ Error: ${result.error}`, 'error');
                }
            } catch (error) {
                showAlert('❌ Error de conexión', 'error');
            }
        }

        async function controlGarra(estado) {
            await sendCommand(estado);
        }

        async function moverMotorDirecto(direccion) {
            const motor = document.getElementById('motor-select').value;
            const pasos = document.getElementById('pasos-input').value;
            const velocidad = document.getElementById('velocidad-input').value;
            
            if (!pasos || pasos < 1) {
                showAlert('⚠️ Ingresa pasos válidos', 'error');
                return;
            }

            try {
                const response = await fetch('/api/mover_motor', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        motor: parseInt(motor),
                        pasos: parseInt(pasos),
                        velocidad: parseInt(velocidad),
                        direccion: direccion
                    })
                });
                const result = await response.json();
                if (result.status === 'success') {
                    showAlert(`✅ Motor M${motor} movido`);
                } else {
                    showAlert(`❌ Error: ${result.error}`, 'error');
                }
            } catch (error) {
                showAlert('❌ Error de conexión', 'error');
            }
        }

        async function actualizarEstado() {
            try {
                const response = await fetch('/api/estado');
                const estado = await response.json();
                if (estado.error) {
                    document.getElementById('estado-container').innerHTML = `<div class="alert error">❌ ${estado.error}</div>`;
                    return;
                }
                document.getElementById('motores-activos').textContent = estado.motores_activos ? 'ACTIVOS' : 'INACTIVOS';
                document.getElementById('motores-activos').className = estado.motores_activos ? 'value active' : 'value';
                document.getElementById('emergency-stop').textContent = estado.emergency_stop ? 'ACTIVADA' : 'NORMAL';
                document.getElementById('garra-estado').textContent = estado.garra_abierta ? 'ABIERTA' : 'CERRADA';
                document.getElementById('velocidad-actual').textContent = estado.velocidad_actual + ' RPM';
                document.getElementById('posicion-m1').textContent = estado.posicion_m1 + '°';
                document.getElementById('posicion-m2').textContent = estado.posicion_m2 + '°';
                document.getElementById('posicion-m3').textContent = estado.posicion_m3 + '°';
                document.getElementById('posicion-m4').textContent = estado.posicion_m4 + '°';
            } catch (error) {
                console.error('Error actualizando estado:', error);
            }
        }

        async function testDatabase() {
            try {
                const response = await fetch('/api/test_db');
                const result = await response.json();
                document.getElementById('db-status').textContent = 
                    result.status === 'success' ? 
                    '✅ Base de datos: CONECTADA' : 
                    '❌ Base de datos: ERROR - ' + result.error;
                showAlert(result.status === 'success' ? '✅ Base de datos conectada' : '❌ Error en base de datos', result.status === 'success' ? 'success' : 'error');
            } catch (error) {
                document.getElementById('db-status').textContent = '❌ Base de datos: ERROR DE CONEXIÓN';
                showAlert('❌ Error conectando a base de datos', 'error');
            }
        }

        async function verComandos() {
            try {
                const response = await fetch('/api/comandos_pendientes/cobot_01');
                const result = await response.json();
                if (result.status === 'success') {
                    showAlert(`📋 ${result.comandos.length} comandos pendientes`);
                    console.log('Comandos:', result.comandos);
                } else {
                    showAlert(`❌ Error: ${result.error}`, 'error');
                }
            } catch (error) {
                showAlert('❌ Error obteniendo comandos', 'error');
            }
        }

        // Actualizar estado cada 5 segundos
        setInterval(actualizarEstado, 5000);
        
        // Probar base de datos al cargar
        document.addEventListener('DOMContentLoaded', function() {
            actualizarEstado();
            testDatabase();
        });
    </script>
</body>
</html>
'''

# ======================= RUTAS PRINCIPALES =======================
@app.route('/')
def dashboard():
    return render_template_string(HTML_DASHBOARD)

@app.route('/api/comando/<accion>')
def enviar_comando(accion):
    """Comandos generales: ON, OFF, STOP, RESET, ABRIR, CERRAR"""
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"status": "error", "error": "No database connection"}), 500
            
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO comandos_robot (esp32_id, comando) VALUES (%s, %s)",
            ('cobot_01', accion.upper())
        )
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Comando guardado: {accion}")
        return jsonify({"status": "success", "comando": accion})
        
    except Exception as e:
        print(f"❌ Error en comando: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/mover_motor', methods=['POST'])
def mover_motor():
    """Mover motor específico con pasos y dirección"""
    try:
        data = request.json
        motor = data.get('motor')
        pasos = data.get('pasos')
        velocidad = data.get('velocidad')
        direccion = data.get('direccion')
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({"status": "error", "error": "No database connection"}), 500
            
        cursor = conn.cursor()
        
        cursor.execute(
            """INSERT INTO comandos_robot 
            (esp32_id, comando, motor_num, pasos, velocidad, direccion) 
            VALUES (%s, %s, %s, %s, %s, %s)""",
            ('cobot_01', 'MOVER_MOTOR', motor, pasos, velocidad, direccion)
        )
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Movimiento motor: M{motor}, {pasos} pasos")
        return jsonify({
            "status": "success", 
            "mensaje": f"Motor M{motor} movido {direccion}"
        })
        
    except Exception as e:
        print(f"❌ Error moviendo motor: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/estado')
def obtener_estado():
    """Obtener estado actual del robot"""
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"status": "error", "error": "No database connection"}), 500
            
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM moduls_tellis WHERE esp32_id = 'cobot_01' ORDER BY timestamp DESC LIMIT 1")
        estado = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if estado:
            return jsonify({
                "motores_activos": bool(estado[2]),
                "emergency_stop": bool(estado[3]), 
                "posicion_m1": float(estado[4]),
                "posicion_m2": float(estado[5]),
                "posicion_m3": float(estado[6]),
                "posicion_m4": float(estado[7]),
                "garra_abierta": bool(estado[8]),
                "velocidad_actual": int(estado[10])
            })
        else:
            return jsonify({"error": "No se encontró estado del robot"})
            
    except Exception as e:
        print(f"❌ Error obteniendo estado: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/test_db')
def test_db():
    """Probar conexión a la base de datos"""
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
    """Obtener comandos pendientes para un ESP32"""
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"status": "error", "error": "No database connection"}), 500
            
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
                "direccion": cmd[7]
            }
            comandos_list.append(comando_data)
        
        cursor.close()
        conn.close()
        
        return jsonify({"status": "success", "comandos": comandos_list})
        
    except Exception as e:
        print(f"❌ Error en comandos_pendientes: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/health')
def health_check():
    """Endpoint de salud para Render"""
    return jsonify({
        "status": "healthy",
        "service": "cobot-dashboard",
        "timestamp": time.time(),
        "database": "connected" if get_db_connection() else "disconnected"
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Iniciando Dashboard Cobot en puerto {port}")
    print(f"✅ Base de datos: {'Conectada' if get_db_connection() else 'Desconectada'}")
    app.run(host='0.0.0.0', port=port, debug=False)
