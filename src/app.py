from flask import Flask, render_template, request, redirect, url_for, flash, session, Response, make_response, jsonify
import os
import cv2
import tempfile
import time
from yolo_processor import YOLOProcessor
from db import get_connection
from create_table import create_vehicle_logs_table, create_users_table
#from create_table import create_test_table  # Cambiamos a la función para crear la tabla de prueba
from video_metadata import get_gps_from_video
import io
import csv
import torch
import datetime
from facultades import facultad_por_coordenadas
from flask import g
from translations import translations
from mysql.connector.errors import IntegrityError, Error
from werkzeug.security import generate_password_hash, check_password_hash
ALLOWED_EXTENSIONS = {'.mov', '.mp4', '.avi'}

from dotenv import load_dotenv
load_dotenv()        
print("✅  python-dotenv está disponible y load_dotenv() no ha fallado.")

try:
    conn = get_connection()
    print("✅ Conexión a MySQL establecida.")
    conn.close()
except Exception as e:
    print("❌ Error conectando a MySQL:", e)

# Crear tabla si no existe
create_vehicle_logs_table()
create_users_table()
#create_test_table()  # Cambiado a tabla de prueba



app = Flask(__name__)
app.secret_key = os.environ['FLASK_SECRET']
app.config['STARTUP_TOKEN'] = str(time.time())

# De momento se almacenan los vídeos en archivos temp
video_source = None
selected_model = None

# Carga global del procesador con modelo por defecto
global_processor = YOLOProcessor(model_path='yolo11s.pt')

@app.before_request
def set_language():
    lang = session.get('lang', 'es')  # Idioma por defecto
    g.t = translations.get(lang, translations['es'])

@app.before_request
def check_valid_session():
    if 'username' in session:
        if session.get('startup_token') != app.config['STARTUP_TOKEN']:
            session.clear()
            flash(g.t['session_expired'], 'warning')
            return redirect(url_for('login'))



@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('expert_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        try:
            conn   = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT username, password, role FROM users WHERE username = %s",
                (username,)
            )
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            # Validación
            if user and check_password_hash(user['password'], password):
                session['username']      = user['username']
                session['role']          = user['role']
                session['startup_token'] = app.config['STARTUP_TOKEN']

                return redirect(
                    url_for('expert_dashboard')
                    if user['role'] == 'expert'
                    else url_for('user_dashboard')
                )

            flash(g.t['invalid_credentials'], 'danger')

        except Error as e:
            flash(f"DB error: {e}", 'danger')

    return render_template('login.html', t=g.t)

@app.route('/logout')
def logout():
    global video_source, global_processor, selected_model
    # Guardamos el idioma actual antes de limpiar la sesión
    current_lang = session.get('lang')
    
    # Limpiamos el resto de la sesión
    session.clear()
    
    # Restauramos el idioma
    if current_lang:
        session['lang'] = current_lang
    
    flash(g.t['session_closed'], 'info')
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
                SELECT COUNT(*) as total FROM vehicle_logs
                WHERE timestamp BETWEEN %s AND %s
            ''', (start_full_time, end_full_time))
            total = cursor.fetchone()['total']

            # Consulta por tipo de vehículo
            cursor.execute('''
                SELECT 
                    vehicle_type as type,
                    COUNT(*) as count
                FROM vehicle_logs
                WHERE timestamp BETWEEN %s AND %s
                GROUP BY vehicle_type
            ''', (start_full_time, end_full_time))
            types = cursor.fetchall()
            
            # KPI: Porcentaje por tipo (con número absoluto)
            tipo_map = {"Coche": 0, "Moto": 0, "Furgoneta": 0, "Camión": 0}
            for row in types:
                tipo_map[row['type']] = row['count']

            vehicle_percentages = []
            for tipo, count in tipo_map.items():
                percentage = round((count / total) * 100, 1) if total > 0 else 0
                vehicle_percentages.append({
                    'type': tipo,
                    'count': count,
                    'percentage': percentage
                })

            # Consulta para gráfico por día y tipo
            cursor.execute('''
                SELECT DATE(timestamp) as dia, vehicle_type, COUNT(*) as count
                FROM vehicle_logs
                WHERE timestamp BETWEEN %s AND %s
                GROUP BY dia, vehicle_type
                ORDER BY dia ASC
            ''', (start_full_time, end_full_time))
            grouped_data = cursor.fetchall()

            # Reestructurar para gráfico
            from collections import defaultdict
            chart_data = defaultdict(lambda: defaultdict(int))
            for row in grouped_data:
                chart_data[str(row['dia'])][row['vehicle_type']] = row['count']

            # Convertir a lista para pasar a template
            chart_data_formatted = [
                {"dia": dia, **counts}
                for dia, counts in chart_data.items()
            ]

            # KPI: promedio por día
            num_days = (datetime.datetime.strptime(end_date, "%Y-%m-%d") - datetime.datetime.strptime(start_date, "%Y-%m-%d")).days + 1
            avg_per_day = round(total / num_days, 2) if num_days > 0 else 0

            # KPI: día con más tráfico
            daily_total = defaultdict(int)
            for row in grouped_data:
                daily_total[row['dia']] += row['count']
            # KPI: día con más tráfico
            busiest_day_raw = max(daily_total.items(), key=lambda x: x[1])[0] if daily_total else None
            busiest_day = datetime.datetime.strptime(str(busiest_day_raw), "%Y-%m-%d").strftime("%d/%m/%Y") if busiest_day_raw else 'N/A'
            # KPI: día con menos tráfico
            quietest_day_raw = min(daily_total.items(), key=lambda x: x[1])[0] if daily_total else None
            quietest_day = datetime.datetime.strptime(str(quietest_day_raw), "%Y-%m-%d").strftime("%d/%m/%Y") if quietest_day_raw else 'N/A'
            
            #3 col KPI
            # Modelo más usado
            cursor.execute('''
                SELECT model_used, COUNT(*) as count
                FROM vehicle_logs
                WHERE timestamp BETWEEN %s AND %s
                GROUP BY model_used
                ORDER BY count DESC
                LIMIT 1
            ''', (start_full_time, end_full_time))
            top_model = cursor.fetchone()
            top_model_name = top_model['model_used'] if top_model else "N/A"

            # Vídeos distintos
            cursor.execute('''
                SELECT COUNT(DISTINCT video_filename) as video_count
                FROM vehicle_logs
                WHERE timestamp BETWEEN %s AND %s
            ''', (start_full_time, end_full_time))
            video_count = cursor.fetchone()['video_count']

            # Facultad más registrada
            cursor.execute('''
                SELECT facultad, COUNT(*) as count
                FROM vehicle_logs
                WHERE timestamp BETWEEN %s AND %s
                GROUP BY facultad
                ORDER BY count DESC
                LIMIT 1
            ''', (start_full_time, end_full_time))
            top_faculty = cursor.fetchone()
            top_faculty_name = top_faculty['facultad'] if top_faculty else "N/A"

            # Facultad menos registrada
            cursor.execute('''
                SELECT facultad, COUNT(*) as count
                FROM vehicle_logs
                WHERE facultad IS NOT NULL AND facultad != ''
                AND timestamp BETWEEN %s AND %s
                GROUP BY facultad
                ORDER BY count ASC
                LIMIT 1
            ''', (start_full_time, end_full_time))
            low_faculty = cursor.fetchone()
            low_faculty_name = low_faculty['facultad'] if low_faculty else "N/A"

            cursor.execute('''
                SELECT facultad,
                    COUNT(*) AS total,
                    SUM(vehicle_type = 'Coche') AS coche,
                    SUM(vehicle_type = 'Moto') AS moto,
                    SUM(vehicle_type = 'Furgoneta') AS furgoneta,
                    SUM(vehicle_type = 'Camión') AS camion,
                    COUNT(DISTINCT video_filename) AS videos
                FROM vehicle_logs
                WHERE facultad IS NOT NULL AND facultad != ''
                AND timestamp BETWEEN %s AND %s
                GROUP BY facultad
            ''', (start_full_time, end_full_time))

            facultades_rows = cursor.fetchall()
            facultades_data = []

            for row in facultades_rows:
                total_facultad = row['total']
                def fmt(count):  # formato "7 (35%)
                    pct = round((count / total_facultad) * 100, 1) if total_facultad > 0 else 0
                    return count, f"{count} ({pct}%)"
                
                val_coche, label_coche = fmt(row['coche'])
                val_moto, label_moto = fmt(row['moto'])
                val_furg, label_furg = fmt(row['furgoneta'])
                val_camion, label_camion = fmt(row['camion'])

                facultades_data.append({
                    'facultad': row['facultad'],
                    'total': total_facultad,
                    'coche': label_coche,
                    'coche_value': val_coche,
                    'moto': label_moto,
                    'moto_value': val_moto,
                    'furgoneta': label_furg,
                    'furgoneta_value': val_furg,
                    'camion': label_camion,
                    'camion_value': val_camion,
                    'videos': row['videos']
                })

    
            report_data = {
                'total': total,
                'types': types,
                'chart_data': chart_data_formatted,
                'avg_per_day': avg_per_day,
                'busiest_day': busiest_day,
                'quietest_day': quietest_day,
                'vehicle_percentages': vehicle_percentages,
                'top_model': top_model_name,
                'video_count': video_count,
                'top_faculty': top_faculty_name,
                'low_faculty': low_faculty_name,
                'facultades': facultades_data
            }

        except Exception as e:
            flash(f"{g.t['error_generate_report']}: {str(e)}", 'danger')
        
    return render_template(
        'user_dashboard.html',
        report_data=report_data,
        chart_data=report_data['chart_data'] if report_data else None,
        start_date=start_date,
        end_date=end_date, t=g.t
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
            flash(g.t['must_finish_first'], "warning")
            return redirect(url_for('expert_dashboard'))
        
        #Form de selección de facultad
        if 'facultad' in request.form:
            selected_faculty = request.form['facultad']
            session['selected_faculty'] = selected_faculty
            flash(f"{g.t['assigned_faculty']}: {selected_faculty}", "success")
            
            session['pending_location'] = selected_faculty

            return redirect(url_for('expert_dashboard'))
        
        #Form principal
        video_file = request.files.get('video')
        if video_file and video_file.filename != '':
            model = request.form.get('model_type')  
            use_cuda = request.form.get('use_cuda') == 'on' and torch.cuda.is_available()
        
            if not model:
                flash(g.t['must_select_model'], "danger")
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
                session['original_filename'] = video_file.filename
                if global_processor:
                    global_processor.current_video_filename = video_file.filename
                cap = cv2.VideoCapture(tmp_file.name)   #Extraer 1r frame
                success, frame = cap.read()
                cap.release()
                if success:
                    frame_path = tmp_file.name + "_first.jpg"
                    cv2.imwrite(frame_path, frame)
                    session['first_frame_path'] = frame_path
                else:
                    flash(g.t['no_first_frame'], "danger")
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
                        flash(f"{g.t['auto_faculty']}: {facultad_detectada}", "success")
                    else:
                        location = None      #Mostrar form si tiene metadatos y no pertenecen a ninguna facultad
                        session['gps_coords'] = f"Lat: {lat:.6f}, Lon: {lon:.6f}"
                        show_faculty_form = True  
                        flash(g.t['manual_faculty_msg'], "warning")

                    session['tmp_video_path'] = tmp_file.name
                    session['pending_model'] = model
                    session['pending_use_cuda'] = use_cuda
                    session['pending_location'] = location
                else:
                    gps_status = "warning"
                    flash(g.t['no_coords'], "warning")
                    show_faculty_form = True
                    session['tmp_video_path'] = tmp_file.name
                    session['pending_model'] = model
                    session['pending_use_cuda'] = use_cuda
                
                device_status = "GPU" if use_cuda else "CPU"
                flash(
                    f"{g.t['video_loaded']} {file_ext} | {g.t['model_selected']}: {os.path.basename(model)} | "
                    f"{g.t['device']}: {device_status}",
                    "success"
                )
                
            except Exception as e:
                    flash(f"{g.t['error_init_model']}: {str(e)}", "danger")
        
        elif 'facultad' not in request.form:
            flash(g.t['no_video_selected'], "danger")
            return redirect(url_for('expert_dashboard'))
        
        if session.get('video_ready'):
            session.pop('first_frame_path', None)

    selected_faculty = session.get('selected_faculty')
    return render_template('expert_dashboard.html', current_user=session.get('username', 'Desconocido'),selected_model=selected_model, cuda_available=torch.cuda.is_available(),gps_coords=gps_coords, show_gps=show_gps, show_faculty_form=show_faculty_form, selected_faculty=selected_faculty, gps_status=gps_status, video_ready=video_ready, t=g.t)

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
            SELECT timestamp, vehicle_type, model_used, facultad, device_used, video_filename
            FROM vehicle_logs
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
        writer.writerow([g.t['csv_header_datetime'],g.t['csv_header_type'],g.t['csv_header_model'],g.t['csv_header_faculty'],g.t['csv_header_device'],g.t['csv_header_filename']])
        
        # Datos
        for record in records:
            writer.writerow([
                record['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                record['vehicle_type'],
                record['model_used'],
                record.get('facultad', 'N/A'),
                record.get('device_used', 'N/A'),
                record.get('video_filename', 'N/A')
            ])
        
        # Crear respuesta
        from flask import make_response
        response = make_response(output.getvalue())
        filename = g.t['report_filename'].format(start_date, end_date)
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        response.headers['Content-type'] = 'text/csv'
        
        return response
        
    except Exception as e:
        flash(f"{g.t['error_generate_csv']}: {str(e)}", 'danger')
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
    return g.t['image_not_available'], 404

@app.route('/set_line', methods=['POST'])
def set_line():
    global video_source, global_processor, selected_model
    
    data = request.get_json()
    if not data:
        return jsonify({"error": g.t['error_no_line']}), 400

    pt1 = (int(data['x1']), int(data['y1']))
    pt2 = (int(data['x2']), int(data['y2']))

    try:
        # Recuperar datos de sesión (sin borrarlos aún)
        tmp_video = session.get('tmp_video_path')
        model = session.get('pending_model')
        use_cuda = session.get('pending_use_cuda')
        location = session.get('pending_location')
        original_filename = session.get('original_filename', 'Desconocido')

        if not all([tmp_video, model, location]):
            return jsonify({"error": g.t['error_incomplete_data']}), 400

        selected_model = model
        video_source = tmp_video
        print("DEBUG /set_line")
        print("tmp_video:", tmp_video)
        print("model:", model)
        print("use_cuda:", use_cuda)
        print("location:", location)
        print("pt1:", pt1, "pt2:", pt2)
        print("original_filename:", original_filename)
        
        global_processor = YOLOProcessor(model_path=model, use_cuda=use_cuda, default_location=location)
        global_processor.current_video_filename = original_filename
        global_processor.set_line(pt1, pt2)
        
        # Ahora que todo ha ido bien, limpiamos la sesión
        session.pop('tmp_video_path', None)
        session.pop('pending_model', None)
        session.pop('pending_use_cuda', None)
        session.pop('pending_location', None)
        session.pop('original_filename', None)

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
    flash(g.t['processing_finished'], "info")
    return redirect(url_for('expert_dashboard'))

@app.route('/set_lang/<lang>')
def set_lang(lang):
    if lang in translations:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'username' in session:
        return redirect(url_for(
            'expert_dashboard' if session.get('role') == 'expert' else 'user_dashboard'
        ))

    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        role     = request.form['role']          # 'user' o 'expert'

        if not username or not password:
            flash(g.t['invalid_credentials'], 'danger')
            return redirect(url_for('register'))
        
        hashed_pw = generate_password_hash(password)

        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                (username, hashed_pw, role)       # ← contraseña en texto plano
            )
            conn.commit()
            flash(g.t['registration_success'], 'success')
            return redirect(url_for('login'))

        except IntegrityError:                   # usuario duplicado
            flash(g.t['user_exists'], 'warning')
        except Exception as e:
            flash(f"{g.t['registration_error']}: {e}", 'danger')
        finally:
            cursor.close()
            conn.close()

    return render_template('register.html', t=g.t)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
