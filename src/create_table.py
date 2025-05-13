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

#def create_test_table():
    #try:
        #conn = get_connection()
        #cursor = conn.cursor()
        #cursor.execute('''
            #CREATE TABLE IF NOT EXISTS test_logs (
                #id INT AUTO_INCREMENT PRIMARY KEY,
                #timestamp DATETIME NOT NULL,
                #vehicle_type VARCHAR(50) NOT NULL,
                #model_used VARCHAR(20) NOT NULL,
                #facultad VARCHAR(255) DEFAULT 'Desconocida'
#                
            #);
        #''')
        ## Añadir columna 'device_used' si no existe
        #cursor.execute("SHOW COLUMNS FROM test_logs LIKE 'device_used'")
        #if not cursor.fetchone():
            #print("⚠️ Añadiendo columna 'device_used'...")
            #cursor.execute('''
                #ALTER TABLE test_logs 
                #ADD COLUMN device_used VARCHAR(10) DEFAULT 'CPU' AFTER facultad
            #''')
#
        ## Añadir columna 'video_filename' si no existe
        #cursor.execute("SHOW COLUMNS FROM test_logs LIKE 'video_filename'")
        #if not cursor.fetchone():
            #print("⚠️ Añadiendo columna 'video_filename'...")
            #cursor.execute('''
                #ALTER TABLE test_logs 
                #ADD COLUMN video_filename VARCHAR(255) DEFAULT 'Desconocido' AFTER device_used
            #''')
        #conn.commit()
        #print("✅ Tabla de prueba 'test_logs' creada.")
    #except Exception as e:
        #print("❌ Error creando la tabla de prueba:", e)
    #finally:
        #cursor.close()
        #conn.close()
