from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QFileDialog, QHBoxLayout, QLabel
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap
import cv2
from yolo_processor import YOLOProcessor

class VideoPlayer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vehicle Detection Video Player")
        self.setGeometry(100, 100, 800, 600)  # Initial window size

        # Initialize YOLO processor
        self.yolo_processor = YOLOProcessor()

        # Main layout
        layout = QVBoxLayout(self)

        # Button layout
        button_layout = QHBoxLayout()
        self.open_button = QPushButton("Seleccionar Video")
        self.play_button = QPushButton("Reproducir")
        self.pause_button = QPushButton("Pausar")
        self.restart_button = QPushButton("Reiniciar")
        
        button_layout.addWidget(self.open_button)
        button_layout.addWidget(self.play_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.restart_button)
        
        layout.addLayout(button_layout)

        # Video display label
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center the video
        layout.addWidget(self.video_label)

        # Timer for frame updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

        # Connect buttons to functions
        self.open_button.clicked.connect(self.open_file)
        self.play_button.clicked.connect(self.timer.start)
        self.pause_button.clicked.connect(self.timer.stop)
        self.restart_button.clicked.connect(self.restart_video)

    def open_file(self):
        """Open a video file and prepare for playback."""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Seleccionar Video", "", "Videos (*.mp4 *.avi *.mov)")
        if file_path:
            # Release any existing video capture
            if hasattr(self, 'cap') and self.cap.isOpened():
                self.cap.release()
            self.cap = cv2.VideoCapture(file_path)
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.timer.setInterval(int(1000 / self.fps))  # Set interval based on FPS
            # Set initial label size to video resolution
            self.video_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.video_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.video_label.setMinimumSize(self.video_width, self.video_height)
            self.timer.start()  # Start playing immediately

    def update_frame(self):
        """Process and display the next video frame."""
        if not hasattr(self, 'cap') or not self.cap.isOpened():
            return

        ret, frame = self.cap.read()
        if not ret:
            self.timer.stop()
            return

        # Resize frame to reduce processing load (e.g., 640x480)
        frame = cv2.resize(frame, (640, 480))

        # Process frame with YOLO
        processed_frame = self.yolo_processor.process_frame(frame)

        # Convert frame to RGB and scale it to fit the label while keeping aspect ratio
        frame_rgb = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        qimage = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        # Scale to fit the label, respecting maximum video resolution
        pixmap = QPixmap.fromImage(qimage).scaled(
            self.video_label.size(), 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        self.video_label.setPixmap(pixmap)

    def restart_video(self):
        """Restart the video from the beginning."""
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.timer.start()

    def closeEvent(self, event):
        """Clean up resources when closing the window."""
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
        event.accept()