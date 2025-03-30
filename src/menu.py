import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QHBoxLayout
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import QUrl

def create_main_window():
    class VideoPlayer(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Reproductor de Video")
            self.setGeometry(100, 100, 800, 600)
            
            # Layout principal
            layout = QVBoxLayout(self)
            
            # Contenedor de botones en la parte superior
            button_layout = QHBoxLayout()
            
            # Botones
            self.open_button = QPushButton("Seleccionar Video")
            self.play_button = QPushButton("Reproducir")
            self.pause_button = QPushButton("Pausar")
            self.restart_button = QPushButton("Reiniciar")
            
            # Agregar botones al layout
            button_layout.addWidget(self.open_button)
            button_layout.addWidget(self.play_button)
            button_layout.addWidget(self.pause_button)
            button_layout.addWidget(self.restart_button)
            
            layout.addLayout(button_layout)
            
            # Widget de video
            self.video_widget = QVideoWidget()
            layout.addWidget(self.video_widget)
            
            # Media Player
            self.media_player = QMediaPlayer()
            self.media_player.setVideoOutput(self.video_widget)
            self.audio_output = QAudioOutput()
            self.media_player.setAudioOutput(self.audio_output)
            
            # Conectar botones
            self.open_button.clicked.connect(self.open_file)
            self.play_button.clicked.connect(self.media_player.play)
            self.pause_button.clicked.connect(self.media_player.pause)
            self.restart_button.clicked.connect(self.restart_video)
        
        def open_file(self):
            file_dialog = QFileDialog()
            file_path, _ = file_dialog.getOpenFileName(self, "Seleccionar Video", "", "Videos (*.mp4 *.avi *.mov)")
            if file_path:
                self.media_player.setSource(QUrl.fromLocalFile(file_path))
                self.media_player.play()
        
        def restart_video(self):
            self.media_player.setPosition(0)
            self.media_player.play()
    
    return VideoPlayer()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = create_main_window()
    player.show()
    sys.exit(app.exec())
