# create_table.py
from db import get_connection

def create_vehicle_logs_table():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vehicle_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp DATETIME NOT NULL,
                vehicle_type VARCHAR(50) NOT NULL,
                model_used VARCHAR(20) NOT NULL,
                facultad VARCHAR(255) DEFAULT 'Desconocida',
                device_used VARCHAR(10) DEFAULT 'CPU',
                video_filename VARCHAR(255) DEFAULT 'Desconocido'
            );
        ''')
        conn.commit()
        print("✅ Tabla 'vehicle_logs' verificada/creada.")
    except Exception as e:
        print("❌ Error creando la tabla 'vehicle_logs':", e)
    finally:
        cursor.close()
        conn.close()

def create_users_table():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(20) DEFAULT 'user'
            );
        ''')
        conn.commit()
        print("✅ Tabla 'users' verificada/creada.")
    except Exception as e:
        print("❌ Error creando la tabla 'users':", e)
    finally:
        cursor.close()
        conn.close()

