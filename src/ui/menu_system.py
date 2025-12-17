# FILE: src/ui/menu_system.py
# (Based on the version you uploaded, with shortcuts changed for capture and record)

from PySide6.QtWidgets import QMenuBar, QMenu, QMessageBox # Keep QMessageBox if handle_about uses it
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtCore import Signal
from typing import List, Tuple # Keep QObject if it was there, not strictly needed for this class structure

class MenuSystem(QMenuBar):
    """Complete menu system for Endoscopy Reporting application"""
    
    # SIGNALS (as per your original file)
    new_patient_triggered = Signal()
    open_patient_triggered = Signal()
    save_patient_triggered = Signal()
    settings_triggered = Signal()
    exit_triggered = Signal()
    
    camera_selected = Signal(int)  # Camera index
    record_toggled = Signal(bool)  # Recording state (True to start, False to stop)
    capture_triggered = Signal()
    
    theme_changed = Signal(str)  # Theme name
    
    about_triggered = Signal()
    help_triggered = Signal()
    
    def __init__(self, parent=None):
        """Initialize the menu system"""
        super().__init__(parent)
        
        # Add padding to move menu bar down
        self.setStyleSheet("""
            QMenuBar {
                padding-top: 8px;
                background-color: #f0f0f0;
            }
            QMenuBar::item {
                background: transparent;
                padding: 4px 8px;
            }
            QMenuBar::item:selected {
                background: #e0e0e0;
            }
        """)
        
        self.setup_file_menu()
        self.setup_camera_menu()
        self.setup_view_menu()
        self.setup_help_menu()
    
    def setup_file_menu(self):
        """Setup File menu with New, Open, Save, Settings, and Exit options"""
        file_menu = self.addMenu("&File")
        
        new_action = QAction("&New Patient", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self.new_patient_triggered.emit)
        file_menu.addAction(new_action)
        
        open_action = QAction("&Open Patient", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.open_patient_triggered.emit)
        file_menu.addAction(open_action)
        
        save_action = QAction("&Save", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_patient_triggered.emit)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        settings_action = QAction("Se&ttings", self)
        # settings_action.setShortcut("Ctrl+,") # Example if you want a shortcut
        settings_action.triggered.connect(self.settings_triggered.emit)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        # Add Minimize option
        minimize_action = QAction("&Minimize", self)
        minimize_action.setShortcut(QKeySequence("Ctrl+M"))
        minimize_action.triggered.connect(self.parent().showMinimized if self.parent() else lambda: None)
        file_menu.addAction(minimize_action)
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.Quit) # e.g., Ctrl+Q
        exit_action.triggered.connect(self.exit_triggered.emit) # Connected in MainWindow
        file_menu.addAction(exit_action)
    
    def setup_camera_menu(self):
        """Setup Camera menu with device selection and capture options"""
        camera_menu = self.addMenu("&Camera")
        
        # Keep a reference + objectName so we can update later
        self.device_menu = QMenu("Select &Device", self)
        self.device_menu.setObjectName("device_menu")
        camera_menu.addMenu(self.device_menu)
        
        self.camera_group = QActionGroup(self)
        self.camera_group.setExclusive(True) # Ensure only one camera can be selected
        
        # Camera devices will be added dynamically by MainWindow using update_camera_list
        # Example: self.add_camera_device(0, "Default Camera") (can be pre-populated or not)

        camera_menu.addSeparator()
        
        # Image capture action
        capture_action = QAction("&Capture Image", self)
        # <<< SHORTCUT CHANGED HERE >>>
        capture_action.setShortcut(QKeySequence("Ctrl+F2")) 
        capture_action.triggered.connect(self.capture_triggered.emit)
        camera_menu.addAction(capture_action)
        
        # Record video action
        # This action will toggle text and emit a boolean state
        self.record_action = QAction("Start &Recording", self)
        self.record_action.setCheckable(True) # Make it checkable to reflect state
        # <<< SHORTCUT CHANGED HERE >>>
        self.record_action.setShortcut(QKeySequence("Ctrl+F3")) 
        self.record_action.triggered.connect(self.toggle_recording_action_state) # Connect to internal state toggle
        camera_menu.addAction(self.record_action)
    
    def add_camera_device(self, device_id, name):
        """Add a camera device to the menu"""
        device_action = QAction(name, self)
        device_action.setCheckable(True)
        device_action.setData(device_id) # Store device_id in the action
        # When triggered, emit the camera_selected signal with the device_id
        device_action.triggered.connect(lambda checked, id=device_id: self.camera_selected.emit(id) if checked else None)
        
        self.camera_group.addAction(device_action)
        
        if hasattr(self, "device_menu") and self.device_menu:
            self.device_menu.addAction(device_action)
        
        # Optional: set first added camera as active by default
        # if not any(act.isChecked() for act in self.camera_group.actions()):
        #    device_action.setChecked(True)

    def toggle_recording_action_state(self):
        """Internal slot to manage the Record Action's text and emit record_toggled signal."""
        if self.record_action.isChecked():
            self.record_action.setText("Stop &Recording")
            self.record_toggled.emit(True) # Request to start recording
        else:
            self.record_action.setText("Start &Recording")
            self.record_toggled.emit(False) # Request to stop recording

    def update_record_action_state(self, is_recording: bool):
        """Called by MainWindow to update the record action's appearance based on actual recording state."""
        if is_recording:
            self.record_action.setChecked(True)
            self.record_action.setText("Stop &Recording")
        else:
            self.record_action.setChecked(False)
            self.record_action.setText("Start &Recording")

    def setup_view_menu(self):
        """Setup View menu with theme options"""
        view_menu = self.addMenu("&View")
        
        theme_menu = QMenu("&Theme", self)
        view_menu.addMenu(theme_menu)
        
        self.theme_action_group = QActionGroup(self) # Store group to access actions
        self.theme_action_group.setExclusive(True)
        
        themes = { # Matches ThemeManager's display names or keys
            "light": "Light",
            "dark": "Dark",
            "professional": "Professional Dark" 
        }
        
        for theme_key, display_name in themes.items():
            action = QAction(display_name, self)
            action.setCheckable(True)
            action.setData(theme_key) # Store theme key
            action.triggered.connect(lambda checked, key=theme_key: self.theme_changed.emit(key) if checked else None)
            self.theme_action_group.addAction(action)
            theme_menu.addAction(action)
            
            # You might want to set a default checked theme here based on settings,
            # or have MainWindow call update_theme_checkmark after ThemeManager loads initial theme.

    def change_theme(self, theme_name): # This method was in your original, ensure it's called or used
        """Handle theme change - likely deprecated if actions directly emit theme_changed(key)"""
        self.theme_changed.emit(theme_name) # Emits the theme name (string)
    
    def update_theme_checkmark(self, current_theme_name: str):
        """Update checkmark for the current theme"""
        for action in self.theme_action_group.actions():
            if action.data() == current_theme_name:
                action.setChecked(True)
                break # Found and set, no need to continue
            else:
                action.setChecked(False) # Ensure others are unchecked if somehow not exclusive
    
    def setup_help_menu(self):
        """Setup Help menu with about and help options"""
        help_menu = self.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.about_triggered.emit) # Connected in MainWindow to self.menu_system.handle_about
        help_menu.addAction(about_action)
        
        help_action = QAction("&Help Contents", self) # More descriptive
        help_action.setShortcut(QKeySequence.HelpContents)
        help_action.triggered.connect(self.help_triggered.emit) # Connected in MainWindow
        help_menu.addAction(help_action)
    
    def handle_about(self):
        """Show about dialog (can be called from MainWindow)"""
        QMessageBox.about(
            self.parentWidget() if self.parentWidget() else self, # Get parent if available for modality
            "About Endoscopy Reporting System",
            "Endoscopy Reporting System v1.0\n\n"
            "A tool for endoscopy image capture and report generation.\n\n"
            "© Medical Software Systems" # Generic placeholder
        )
    
    def update_camera_list(self, camera_list: List[Tuple[int, str]]):
        """Update the list of available cameras
        
        Args:
            camera_list: List of (id, name) tuples for available cameras
        """
        device_menu = getattr(self, "device_menu", None)
        if not device_menu:
            return

        # Clear existing camera actions from the group and menu
        for action in self.camera_group.actions():
            self.camera_group.removeAction(action)
            device_menu.removeAction(action)
            action.deleteLater() # Ensure old actions are properly deleted
            
        if not camera_list:
            no_cam_action = QAction("No cameras found", self)
            no_cam_action.setEnabled(False)
            device_menu.addAction(no_cam_action)
        else:
            for camera_id, camera_name in camera_list:
                self.add_camera_device(camera_id, camera_name)
            # Optionally, check the first camera by default if none is checked
            if self.camera_group.actions() and not self.camera_group.checkedAction():
                 self.camera_group.actions()[0].setChecked(True)
                 # self.camera_selected.emit(self.camera_group.actions()[0].data()) # Emit selection for default

    # set_camera_active was in your original file, ensure it's used if needed by MainWindow
    def set_camera_active(self, device_id: int):
        """Set the active camera in the menu by checking the corresponding action."""
        for action in self.camera_group.actions():
            if action.data() == device_id:
                action.setChecked(True) # This will trigger its connected slot if not already checked
                break
