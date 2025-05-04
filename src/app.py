from flask import Flask, render_template, request, redirect, url_for, flash, session, Response
import os
import cv2
import tempfile
import time
from yolo_processor import YOLOProcessor
from db import get_connection
#from create_table import create_vehicle_logs_table
from create_table import create_test_table  # Cambiamos a la función para crear la tabla de prueba

try:
    conn = get_connection()
    print("✅ Conexión a MySQL establecida.")
    conn.close()
except Exception as e:
    print("❌ Error conectando a MySQL:", e)

# Crear tabla si no existe
#create_vehicle_logs_table()
create_test_table()  # Cambiado a tabla de prueba



app = Flask(__name__)
app.secret_key = 'mi_clave_secreta'
app.config['STARTUP_TOKEN'] = str(time.time())

# De momento se almacenan los vídeos en archivos temp
video_source = None
selected_model = None

# Carga global del procesador con modelo por defecto
global_processor = YOLOProcessor(model_path='yolo11s.pt')

@app.before_request
def check_valid_session():
    if 'username' in session:
        if session.get('startup_token') != app.config['STARTUP_TOKEN']:
            session.clear()
            flash('La sesión expiró. Inicia sesión nuevamente.', 'warning')
            return redirect(url_for('login'))

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('expert_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == 'expert' and password == 'expert':
            session['username'] = username
            session['role'] = 'expert'
            session['startup_token'] = app.config['STARTUP_TOKEN']
            return redirect(url_for('expert_dashboard'))
        
        elif username == 'user' and password == 'user':  # Nuevo usuario básico
            session['username'] = username
            session['role'] = 'user'
            session['startup_token'] = app.config['STARTUP_TOKEN']
            return redirect(url_for('user_dashboard'))  # Nueva ruta
        
        else:
            flash('Credenciales incorrectas.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada.', 'info')
    return redirect(url_for('login'))

@app.route('/user_dashboard', methods=['GET', 'POST'])
def user_dashboard():
    if 'username' not in session or session.get('role') != 'user':
        return redirect(url_for('login'))
    
    report_data = None
    start_date = end_date = None

    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        
        try:
            
            # Añadir horas para completar los dias
            start_full_time = f"{start_date} 00:00:00"
            end_full_time = f"{end_date} 23:59:59"
            
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)

            
            # Consulta total 
            cursor.execute('''
                SELECT COUNT(*) as total FROM test_logs
                WHERE timestamp BETWEEN %s AND %s
            ''', (start_full_time, end_full_time))
            total = cursor.fetchone()['total']

            # Consulta por tipo de vehículo
            cursor.execute('''
                SELECT 
                    vehicle_type as type,
                    COUNT(*) as count
                FROM test_logs
                WHERE timestamp BETWEEN %s AND %s
                GROUP BY vehicle_type
            ''', (start_full_time, end_full_time))
            types = cursor.fetchall()

            report_data = {
                'total': total,
                'types': types  
            }

        except Exception as e:
            flash(f'Error al generar reporte: {str(e)}', 'danger')
            
    return render_template(
        'user_dashboard.html',
        report_data=report_data,
        start_date=start_date,
        end_date=end_date
    )

@app.route('/expert_dashboard', methods=['GET', 'POST'])
def expert_dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    global video_source, selected_model, global_processor
    if request.method == 'POST':
        video_file = request.files.get('video')
        model = request.form.get('model_type')  
        if video_file and model:
            selected_model = model
            # Reinstanciar el procesador con el modelo seleccionado
            global_processor = YOLOProcessor(model_path=selected_model)
            # Crear un archivo temporal para guardar el video durante el procesamiento
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            video_file.save(tmp_file.name)
            video_source = tmp_file.name
            flash(f"Video cargado. Modelo seleccionado: {selected_model}", "success")
        else:
            flash("Debes seleccionar un video y un modelo.", "warning")
    current_user = session.get('username', 'Desconocido')
    return render_template('expert_dashboard.html', current_user=current_user, selected_model=selected_model)

@app.route('/video_feed')
def video_feed():
    # Devuelve un streaming de los frames procesados con YOLO
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

def gen_frames():
    global video_source, global_processor
    if video_source is None:
        return  # Si no hay video, no se transmite nada.
    cap = cv2.VideoCapture(video_source)
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break
        # Redimensiona el frame para un procesamiento razonable en CPU (a ajustar más adelante)
        frame = cv2.resize(frame, (640, 480))
        processed_frame = global_processor.process_frame(frame)
        ret, buffer = cv2.imencode('.jpg', processed_frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    cap.release()
    # Al terminar, elimina el archivo temporal para no guardar videos
    if os.path.exists(video_source):
        os.remove(video_source)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
