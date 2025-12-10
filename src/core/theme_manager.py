# FIXED THEME_MANAGER.PY - CONSOLIDATED THEMES AND FIXED TEXT VISIBILITY
# FILE: src/core/theme_manager.py

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import QObject, Signal

class ThemeManager(QObject):
    """Manager for application themes and styling with improved dark mode support"""
    
    # SIGNALS
    theme_applied = Signal(str)  # Emits theme name when applied
    
    def __init__(self, settings_manager=None, parent=None):
        """Initialize the theme manager
        
        Args:
            settings_manager: SettingsManager instance for accessing saved theme
            parent: Parent QObject
        """
        super().__init__(parent)
        self.settings = settings_manager
        self.current_theme = "dark"  # Default theme
        
        # Initialize theme definitions - CONSOLIDATED AND FIXED
        self.themes = {
            "light": self.get_light_theme(),
            "dark": self.get_dark_theme(),
            "professional": self.get_professional_theme(),  # RENAMED FROM PRO_DARK
        }
        
        # Load saved theme if available
        if self.settings:
            saved_theme = self.settings.get_theme()
            # Handle legacy theme names
            if saved_theme == "pro_dark":
                saved_theme = "professional"
            if saved_theme in self.themes:
                self.current_theme = saved_theme
    
    def get_light_theme(self):
        """Get light theme stylesheet and palette
        
        Returns:
            Dictionary with theme components
        """
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(240, 240, 240))
        palette.setColor(QPalette.WindowText, QColor(0, 0, 0))
        palette.setColor(QPalette.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))
        palette.setColor(QPalette.Text, QColor(0, 0, 0))
        palette.setColor(QPalette.Button, QColor(240, 240, 240))
        palette.setColor(QPalette.ButtonText, QColor(0, 0, 0))
        palette.setColor(QPalette.Link, QColor(0, 0, 255))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        
        # Light theme stylesheet
        stylesheet = """
            QMainWindow {
                background-color: #f0f0f0;
                color: #000000;
            }
            QWidget {
                background-color: #f0f0f0;
                color: #000000;
            }
            QLabel {
                color: #000000;
            }
            QLineEdit, QComboBox {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #cccccc;
                padding: 5px;
                border-radius: 3px;
            }
            QTextEdit {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #cccccc;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0069d9;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                color: #000000;
                padding: 8px 15px;
            }
            QTabBar::tab:selected {
                background-color: #f0f0f0;
                border-bottom: 2px solid #007bff;
            }
            QMenuBar {
                background-color: #f0f0f0;
                color: #000000;
            }
            QMenuBar::item {
                background-color: #f0f0f0;
                color: #000000;
            }
            QMenuBar::item:selected {
                background-color: #e0e0e0;
            }
            QMenu {
                background-color: #f8f8f8;
                color: #000000;
                border: 1px solid #cccccc;
            }
            QMenu::item:selected {
                background-color: #e0e0e0;
            }
            QGroupBox, QFrame {
                border: 1px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
                background-color: #f8f9fa;
                color: #2c3e50;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
        """
        
        return {
            "name": "light",
            "palette": palette,
            "stylesheet": stylesheet,
            "display_name": "Light Theme"
        }
    
    def get_dark_theme(self):
        """Get dark theme stylesheet and palette - FIXED TEXT VISIBILITY
        
        Returns:
            Dictionary with theme components
        """
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(43, 43, 43))
        palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.Base, QColor(30, 30, 30))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        
        # Dark theme stylesheet - FIXED TEXT VISIBILITY
        stylesheet = """
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QLineEdit, QComboBox {
                background-color: #3b3b3b;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 5px;
                border-radius: 3px;
            }
            QTextEdit {
                background-color: #3b3b3b;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 5px;
                border-radius: 3px;
                selection-background-color: #0078d4;
                selection-color: #ffffff;
            }
            QPushButton {
                background-color: #0d47a1;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #2b2b2b;
            }
            QTabBar::tab {
                background-color: #2b2b2b;
                color: #ffffff;
                padding: 8px 15px;
                border: 1px solid #555555;
            }
            QTabBar::tab:selected {
                background-color: #3b3b3b;
                border-bottom: 2px solid #1565c0;
            }
            QMenuBar {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QMenuBar::item {
                background-color: #2b2b2b;
                color: #ffffff;
                padding: 4px 8px;
            }
            QMenuBar::item:selected {
                background-color: #3b3b3b;
            }
            QMenu {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QMenu::item:selected {
                background-color: #3b3b3b;
            }
            QGroupBox, QFrame {
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
                color: #ffffff;
            }
            QScrollBar:vertical {
                border: none;
                background: #2b2b2b;
                width: 12px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background: #666666;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                border: none;
                background: #2b2b2b;
                height: 12px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: #555555;
                min-width: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #666666;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """
        
        return {
            "name": "dark",
            "palette": palette,
            "stylesheet": stylesheet,
            "display_name": "Dark Theme"
        }
    
    def get_professional_theme(self):
        """Get professional theme with enhanced contrast - RENAMED AND IMPROVED
        
        Returns:
            Dictionary with theme components
        """
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(24, 24, 27))
        palette.setColor(QPalette.WindowText, QColor(231, 233, 237))
        palette.setColor(QPalette.Base, QColor(32, 33, 36))
        palette.setColor(QPalette.AlternateBase, QColor(45, 45, 50))
        palette.setColor(QPalette.Text, QColor(231, 233, 237))
        palette.setColor(QPalette.Button, QColor(45, 45, 50))
        palette.setColor(QPalette.ButtonText, QColor(231, 233, 237))
        palette.setColor(QPalette.Link, QColor(66, 133, 244))
        palette.setColor(QPalette.Highlight, QColor(66, 133, 244))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        
        # Professional theme stylesheet - ENHANCED CONTRAST
        stylesheet = """
            QMainWindow {
                background-color: #18181b;
                color: #e7e9ed;
            }
            QWidget {
                background-color: #18181b;
                color: #e7e9ed;
            }
            QLabel {
                color: #e7e9ed;
            }
            QLineEdit, QComboBox {
                background-color: #202124;
                color: #e7e9ed;
                border: 1px solid #3c4043;
                padding: 6px;
                border-radius: 4px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 2px solid #4285f4;
            }
            QTextEdit {
                background-color: #202124;
                color: #e7e9ed;
                border: 1px solid #3c4043;
                padding: 8px;
                border-radius: 4px;
                selection-background-color: #4285f4;
                selection-color: #ffffff;
                font-size: 11px;
                line-height: 1.4;
            }
            QTextEdit:focus {
                border: 2px solid #4285f4;
            }
            QPushButton {
                background-color: #4285f4;
                color: white;
                border: none;
                padding: 10px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #5a95f5;
                box-shadow: 0px 2px 4px rgba(0, 0, 0, 0.2);
            }
            QPushButton:pressed {
                background-color: #3367d6;
            }
            QTabWidget::pane {
                border: 1px solid #3c4043;
                background-color: #18181b;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #202124;
                color: #e7e9ed;
                padding: 10px 16px;
                border: 1px solid #3c4043;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #18181b;
                border-bottom: 2px solid #4285f4;
                color: #ffffff;
            }
            QTabBar::tab:hover:!selected {
                background-color: #2d2d32;
            }
            QMenuBar {
                background-color: #18181b;
                color: #e7e9ed;
                padding: 4px;
            }
            QMenuBar::item {
                background-color: #18181b;
                color: #e7e9ed;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background-color: #2d2d32;
            }
            QMenu {
                background-color: #202124;
                color: #e7e9ed;
                border: 1px solid #3c4043;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #2d2d32;
            }
            QGroupBox, QFrame {
                border: 1px solid #3c4043;
                border-radius: 6px;
                margin-top: 12px;
                font-weight: bold;
                background-color: #1a1a1d;
                color: #e7e9ed;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #e7e9ed;
                font-size: 12px;
                font-weight: 600;
            }
            QScrollBar:vertical {
                border: none;
                background: #202124;
                width: 14px;
                margin: 0px;
                border-radius: 7px;
            }
            QScrollBar::handle:vertical {
                background: #3c4043;
                min-height: 25px;
                border-radius: 7px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: #4a4a4f;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                border: none;
                background: #202124;
                height: 14px;
                margin: 0px;
                border-radius: 7px;
            }
            QScrollBar::handle:horizontal {
                background: #3c4043;
                min-width: 25px;
                border-radius: 7px;
                margin: 2px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #4a4a4f;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """
        
        return {
            "name": "professional",
            "palette": palette,
            "stylesheet": stylesheet,
            "display_name": "Professional Dark"
        }
    
    def apply_theme(self, theme_name=None):
        """Apply a theme to the application
        
        Args:
            theme_name: Name of the theme to apply (optional)
            
        Returns:
            True if successful, False otherwise
        """
        # Use provided theme name or current theme
        theme_name = theme_name or self.current_theme
        
        # Handle legacy theme names
        if theme_name == "pro_dark":
            theme_name = "professional"
        
        # Find theme
        theme = self.themes.get(theme_name)
        if not theme:
            # Default to dark theme if not found
            theme = self.themes.get("dark")
            theme_name = "dark"
        
        try:
            # Get application instance
            app = QApplication.instance()
            if not app:
                return False
            
            # Apply palette
            app.setPalette(theme["palette"])
            
            # Apply stylesheet
            app.setStyleSheet(theme["stylesheet"])
            
            # Update current theme
            self.current_theme = theme_name
            
            # Save theme in settings if available
            if self.settings:
                self.settings.set_theme(theme_name)
            
            # Emit signal
            self.theme_applied.emit(theme_name)
            
            return True
            
        except Exception as e:
            print(f"Error applying theme: {e}")
            return False
    
    def get_theme_names(self):
        """Get list of available theme names
        
        Returns:
            List of theme names
        """
        return list(self.themes.keys())
    
    def get_theme_display_names(self):
        """Get list of theme display names with theme name keys
        
        Returns:
            Dictionary of {name: display_name} pairs
        """
        return {name: theme.get("display_name", name.title()) 
                for name, theme in self.themes.items()}
    
    def get_current_theme(self):
        """Get current theme name
        
        Returns:
            Current theme name
        """
        return self.current_theme