# FILE: src/ui/captured_media_tab.py
# ICON REPLACEMENTS: Delete buttons now use X.png icon

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QScrollArea, QGridLayout)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QIcon
from pathlib import Path
import logging

class ImageThumbnail(QWidget):
    selected = Signal(str)  # Emits image path when selected
    deleted = Signal(str)   # Emits path when deleted

    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.image_path = str(image_path)
        self.is_selected = False
        self.setup_ui()
        self.load_image()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Image display
        self.image_label = QLabel()
        # Increased thumbnail size
        self.image_label.setFixedSize(200, 150)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #e8e8e8;
                border: none;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.image_label)

        # Buttons
        btn_layout = QHBoxLayout()
        
        # ICON REPLACEMENT: 
        self.select_btn = QPushButton()
        self.select_btn.setIcon(QIcon("icons/tick.png"))
        self.select_btn.setFixedSize(40, 40)  # Larger buttons
        self.select_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50; /* Green */
                color: white;
                border: none;
                border-radius: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        # ICON REPLACEMENT: Use X icon instead of text
        self.delete_btn = QPushButton()
        self.delete_btn.setIcon(QIcon("icons/x.png"))
        self.delete_btn.setFixedSize(40, 40)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336; /* Red */
                color: white;
                border: none;
                border-radius: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        
        # Connect button clicks
        self.select_btn.clicked.connect(self.handle_select)
        self.delete_btn.clicked.connect(lambda: self.deleted.emit(self.image_path))
        
        btn_layout.addWidget(self.select_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        # Set initial unselected state
        self.set_selected(False)

    def handle_select(self):
        # Toggle selection state
        self.set_selected(not self.is_selected)
        # Emit signal with path
        self.selected.emit(self.image_path)
    
    def set_selected(self, selected):
        """Set the selected state of this thumbnail"""
        self.is_selected = selected
        
        # Update visual appearance based on selection state
        if selected:
            # Highlight the entire thumbnail
            self.setStyleSheet("""
                QWidget {
                    background-color: #e3f2fd; /* Light blue background */
                    border: 2px solid #2196F3; /* Blue border */
                    border-radius: 6px;
                }
            """)
        else:
            # Reset to default style
            self.setStyleSheet("")
    
    def load_image(self):
        try:
            pixmap = QPixmap(self.image_path)
            scaled_pixmap = pixmap.scaled(
                self.image_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
        except Exception as e:
            logging.error(f"Failed to load image {self.image_path}: {e}")
            self.image_label.setText("Failed to load")

class CapturedMediaTab(QWidget):
    image_selected = Signal(str)  # Emits path when image is selected
    image_deleted = Signal(str)   # Emits path when image is deleted

    def __init__(self, parent=None):
        super().__init__(parent)
        self.images = []
        self.selected_images = set()  # Track selected images
        self.thumbnails = {}  # Keep references to thumbnails
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #f5f5f5;
            }
        """)

        # Container for grid
        self.container = QWidget()
        self.container.setStyleSheet("background-color: #f5f5f5;")
        self.grid_layout = QGridLayout(self.container)
        self.grid_layout.setSpacing(10)
        
        scroll.setWidget(self.container)
        layout.addWidget(scroll)

    def add_image(self, image_path):
        """Add a new image to the grid"""
        try:
            # Create thumbnail
            thumbnail = ImageThumbnail(image_path)
            thumbnail.selected.connect(self.handle_image_selected)
            thumbnail.deleted.connect(self.handle_image_deleted)

            # Add to grid
            row = len(self.images) // 3
            col = len(self.images) % 3
            
            self.grid_layout.addWidget(thumbnail, row, col)
            self.images.append(image_path)
            
            # Store reference to thumbnail
            self.thumbnails[image_path] = thumbnail
            
            logging.info(f"Added image to grid: {image_path}")
            return True  # Success
            
        except Exception as e:
            logging.error(f"Failed to add image to grid: {e}")
            return False

    def handle_image_deleted(self, image_path):
        """Handle image deletion"""
        try:
            # Remove from list
            if image_path in self.images:
                self.images.remove(image_path)
                
                # Delete file
                Path(image_path).unlink(missing_ok=True)
                
                # Rebuild grid
                self.rebuild_grid()
                
                # Emit signal
                self.image_deleted.emit(image_path)
                
                logging.info(f"Deleted image: {image_path}")
                
        except Exception as e:
            logging.error(f"Failed to delete image: {e}")

    def rebuild_grid(self):
        """Rebuild the entire grid after deletion"""
        # Clear grid
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Clear thumbnails dictionary but keep selected_images set
        self.thumbnails.clear()

        # Rebuild with remaining images
        for i, image_path in enumerate(self.images):
            thumbnail = ImageThumbnail(image_path)
            thumbnail.selected.connect(self.handle_image_selected)
            thumbnail.deleted.connect(self.handle_image_deleted)
            
            # Restore selection state if this image was previously selected
            if image_path in self.selected_images:
                thumbnail.set_selected(True)
            
            row = i // 3
            col = i % 3
            self.grid_layout.addWidget(thumbnail, row, col)
            
            # Store reference to new thumbnail
            self.thumbnails[image_path] = thumbnail

    def handle_image_selected(self, image_path):
        """Handle image selection and update visual state"""
        try:
            # Toggle selection in our tracking set
            if image_path in self.selected_images:
                self.selected_images.remove(image_path)
                # Update visual state if we still have the thumbnail
                if image_path in self.thumbnails:
                    self.thumbnails[image_path].set_selected(False)
            else:
                self.selected_images.add(image_path)
                # Update visual state if we still have the thumbnail
                if image_path in self.thumbnails:
                    self.thumbnails[image_path].set_selected(True)
                
            # Forward the selection signal
            self.image_selected.emit(image_path)
            
            logging.info(f"Image selection toggled: {image_path}")
            
        except Exception as e:
            logging.error(f"Failed to handle image selection: {e}")
    
    def clear(self):
        """Clear all images"""
        self.images.clear()
        self.selected_images.clear()
        self.thumbnails.clear()
        self.rebuild_grid()