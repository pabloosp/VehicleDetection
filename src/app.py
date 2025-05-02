from flask import Flask, render_template, request, redirect, url_for, flash, session, Response
import os
import cv2
import tempfile
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

# De momento se almacenan los vídeos en archivos temp
video_source = None
selected_model = None

# Carga global del procesador con modelo por defecto
global_processor = YOLOProcessor(model_path='yolo11s.pt')

@app.route('/')
def index():
    # Simula un usuario
    session['username'] = 'Experto'
    return redirect(url_for('dashboard'))

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
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
    return render_template('dashboard.html', current_user=current_user, selected_model=selected_model)

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
