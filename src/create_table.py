# create_table.py
from db import get_connection

def create_vehicle_logs_table():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vehicle_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp DATETIME NOT NULL
            );
        ''')
        conn.commit()
        print("✅ Tabla 'vehicle_logs' verificada/creada.")
    except Exception as e:
        print("❌ Error creando la tabla 'vehicle_logs':", e)
    finally:
        cursor.close()
        conn.close()
