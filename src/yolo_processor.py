from ultralytics import YOLO
import cv2

class YOLOProcessor:
    def __init__(self, model_path='yolo11s.pt'):  # Nano model
        self.model = YOLO(model_path)
        self.class_list = self.model.names

    def process_frame(self, frame):
        # Run YOLO tracking on the frame
        results = self.model.track(frame, persist=True, classes=[1, 2, 3, 5, 6, 7])  # Vehicle classes

        # Check if boxes and tracking IDs exist
        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu()
            track_ids = results[0].boxes.id.int().cpu().tolist()
            class_indices = results[0].boxes.cls.int().cpu().tolist()
            confidences = results[0].boxes.conf.cpu()

            for box, track_id, class_idx, conf in zip(boxes, track_ids, class_indices, confidences):
                x1, y1, x2, y2 = map(int, box)
                cx = (x1 + x2) // 2  # Center x-coordinate
                cy = (y1 + y2) // 2  # Center y-coordinate
                class_name = self.class_list[class_idx]

                # Draw center point, label, and bounding box
                cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1)
                cv2.putText(frame, f"ID: {track_id} {class_name}", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        return frame