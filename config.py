# config.py - Configuración de la base de datos
import os

def get_mysql_config():
    """Obtiene configuración MySQL desde variables de entorno de Railway"""
    
    # PRIORIDAD 1: DATABASE_URL de Railway
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url and database_url.startswith('mysql://'):
        try:
            # Formato: mysql://user:password@host:port/database
            database_url = database_url.replace('mysql://', '')
            user_pass, host_db = database_url.split('@')
            user, password = user_pass.split(':')
            host_port, database = host_db.split('/')
            host, port = host_port.split(':') if ':' in host_port else (host_port, '3306')
            
            print(f"✅ Configuración desde DATABASE_URL: {host}:{port}")
            
            return {
                'host': host,
                'port': int(port),
                'user': user,
                'password': password,
                'database': database
            }
        except Exception as e:
            print(f"❌ Error parseando DATABASE_URL: {e}")
    
    # PRIORIDAD 2: Variables individuales de Railway
    mysql_host = os.environ.get('MYSQLHOST') or os.environ.get('MYSQL_HOST')
    
    if mysql_host:
        print(f"✅ Configuración desde variables individuales: {mysql_host}")
        return {
            'host': mysql_host,
            'port': int(os.environ.get('MYSQLPORT', 3306)),
            'user': os.environ.get('MYSQLUSER') or os.environ.get('MYSQL_USER', 'root'),
            'password': os.environ.get('MYSQLPASSWORD') or os.environ.get('MYSQL_PASSWORD', ''),
            'database': os.environ.get('MYSQLDATABASE') or os.environ.get('MYSQL_DATABASE', 'railway')
        }
    
    # PRIORIDAD 3: Fallback para desarrollo
    print("⚠️ Usando configuración de desarrollo")
    return {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': '',
        'database': 'cobot_db'
    }
