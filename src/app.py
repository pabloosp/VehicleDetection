from flask import Flask, render_template, request, redirect, url_for, flash, session, Response, make_response, jsonify
import os
import cv2
import tempfile
import time
from yolo_processor import YOLOProcessor
from db import get_connection
#from create_table import create_vehicle_logs_table
from create_table import create_test_table  # Cambiamos a la función para crear la tabla de prueba
from video_metadata import get_gps_from_video
import io
import csv
import torch
from facultades import facultad_por_coordenadas
ALLOWED_EXTENSIONS = {'.mov', '.mp4', '.avi'}

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
    global video_source, global_processor, selected_model
    for key in [
        'tmp_video_path', 'pending_model', 'pending_use_cuda',
        'pending_location', 'first_frame_path', 'selected_faculty',
        'gps_coords', 'video_ready'
    ]:
        session.pop(key, None)
    # Limpiar referencias globales
    video_source = None
    global_processor = None
    selected_model = None
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
    
    global video_source, global_processor, selected_model
    gps_coords = None
    show_gps= False
    show_faculty_form = False
    selected_faculty = None
    gps_status = None
    video_ready = session.get('video_ready', False)
    
    if request.method == 'POST':
        
        if session.get('video_ready'):
            flash("Finaliza el procesamiento actual antes de subir un nuevo video.", "warning")
            return redirect(url_for('expert_dashboard'))
        
        #Form de selección de facultad
        if 'facultad' in request.form:
            selected_faculty = request.form['facultad']
            session['selected_faculty'] = selected_faculty
            flash(f"Facultad asignada: {selected_faculty}", "success")
            
            session['pending_location'] = selected_faculty

            return redirect(url_for('expert_dashboard'))
        
        #Form principal
        video_file = request.files.get('video')
        if video_file and video_file.filename != '':
            model = request.form.get('model_type')  
            use_cuda = request.form.get('use_cuda') == 'on' and torch.cuda.is_available()
        
            if not model:
                flash("Debes seleccionar un modelo YOLO", "danger")
                return redirect(url_for('expert_dashboard'))
            
            if video_source and os.path.exists(video_source):
                os.remove(video_source)
            video_source = None
            selected_model = None
            if global_processor:
                global_processor.reset_counter()
            session.pop('tmp_video_path', None)
            session.pop('pending_model', None)
            session.pop('pending_use_cuda', None)
            
            try:
                file_ext = os.path.splitext(video_file.filename)[1].lower() #Extraer extensión
                tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
                video_file.save(tmp_file.name)
                cap = cv2.VideoCapture(tmp_file.name)   #Extraer 1r frame
                success, frame = cap.read()
                cap.release()
                if success:
                    frame_path = tmp_file.name + "_first.jpg"
                    cv2.imwrite(frame_path, frame)
                    session['first_frame_path'] = frame_path
                else:
                    flash("No se pudo obtener el primer frame del vídeo", "danger")
                    return redirect(url_for('expert_dashboard'))
            
            
                gps_coords = get_gps_from_video(tmp_file.name)
                show_gps = True  #Activar visualización de coords/aviso
                
                
                if gps_coords:
                    gps_status = "success"
                    lat = gps_coords['lat']
                    lon = gps_coords['lon']
                    
                    facultad_detectada = facultad_por_coordenadas(lat, lon)
                    
                    if facultad_detectada:
                        location = facultad_detectada
                        session['gps_coords'] = location
                        session['selected_faculty'] = location 
                        flash(f"Facultad detectada automáticamente: {facultad_detectada}", "success")
                    else:
                        location = None      #Mostrar form si tiene metadatos y no pertenecen a ninguna facultad
                        session['gps_coords'] = f"Lat: {lat:.6f}, Lon: {lon:.6f}"
                        show_faculty_form = True  
                        flash("Coordenadas detectadas, pero fuera de zonas conocidas. Seleccione la facultad manualmente.", "warning")

                    session['tmp_video_path'] = tmp_file.name
                    session['pending_model'] = model
                    session['pending_use_cuda'] = use_cuda
                    session['pending_location'] = location
                else:
                    gps_status = "warning"
                    flash("Coordenadas no detectadas. Por favor seleccione la facultad manualmente", "warning")
                    show_faculty_form = True
                    session['tmp_video_path'] = tmp_file.name
                    session['pending_model'] = model
                    session['pending_use_cuda'] = use_cuda
                
                device_status = "GPU" if use_cuda else "CPU"
                flash(
                    f"Video {file_ext} cargado | Modelo: {os.path.basename(model)} | "
                    f"Dispositivo: {device_status}",
                    "success"
                )
                
            except Exception as e:
                    flash(f"Error al inicializar el modelo: {str(e)}", "danger")
        
        elif 'facultad' not in request.form:
            flash("No se ha seleccionado ningún archivo de video", "danger")
            return redirect(url_for('expert_dashboard'))
        
        if session.get('video_ready'):
            session.pop('first_frame_path', None)

    selected_faculty = session.get('selected_faculty')
    return render_template('expert_dashboard.html', current_user=session.get('username', 'Desconocido'),selected_model=selected_model, cuda_available=torch.cuda.is_available(),gps_coords=gps_coords, show_gps=show_gps, show_faculty_form=show_faculty_form, selected_faculty=selected_faculty, gps_status=gps_status, video_ready=video_ready)

@app.route('/export_csv/<start_date>/<end_date>')
def export_csv(start_date, end_date):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        # Añadir horas para completar los dias
        start_full = f"{start_date} 00:00:00"
        end_full = f"{end_date} 23:59:59"
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('''
            SELECT timestamp, vehicle_type, model_used 
            FROM test_logs
            WHERE timestamp BETWEEN %s AND %s
            ORDER BY timestamp DESC
        ''', (start_full, end_full))
        
        records = cursor.fetchall()
        
        # Generar CSV
        import io
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Cabeceras
        writer.writerow(['Fecha y Hora', 'Tipo de Vehículo', 'Modelo Utilizado'])
        
        # Datos
        for record in records:
            writer.writerow([
                record['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                record['vehicle_type'],
                record['model_used']
            ])
        
        # Crear respuesta
        from flask import make_response
        response = make_response(output.getvalue())
        filename = f"reporte_{start_date}_a_{end_date}.csv"
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        response.headers['Content-type'] = 'text/csv'
        
        return response
        
    except Exception as e:
        flash(f'Error al generar CSV: {str(e)}', 'danger')
        return redirect(url_for('user_dashboard'))

@app.route('/video_feed')
def video_feed():
    # Devuelve un streaming de los frames procesados con YOLO
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

def gen_frames():
    global video_source, global_processor
    if video_source is None:
        return  # Si no hay video, no se transmite nada.
    cap = cv2.VideoCapture(video_source)
    video_path = video_source  # Guardar ruta antes de borrar referencia global
    video_source = None  
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
    if video_path and os.path.exists(video_path):
        try:
            os.remove(video_path)
        except PermissionError:
            print(f"No se pudo borrar el archivo {video_path} porque está en uso.")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/first_frame_image')
def first_frame_image():
    frame_path = session.get('first_frame_path')
    if frame_path and os.path.exists(frame_path):
        return Response(open(frame_path, 'rb').read(), mimetype='image/jpeg')
    return "Imagen no disponible", 404

@app.route('/set_line', methods=['POST'])
def set_line():
    global video_source, global_processor, selected_model
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No se recibió línea"}), 400

    pt1 = (int(data['x1']), int(data['y1']))
    pt2 = (int(data['x2']), int(data['y2']))

    try:
        # Recuperar datos de sesión (sin borrarlos aún)
        tmp_video = session.get('tmp_video_path')
        model = session.get('pending_model')
        use_cuda = session.get('pending_use_cuda')
        location = session.get('pending_location')

        if not all([tmp_video, model, location]):
            return jsonify({"error": "Datos de vídeo incompletos"}), 400

        selected_model = model
        video_source = tmp_video
        print("DEBUG /set_line")
        print("tmp_video:", tmp_video)
        print("model:", model)
        print("use_cuda:", use_cuda)
        print("location:", location)
        print("pt1:", pt1, "pt2:", pt2)
        
        global_processor = YOLOProcessor(model_path=model, use_cuda=use_cuda, default_location=location)
        global_processor.set_line(pt1, pt2)
        
        # Ahora que todo ha ido bien, limpiamos la sesión
        session.pop('tmp_video_path', None)
        session.pop('pending_model', None)
        session.pop('pending_use_cuda', None)
        session.pop('pending_location', None)

        # Borrar la imagen del primer frame
        first_frame_path = session.pop('first_frame_path', None)
        if first_frame_path and os.path.exists(first_frame_path):
            try:
                os.remove(first_frame_path)
            except:
                pass

        session['video_ready'] = True
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/end_video', methods=['POST'])
def end_video():
    global video_source, global_processor, selected_model
    video_source = None
    selected_model = None
    if global_processor:
        global_processor.reset_counter()
    session['video_ready'] = False
    session.pop('selected_faculty', None)
    flash("Procesamiento finalizado. Puedes subir un nuevo video.", "info")
    return redirect(url_for('expert_dashboard'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
