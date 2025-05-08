import cv2
from ultralytics import YOLO
from flask import Flask, render_template, request, redirect, url_for, flash, session, Response
import os
import tempfile
from db import get_connection
import datetime
from ultralytics import YOLO
import torch

class YOLOProcessor:
    def __init__(self, model_path='yolo11s.pt', use_cuda=False, default_location="Desconocida"):
        #Configurar Cuda
        self.device = 'cuda' if (use_cuda and torch.cuda.is_available()) else 'cpu'
        # Cargar el modelo YOLO
        self.model = YOLO(model_path).to(self.device)
        # Guardar el nombre del modelo y quitar pt
        self.model_name = os.path.basename(model_path).replace('.pt', '')
        # Lista de nombres de clases que puede detectar el modelo
        self.class_list = self.model.names
        # Conjunto para almacenar IDs de vehículos que ya cruzaron
        self.crossed_ids = set()
        # Contador total de vehículos
        self.vehicle_count = 0
        # Posición Y de la línea de conteo (ajustable)
        self.line_y = 150
        # Diccionario para guardar posiciones anteriores de vehículos
        self.prev_centers = {}
        # Ubi
        self.current_location = default_location  # Nuevo atributo
        
        print(f"Modelo cargado en: {self.device.upper()}")
        
    def set_line(self, pt1, pt2):
        self.line_start = pt1
        self.line_end = pt2
        

    def reset_counter(self):
        """Reinicia todos los contadores y registros"""
        self.crossed_ids = set()
        self.vehicle_count = 0
        self.prev_centers = {}
        
    def save_vehicle_log(self, vehicle_type):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            timestamp = datetime.datetime.now()  # Obtener la fecha y hora actuales
            cursor.execute('''
                INSERT INTO test_logs (timestamp, vehicle_type, model_used, facultad)
                VALUES (%s, %s, %s, %s)
            ''', (timestamp, vehicle_type, self.model_name, self.current_location))
            conn.commit()
            print(f"✅ Vehículo ({vehicle_type}) registrado con modelo {self.model_name} en {self.current_location}")
        except Exception as e:
            print("❌ Error guardando el log del vehículo:", e)
        finally:
            cursor.close()
            conn.close()

    def process_frame(self, frame):
        """Procesa un frame para detectar y contar vehículos"""
        # Detectar y rastrear vehículos (solo clases especificadas)
        results = self.model.track(frame, persist=True, classes=[2, 3, 5, 7], device=self.device)  # 2: coche, 3: moto, 5: autobús, 7: camión

        if results[0].boxes is not None and results[0].boxes.id is not None:
            # Obtener coordenadas de las cajas delimitadoras
            boxes = results[0].boxes.xyxy.cpu()
            # Obtener IDs de seguimiento
            track_ids = results[0].boxes.id.int().cpu().tolist()
            # Obtener índices de clase
            class_indices = results[0].boxes.cls.int().cpu().tolist()

            for box, track_id, class_idx in zip(boxes, track_ids, class_indices):
                # Convertir coordenadas a enteros
                x1, y1, x2, y2 = map(int, box)
                # Calcular centro del vehículo
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

                # Dibujar caja delimitadora y centro
                cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1) # Punto rojo en el centro
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)  # Caja verde
                # Mostrar ID del vehículo
                cv2.putText(frame, f"ID: {track_id}", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1, cv2.LINE_AA)
                
                # Verificar si el vehículo cruzó la línea
                if track_id in self.prev_centers:
                    prev_point = self.prev_centers[track_id]
                    curr_point = (cx, cy)

                    def lines_intersect(a1, a2, b1, b2):
                        """Verifica si los segmentos (a1, a2) y (b1, b2) se cruzan"""
                        def ccw(p1, p2, p3):
                            return (p3[1]-p1[1]) * (p2[0]-p1[0]) > (p2[1]-p1[1]) * (p3[0]-p1[0])
                        return ccw(a1, b1, b2) != ccw(a2, b1, b2) and ccw(a1, a2, b1) != ccw(a1, a2, b2)

                    if hasattr(self, 'line_start') and hasattr(self, 'line_end'):
                        crossed = lines_intersect(prev_point, curr_point, self.line_start, self.line_end)
                    else:
                        crossed = prev_point[1] <= self.line_y and cy > self.line_y

                    if crossed and track_id not in self.crossed_ids:
                        self.crossed_ids.add(track_id)
                        self.vehicle_count += 1
                        vehicle_type = "Coche" if class_idx == 2 else "Moto" if class_idx == 3 else "Furgoneta" if class_idx == 5 else "Camión"
                        self.save_vehicle_log(vehicle_type)
                
                # Guardar posición actual para el próximo frame
                self.prev_centers[track_id] = (cx, cy)

        # Dibujar línea de conteo y contador
        # Dibuja línea personalizada si está definida
        if hasattr(self, 'line_start') and hasattr(self, 'line_end'):
            cv2.line(frame, self.line_start, self.line_end, (0, 0, 255), 3)
        else:
            cv2.line(frame, (50, self.line_y), (370, self.line_y), (0, 0, 255), 3)  # Línea roja
            
        cv2.putText(frame, f"Vehicles: {self.vehicle_count}", (50, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)  # Contador blanco
        return frame