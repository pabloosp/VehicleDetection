import sys
from PyQt6.QtWidgets import QApplication
from menu import VideoPlayer

if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = VideoPlayer()
    player.show()
    sys.exit(app.exec())