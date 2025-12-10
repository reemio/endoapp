# FILE: src/ui/right_panel.py
# ICON REPLACEMENTS: Camera and Record buttons now use PNG icons

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget,
    QScrollArea, QGridLayout, QFrame, QSizePolicy, QFileDialog, QLineEdit,
    QComboBox, QSlider, QToolButton
)
from PySide6.QtCore import Qt, Signal, QSize, QTimer, QPoint
from PySide6.QtGui import QImage, QPixmap, QPainter, QFont, QIcon, QColor
import logging
from pathlib import Path
from typing import Optional

try:
    import cv2
except ImportError:
    logging.warning("OpenCV (cv2) not found. Video thumbnail/duration features will be basic or disabled.")
    cv2 = None

import subprocess
import platform
import os

# Import the CapturedMediaTab and ReportImagesTab classes
from src.ui.captured_media_tab import CapturedMediaTab
from src.ui.report_images_tab import ReportImagesTab

# Constants for thumbnail sizes
CAPTURED_THUMB_WIDTH = 200
CAPTURED_THUMB_HEIGHT = 150
REPORT_SLOT_IMAGE_MIN_SIZE = 150


class VideoFeed(QWidget):
    """Video feed display area. Buttons are now managed by RightPanel."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setupUI()

    def setupUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        self.video_label = QLabel()
        self.video_label.setMinimumHeight(200) 
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setScaledContents(True) 
        self.video_label.setStyleSheet("QLabel { background-color: black; border: none; }")
        self.video_label.setText("Initializing camera...")
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.video_label, 1)
        
        self.recording_indicator = QLabel(self.video_label) 
        self.recording_indicator.setStyleSheet("QLabel { color:red;font-weight:bold;background-color:rgba(0,0,0,160);border-radius:4px;padding:3px 6px;font-size:9pt;}")
        self.recording_indicator.setAlignment(Qt.AlignCenter)
        self.recording_indicator.setText("● REC 00:00")
        self.recording_indicator.adjustSize()
        self.recording_indicator.hide()
        
        self.blink_timer = QTimer(self)
        self.blink_timer.setInterval(500)
        self.blink_timer.timeout.connect(self.toggle_indicator_visibility)
        self.video_label.installEventFilter(self)

    def eventFilter(self, w, e):
        if w == self.video_label and e.type() == e.Type.Resize:
            self.reposition_recording_indicator()
        return super().eventFilter(w, e)

    def reposition_recording_indicator(self):
        if hasattr(self, 'recording_indicator') and self.video_label and self.recording_indicator.isVisible():
            self.recording_indicator.adjustSize()
            ind_w = self.recording_indicator.width()
            lbl_w = self.video_label.width()
            self.recording_indicator.move(lbl_w - ind_w - 5, 5)

    def update_frame(self, qi: QImage):
        if qi.isNull(): 
            self.video_label.setText("No signal...")
            return
        self.video_label.setPixmap(QPixmap.fromImage(qi))

    def update_recording_time(self, ts: str):
        if hasattr(self, 'recording_indicator'):
            pfx = "● " if self.recording_indicator.text().startswith("●") else "  "
            txt = f"REC {ts}"
            self.recording_indicator.setText(f"{pfx}{txt}")
            self.reposition_recording_indicator()

    def start_recording_indicator(self):
        if hasattr(self, 'recording_indicator'):
            self.recording_indicator.setText("● REC 00:00")
            self.reposition_recording_indicator()
            self.recording_indicator.show()
            if not self.blink_timer.isActive():
                self.blink_timer.start()

    def stop_recording_indicator(self):
        if hasattr(self, 'recording_indicator'):
            if self.blink_timer.isActive():
                self.blink_timer.stop()
            self.recording_indicator.hide()

    def toggle_indicator_visibility(self):
        if hasattr(self, 'recording_indicator') and self.recording_indicator.isVisible():
            ct = self.recording_indicator.text()
            tp = ct.split("REC", 1)
            time_part = ("REC" + tp[1]) if len(tp) > 1 else "REC 00:00"
            self.recording_indicator.setText(("  " if ct.startswith("●") else "● ") + time_part)

    def cleanup(self):
        if hasattr(self, 'blink_timer'):
            self.blink_timer.stop()
        logging.info("VideoFeed cleanup.")


class BaseMediaThumbnail(QWidget):
    selected = Signal(str) 
    deleted = Signal(str)  
    
    TICK_STYLE = """QPushButton { 
        background-color: transparent !important;
        min-width: 36px; 
        max-width: 36px; 
        min-height: 36px; 
        max-height: 36px; 
        border: none !important; 
        padding: 0px; 
    } 
    QPushButton:hover { 
        background-color: rgba(69, 160, 73, 0.15); 
        border-radius: 18px;
    }"""
    
    CROSS_STYLE = """QPushButton { 
        background-color: transparent !important;
        min-width: 36px; 
        max-width: 36px; 
        min-height: 36px; 
        max-height: 36px; 
        border: none !important; 
        padding: 0px; 
    } 
    QPushButton:hover { 
        background-color: rgba(211, 47, 47, 0.15); 
        border-radius: 18px;
    }"""

    def __init__(self, media_path, parent=None):
        super().__init__(parent)
        self.media_path = str(media_path)
        self.parent_tab = parent 
        self._raw_pixmap = None 
        self.is_selected_for_report_visual = False
        self.setMinimumWidth(CAPTURED_THUMB_WIDTH + 10)
        self.setMinimumHeight(CAPTURED_THUMB_HEIGHT + 40)
        self.setup_thumbnail_ui()
        
    def setup_thumbnail_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5,5,5,5)
        main_layout.setSpacing(0)
        
        image_container = QWidget()
        image_container.setFixedSize(CAPTURED_THUMB_WIDTH, CAPTURED_THUMB_HEIGHT + 40)
        image_container_layout = QVBoxLayout(image_container)
        image_container_layout.setContentsMargins(0,0,0,0)
        image_container_layout.setSpacing(0)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("QLabel { background-color: #e8e8e8; border: none; border-radius: 3px; }")
        self.image_label.setFixedSize(CAPTURED_THUMB_WIDTH, CAPTURED_THUMB_HEIGHT)
        image_container_layout.addWidget(self.image_label)
        
        button_container = QWidget()
        button_container.setFixedHeight(40)
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0,5,0,0)
        button_layout.setSpacing(10)
        
        # ICON REPLACEMENT: Use tick icon instead of text
        self.tick_button = QPushButton()
        self.tick_button.setIcon(QIcon("icons/tick.png"))  # Using tick icon for select
        self.tick_button.setFixedSize(36, 36)
        self.tick_button.setStyleSheet(self.TICK_STYLE)
        self.tick_button.setToolTip("Add to report images")
        self.tick_button.clicked.connect(lambda: self.selected.emit(self.media_path))
        
        # ICON REPLACEMENT: Use X icon instead of text
        self.cross_button = QPushButton()
        self.cross_button.setIcon(QIcon("icons/x.png"))
        self.cross_button.setFixedSize(36, 36)
        self.cross_button.setStyleSheet(self.CROSS_STYLE)
        self.cross_button.setToolTip("Delete this media")
        self.cross_button.clicked.connect(lambda: self.deleted.emit(self.media_path))
        
        button_layout.addStretch()
        button_layout.addWidget(self.tick_button)
        button_layout.addSpacing(8)
        button_layout.addWidget(self.cross_button)
        button_layout.addStretch()
        
        image_container_layout.addWidget(button_container)
        main_layout.addWidget(image_container)
        main_layout.addStretch()
        
        self.setToolTip(Path(self.media_path).name)
    
    def _update_pixmap_display(self): 
        if hasattr(self, '_raw_pixmap') and self._raw_pixmap and not self._raw_pixmap.isNull():
            scaled_pixmap = self._raw_pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
        elif not hasattr(self, '_raw_pixmap') or not self._raw_pixmap: 
            self.image_label.setText("No Preview") 
            self.image_label.setStyleSheet("QLabel { background-color: #e8e8e8; border: none; border-radius: 3px; color: #666; qproperty-alignment: AlignCenter; }")

    def set_highlighted(self, highlighted=True):
        """Set highlighted state (blue border when image is in report)"""
        try:
            self._is_highlighted = highlighted
            if highlighted:
                self.setStyleSheet("""
                    QWidget { 
                        border: 4px solid #2196F3 !important; 
                        border-radius: 4px !important; 
                        background-color: #e3f2fd !important; 
                    }
                    QLabel {
                        border: none !important;
                    }
                """)
                self.tick_button.setStyleSheet("""
                    QPushButton {
                        background-color: #4CAF50 !important;
                        border-radius: 14px !important;
                        border: none !important;
                        padding: 5px !important;
                        color: white !important;
                        font-size: 18px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #45a049 !important;
                    }
                """)
                self.tick_button.setToolTip("Already added to report")
                logging.info(f"Highlighted thumbnail for: {self.media_path}")
            else:
                self.setStyleSheet("")
                self.tick_button.setStyleSheet(self.TICK_STYLE)
                self.tick_button.setToolTip("Add to report images")
        except Exception as e: 
            logging.error(f"MediaThumb: set_highlighted error: {e}")


class ImageThumbnail(BaseMediaThumbnail):
    def __init__(self, image_path, parent=None):
        super().__init__(image_path, parent)
        self.load_image()

    def load_image(self):
        try:
            self._raw_pixmap = QPixmap(self.media_path) 
            if self._raw_pixmap.isNull():
                self.image_label.setText("Load Error")
                logging.warning(f"IT: Null pixmap {self.media_path}")
                return
            self._update_pixmap_display() 
        except Exception as e:
            logging.error(f"IT: Load failed {self.media_path}: {e}")
            self.image_label.setText("Load Failed")


class VideoThumbnail(BaseMediaThumbnail):
    play_clicked = Signal(str)
    
    def __init__(self, video_path, thumbnail_image_path=None, parent=None):
        super().__init__(video_path, parent)
        self.thumbnail_image_path = thumbnail_image_path
        self.load_video_thumb()
        
        self.image_label.mousePressEvent = lambda e: self.play_clicked.emit(self.media_path)
        
        if hasattr(self, 'tick_button'):
            self.tick_button.setVisible(False)
            self.tick_button.setEnabled(False)
            
        # Use play icon for video play button
        self.play_button = QPushButton()
        self.play_button.setIcon(QIcon("icons/record.png"))  # Using record icon for play
        self.play_button.setFixedSize(36, 36)
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(25, 135, 84, 0.7);
                border-radius: 18px;
                border: none;
                padding: 5px;
                color: white;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(25, 135, 84, 0.9);
            }
        """)
        self.play_button.setToolTip("Play video")
        self.play_button.clicked.connect(lambda: self.play_clicked.emit(self.media_path))
        
        self.mousePressEvent = lambda event: self.play_clicked.emit(self.media_path)

        self.play_overlay = QLabel("▶", self.image_label) 
        self.play_overlay.setAlignment(Qt.AlignCenter)
        self.play_overlay.setStyleSheet("""
            QLabel { 
                color: white; 
                background-color: rgba(0,0,0,0.4); 
                border-radius: 18px; 
                font-size: 24px; 
                qproperty-alignment: AlignCenter; 
            }
        """)
        self.play_overlay.setFixedSize(36,36)
        self.play_overlay.show()

        self.duration_label = QLabel(self.image_label) 
        self.duration_label.setAlignment(Qt.AlignAbsolute | Qt.AlignRight | Qt.AlignBottom) 
        self.duration_label.setStyleSheet("""
            QLabel { 
                color: white; 
                background-color: rgba(0,0,0,0.6); 
                border-radius: 2px; 
                padding: 1px 4px; 
                font-size: 8pt; 
            }
        """)
        self.duration_label.hide() 
        self.load_duration() 
        self.reposition_overlays() 

    def load_video_thumb(self):
        try:
            if self.thumbnail_image_path and Path(self.thumbnail_image_path).exists():
                self._raw_pixmap = QPixmap(self.thumbnail_image_path)
            
            if self._raw_pixmap is None or self._raw_pixmap.isNull():
                self._raw_pixmap = QPixmap(CAPTURED_THUMB_WIDTH, CAPTURED_THUMB_HEIGHT)
                self._raw_pixmap.fill(QColor("#1c1c1c"))
                painter = QPainter(self._raw_pixmap)
                painter.setPen(Qt.darkGray)
                painter.setFont(QFont("Arial", 10, QFont.Bold))
                painter.drawText(self._raw_pixmap.rect(), Qt.AlignCenter, "Video")
                painter.end()
            self._update_pixmap_display()
        except Exception as e:
            logging.error(f"VT: Load thumb failed {self.media_path}: {e}")
            self.image_label.setText("Video Error")
    
    def load_duration(self):
        try:
            if hasattr(self.parent_tab, "get_video_duration"):
                duration_str = self.parent_tab.get_video_duration(self.media_path)
                if duration_str and duration_str != "00:00": 
                    self.duration_label.setText(duration_str)
                    self.duration_label.show()
                else:
                    self.duration_label.hide()
            else:
                self.duration_label.hide()
        except Exception as e:
            logging.error(f"VT: Failed to load duration: {e}")
            self.duration_label.hide()
        self.reposition_overlays()

    def resizeEvent(self, event: QSize): 
        super().resizeEvent(event)
        self.reposition_overlays()

    def reposition_overlays(self):
        if hasattr(self,'image_label') and self.image_label:
            label_width = self.image_label.width()
            label_height = self.image_label.height()
            if hasattr(self,'play_overlay'):
                self.play_overlay.move((label_width - self.play_overlay.width())//2, (label_height - self.play_overlay.height())//2)
            if hasattr(self,'duration_label') and self.duration_label.isVisible():
                self.duration_label.adjustSize()
                self.duration_label.move(label_width - self.duration_label.width() - 2, label_height - self.duration_label.height() - 2)


class MediaScrollArea(QScrollArea): 
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame) 
        self.setStyleSheet("QScrollArea { background-color: #f5f5f5; border: none; }")

        self.container_widget = QWidget()
        self.container_widget.setStyleSheet("QWidget { background-color: #f5f5f5; }")
        self.content_layout = QHBoxLayout(self.container_widget)
        self.content_layout.setContentsMargins(3,3,3,3)
        self.content_layout.setSpacing(5)
        self.content_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.setWidget(self.container_widget)
        self.container_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def add_thumbnail(self, thumbnail_widget: QWidget): 
        self.content_layout.addWidget(thumbnail_widget)

    def clear_thumbnails(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()


class CapturedContentTab(QWidget):
    item_selected = Signal(str) 
    item_deleted = Signal(str)  
    video_play_requested = Signal(str) 

    def __init__(self, media_type, parent=None): 
        super().__init__(parent)
        self.media_type = media_type
        self.items_paths = []
        self.thumbnail_widgets = {}
        self.setupUI()
        
        tooltip = "Click to add to report" if media_type == "image" else "Click to play video"
        self.setToolTip(tooltip)

    def setupUI(self): 
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        self.media_scroll_area = MediaScrollArea(self)
        layout.addWidget(self.media_scroll_area)

    def add_media_item(self, item_path_str: str):
        if item_path_str in self.thumbnail_widgets: 
            logging.info(f"CCT ({self.media_type}): Item {item_path_str} exists.")
            return
        try:
            thumbnail_widget = None
            if self.media_type == "image":
                thumbnail_widget = ImageThumbnail(item_path_str, self) 
                thumbnail_widget.selected.connect(self.item_selected.emit) 
                thumbnail_widget.deleted.connect(self._handle_item_deleted_internal)
            elif self.media_type == "video":
                thumbnail_widget = VideoThumbnail(item_path_str, self._generate_or_get_video_thumbnail_path(item_path_str), self) 
                thumbnail_widget.selected.connect(self.item_selected.emit) 
                thumbnail_widget.deleted.connect(self._handle_item_deleted_internal)
                thumbnail_widget.play_clicked.connect(self.video_play_requested.emit)
            
            if thumbnail_widget:
                self.media_scroll_area.add_thumbnail(thumbnail_widget)
                self.items_paths.append(item_path_str)
                self.thumbnail_widgets[item_path_str] = thumbnail_widget
        except Exception as e: 
            logging.error(f"CCT ({self.media_type}): Failed to add item {item_path_str}: {e}")

    def _handle_item_deleted_internal(self, item_path_str: str):
        try:
            if item_path_str in self.items_paths:
                self.items_paths.remove(item_path_str)
            thumb_widget_to_remove = self.thumbnail_widgets.pop(item_path_str, None)
            if thumb_widget_to_remove:
                thumb_widget_to_remove.deleteLater()
            
            self.item_deleted.emit(item_path_str) 
            
            file_to_delete = Path(item_path_str)
            file_to_delete.unlink(missing_ok=True)
            logging.info(f"CCT ({self.media_type}): Deleted file {item_path_str}")
            
            if self.media_type == "video": 
                thumb_cache_dir = Path("data/cache/thumbnails")
                cached_thumb_path = thumb_cache_dir / f"{file_to_delete.stem}_thumb.jpg"
                cached_thumb_path.unlink(missing_ok=True)
        except Exception as e: 
            logging.error(f"CCT ({self.media_type}): Failed to handle deletion for {item_path_str}: {e}")

    def _generate_or_get_video_thumbnail_path(self, video_path_str: str) -> Optional[str]: 
        video_file = Path(video_path_str)
        thumb_cache_dir = Path("data/cache/thumbnails")
        thumb_cache_dir.mkdir(parents=True,exist_ok=True)
        thumb_path = thumb_cache_dir / f"{video_file.stem}_thumb.jpg"
        
        if thumb_path.exists() and thumb_path.stat().st_size > 0:
            return str(thumb_path)
            
        if cv2:
            try:
                cap = cv2.VideoCapture(video_path_str)
                if not cap.isOpened():
                    logging.warning(f"CV2:FailOpenVidThumb:{video_path_str}")
                    return None
                fps = cap.get(cv2.CAP_PROP_FPS)
                tfn = int(fps if fps and fps > 0 else 0) 
                cap.set(cv2.CAP_PROP_POS_FRAMES, tfn)
                ret, frame = cap.read()
                if not ret and tfn > 0:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = cap.read()
                cap.release()
                if ret and frame is not None:
                    cv2.imwrite(str(thumb_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    return str(thumb_path)
                else:
                    logging.warning(f"CV2:FailReadFrameThumb:{video_path_str}")
            except Exception as e:
                logging.error(f"CCT:OpenCVThumbGenFail {video_path_str}:{e}")
        return None 

    def get_video_duration(self, video_path_str: str) -> Optional[str]: 
        if cv2:
            try:
                if not video_path_str or not Path(video_path_str).exists():
                    return "00:00"
                cap = cv2.VideoCapture(video_path_str)
                if not cap.isOpened():
                    return "00:00"
                fc = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                cap.release()
                if fc > 0 and fps > 0:
                    ds = fc/fps
                    m, s = divmod(int(ds), 60)
                    return f"{m:02d}:{s:02d}"
            except Exception as e:
                logging.error(f"CCT:ErrGetDuration {video_path_str}: {e}")
        return "00:00" 

    def update_thumbnail_highlight(self, item_path_str: str, is_highlighted: bool):
        """Updates the highlight state of a specific thumbnail."""
        if item_path_str in self.thumbnail_widgets:
            thumbnail = self.thumbnail_widgets[item_path_str]
            if hasattr(thumbnail, 'set_highlighted'):
                thumbnail.set_highlighted(is_highlighted)


class CapturedMediaTab(QWidget):
    image_selected_for_report = Signal(str) 
    image_deleted_from_system = Signal(str) 
    video_deleted_from_system = Signal(str) 
    video_play_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUI()

    def setupUI(self): 
        outer_layout = QVBoxLayout(self) 
        outer_layout.setContentsMargins(0,0,0,0)
        outer_layout.setSpacing(0)
        
        self.captured_media_tab = QWidget()
        outer_layout.addWidget(self.captured_media_tab)
        
        media_layout = QVBoxLayout(self.captured_media_tab)
        media_layout.setContentsMargins(5,5,5,5)
        media_layout.setSpacing(5)
        
        self.media_scroll_area = MediaScrollArea(self)
        self.media_scroll_area.setStyleSheet("""
            QScrollArea { 
                border: none; 
                background-color: #f5f5f5; 
            }
            QScrollBar:vertical {
                background: #f0f0f0;
                width: 14px;    
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #c0c0c0;
                min-height: 20px;
                border-radius: 7px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a0a0a0;
            }
            QScrollBar:horizontal {
                background: #f0f0f0;
                height: 14px;    
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: #c0c0c0;
                min-width: 20px;
                border-radius: 7px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #a0a0a0;
            }
            QScrollBar::add-line, QScrollBar::sub-line {
                height: 0px;
                width: 0px;
            }
            QScrollBar::add-page, QScrollBar::sub-page {
                background: none;
            }
        """)
        media_layout.addWidget(self.media_scroll_area)
        
        self.media_container = QWidget()
        self.media_container.setStyleSheet("background-color: #f5f5f5;")
        self.media_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        self.media_layout = QHBoxLayout(self.media_container)
        self.media_layout.setContentsMargins(5,5,5,5)
        self.media_layout.setSpacing(10)
        self.media_layout.setAlignment(Qt.AlignLeft)
        
        self.media_scroll_area.setWidget(self.media_container)
        self.media_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.media_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.items_paths = []
        self.thumbnail_widgets = {}

    def add_image(self, image_path):
        self.add_media_item(image_path, "image")
        
    def add_video(self, video_path):
        self.add_media_item(video_path, "video")
    
    def add_media_item(self, item_path_str, media_type):
        """Add a media item (image or video) to the horizontal layout"""
        item_path_str = str(item_path_str)
        if item_path_str in self.thumbnail_widgets: 
            logging.info(f"CM: Item {item_path_str} already exists.")
            return
        
        try:
            thumbnail_widget = None
            if media_type == "image":
                thumbnail_widget = ImageThumbnail(item_path_str, self)
                thumbnail_widget.selected.connect(lambda path=item_path_str: self.image_selected_for_report.emit(path))
                thumbnail_widget.deleted.connect(lambda path=item_path_str: self.handle_media_item_deleted(path))
            elif media_type == "video":
                thumbnail_image_path_str = self._generate_or_get_video_thumbnail_path(item_path_str)
                thumbnail_widget = VideoThumbnail(item_path_str, thumbnail_image_path_str, self)
                thumbnail_widget.deleted.connect(lambda path=item_path_str: self.handle_media_item_deleted(path))
                thumbnail_widget.play_clicked.connect(lambda path=item_path_str: self.video_play_requested.emit(path))
            
            if thumbnail_widget:
                self.media_layout.addWidget(thumbnail_widget)
                self.items_paths.append(item_path_str)
                self.thumbnail_widgets[item_path_str] = thumbnail_widget
                
                QTimer.singleShot(100, lambda: self.media_scroll_area.ensureWidgetVisible(thumbnail_widget))
                logging.info(f"CM: Successfully added {media_type} item: {item_path_str}")
        except Exception as e: 
            logging.error(f"CM: Failed to add {media_type} item {item_path_str}: {e}")

    def handle_media_item_deleted(self, item_path_str):
        """Handle deletion of a media item (image or video)"""
        try:
            media_type = "unknown"
            if Path(item_path_str).suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']:
                media_type = "image"
                self.image_deleted_from_system.emit(item_path_str)
            elif Path(item_path_str).suffix.lower() in ['.mp4', '.avi', '.mov', '.wmv']:
                media_type = "video"
                self.video_deleted_from_system.emit(item_path_str)
                self._cleanup_video_thumbnail(item_path_str)
                
            if item_path_str in self.items_paths:
                self.items_paths.remove(item_path_str)
            
            if item_path_str in self.thumbnail_widgets:
                thumbnail = self.thumbnail_widgets.pop(item_path_str)
                thumbnail.deleteLater()
            
            self.rebuild_grid()
            logging.info(f"CM: Successfully deleted {media_type} item: {item_path_str}")
        except Exception as e: 
            logging.error(f"CM: Failed to handle deletion for {item_path_str}: {e}")
    
    def update_thumbnail_highlight(self, item_path_str, is_highlighted):
        """Updates the highlight state of a specific thumbnail."""
        if item_path_str in self.thumbnail_widgets:
            thumbnail = self.thumbnail_widgets[item_path_str]
            if hasattr(thumbnail, 'set_highlighted'):
                thumbnail.set_highlighted(is_highlighted)
                logging.info(f"CM: Updated highlight state for {item_path_str} to {is_highlighted}")
        
    def _generate_or_get_video_thumbnail_path(self, video_path_str):
        """Generate or get thumbnail for a video"""
        video_file = Path(video_path_str)
        thumb_cache_dir = Path("data/cache/thumbnails")
        thumb_cache_dir.mkdir(parents=True, exist_ok=True)
        thumb_path = thumb_cache_dir / f"{video_file.stem}_thumb.jpg"
        
        if thumb_path.exists() and thumb_path.stat().st_size > 0:
            return str(thumb_path)
            
        if cv2:
            try:
                cap = cv2.VideoCapture(video_path_str)
                if not cap.isOpened():
                    logging.warning(f"CV2: Failed to open video for thumbnail: {video_path_str}")
                    return None
                    
                fps = cap.get(cv2.CAP_PROP_FPS)
                tfn = int(fps if fps and fps > 0 else 0)
                cap.set(cv2.CAP_PROP_POS_FRAMES, tfn)
                ret, frame = cap.read()
                
                if not ret and tfn > 0:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = cap.read()
                    
                cap.release()
                
                if ret and frame is not None:
                    cv2.imwrite(str(thumb_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    return str(thumb_path)
                else:
                    logging.warning(f"CV2: Failed to read frame for thumbnail: {video_path_str}")
            except Exception as e:
                logging.error(f"CM: OpenCV thumbnail generation failed for {video_path_str}: {e}")
                
        return None
    
    def _cleanup_video_thumbnail(self, video_path_str):
        """Clean up video thumbnail when video is deleted"""
        try:
            video_file = Path(video_path_str)
            thumb_cache_dir = Path("data/cache/thumbnails")
            cached_thumb_path = thumb_cache_dir / f"{video_file.stem}_thumb.jpg"
            cached_thumb_path.unlink(missing_ok=True)
        except Exception as e:
            logging.error(f"Failed to cleanup video thumbnail: {e}")
    
    def rebuild_grid(self):
        """Rebuild the horizontal layout after deletion"""
        while self.media_layout.count():
            item = self.media_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        
        self.thumbnail_widgets.clear()

        for item_path in self.items_paths:
            if Path(item_path).suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']:
                thumbnail = ImageThumbnail(item_path, self)
                thumbnail.selected.connect(lambda path=item_path: self.image_selected_for_report.emit(path))
                thumbnail.deleted.connect(lambda path=item_path: self.handle_media_item_deleted(path))
            else:
                thumbnail_image_path_str = self._generate_or_get_video_thumbnail_path(item_path)
                thumbnail = VideoThumbnail(item_path, thumbnail_image_path_str, self)
                thumbnail.deleted.connect(lambda path=item_path: self.handle_media_item_deleted(path))
                thumbnail.play_clicked.connect(lambda path=item_path: self.video_play_requested.emit(path))
            
            self.media_layout.addWidget(thumbnail)
            self.thumbnail_widgets[item_path] = thumbnail
                
        logging.info(f"CM: Rebuilt media grid with {len(self.items_paths)} items")

    def clear(self):
        """Clear UI list of captured media without deleting files."""
        self.items_paths.clear()
        while self.media_layout.count():
            item = self.media_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        self.thumbnail_widgets.clear()


class ReportImageSlot(QFrame): 
    image_deleted_at_index = Signal(int) 
    label_changed = Signal(int, str)
    request_move_left = Signal(int)
    request_move_right = Signal(int)

    def __init__(self, index, parent=None):
        super().__init__(parent)
        self.index = index
        self.image_path = None
        self._raw_pixmap = None
        self.setMinimumHeight(REPORT_SLOT_IMAGE_MIN_SIZE + 60)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred) 
        self.setup_ui()

    def setup_ui(self):
        self.setFrameStyle(QFrame.NoFrame)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(1,1,1,1)
        layout.setSpacing(2)      

        top_controls_layout = QVBoxLayout()
        top_controls_layout.setSpacing(1)
        button_bar_layout = QHBoxLayout()
        button_bar_layout.setContentsMargins(0,0,0,0)
        
        # ICON REPLACEMENT: Move buttons use icons
        self.btn_move_left = QPushButton()
        self.btn_move_left.setIcon(QIcon("icons/left.png"))  # Using left icon for left arrow
        self.btn_move_left.setFixedSize(32, 32)
        self.btn_move_left.setToolTip("Move image left")
        self.btn_move_left.setStyleSheet("""
            QPushButton { 
                border: none !important; 
                background-color: transparent !important; 
                padding: 0px; 
            } 
            QPushButton:hover { 
                background-color: rgba(76,175,80,0.1); 
                border-radius: 16px; 
            }
            QPushButton:disabled { 
                opacity: 0.3;
            }
        """)
        self.btn_move_left.clicked.connect(lambda: self.request_move_left.emit(self.index))
        
        # ICON REPLACEMENT: Delete button uses X icon
        self.btn_delete = QPushButton()
        self.btn_delete.setIcon(QIcon("icons/x.png"))
        self.btn_delete.setFixedSize(32, 32)
        self.btn_delete.setToolTip("Remove image from report")
        self.btn_delete.setStyleSheet("""
            QPushButton { 
                border: none !important; 
                background-color: transparent !important; 
                padding: 0px; 
            } 
            QPushButton:hover { 
                background-color: rgba(244,67,54,0.1); 
                border-radius: 16px; 
            }
            QPushButton:disabled { 
                opacity: 0.3;
            }
        """)
        self.btn_delete.clicked.connect(lambda: self.image_deleted_at_index.emit(self.index))
        
        self.btn_move_right = QPushButton()
        self.btn_move_right.setIcon(QIcon("icons/right.png"))  # Using right icon for right arrow
        self.btn_move_right.setFixedSize(32, 32)
        self.btn_move_right.setToolTip("Move image right")
        self.btn_move_right.setStyleSheet("""
            QPushButton { 
                border: none !important; 
                background-color: transparent !important; 
                padding: 0px; 
            } 
            QPushButton:hover { 
                background-color: rgba(76,175,80,0.1); 
                border-radius: 16px; 
            }
            QPushButton:disabled { 
                opacity: 0.3;
            }
        """)
        self.btn_move_right.clicked.connect(lambda: self.request_move_right.emit(self.index))
        
        button_bar_layout.addWidget(self.btn_move_left)
        button_bar_layout.addStretch()
        button_bar_layout.addWidget(self.btn_delete)
        button_bar_layout.addStretch()
        button_bar_layout.addWidget(self.btn_move_right)
        top_controls_layout.addLayout(button_bar_layout)

        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText(f"Image {self.index + 1} Label")
        self.label_edit.textChanged.connect(lambda text: self.label_changed.emit(self.index, text))
        self.label_edit.setStyleSheet("""
            QLineEdit { 
                padding: 3px; 
                font-size: 8pt; 
                border: 1px solid #d0d0d0; 
                border-radius: 3px; 
                background-color: white; 
                color: #333; 
            }
        """)
        self.label_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        top_controls_layout.addWidget(self.label_edit)
        layout.addLayout(top_controls_layout) 

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(REPORT_SLOT_IMAGE_MIN_SIZE, REPORT_SLOT_IMAGE_MIN_SIZE) 
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) 
        self.image_label.setStyleSheet("""
            QLabel { 
                background-color: #f5f5f5; 
                border: 1px solid #d0d0d0; 
                border-radius: 3px; 
            }
        """)
        self.image_label.setText("Empty")
        layout.addWidget(self.image_label, 1) 
        self.update_button_states(False, 0, 0)

    def set_image(self, image_path=None, label=None):
        self.image_path = image_path
        has_image = False
        if image_path and Path(image_path).exists():
            try:
                self._raw_pixmap = QPixmap(image_path)
                if self._raw_pixmap.isNull():
                    raise ValueError("Pixmap null")
                self._apply_pixmap_scaling()
                if label is not None:
                    self.label_edit.setText(label)
                has_image = True
            except Exception as e:
                logging.error(f"RISlot: Err load img {image_path}:{e}")
                self._raw_pixmap = None
                self.image_label.setText("LoadErr")
        else:
            self._raw_pixmap = None
            self.clear_display_only() 

    def _apply_pixmap_scaling(self):
        if not hasattr(self, 'image_label'):
            return 
        if not hasattr(self, '_raw_pixmap') or not self._raw_pixmap or self._raw_pixmap.isNull():
            self.image_label.clear()
            self.image_label.setText("Empty")
            return
        lbl_w = self.image_label.width()
        lbl_h = self.image_label.height()
        if lbl_w <= 1 or lbl_h <= 1:
            return 
        target_edge = min(lbl_w, lbl_h)
        if target_edge <= 10:
            target_edge = REPORT_SLOT_IMAGE_MIN_SIZE
        spx = self._raw_pixmap.scaled(QSize(target_edge,target_edge), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        cp = QPixmap(self.image_label.size())
        cp.fill(Qt.transparent)
        p = QPainter(cp)
        p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        x = (lbl_w - spx.width()) / 2
        y = (lbl_h - spx.height()) / 2
        p.drawPixmap(int(x), int(y), spx)
        p.end()
        self.image_label.setPixmap(cp)

    def clear_display_only(self): 
        self.image_path = None
        self._raw_pixmap = None
        if hasattr(self, 'image_label'):
            self.image_label.clear()
            self.image_label.setText("Empty")
        
    def clear_all(self): 
        self.clear_display_only()
        if hasattr(self, 'label_edit'):
            self.label_edit.clear()

    def update_button_states(self, has_image, current_idx=-1, total_images=-1):
        if hasattr(self, 'btn_delete'):
            self.btn_delete.setEnabled(has_image)
        if hasattr(self, 'btn_move_left'):
            self.btn_move_left.setEnabled(has_image and current_idx > 0)
        if hasattr(self, 'btn_move_right'):
            self.btn_move_right.setEnabled(has_image and current_idx < total_images - 1)

    def resizeEvent(self, event: QSize): 
        super().resizeEvent(event)
        if hasattr(self, 'image_label'): 
            if hasattr(self, '_raw_pixmap') and self._raw_pixmap and not self._raw_pixmap.isNull():
                self._apply_pixmap_scaling()
            elif not self.image_path:
                self.image_label.setText("Empty") 


class ReportImagesTab(QWidget): 
    images_changed = Signal(list)
    import_images_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.images = [] 
        self.max_images = 6
        self.slots = [] 
        self.setup_ui()
    
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5,2,5,5)
        main_layout.setSpacing(2) 

        top_bar_layout = QHBoxLayout()
        self.btn_import_images = QPushButton("Import Image(s)")
        self.btn_import_images.setStyleSheet("QPushButton{padding:5px 10px;font-size:9pt;background-color:#005A9C;color:white;border-radius:3px;} QPushButton:hover{background-color:#004C80}")
        self.btn_import_images.setToolTip("Import images from computer")
        self.btn_import_images.clicked.connect(self.import_images_requested)
        top_bar_layout.addWidget(self.btn_import_images)
        top_bar_layout.addStretch()
        main_layout.addLayout(top_bar_layout)

        self.slots_grid_layout = QGridLayout()
        self.slots_grid_layout.setSpacing(3)
        for i in range(self.max_images):
            slot = ReportImageSlot(i, self)
            slot.label_changed.connect(self.update_image_label)
            slot.image_deleted_at_index.connect(self.remove_image_at_index)
            slot.request_move_left.connect(self.handle_move_left)
            slot.request_move_right.connect(self.handle_move_right)
            row, col = divmod(i, 3)
            self.slots_grid_layout.addWidget(slot, row, col)
            self.slots.append(slot)
        for c_idx in range(3):
            self.slots_grid_layout.setColumnStretch(c_idx, 1)
        for r_idx in range(2):
            self.slots_grid_layout.setRowStretch(r_idx, 1) 
        main_layout.addLayout(self.slots_grid_layout, 1) 
        self.update_counter()
    
    def handle_move_left(self, index):
        if 0 < index < len(self.images):
            self.images[index], self.images[index-1] = self.images[index-1], self.images[index]
            self.update_display()
            self.images_changed.emit(self.get_images())
            
    def handle_move_right(self, index):
        if 0 <= index < len(self.images)-1:
            self.images[index], self.images[index+1] = self.images[index+1], self.images[index]
            self.update_display()
            self.images_changed.emit(self.get_images())

    def add_image(self, image_path_to_add: str): 
        try:
            if len(self.images) >= self.max_images: 
                logging.warning(f"Max {self.max_images} images reached.")
                return False
            if not Path(image_path_to_add).exists(): 
                logging.error(f"RI Add: Path N/E {image_path_to_add}")
                return False
            if any(img_p == image_path_to_add for img_p, _ in self.images): 
                logging.info(f"RI Add: Img exists {image_path_to_add}")
                return False
            self.images.append((str(image_path_to_add),""))
            self.update_display()
            self.images_changed.emit(self.get_images())
            return True
        except Exception as e: 
            logging.error(f"RI Tab: Fail add image: {e}")
            return False
    
    def remove_image_at_index(self, index_to_remove: int):
        try:
            if 0 <= index_to_remove < len(self.images):
                self.images.pop(index_to_remove)
                self.update_display()
                self.images_changed.emit(self.get_images())
        except Exception as e: 
            logging.error(f"RI Tab: Fail remove image at {index_to_remove}: {e}")

    def update_image_label(self, index: int, label: str):
        try:
            if 0 <= index < len(self.images):
                img_p, _ = self.images[index]
                self.images[index] = (img_p, label)
                self.images_changed.emit(self.get_images())
        except Exception as e: 
            logging.error(f"RI Tab: Fail update label for {index}: {e}")

    def update_display(self):
        try:
            num_current_images = len(self.images)
            for i, slot_widget in enumerate(self.slots):
                if i < num_current_images:
                    img_path_s, img_label_s = self.images[i]
                    slot_widget.set_image(img_path_s, img_label_s)
                    slot_widget.update_button_states(True, i, num_current_images)
                else: 
                    slot_widget.clear_all() 
                    slot_widget.update_button_states(False, i, num_current_images)
                slot_widget.setVisible(True) 
            self.update_counter()
        except Exception as e: 
            logging.error(f"RI Tab: Fail update display: {e}")
    
    def update_counter(self):
        """Update the tab text to show current image count"""
        try:
            current_count = len(self.images)
            parent_widget = self.parentWidget()
            if parent_widget and isinstance(parent_widget, RightPanel):
                if hasattr(parent_widget, 'tabs_widget_actual'):
                    tab_widget = parent_widget.tabs_widget_actual
                    for i in range(tab_widget.count()):
                        if tab_widget.widget(i) is self:
                            new_text = f"Report Images {current_count}/{self.max_images}"
                            tab_widget.setTabText(i, new_text)
                            logging.info(f"Updated tab text to: {new_text}")
                            break
        except Exception as e:
            logging.error(f"Failed to update report images counter: {e}")

    def get_images(self): 
        return [(str(p), str(l)) for p, l in self.images if p] 
        
    def set_images(self, images_list_tuples): 
        try: 
            self.images = []
            for p, l in images_list_tuples[:self.max_images]:
                if p and Path(p).exists(): 
                    self.images.append((str(p),str(l)))
                elif p: 
                    logging.warning(f"RITab set_images: Path {p} N/E, skipping.")
            self.update_display()
            self.images_changed.emit(self.get_images())
        except Exception as e: 
            logging.error(f"RI Tab: Fail set images: {e}")
            
    def clear(self): 
        self.images.clear()
        self.update_display()
        self.images_changed.emit(self.get_images())


class RightPanel(QWidget):
    image_captured = Signal()
    recording_state_changed = Signal(bool)
    import_images_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # FIXED: Initialize recording state properly
        self.is_recording = False
        
        # ICON REPLACEMENT: Camera button uses camera icon
        self.capture_btn = QPushButton()
        self.capture_btn.setIcon(QIcon("icons/camera.png"))
        desired_capture_icon_width = 42  
        desired_capture_icon_height = 42 
        self.capture_btn.setIconSize(QSize(desired_capture_icon_width, desired_capture_icon_height))
        self.capture_btn.setFixedSize(QSize(58, 58))
        self.capture_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 3px;
            } 
            QPushButton:hover {
                background-color: rgba(40,167,69,0.1);
                border-radius: 5px;
            }
        """)
        self.capture_btn.setToolTip("Capture Image")
        self.capture_btn.setFocusPolicy(Qt.NoFocus)
        
        # ICON REPLACEMENT: Record button uses record icon
        self.record_btn = QToolButton()
        self.record_btn.setIcon(QIcon("icons/record.png"))
        desired_record_icon_width = 42  
        desired_record_icon_height = 42 
        self.record_btn.setIconSize(QSize(desired_record_icon_width, desired_record_icon_height))
        self.record_btn.setAutoRaise(True)
        self.record_btn.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.record_btn.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                border: none;
                padding: 3px;
            }
            QToolButton:hover {
                background-color: rgba(220,53,69,0.1);
                border-radius: 5px;
            }
        """)
        self.record_btn.setFixedSize(QSize(58, 58))
        self.record_btn.setToolTip("Start Recording")
        self.record_btn.setFocusPolicy(Qt.NoFocus)
        
        self.setup_ui()
        self.setup_connections() 

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5,5,5,5)
        self.main_layout.setSpacing(3)
        
        # Container for VideoFeed and its controls
        self.video_feed_area_container = QWidget()
        video_feed_area_layout = QVBoxLayout(self.video_feed_area_container)
        video_feed_area_layout.setContentsMargins(0,0,0,0)
        video_feed_area_layout.setSpacing(3)
        self.video_feed = VideoFeed(self)
        video_feed_area_layout.addWidget(self.video_feed, 1)

        video_controls_layout = QHBoxLayout()
        video_controls_layout.setContentsMargins(0,2,0,0)
        video_controls_layout.addStretch()
        video_controls_layout.addWidget(self.capture_btn)

        # !!! ADD SPACING HERE !!!
        desired_spacing = 25  # For example, 15 pixels of space
        video_controls_layout.addSpacing(desired_spacing)

        video_controls_layout.addWidget(self.record_btn)
        video_controls_layout.addStretch()
        video_feed_area_layout.addLayout(video_controls_layout)
        
        self.video_feed_area_container.setMinimumHeight(400)
        self.video_feed_area_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.main_layout.addWidget(self.video_feed_area_container, 70)
        
        # FIXED: Connect record button ONLY ONCE
        self.record_btn.clicked.connect(self.toggle_recording_state)

        self.tabs_widget_actual = QTabWidget() 
        self.tabs_widget_actual.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tabs_widget_actual.setMinimumHeight(200)
        self.tabs_widget_actual.setStyleSheet("""
            QTabWidget::pane { 
                border: none; 
                background-color: #f5f5f5; 
            }
            QTabBar::tab { 
                background-color: #e8e8e8; 
                color: #444;
                padding: 7px 18px;
                min-width: 120px;
                border: none; 
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-weight: normal;
            }
            QTabBar::tab:selected { 
                background-color: #f5f5f5; 
                color: #0095FF; 
                font-weight: bold; 
            }
            QTabBar::tab:!selected:hover { 
                background-color: #f0f0f0;
                color: #333;
                border: none; 
            }
        """)
        
        self.captured_media_tab = CapturedMediaTab(self)
        self.report_images_tab = ReportImagesTab(self)   
        self.tabs_widget_actual.addTab(self.captured_media_tab, "Captured Media")
        self.tabs_widget_actual.addTab(self.report_images_tab, "Report Images")
        self.update_report_tab_text()
        
        self.main_layout.addWidget(self.tabs_widget_actual, 30) 
        self.tabs_widget_actual.currentChanged.connect(self.handle_main_tab_changed)
        
    def handle_main_tab_changed(self, index):
        is_report_tab_selected = (self.tabs_widget_actual.widget(index) == self.report_images_tab)
        self.video_feed_area_container.setVisible(not is_report_tab_selected)
        if is_report_tab_selected:
            self.main_layout.setStretchFactor(self.video_feed_area_container, 0)
            self.main_layout.setStretchFactor(self.tabs_widget_actual, 100)
        else:
            self.main_layout.setStretchFactor(self.video_feed_area_container, 70)
            self.main_layout.setStretchFactor(self.tabs_widget_actual, 30)
        self.main_layout.activate()

    def update_report_tab_text(self, images_list=None):
        if hasattr(self, 'report_images_tab') and hasattr(self, 'tabs_widget_actual'):
            num_images = len(self.report_images_tab.get_images())
            max_images = self.report_images_tab.max_images
            for i in range(self.tabs_widget_actual.count()):
                if self.tabs_widget_actual.widget(i) == self.report_images_tab:
                    self.tabs_widget_actual.setTabText(i, f"Report Images {num_images}/{max_images}")
                    break
        
    def setup_connections(self):
        """Connect signals between UI components with error handling"""
        try:
            # Connect captured media tab signals
            if hasattr(self, 'captured_media_tab'):
                if hasattr(self.captured_media_tab, 'image_selected_for_report') and hasattr(self, 'handle_captured_image_selected_for_report'):
                    self.captured_media_tab.image_selected_for_report.connect(self.handle_captured_image_selected_for_report)
                if hasattr(self.captured_media_tab, 'image_deleted_from_system') and hasattr(self, 'update_report_images_on_capture_delete'):
                    self.captured_media_tab.image_deleted_from_system.connect(self.update_report_images_on_capture_delete)
                if hasattr(self.captured_media_tab, 'video_deleted_from_system'):
                    self.captured_media_tab.video_deleted_from_system.connect(lambda x: logging.info(f"Video deleted: {x}"))
            
            # Connect report images tab signals
            if hasattr(self, 'report_images_tab'):
                if hasattr(self.report_images_tab, 'images_changed'):
                    self.report_images_tab.images_changed.connect(self.update_captured_media_highlights)
                    self.report_images_tab.images_changed.connect(self.update_report_tab_text)
                if hasattr(self.report_images_tab, 'import_images_requested') and hasattr(self, 'import_images_requested'):
                    self.report_images_tab.import_images_requested.connect(self.import_images_requested.emit)
                
            # Set up the capture button
            if hasattr(self, 'capture_btn'):
                if hasattr(self, 'image_captured'):
                    self.capture_btn.clicked.connect(lambda: self.image_captured.emit())
                    logging.info("Capture button connected successfully")
                else:
                    logging.error("Missing image_captured signal in RightPanel")
                
            logging.info("RightPanel: Connections set up successfully")
        except Exception as e:
            logging.error(f"RightPanel: Error setting up connections: {str(e)}")
        
        self.update_captured_media_highlights()

    def handle_captured_image_selected_for_report(self, image_path):
        """Handler for when an image is selected from captured media to add to report"""
        if not hasattr(self, 'report_images_tab') or not image_path:
            logging.error(f"Cannot add image to report: missing components or invalid path: {image_path}")
            return
            
        success = self.report_images_tab.add_image(image_path)
        
        if success:
            logging.info(f"Added image to report: {image_path}")
            self.update_captured_media_highlights()
            if hasattr(self, 'tabs_widget_actual'):
                report_tab_index = self.tabs_widget_actual.indexOf(self.report_images_tab)
                if report_tab_index >= 0:
                    self.tabs_widget_actual.setCurrentIndex(report_tab_index)
        else:
            logging.warning(f"Failed to add image to report: {image_path}")
            
    def update_report_images_on_capture_delete(self, deleted_image_path):
        """If an image deleted from captured media is in report images, remove it from there too."""
        if hasattr(self.report_images_tab, 'images'):
            current_report_images = self.report_images_tab.get_images()
            new_report_images = [(p, l) for p, l in current_report_images if p != deleted_image_path]
            if len(new_report_images) < len(current_report_images):
                self.report_images_tab.set_images(new_report_images)
        self.update_captured_media_highlights()

    def update_captured_media_highlights(self):
        """Update highlights on thumbnails based on which images are in the report"""
        if hasattr(self, 'report_images_tab') and hasattr(self.report_images_tab, 'get_images'):
            report_image_paths = [path for path, label in self.report_images_tab.get_images()]
            
            if hasattr(self, 'captured_media_tab') and hasattr(self.captured_media_tab, 'thumbnail_widgets'):
                for path, thumb in self.captured_media_tab.thumbnail_widgets.items():
                    if hasattr(thumb, 'set_highlighted'):
                        is_in_report = path in report_image_paths
                        thumb.set_highlighted(is_in_report)

    def get_report_images(self): 
        if hasattr(self, 'report_images_tab'):
            return self.report_images_tab.get_images()
        return []

    def set_report_images(self, images_list_tuples): 
        if hasattr(self, 'report_images_tab'):
            self.report_images_tab.set_images(images_list_tuples)
        
    def toggle_recording_state(self):
        """ICON REPLACEMENT: Toggle between recording and stopped states"""
        try:
            if not self.is_recording:
                # Change to stop recording state
                self.is_recording = True
                self.record_btn.setIcon(QIcon("icons/stop_record.png"))
                self.record_btn.setStyleSheet("""
                    QToolButton {
                        background-color: transparent;
                        border: none;
                        padding: 5px;
                    }
                    QToolButton:hover {
                        background-color: rgba(255,193,7,0.1);
                        border-radius: 5px;
                    }
                """)
                self.record_btn.setToolTip("Stop Recording")
                # Start the actual recording indicator
                if hasattr(self, 'video_feed') and hasattr(self.video_feed, 'start_recording_indicator'):
                    self.video_feed.start_recording_indicator()
                self.recording_state_changed.emit(True)
                logging.info("Started recording video")
            else:
                # Change to start recording state
                self.is_recording = False
                self.record_btn.setIcon(QIcon("icons/record.png"))
                self.record_btn.setStyleSheet("""
                    QToolButton {
                        background-color: transparent;
                        border: none;
                        padding: 5px;
                    }
                    QToolButton:hover {
                        background-color: rgba(220,53,69,0.1);
                        border-radius: 5px;
                    }
                """)
                self.record_btn.setToolTip("Start Recording")
                # Stop the actual recording indicator
                if hasattr(self, 'video_feed') and hasattr(self.video_feed, 'stop_recording_indicator'):
                    self.video_feed.stop_recording_indicator()
                self.recording_state_changed.emit(False)
                logging.info("Stopped recording video")
        except Exception as e:
            logging.error(f"Error in toggle_recording_state: {e}")
            
    def cleanup(self):
        if hasattr(self, 'video_feed'):
            self.video_feed.cleanup()
        logging.info("RP cleanup done.")
