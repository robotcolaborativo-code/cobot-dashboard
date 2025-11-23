from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>🤖 Control Robot</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { 
                font-family: Arial, sans-serif; 
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea, #764ba2);
                min-height: 100vh;
            }
            .container {
                max-width: 600px;
                margin: 0 auto;
                background: white;
                padding: 30px;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            }
            h1 {
                text-align: center;
                color: #333;
                margin-bottom: 10px;
            }
            .btn {
                display: block;
                width: 100%;
                padding: 15px;
                margin: 10px 0;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                cursor: pointer;
            }
            .btn-on {
                background: #28a745;
                color: white;
            }
            .btn-off {
                background: #dc3545;
                color: white;
            }
            .status {
                padding: 15px;
                margin: 20px 0;
                border-radius: 10px;
                text-align: center;
                background: #d4edda;
                color: #155724;
                border: 2px solid #c3e6cb;
            }
            .message {
                margin-top: 20px;
                padding: 15px;
                border-radius: 8px;
                text-align: center;
                display: none;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 CONTROL ROBOT</h1>
            <p style="text-align: center; color: #666;">Dashboard básico - Versión 1.0</p>
            
            <div class="status">
                ✅ SERVIDOR FUNCIONANDO CORRECTAMENTE
            </div>
            
            <button class="btn btn-on" onclick="sendCommand('ON')">🔌 ENCENDER MOTORES</button>
            <button class="btn btn-off" onclick="sendCommand('OFF')">⚙️ APAGAR MOTORES</button>
            <button class="btn btn-on" onclick="sendCommand('ABRIR')">🔓 ABRIR GARRA</button>
            <button class="btn btn-off" onclick="sendCommand('CERRAR')">🔒 CERRAR GARRA</button>
            <button class="btn btn-off" onclick="sendCommand('STOP')">🛑 PARADA EMERGENCIA</button>
            
            <div id="message" class="message"></div>
        </div>

        <script>
            function showMessage(text, isError = false) {
                const messageDiv = document.getElementById('message');
                messageDiv.textContent = text;
                messageDiv.style.background = isError ? '#f8d7da' : '#d4edda';
                messageDiv.style.color = isError ? '#721c24' : '#155724';
                messageDiv.style.display = 'block';
                setTimeout(() => {
                    messageDiv.style.display = 'none';
                }, 3000);
            }

            async function sendCommand(comando) {
                try {
                    const response = await fetch(`/api/${comando}`);
                    const result = await response.json();
                    showMessage(`✅ ${result.message}`);
                } catch (error) {
                    showMessage('❌ Error de conexión', true);
                }
            }
        </script>
    </body>
    </html>
    """

@app.route('/api/ON')
def encender():
    return jsonify({"success": True, "message": "Motores energizados"})

@app.route('/api/OFF')
def apagar():
    return jsonify({"success": True, "message": "Motores apagados"})

@app.route('/api/ABRIR')
def abrir_garra():
    return jsonify({"success": True, "message": "Garra abierta"})

@app.route('/api/CERRAR')
def cerrar_garra():
    return jsonify({"success": True, "message": "Garra cerrada"})

@app.route('/api/STOP')
def parada_emergencia():
    return jsonify({"success": True, "message": "Parada de emergencia activada"})

@app.route('/api/health')
def health_check():
    return jsonify({"status": "healthy", "service": "cobot-dashboard"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print("🚀 Servidor iniciado en puerto", port)
    app.run(host='0.0.0.0', port=port, debug=False)