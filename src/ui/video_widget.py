from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                              QLabel, QPushButton)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from src.core.camera_manager import CameraManager

class VideoWidget(QWidget):
    image_captured = Signal(str)  # Emits image path when captured
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_camera()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Video display
        self.video_label = QLabel()
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: black;
                border: 1px solid #333;
            }
        """)
        layout.addWidget(self.video_label)

        # Controls
        controls_layout = QHBoxLayout()
        
        self.capture_btn = QPushButton("Capture Image")
        self.record_btn = QPushButton("Start Recording")
        
        self.capture_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        
        self.record_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        
        controls_layout.addWidget(self.capture_btn)
        controls_layout.addWidget(self.record_btn)
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)

    def setup_camera(self):
        self.camera = CameraManager()
        self.camera.frame_ready.connect(self.update_frame)
        self.camera.camera_error.connect(self.handle_camera_error)
        self.camera.image_captured.connect(self.image_captured.emit)
        
        # Connect buttons
        self.capture_btn.clicked.connect(self.camera.capture_image)
        self.record_btn.clicked.connect(self.toggle_recording)
        
        # Initialize recording state
        self.is_recording = False

    def update_frame(self, image):
        if not isinstance(image, QImage):
            return
            
        pixmap = QPixmap.fromImage(image)
        if pixmap.isNull():
            return
            
        # Scale pixmap to fit label while maintaining aspect ratio
        scaled_pixmap = pixmap.scaled(
            self.video_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.video_label.setPixmap(scaled_pixmap)

    def toggle_recording(self):
        if not self.is_recording:
            self.camera.start_recording()
            self.record_btn.setText("Stop Recording")
            self.record_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffc107;
                    color: black;
                    border: none;
                    padding: 8px 15px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #e0a800;
                }
            """)
            self.is_recording = True
        else:
            self.camera.stop_recording()
            self.record_btn.setText("Start Recording")
            self.record_btn.setStyleSheet("""
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border: none;
                    padding: 8px 15px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)
            self.is_recording = False

    def handle_camera_error(self, error_msg):
        print(f"Camera error: {error_msg}")

    def cleanup(self):
        self.camera.cleanup_camera()