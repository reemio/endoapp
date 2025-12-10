# FILE: src/ui/report_images_tab.py
# ICON REPLACEMENTS: Move and delete buttons now use PNG icons

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QLineEdit, QFrame, QGridLayout)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QIcon
import logging
from pathlib import Path

class ReportImageSlot(QFrame):
    moved = Signal(int, str)  # index, direction
    deleted = Signal(int)     # index
    label_changed = Signal(int, str)  # index, new_label

    def __init__(self, index, parent=None):
        super().__init__(parent)
        self.index = index
        self.setup_ui()

    def setup_ui(self):
        self.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.setLineWidth(2)
        self.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border: 1px solid #555;
                border-radius: 4px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Label field
        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText(f"Image {self.index + 1} Label")
        self.label_edit.textChanged.connect(
            lambda text: self.label_changed.emit(self.index, text)
        )
        layout.addWidget(self.label_edit)

        # Image display
        self.image_label = QLabel()
        self.image_label.setFixedSize(180, 120)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #1b1b1b;
                border: 1px dashed #555;
            }
        """)
        layout.addWidget(self.image_label)

        # Navigation buttons
        btn_layout = QHBoxLayout()
        
        # ICON REPLACEMENT: 
        self.left_btn = QPushButton()
        self.left_btn.setIcon(QIcon("icons/left.png"))
        self.left_btn.clicked.connect(lambda: self.moved.emit(self.index, "left"))
        
        # ICON REPLACEMENT: 
        self.right_btn = QPushButton()
        self.right_btn.setIcon(QIcon("icons/right.png"))
        self.right_btn.clicked.connect(lambda: self.moved.emit(self.index, "right"))
        
        # ICON REPLACEMENT: 
        self.delete_btn = QPushButton()
        self.delete_btn.setIcon(QIcon("icons/x.png"))
        self.delete_btn.clicked.connect(lambda: self.deleted.emit(self.index))

        # Style buttons
        for btn in [self.left_btn, self.right_btn, self.delete_btn]:
            btn.setFixedSize(30, 30)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #3b3b3b;
                    border: none;
                    border-radius: 15px;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #4b4b4b;
                }
            """)

        btn_layout.addWidget(self.left_btn)
        btn_layout.addWidget(self.right_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)

    def set_image(self, image_path=None, label=None):
        if image_path and Path(image_path).exists():
            pixmap = QPixmap(image_path)
            scaled_pixmap = pixmap.scaled(
                self.image_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
            if label is not None:
                self.label_edit.setText(label)
        else:
            self.clear()

    def clear(self):
        self.image_label.clear()
        self.image_label.setText("Empty Slot")
        self.label_edit.clear()

class ReportImagesTab(QWidget):
    images_changed = Signal()  # Emits when images are changed

    def __init__(self, parent=None):
        super().__init__(parent)
        self.images = []  # List of (path, label) tuples
        self.max_images = 6
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Title
        title = QLabel("Report Images (Max 6)")
        title.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: white;
            }
        """)
        layout.addWidget(title)

        # Grid for image slots
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(10)

        # Create image slots
        self.slots = []
        for i in range(self.max_images):
            slot = ReportImageSlot(i)
            slot.moved.connect(self.move_image)
            slot.deleted.connect(self.remove_image)
            slot.label_changed.connect(self.update_image_label)
            
            row = i // 3
            col = i % 3
            self.grid_layout.addWidget(slot, row, col)
            self.slots.append(slot)

        layout.addLayout(self.grid_layout)
        layout.addStretch()

    def add_image(self, image_path):
        """Add new image to report"""
        try:
            if len(self.images) >= self.max_images:
                logging.warning("Maximum number of report images reached")
                return False

            if not Path(image_path).exists():
                logging.error(f"Image file not found: {image_path}")
                return False

            self.images.append((image_path, ""))
            self.update_display()
            self.images_changed.emit()
            return True

        except Exception as e:
            logging.error(f"Failed to add image: {e}")
            return False

    def move_image(self, index, direction):
        """Move image left or right"""
        try:
            if direction == "left" and index > 0:
                self.images[index], self.images[index-1] = \
                    self.images[index-1], self.images[index]
                self.update_display()
                self.images_changed.emit()
            
            elif direction == "right" and index < len(self.images)-1:
                self.images[index], self.images[index+1] = \
                    self.images[index+1], self.images[index]
                self.update_display()
                self.images_changed.emit()

        except Exception as e:
            logging.error(f"Failed to move image: {e}")

    def remove_image(self, index):
        """Remove image from report"""
        try:
            if 0 <= index < len(self.images):
                self.images.pop(index)
                self.update_display()
                self.images_changed.emit()
        except Exception as e:
            logging.error(f"Failed to remove image: {e}")

    def update_image_label(self, index, label):
        """Update image label"""
        try:
            if 0 <= index < len(self.images):
                image_path = self.images[index][0]
                self.images[index] = (image_path, label)
                self.images_changed.emit()
        except Exception as e:
            logging.error(f"Failed to update image label: {e}")

    def update_display(self):
        """Update all image slots"""
        try:
            for i, slot in enumerate(self.slots):
                if i < len(self.images):
                    image_path, label = self.images[i]
                    slot.set_image(image_path, label)
                else:
                    slot.clear()
        except Exception as e:
            logging.error(f"Failed to update display: {e}")

    def get_images(self):
        """Get list of images and their labels
        
        Returns:
            List of (image_path, label) tuples
        """
        return self.images.copy()

    def set_images(self, images):
        """Set images from saved state"""
        try:
            self.images = images[:self.max_images].copy()
            self.update_display()
        except Exception as e:
            logging.error(f"Failed to set images: {e}")

    def clear(self):
        """Clear all images"""
        self.images.clear()
        self.update_display()

# ADD THIS TO THE END OF THE ReportImagesTab CLASS IN src/ui/report_images_tab.py
# (Make sure it's properly indented to be part of the class)

def get_images(self):
    """Get list of images and their labels
    
    Returns:
        List of (image_path, label) tuples
    """
    # Make sure images is defined
    if not hasattr(self, 'images'):
        self.images = []
    
    # Return a copy to prevent external modification
    return self.images.copy()