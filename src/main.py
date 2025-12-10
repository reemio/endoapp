# FILE: src/main.py - FIXED REPORT GENERATION CRITICAL ISSUES
# FIXES: 1) Missing import at top, 2) Error handling, 3) Data validation, 4) Dependencies check

#!/usr/bin/env python3
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QMessageBox,
    QFileDialog, QDialog
)
from PySide6.QtCore import (
    Qt,
    QUrl,
    QObject,
    Signal as PySideSignal,
    QTimer,
    Slot,
    QSignalBlocker,
)
from PySide6.QtGui import QIcon, QDesktopServices 
import sys
from pathlib import Path
import traceback
from datetime import datetime
import os
import platform
import logging 
import subprocess 
import time
import threading

# CRITICAL FIX: ADD MISSING IMPORTS FOR REPORT GENERATION
try:
    from src.ui.report_preview_dialog import ReportPreviewDialog
    REPORT_PREVIEW_AVAILABLE = True
    print("✅ ReportPreviewDialog imported successfully")
except ImportError as e:
    REPORT_PREVIEW_AVAILABLE = False
    print(f"❌ ReportPreviewDialog import failed: {e}")

# CHECK PDF GENERATION DEPENDENCIES
try:
    from fpdf import FPDF
    from PIL import Image
    PDF_DEPENDENCIES_AVAILABLE = True
    print("✅ PDF generation dependencies available")
except ImportError as e:
    PDF_DEPENDENCIES_AVAILABLE = False
    print(f"❌ PDF generation dependencies missing: {e}")

PROJECT_ROOT = Path(__file__).resolve().parent.parent 
SRC_DIR_FOR_MAIN = PROJECT_ROOT / "src" 
if str(SRC_DIR_FOR_MAIN) not in sys.path:
    sys.path.insert(0, str(SRC_DIR_FOR_MAIN))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.camera_manager import CameraManager 
from src.core.database_manager import DatabaseManager
from src.core.error_handler import ErrorHandler
from src.core.settings_manager import SettingsManager 
from src.core.file_manager import FileManager
from src.core.search_manager import SearchManager
from src.core.report_generator import ReportGenerator
from src.core.theme_manager import ThemeManager

from src.ui.left_panel import LeftPanel
from src.ui.right_panel import RightPanel
from src.ui.menu_system import MenuSystem
from src.ui.refinement_dialog import RefinementDialog
from src.ui.ai_settings_dialog import AISettingsDialog
from src.services.ai_refinement_service import AIRefinementService

DATA_DIR_FOR_MAIN = PROJECT_ROOT / "data"
required_dirs_list_main = [ 
    DATA_DIR_FOR_MAIN / "hospitals", DATA_DIR_FOR_MAIN / "images" / "captured",
    DATA_DIR_FOR_MAIN / "videos" / "captured", DATA_DIR_FOR_MAIN / "logs",
    DATA_DIR_FOR_MAIN / "database", DATA_DIR_FOR_MAIN / "settings",
    DATA_DIR_FOR_MAIN / "temp", DATA_DIR_FOR_MAIN / "backups",
    DATA_DIR_FOR_MAIN / "settings" / "backup", 
]
for directory_item_main in required_dirs_list_main:
    try:
        directory_item_main.mkdir(parents=True, exist_ok=True)
    except Exception as e_dir_create:
        print(f"Warning: Dir creation {directory_item_main}: {e_dir_create}")


class MainWindow(QMainWindow):
    camera_menu_update_requested = PySideSignal(list)
    def __init__(self):
        init_log_path_main = DATA_DIR_FOR_MAIN / "logs" / "init_error.log" 
        try:
            init_log_path_main.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e_dir_create_init:
            print(f"Could not create dir for init_error.log: {e_dir_create_init}")

        log_file_init_phase_obj = None 
        try:
            print("Starting MainWindow initialization") 
            super().__init__()
            self.setWindowTitle("Endoscopy Reporting System")
            
            try:
                log_file_init_phase_obj = open(init_log_path_main, "a")
                log_file_init_phase_obj.write(f"\n\n--- New Application Start: {datetime.now()} ---\n")
            except IOError as e_io_init:
                print(f"Warning: Could not write to init_error.log: {e_io_init}")

            def write_to_init_log(message): 
                if log_file_init_phase_obj and not log_file_init_phase_obj.closed:
                    try:
                        log_file_init_phase_obj.write(message + "\n")
                    except IOError:
                        pass 
            
            self.error_handler = None
            self.data_dirty = False
            self._suppress_dirty_events = False
            self._last_open_prompted_path = None
            self._last_open_prompt_ts = 0
            try:
                write_to_init_log("Initializing error handler...")
                self.error_handler = ErrorHandler(self)
                self.error_handler.log_info("ErrorHandler OK.")
                write_to_init_log("Error handler initialized.")
            except Exception as e_eh:
                error_msg_eh = f"CRITICAL: Failed ErrorHandler: {str(e_eh)}\n{traceback.format_exc()}"
                write_to_init_log(f"ERROR: {error_msg_eh}")
                print(error_msg_eh) 
                QMessageBox.critical(None,"CritErr",f"Failed EH: {str(e_eh)}\nApp cannot continue.")
                if log_file_init_phase_obj:
                    log_file_init_phase_obj.close()
                sys.exit(1) 

            self.settings = None
            try:
                self.error_handler.log_info("Initializing SettingsManager...")
                self.settings = SettingsManager(self)
                self.error_handler.log_info("SettingsManager OK.")
                self.ai_refinement_service = AIRefinementService(self.settings, self.error_handler)
            except Exception as e_sm:
                self.error_handler.log_error("InitError", f"Failed SM: {str(e_sm)}\n{traceback.format_exc()}")
                QMessageBox.warning(self,"InitWarn",f"Settings manager fail: {str(e_sm)}\nFeatures impaired.")
                self.ai_refinement_service = None
            
            try:
                self.error_handler.log_info("Initializing core components...")
                self.initialize_core_components(log_file_init_phase_obj) 
                self.error_handler.log_info("Core components init finished.")
            except Exception as e_core:
                self.error_handler.log_error("InitError",f"Failed core comps: {str(e_core)}\n{traceback.format_exc()}")
            
            try:
                self.error_handler.log_info("Setting up UI...")
                self.setup_ui()
                self.error_handler.log_info("UI setup OK.")
            except Exception as e_ui:
                self.error_handler.log_error("UIError",f"Failed UI setup: {str(e_ui)}\n{traceback.format_exc()}")
            
            try:
                self.error_handler.log_info("Connecting DB to UI...")
                self.connect_database_to_ui()
                self.error_handler.log_info("DB connected to UI.")
            except Exception as e_dbui:
                self.error_handler.log_error("DBUIError",f"Failed DB to UI: {str(e_dbui)}\n{traceback.format_exc()}")
            
            try:
                self.error_handler.log_info("Setting up menu...")
                self.setup_menu_system()
                self.error_handler.log_info("Menu setup OK.")
            except Exception as e_menu:
                self.error_handler.log_error("MenuError",f"Failed menu: {str(e_menu)}\n{traceback.format_exc()}")
            
            try:
                self.error_handler.log_info("Connecting signals...")
                self.connect_signals()
                self.error_handler.log_info("Signals connected.")
            except Exception as e_sig:
                self.error_handler.log_error("SignalError",f"Failed signals: {str(e_sig)}\n{traceback.format_exc()}")
            
            if log_file_init_phase_obj and not log_file_init_phase_obj.closed: 
                write_to_init_log("MainWindow init sequence OK.")
                log_file_init_phase_obj.close()
            
            self.apply_initial_theme()
            self.showFullScreen() 
            self.error_handler.log_info("App started successfully and MainWindow is fullscreen.")
            try:
                self.camera_menu_update_requested.connect(self._apply_camera_menu_list)
            except Exception as signal_err:
                if self.error_handler:
                    self.error_handler.log_warning(f"Failed to connect camera menu signal: {signal_err}")
            
        except Exception as e_init_top: 
            error_msg = f"FATAL Error during MainWindow initialization: {str(e_init_top)}"
            detailed_tb = traceback.format_exc()
            print(f"{error_msg}\n{detailed_tb}")
            try:
                with open(init_log_path_main, "a") as final_log_f: 
                    final_log_f.write(f"CRITICAL ERROR IN __INIT__: {error_msg}\n{detailed_tb}\n")
            except:
                pass 
            QMessageBox.critical(None,"App Init Fatal Error",f"Critical error during startup:\n{str(e_init_top)}\nApp will exit.")
            if log_file_init_phase_obj and not log_file_init_phase_obj.closed:
                log_file_init_phase_obj.close()
            sys.exit(1)

    def initialize_core_components(self, log_file=None):
        def write_log_local(message): 
            if log_file and not log_file.closed:
                try:
                    log_file.write(message + "\n")
                except IOError:
                    pass 
        
        eh_log_info = getattr(self.error_handler, 'log_info', lambda msg: write_log_local(f"INFO_EH_FALLBACK: {msg}"))
        eh_log_error = getattr(self.error_handler, 'log_error', lambda et, msg, tb="": write_log_local(f"ERROR_EH_FALLBACK ({et}): {msg}\n{tb}"))
        
        def log_attempt(name):
            eh_log_info(f"Initializing {name}...")
        def log_ok(name):
            eh_log_info(f"{name} initialized.")
        def log_fail(name, e, tb_str, critical=False):
            msg = f"Failed to initialize {name}: {str(e)}"
            eh_log_error("InitError", msg, tb_str)
            if critical:
                QMessageBox.critical(self, "Critical Component Error", f"{msg}\nApplication may not function.")

        # CORRECTED Placeholder Camera Definition with QObject and PySideSignal
        class PlaceholderCameraLocal(QObject):
            frame_ready = PySideSignal(object)
            image_captured = PySideSignal(str)
            camera_error = PySideSignal(str)
            video_started = PySideSignal(str)
            video_stopped = PySideSignal(str)
            recording_time_updated = PySideSignal(str)
            recording_size_updated = PySideSignal(str)
            
            def cleanup_camera(self):
                pass
            emergency_cleanup = cleanup_camera
            
            def get_available_cameras(self):
                return [(0,"Placeholder")]
            
            def capture_image(self):
                self.camera_error.emit("Cam N/A (placeholder)")
                return None
                
            def start_recording(self):
                self.camera_error.emit("Cam N/A (placeholder)")
                return None
                
            def stop_recording(self):
                return None
                
            def select_camera(self, dev_id):
                self.camera_error.emit(f"Placeholder select {dev_id}")

        try:
            if self.settings:
                log_attempt("ThemeManager")
                self.theme_manager = ThemeManager(self.settings, self)
                log_ok("ThemeManager")
            else:
                log_fail("ThemeManager", Exception("SettingsManager N/A"), traceback.format_exc())
                
            log_attempt("DatabaseManager")
            self.db = DatabaseManager()
            log_ok("DatabaseManager")
            
            if self.settings and self.db:
                log_attempt("FileManager")
                self.file_manager = FileManager(self.settings, self)
                log_ok("FileManager")
                
                log_attempt("SearchManager")
                self.search_manager = SearchManager(self.db, self)
                log_ok("SearchManager")
                
                log_attempt("ReportGenerator")
                self.report_generator = ReportGenerator(self.db, self)
                log_ok("ReportGenerator")
                
                if hasattr(self,'file_manager') and self.file_manager:
                    log_attempt("CameraManager (Adaptive)")
                    self.camera_manager = CameraManager(self.file_manager, self)
                    log_ok("CameraManager (Adaptive)")
                else: 
                    log_fail("CameraManager (Adaptive)", Exception("FileManager N/A"), traceback.format_exc())
                    self.camera_manager = PlaceholderCameraLocal(self)
                    eh_log_info("Using placeholder camera (FileManager missing).")
            else:
                missing = [("SettingsManager" if not self.settings else ""), ("DatabaseManager" if not self.db else "")]
                missing = [m for m in missing if m]
                log_fail("Key Core Components", Exception(f"Deps missing: {', '.join(missing)}"), "", critical=True)
                if not hasattr(self,'camera_manager'):
                    self.camera_manager = PlaceholderCameraLocal(self)
                    eh_log_info("Using placeholder camera (Core deps missing).")
        except Exception as e_core_overall:
            log_fail("Core Components Initialization (Overall Block)", e_core_overall, traceback.format_exc(), critical=True)

    def setup_ui(self): 
        try:
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            main_layout = QHBoxLayout(central_widget)
            main_layout.setContentsMargins(0,0,0,0)
            main_layout.setSpacing(0)
            
            self.left_panel = LeftPanel(self)
            if hasattr(self.left_panel, 'data_changed'):
                self.left_panel.data_changed.connect(self.mark_data_dirty)
            main_layout.addWidget(self.left_panel, 40)
            
            try:
                self.right_panel = RightPanel(self)
                main_layout.addWidget(self.right_panel, 60)
                if self.error_handler:
                    self.error_handler.log_info("Right panel initialized successfully.")
            except Exception as e_right:
                if self.error_handler:
                    self.error_handler.log_error("RightPanelError", f"Failed to initialize right panel: {str(e_right)}\n{traceback.format_exc()}")
                # Create a placeholder to avoid None errors
                self.right_panel = QWidget()
                main_layout.addWidget(self.right_panel, 60)
        except Exception as e_ui:
            if self.error_handler:
                self.error_handler.log_error("UISetupError", f"Failed to set up UI: {str(e_ui)}\n{traceback.format_exc()}")
        
        # FIXED: Ensure camera manager frame connection
        if (hasattr(self, 'camera_manager') and self.camera_manager and 
            hasattr(self.right_panel, 'video_feed') and self.right_panel.video_feed and 
            hasattr(self.camera_manager, 'frame_ready')):
            try:
                self.camera_manager.frame_ready.connect(self.right_panel.video_feed.update_frame)
                if self.error_handler:
                    self.error_handler.log_info("Camera frame connection established successfully.")
            except Exception as e_cam_conn:
                if self.error_handler:
                    self.error_handler.log_error("CameraConnectionError", f"Failed to connect camera frames: {str(e_cam_conn)}")
        elif self.error_handler:
            self.error_handler.log_warning("Could not connect camera_manager.frame_ready to video_feed in setup_ui.")
    
    def connect_database_to_ui(self): 
        try:
            if hasattr(self, 'db') and self.db and hasattr(self, 'left_panel') and self.left_panel:
                self.left_panel.set_database(self.db)
                if hasattr(self.left_panel, 'save_btn'):
                    self.left_panel.save_btn.clicked.connect(self.handle_save_with_dropdown_history)
                if self.error_handler:
                    self.error_handler.log_info("DB connected to left panel UI.")
            elif self.error_handler:
                self.error_handler.log_warning("Cannot connect DB to UI: components missing.")
        except Exception as e:
            if self.error_handler:
                self.error_handler.log_error("DatabaseUIError", f"Failed connect DB to UI: {e}")
            QMessageBox.warning(self, "DB Connection Error", f"Failed connect DB to UI: {e}")
    
    def setup_menu_system(self): 
        try:
            self.menu_system = MenuSystem(self)
            self.setMenuBar(self.menu_system)
            
            self.menu_system.new_patient_triggered.connect(self.handle_new_patient)
            self.menu_system.open_patient_triggered.connect(self.handle_open_patient)
            self.menu_system.save_patient_triggered.connect(self.handle_save_patient)
            self.menu_system.settings_triggered.connect(self.handle_settings)
            self.menu_system.exit_triggered.connect(self.handle_exit)
            
            if hasattr(self,'camera_manager') and self.camera_manager:
                self.menu_system.camera_selected.connect(self.handle_camera_select)
                self.menu_system.record_toggled.connect(self.handle_record_toggle)
                self.menu_system.capture_triggered.connect(self.handle_capture_image)
                self.refresh_camera_menu_async()
            else:
                self.menu_system.update_camera_list([])
                
            if hasattr(self,'theme_manager') and self.theme_manager: 
                self.menu_system.theme_changed.connect(self.handle_theme_change)
                
            self.menu_system.about_triggered.connect(self.menu_system.handle_about)
            self.menu_system.help_triggered.connect(self.handle_help)
            
            if self.error_handler:
                self.error_handler.log_info("Menu system initialized.")
        except Exception as e:
            if self.error_handler:
                self.error_handler.log_error("MenuError", f"Failed menu setup: {e}")
            QMessageBox.warning(self, "Menu Init Error", f"Failed menu setup: {e}")

    def refresh_camera_menu_async(self):
        if not hasattr(self, 'menu_system') or not self.menu_system:
            return

        def worker():
            camera_list = []
            try:
                if hasattr(self, 'camera_manager') and self.camera_manager:
                    camera_list = self.camera_manager.get_available_cameras()
            except Exception as cam_err:
                if self.error_handler:
                    self.error_handler.log_warning(f"Camera scan failed: {cam_err}")
            self.camera_menu_update_requested.emit(camera_list)

        threading.Thread(target=worker, daemon=True).start()

    @Slot(list)
    def _apply_camera_menu_list(self, camera_list):
        if hasattr(self, 'menu_system') and self.menu_system:
            self.menu_system.update_camera_list(camera_list or [])

    def connect_signals(self): 
        """FIXED: Critical signal connections for video recording and report generation"""
        try:
            # CRITICAL: Right Panel -> Main App (Video Recording)
            if hasattr(self, 'right_panel') and self.right_panel:
                # FIXED: Video recording signal connection
                if hasattr(self.right_panel, 'recording_state_changed'):
                    self.right_panel.recording_state_changed.connect(self.handle_record_button)
                    if self.error_handler:
                        self.error_handler.log_info("✅ CRITICAL: Video recording signal connected successfully.")
                else:
                    if self.error_handler:
                        self.error_handler.log_error("SignalError", "❌ CRITICAL: RightPanel does not have recording_state_changed signal.")
                
                # Image capture connection
                if hasattr(self.right_panel, 'image_captured'): 
                    self.right_panel.image_captured.connect(self.handle_image_capture)
                    if self.error_handler:
                        self.error_handler.log_info("✅ Image capture signal connected.")
                
                # Import images connection
                if hasattr(self.right_panel, 'import_images_requested'): 
                    self.right_panel.import_images_requested.connect(self.handle_import_report_images)
                    
                # Video playback connection
                if (hasattr(self.right_panel, 'captured_media_tab') and 
                    hasattr(self.right_panel.captured_media_tab, 'video_play_requested')):
                    self.right_panel.captured_media_tab.video_play_requested.connect(self.handle_play_video)
                    
                if self.error_handler: 
                    self.error_handler.log_info("✅ RightPanel -> MainApp signals connected successfully.")

            # CRITICAL: Left Panel -> Main App (Report Generation)
            if hasattr(self, 'left_panel') and self.left_panel:
                # FIXED: Report generation signal connection with enhanced validation
                if hasattr(self.left_panel, 'generate_report_requested'): 
                    self.left_panel.generate_report_requested.connect(self.handle_generate_report)
                    if self.error_handler:
                        self.error_handler.log_info("✅ CRITICAL: Report generation signal connected successfully.")
                        self.error_handler.log_info(f"📋 Report preview available: {REPORT_PREVIEW_AVAILABLE}")
                        self.error_handler.log_info(f"📄 PDF dependencies available: {PDF_DEPENDENCIES_AVAILABLE}")
                else:
                    if self.error_handler:
                        self.error_handler.log_error("SignalError", "❌ CRITICAL: LeftPanel does not have generate_report_requested signal.")
                
                # Other left panel connections
                if hasattr(self.left_panel, 'save_requested'): 
                    self.left_panel.save_requested.connect(self.handle_save_with_dropdown_history)
                if hasattr(self.left_panel, 'search_requested'): 
                    self.left_panel.search_requested.connect(self.handle_search)
                if hasattr(self.left_panel, 'new_patient_requested'): 
                    self.left_panel.new_patient_requested.connect(self.handle_new_patient)
                if hasattr(self.left_panel, 'refinement_requested'):
                    self.left_panel.refinement_requested.connect(self.handle_refinement_request)
                    
                if self.error_handler: 
                    self.error_handler.log_info("✅ LeftPanel -> MainApp signals connected successfully.")
                
            # Camera Manager -> Main App
            if hasattr(self, 'camera_manager') and self.camera_manager:
                if hasattr(self.camera_manager, 'error_signal'): 
                    self.camera_manager.error_signal.connect(self.handle_camera_error)
                if hasattr(self.camera_manager, 'video_started'): 
                    self.camera_manager.video_started.connect(self.handle_video_started)
                if hasattr(self.camera_manager, 'video_stopped'): 
                    self.camera_manager.video_stopped.connect(self.handle_video_stopped)
                if hasattr(self.camera_manager, 'image_captured'): 
                    self.camera_manager.image_captured.connect(self.handle_image_captured_with_context)
                if self.error_handler: 
                    self.error_handler.log_info("✅ CameraManager -> MainApp signals connected successfully.")
                
            # ReportGenerator -> Main App
            if hasattr(self, 'report_generator') and self.report_generator:
                if hasattr(self.report_generator, 'report_generated'): 
                    self.report_generator.report_generated.connect(self.handle_report_generated)
                if hasattr(self.report_generator, 'report_error'): 
                    self.report_generator.report_error.connect(self.handle_report_error)
                if self.error_handler: 
                    self.error_handler.log_info("✅ ReportGenerator -> MainApp signals connected successfully.")
                
            # Theme Manager -> Main App 
            if hasattr(self, 'theme_manager') and self.theme_manager and hasattr(self.theme_manager, 'theme_applied'):
                self.theme_manager.theme_applied.connect(self.handle_theme_applied)
                if self.error_handler: 
                    self.error_handler.log_info("✅ ThemeManager -> MainApp signals connected successfully.")
            
            # LeftPanel Buttons -> Main App
            if hasattr(self, 'left_panel') and self.left_panel:
                if hasattr(self.left_panel, 'find_btn') and hasattr(self, 'handle_open_patient'):
                    self.left_panel.find_btn.clicked.connect(self.handle_open_patient)
                    if self.error_handler:
                        self.error_handler.log_info("✅ Connected left_panel.find_btn to handle_open_patient")

            if self.error_handler: 
                self.error_handler.log_info("✅ ALL CRITICAL SIGNALS CONNECTED SUCCESSFULLY")
        except Exception as e:
            if self.error_handler: 
                self.error_handler.log_error("SignalError", f"❌ CRITICAL ERROR connecting signals: {str(e)}\n{traceback.format_exc()}")
            QMessageBox.critical(self, "Critical Signal Connection Error", f"Failed to connect critical signals: {str(e)}")

    def mark_data_dirty(self, *_):
        if getattr(self, '_suppress_dirty_events', False):
            return
        self.data_dirty = True

    def _set_data_clean(self):
        self.data_dirty = False

    def handle_save_with_dropdown_history(self, checked=False, show_message=True):
        try: 
            saved = self._save_patient(show_message=show_message)
            if not saved:
                return False
            if (hasattr(self, 'left_panel') and self.left_panel and 
                hasattr(self.left_panel, 'save_dropdown_values_to_database')):
                self.left_panel.save_dropdown_values_to_database()
            return True
        except Exception as e: 
            if self.error_handler:
                self.error_handler.log_error("SaveError",f"Error in save with dropdown history: {str(e)}")
            QMessageBox.warning(self, "Save Error", f"Error saving data: {str(e)}")
            return False

    def handle_save_patient(self):
        self._save_patient(show_message=True)

    def _save_patient(self, show_message=True):
        try:
            if not (hasattr(self, 'left_panel') and self.left_panel and hasattr(self, 'db') and self.db):
                if show_message:
                    QMessageBox.warning(self, "Save Error", "Cannot save patient - database or UI not initialized.")
                return False
                
            patient_data = self.left_panel.get_patient_info()
            required_fields = ["patient_id", "name", "gender", "hospital_name"] 
            missing_fields = [field for field in required_fields if not patient_data.get(field)]
            if missing_fields:
                if show_message:
                    QMessageBox.warning(self, "Missing Information", f"Please fill in required fields: {', '.join(missing_fields)}")
                return False
                
            report_data_from_ui = self.left_panel.get_report_data()
            report_data_from_ui["report_title"] = patient_data.get("report_title", "ENDOSCOPY REPORT")
            report_data_from_ui["indication"] = patient_data.get("indication", "")
            visit_date_str = patient_data.get("date")
            report_date_value = None
            if visit_date_str:
                try:
                    visit_dt = datetime.strptime(visit_date_str, "%d/%m/%Y")
                    report_date_value = visit_dt.strftime("%Y-%m-%d 00:00:00")
                except ValueError:
                    report_date_value = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            else:
                report_date_value = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            report_data_from_ui["report_date"] = report_date_value
            patient_id_for_report = patient_data["patient_id"]
            
            try:
                existing_patient = self.db.get_patient(patient_data["patient_id"])
                report_id_for_images = None
                
                if existing_patient:
                    self.db.update_patient(patient_data["patient_id"], patient_data)
                    existing_report = self.db.get_report(patient_id=patient_id_for_report) 
                    if existing_report:
                        self.db.update_report(existing_report["report_id"], report_data_from_ui)
                        report_id_for_images = existing_report["report_id"]
                    else:
                        new_rid = self.settings.get_next_report_id() if hasattr(self,'settings') else f"R-ERR-{datetime.now().timestamp()}"
                        report_data_from_ui["report_id"] = new_rid
                        report_data_from_ui["patient_id"] = patient_id_for_report
                        self.db.add_report(report_data_from_ui)
                        report_id_for_images = new_rid
                else: 
                    self.db.add_patient(patient_data)
                    new_rid = self.settings.get_next_report_id() if hasattr(self,'settings') else f"R-ERR-{datetime.now().timestamp()}"
                    report_data_from_ui["report_id"] = new_rid
                    report_data_from_ui["patient_id"] = patient_id_for_report
                    self.db.add_report(report_data_from_ui)
                    report_id_for_images = new_rid
                    
                if (hasattr(self,'right_panel') and self.right_panel and 
                    hasattr(self.right_panel,'report_images_tab') and report_id_for_images):
                    report_images_tuples = self.right_panel.report_images_tab.get_images() 
                    for idx, (img_path, lbl) in enumerate(report_images_tuples):
                        self.db.add_report_image(report_id_for_images, img_path, lbl, idx)
                        
                if show_message:
                    QMessageBox.information(self, "Save Successful", "Patient and report data saved.")
                self._set_data_clean()
                if self.error_handler:
                    self.error_handler.log_info(f"Saved patient: {patient_id_for_report}")
                return True
            except Exception as db_err:
                if self.error_handler:
                    self.error_handler.log_error("DBSaveError", f"DB save failed: {db_err}\n{traceback.format_exc()}")
                if show_message:
                    QMessageBox.critical(self, "Save Failed", f"DB error: {str(db_err)}")
                return False
        except Exception as e:
            if self.error_handler:
                self.error_handler.log_error("SavePatientError", f"Error saving patient: {str(e)}")
            if show_message:
                QMessageBox.warning(self, "Save Patient Error", f"Error saving patient: {str(e)}")
            return False

    def handle_new_patient(self): 
        try:
            if self.check_unsaved_changes():
                return 
            if hasattr(self, 'left_panel') and self.left_panel:
                self._suppress_dirty_events = True
                try:
                    self.left_panel.clear_all_fields()
                finally:
                    self._suppress_dirty_events = False
                    self._set_data_clean()
            if hasattr(self, 'right_panel') and self.right_panel:
                if hasattr(self.right_panel, 'report_images_tab'):
                    # Clear report images shown in UI (do not delete files)
                    self.right_panel.report_images_tab.clear()
                if hasattr(self.right_panel, 'captured_media_tab'):
                    # Clear captured media list in UI (keep files on disk)
                    self.right_panel.captured_media_tab.clear()
            if self.error_handler:
                self.error_handler.log_info("New Patient: Fields cleared.")
            QMessageBox.information(self, "New Patient", "Fields cleared.")
        except Exception as e:
            if self.error_handler:
                self.error_handler.log_error("NewPatientError", f"Error new patient: {str(e)}")
            QMessageBox.warning(self, "New Patient Error", f"Error: {str(e)}")

    def handle_open_patient(self): 
        try:
            if self.check_unsaved_changes():
                return
            if hasattr(self, 'search_manager') and self.search_manager:
                pid = self.search_manager.show_patient_search_dialog(self)
                if pid:
                    self.load_patient(pid)
            else:
                QMessageBox.information(self, "Not Implemented", "Patient search N/A.")
        except Exception as e:
            if self.error_handler:
                self.error_handler.log_error("OpenPatientError", f"Error open patient: {str(e)}")
            QMessageBox.warning(self, "Open Patient Error", f"Error: {str(e)}")

    def handle_generate_report(self): 
        """COMPLETELY FIXED: Comprehensive report generation with dependency checks and error handling"""
        try:
            if self.error_handler:
                self.error_handler.log_info("🔄 Report generation started...")
            
            # CRITICAL FIX: Check dependencies first
            if not REPORT_PREVIEW_AVAILABLE:
                QMessageBox.critical(
                    self, 
                    "Report Generation Error", 
                    "Report preview dialog is not available.\n\nThis could be due to:\n"
                    "• Missing src/ui/report_preview_dialog.py file\n"
                    "• Import path issues\n"
                    "• Python module problems\n\n"
                    "Please check the logs for more details."
                )
                if self.error_handler:
                    self.error_handler.log_error("ReportError", "ReportPreviewDialog not available")
                return
            
            if not PDF_DEPENDENCIES_AVAILABLE:
                QMessageBox.critical(
                    self, 
                    "Missing Dependencies", 
                    "PDF generation dependencies are missing.\n\n"
                    "Please install required packages:\n"
                    "• pip install fpdf2\n"
                    "• pip install Pillow\n\n"
                    "Then restart the application."
                )
                if self.error_handler:
                    self.error_handler.log_error("ReportError", "PDF dependencies missing: fpdf2, Pillow")
                return
            
            # VALIDATION: Check if left panel exists
            if not (hasattr(self, 'left_panel') and self.left_panel):
                QMessageBox.warning(self, "Report Error", "Patient panel not available.")
                if self.error_handler:
                    self.error_handler.log_error("ReportError", "Left panel not available")
                return
            
            # GET PATIENT DATA
            try:
                pd = self.left_panel.get_patient_info()
                rtf = self.left_panel.get_report_data() 
                
                if self.error_handler:
                    self.error_handler.log_info(f"📋 Patient data retrieved: {pd.get('patient_id', 'NO_ID')}")
                    self.error_handler.log_info(f"📄 Report data retrieved: {len(rtf.get('findings', ''))} chars findings")
            except Exception as data_err:
                if self.error_handler:
                    self.error_handler.log_error("ReportError", f"Failed to get patient/report data: {data_err}")
                QMessageBox.critical(self, "Data Error", f"Failed to retrieve patient data: {str(data_err)}")
                return
            
            # VALIDATION: Check required fields
            if not pd.get("patient_id") or not pd.get("name"):
                QMessageBox.warning(self, "Missing Info", "Please fill in Patient ID and Name before generating report.")
                if self.error_handler:
                    self.error_handler.log_warning("❌ Report generation aborted: missing patient ID or name")
                return
            
            # GET IMAGES
            imgs = []
            try:
                if (hasattr(self,'right_panel') and self.right_panel and 
                    hasattr(self.right_panel,'report_images_tab')):
                    imgs = self.right_panel.report_images_tab.get_images()
                    if self.error_handler:
                        self.error_handler.log_info(f"🖼️ Images retrieved: {len(imgs)} images")
                else:
                    if self.error_handler:
                        self.error_handler.log_warning("⚠️ No report images tab found")
            except Exception as img_err:
                if self.error_handler:
                    self.error_handler.log_error("ReportError", f"Failed to get images: {img_err}")
                # Continue without images
                imgs = []
            
            # ENHANCED DATA PREPARATION FOR PDF
            try:
                enhanced_patient_data = pd.copy()
                enhanced_patient_data['report_title'] = pd.get('report_title', rtf.get('report_title', 'ENDOSCOPY REPORT'))
                enhanced_patient_data['indication'] = pd.get('indication', rtf.get('indication', ''))
                
                if self.error_handler:
                    self.error_handler.log_info(f"📊 Enhanced patient data: report_title='{enhanced_patient_data.get('report_title')}', indication='{enhanced_patient_data.get('indication')}'")
            except Exception as enhance_err:
                if self.error_handler:
                    self.error_handler.log_error("ReportError", f"Failed to enhance patient data: {enhance_err}")
                QMessageBox.critical(self, "Data Processing Error", f"Failed to process patient data: {str(enhance_err)}")
                return
            
            # SHOW REPORT PREVIEW DIALOG
            try:
                if self.error_handler:
                    self.error_handler.log_info("📋 Creating report preview dialog...")
                
                prev_dlg = ReportPreviewDialog(enhanced_patient_data, rtf, imgs, self) 
                prev_dlg.report_generated.connect(self.handle_report_generated)
                
                if self.error_handler:
                    self.error_handler.log_info("✅ Report preview dialog created successfully")
                
                # Execute dialog
                result = prev_dlg.exec()
                
                if self.error_handler:
                    self.error_handler.log_info(f"📋 Report preview dialog finished with result: {result}")
                
            except Exception as dialog_err:
                error_details = f"Failed to create or show report preview dialog: {str(dialog_err)}"
                if self.error_handler:
                    self.error_handler.log_error("DialogError", f"{error_details}\n{traceback.format_exc()}")
                
                # Show detailed error message
                QMessageBox.critical(
                    self, 
                    "Report Preview Error", 
                    f"{error_details}\n\n"
                    f"Technical details:\n{str(dialog_err)}\n\n"
                    f"Please check the application logs for more information."
                )
                
        except Exception as e:
            error_details = f"❌ CRITICAL: Error generating report: {str(e)}"
            if self.error_handler:
                self.error_handler.log_error("ReportError", f"{error_details}\n{traceback.format_exc()}")
            
            # Show user-friendly error message
            QMessageBox.critical(
                self, 
                "Report Generation Error", 
                f"A critical error occurred while generating the report:\n\n{str(e)}\n\n"
                f"Please check:\n"
                f"• Patient data is filled correctly\n"
                f"• Required dependencies are installed\n"
                f"• Application logs for more details"
            )
    
    def handle_refinement_request(self, report_payload=None):
        if not self.left_panel:
            return
        if not getattr(self, "ai_refinement_service", None):
            if self.settings:
                self.ai_refinement_service = AIRefinementService(self.settings, self.error_handler)
            else:
                QMessageBox.warning(self, "AI Refinement", "Settings are unavailable; cannot start AI session.")
                return
        if hasattr(self.ai_refinement_service, "refresh_settings"):
            self.ai_refinement_service.refresh_settings()
        patient_snapshot = {}
        try:
            if hasattr(self.left_panel, "get_all_data"):
                patient_snapshot = self.left_panel.get_all_data()
        except Exception as exc:  # noqa: BLE001
            if self.error_handler:
                self.error_handler.log_warning(f"Failed to collect patient context for AI refinement: {exc}")
        dialog = RefinementDialog(
            parent=self,
            service=self.ai_refinement_service,
            initial_sections=report_payload or {},
            patient_context=patient_snapshot,
            default_brevity=getattr(self.ai_refinement_service, "default_brevity", True),
        )
        dialog.refinement_applied.connect(self.apply_ai_refinement)
        dialog.exec()

    def apply_ai_refinement(self, refined_sections):
        if not self.left_panel:
            return
        try:
            mappings = [
                (getattr(self.left_panel, "findings_text", None), refined_sections.get("findings", "")),
                (getattr(self.left_panel, "conclusions_text", None), refined_sections.get("conclusions", "")),
                (getattr(self.left_panel, "recommendations_text", None), refined_sections.get("recommendations", "")),
            ]
            for widget, value in mappings:
                if widget is None:
                    continue
                blocker = QSignalBlocker(widget)
                widget.setPlainText((value or "").strip())
                del blocker
            self.data_dirty = True
            if self.error_handler:
                self.error_handler.log_info("AI refinement content applied to form fields.")
        except Exception as exc:  # noqa: BLE001
            if self.error_handler:
                self.error_handler.log_error("AIRefineApplyError", f"Failed to apply AI refinement: {exc}")
            QMessageBox.warning(self, "AI Refinement", f"Could not apply AI output: {exc}")

    def handle_capture_image(self): 
        try:
            if hasattr(self, 'camera_manager') and self.camera_manager:
                self.camera_manager.capture_image()
                if self.error_handler:
                    self.error_handler.log_info("📸 Image capture requested")
            else:
                QMessageBox.warning(self, "Camera Error", "Camera manager not available.")
        except Exception as e:
            if self.error_handler:
                self.error_handler.log_error("CaptureError", f"Error capturing image: {str(e)}")
            QMessageBox.warning(self, "Capture Error", f"Error: {str(e)}")

    def handle_record_button(self, should_start_recording: bool):
        """FIXED: Video recording handler with comprehensive error handling"""
        try:
            if self.error_handler:
                self.error_handler.log_info(f"🎥 Recording button pressed: {'START' if should_start_recording else 'STOP'}")
            
            if not (hasattr(self, 'camera_manager') and self.camera_manager):
                QMessageBox.warning(self, "Camera Error", "Camera not available or not initialized.")
                if self.error_handler:
                    self.error_handler.log_error("CameraError", "❌ Camera manager not available for recording")
                return

            if should_start_recording:
                if self.error_handler:
                    self.error_handler.log_info("▶️ Attempting to start recording via handle_record_button.")
                result = self.camera_manager.start_recording()
                if self.error_handler:
                    self.error_handler.log_info(f"📹 Start recording result: {result}")
            else:
                if self.error_handler:
                    self.error_handler.log_info("⏹️ Attempting to stop recording via handle_record_button.")
                result = self.camera_manager.stop_recording()
                if self.error_handler:
                    self.error_handler.log_info(f"⏸️ Stop recording result: {result}")
        except Exception as e:
            if self.error_handler:
                self.error_handler.log_error("RecordError", f"❌ Error record toggle: {str(e)}\n{traceback.format_exc()}")
            QMessageBox.warning(self, "Recording Error", f"Error: {str(e)}")

    def handle_image_captured_with_context(self, image_path_final): 
        try:
            if not image_path_final or not Path(image_path_final).exists():
                if self.error_handler:
                    self.error_handler.log_warning(f"Img captured signal invalid path: {image_path_final}")
                return
            # FIXED: Use captured_media_tab instead of captured_tab
            if (hasattr(self, 'right_panel') and self.right_panel and 
                hasattr(self.right_panel, 'captured_media_tab')):
                self.right_panel.captured_media_tab.add_image(image_path_final) 
                if self.error_handler:
                    self.error_handler.log_info(f"Added image to captured UI: {image_path_final}")
            elif self.error_handler:
                self.error_handler.log_warning("Cannot add captured image to UI, components missing.")
        except Exception as e:
            if self.error_handler:
                self.error_handler.log_error("ImageHandlingError", f"Error handling captured image UI: {str(e)}")
            QMessageBox.warning(self, "Image Error", f"Error handling captured image: {str(e)}")

    def handle_import_report_images(self):
        """Import images from filesystem to report tab"""
        if not (hasattr(self, 'right_panel') and 
                hasattr(self.right_panel, 'report_images_tab')):
            QMessageBox.warning(self, "Import Error", "Core components missing.")
            return
        
        # Get context from left panel for better file organization
        hospital_name = "Unknown Hospital"
        patient_name = "Unknown Patient"
        patient_id = "UNKNOWN"
        if hasattr(self, 'left_panel') and self.left_panel:
            patient_data = self.left_panel.get_patient_info()
            hospital_name = patient_data.get("hospital_name", "Unknown Hospital")
            patient_name = patient_data.get("name", "Unknown Patient")
            patient_id = patient_data.get("patient_id", "UNKNOWN")
        
        default_import_path = str(Path.home() / "Pictures")
        source_image_paths, _ = QFileDialog.getOpenFileNames(
            self, 
            "Select Images to Import for Report", 
            default_import_path, 
            "Image files (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff)"
        )
        
        if source_image_paths:
            imported_count = 0
            for source_path_str in source_image_paths:
                if len(self.right_panel.report_images_tab.images) >= self.right_panel.report_images_tab.max_images:
                    QMessageBox.warning(self,"Import Limit",f"Max {self.right_panel.report_images_tab.max_images} images.")
                    break
                    
                if hasattr(self, 'file_manager') and self.file_manager:
                    new_copied_path = self.file_manager.import_image(source_path_str, hospital_name, patient_name, patient_id)
                else:
                    new_copied_path = source_path_str  # Use original path if no file manager
                    
                if new_copied_path:
                    if self.right_panel.report_images_tab.add_image(new_copied_path):
                        imported_count += 1
                        
            if imported_count > 0:
                QMessageBox.information(self, "Import Successful", f"{imported_count} image(s) imported.")

    def load_patient(self, patient_id_to_load): 
        try:
            if not (hasattr(self, 'db') and self.db):
                QMessageBox.warning(self, "Load Error", "DB N/A.")
                return
                
            patient_data = self.db.get_patient(patient_id_to_load)
            if not patient_data:
                QMessageBox.warning(self, "Not Found", f"PID {patient_id_to_load} not found.")
                return
                
            self._suppress_dirty_events = True
            try:
                if hasattr(self, 'left_panel') and self.left_panel:
                    self.left_panel.set_patient_info(patient_data) 
                    
                report_data = self.db.get_report(patient_id=patient_id_to_load) 
                if report_data:
                    if hasattr(self, 'left_panel') and self.left_panel:
                        self.left_panel.set_report_data(report_data) 
                        
                    report_id_for_images = report_data.get("report_id")
                    if (report_id_for_images and hasattr(self, 'right_panel') and self.right_panel and 
                        hasattr(self.right_panel, 'report_images_tab')):
                        report_images_tuples = self.db.get_report_images(report_id_for_images) 
                        self.right_panel.report_images_tab.set_images(report_images_tuples) 
                else: 
                    if (hasattr(self, 'left_panel') and 
                        hasattr(self.left_panel, 'clear_report_fields')):
                        self.left_panel.clear_report_fields() 
                    if (hasattr(self, 'right_panel') and self.right_panel and 
                        hasattr(self.right_panel, 'report_images_tab')):
                        self.right_panel.report_images_tab.clear()
            finally:
                self._suppress_dirty_events = False
                self._set_data_clean()
                    
            if self.error_handler:
                self.error_handler.log_info(f"Loaded patient: {patient_id_to_load}")
        except Exception as e:
            if self.error_handler:
                self.error_handler.log_error("LoadPatientError", f"Error loading patient: {str(e)}\n{traceback.format_exc()}")
            QMessageBox.warning(self, "Load Error", f"Error loading patient: {str(e)}")

    def handle_theme_change(self, theme_name): 
        try:
            if hasattr(self, 'theme_manager') and self.theme_manager:
                success = self.theme_manager.apply_theme(theme_name)
                if success:
                    if self.error_handler:
                        self.error_handler.log_info(f"Theme changed to: {theme_name}")
                    if hasattr(self, 'menu_system') and self.menu_system:
                        self.menu_system.update_theme_checkmark(theme_name)
                else:
                    QMessageBox.warning(self, "Theme Error", f"Failed to apply theme: {theme_name}")
            else:
                QMessageBox.warning(self, "Theme Error", "Theme manager N/A.")
        except Exception as e:
            if self.error_handler:
                self.error_handler.log_error("ThemeError", f"Error changing theme: {str(e)}")
            QMessageBox.warning(self, "Theme Error", f"Error changing theme: {str(e)}")

    def apply_initial_theme(self): 
        try:
            if hasattr(self, 'theme_manager') and self.theme_manager:
                self.theme_manager.apply_theme() 
                current_applied_theme = self.theme_manager.get_current_theme()
                if hasattr(self, 'menu_system') and self.menu_system:
                    self.menu_system.update_theme_checkmark(current_applied_theme)
        except Exception as e:
            if self.error_handler:
                self.error_handler.log_error("ThemeError", f"Error applying initial theme: {str(e)}")

    def handle_theme_applied(self, theme_name): 
        try:
            if hasattr(self, 'menu_system') and self.menu_system:
                self.menu_system.update_theme_checkmark(theme_name)
            if self.error_handler:
                self.error_handler.log_info(f"Theme applied: {theme_name}")
        except Exception as e:
            if self.error_handler:
                self.error_handler.log_error("ThemeError", f"Error handling theme applied: {str(e)}")

    def handle_record_toggle(self, recording_state_requested):
        """Handle recording toggle from menu"""
        try:
            if not (hasattr(self, 'camera_manager') and self.camera_manager):
                QMessageBox.warning(self, "Camera Error", "Camera N/A.")
                return
                
            is_rec_now = False
            if (hasattr(self.camera_manager, 'video_recorder') and 
                self.camera_manager.video_recorder):
                is_rec_now = self.camera_manager.video_recorder.is_recording()
                
            if recording_state_requested and not is_rec_now:
                if self.error_handler:
                    self.error_handler.log_info("Starting video recording (menu).")
                self.camera_manager.start_recording()
            elif not recording_state_requested and is_rec_now:
                if self.error_handler:
                    self.error_handler.log_info("Stopping video recording (menu).")
                self.camera_manager.stop_recording()
        except Exception as e:
            action = "starting" if recording_state_requested else "stopping"
            if self.error_handler:
                self.error_handler.log_error("RecordToggleError", f"Menu record {action} error: {str(e)}")
            QMessageBox.warning(self, "Recording Error", f"Error {action} record: {str(e)}")

    def handle_camera_select(self, device_id): 
        try:
            if hasattr(self, 'camera_manager') and self.camera_manager:
                success = self.camera_manager.select_camera(device_id) 
                if success and self.error_handler:
                    self.error_handler.log_info(f"Selected camera device: {device_id}")
            else:
                QMessageBox.warning(self, "Camera Error", "Camera N/A.")
        except Exception as e:
            if self.error_handler:
                self.error_handler.log_error("CameraSelectError", f"Error selecting camera: {str(e)}")
            QMessageBox.warning(self, "Camera Selection Error", f"Error: {str(e)}")

    def handle_video_started(self, video_path): 
        try:
            if self.error_handler:
                self.error_handler.log_info(f"📹 Video recording started: {video_path}")
                
            # Update right panel UI
            if hasattr(self, 'right_panel') and self.right_panel:
                if (hasattr(self.right_panel, 'video_feed') and 
                    hasattr(self.right_panel.video_feed, 'start_recording_indicator')):
                    self.right_panel.video_feed.start_recording_indicator()
                    
                # Update record button state
                if hasattr(self.right_panel, 'is_recording'):
                    self.right_panel.is_recording = True
                if hasattr(self.right_panel, 'record_btn'):
                    self.right_panel.record_btn.setText("⏹")
                    self.right_panel.record_btn.setToolTip("Stop Recording")
                    
            # Update menu system
            if (hasattr(self, 'menu_system') and 
                hasattr(self.menu_system, 'update_record_action_state')):
                self.menu_system.update_record_action_state(True)
        except Exception as e:
            if self.error_handler:
                self.error_handler.log_error("VideoStartError", f"Error handling video start: {str(e)}")

    def handle_video_stopped(self, video_path): 
        try:
            if self.error_handler:
                self.error_handler.log_info(f"⏹️ Video recording stopped. Path: {video_path if video_path else 'N/A'}")
                
            # Update right panel UI
            if hasattr(self, 'right_panel') and self.right_panel:
                if (hasattr(self.right_panel, 'video_feed') and 
                    hasattr(self.right_panel.video_feed, 'stop_recording_indicator')):
                    self.right_panel.video_feed.stop_recording_indicator()
                    
                # Update record button state
                if hasattr(self.right_panel, 'is_recording'):
                    self.right_panel.is_recording = False
                if hasattr(self.right_panel, 'record_btn'):
                    self.right_panel.record_btn.setText("⏺")
                    self.right_panel.record_btn.setToolTip("Start Recording")
                    
            # Update menu system
            if (hasattr(self, 'menu_system') and 
                hasattr(self.menu_system, 'update_record_action_state')):
                self.menu_system.update_record_action_state(False)
                
            # Add video to captured media if valid
            if not video_path or not Path(video_path).exists():
                if self.error_handler:
                    self.error_handler.log_warning(f"Video stopped, but path invalid/missing: {video_path}")
                return
                
            # FIXED: Use captured_media_tab instead of captured_tab
            if (hasattr(self, 'right_panel') and self.right_panel and 
                hasattr(self.right_panel, 'captured_media_tab')):
                self.right_panel.captured_media_tab.add_video(video_path)
                if self.error_handler:
                    self.error_handler.log_info(f"✅ Added video to captured media: {video_path}")
            elif self.error_handler:
                self.error_handler.log_warning("Cannot add video to UI, components missing.")
        except Exception as e:
            if self.error_handler:
                self.error_handler.log_error("VideoHandlingError", f"Error handling stopped video: {str(e)}")
            QMessageBox.warning(self, "Video Error", f"Error: {str(e)}")
            
    def handle_camera_error(self, error_message): 
        if self.error_handler:
            self.error_handler.log_error("CameraManagerError", error_message)
        # Only show popup for serious errors, not frame drops
        if ("frame" not in error_message.lower() and "timeout" not in error_message.lower() or 
            "Could not open" in error_message or "access" in error_message.lower()):
            QMessageBox.warning(self, "Camera Error", error_message)

    def handle_report_generated(self, report_path): 
        try:
            report_path = str(report_path)
            if self.error_handler:
                self.error_handler.log_info(f"📄 Report generated: {report_path}")
            save_success = self.handle_save_with_dropdown_history(show_message=False)
            if not save_success and self.error_handler:
                self.error_handler.log_warning("Auto-save after report generation failed.")
            now = time.time()
            if (self._last_open_prompted_path == report_path and 
                now - getattr(self, "_last_open_prompt_ts", 0) < 2):
                return
            if QMessageBox.question(
                self,
                "Report Generated",
                f"Report saved to:\n{report_path}\n\nOpen now?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            ) == QMessageBox.Yes:
                path_open = str(Path(report_path).resolve())
                sys_plat = platform.system()
                if sys_plat == "Windows":
                    os.startfile(path_open)
                elif sys_plat == "Darwin":
                    subprocess.run(("open", path_open), check=False) 
                else:
                    subprocess.run(("xdg-open", path_open), check=False)
            self._last_open_prompted_path = report_path
            self._last_open_prompt_ts = now
        except Exception as e_open:
            if self.error_handler:
                self.error_handler.log_error("ReportOpenError", f"Error opening report: {e_open}")
            QMessageBox.warning(self, "Report Error", f"Error opening report: {str(e_open)}")

    def handle_report_error(self, error_message): 
        if self.error_handler:
            self.error_handler.log_error("ReportGenerationError", error_message)
        QMessageBox.critical(self, "Report Generation Failed", f"Failed to generate report: {error_message}")

    def handle_image_capture(self):
        """Handle image capture button pressed in the UI"""
        try:
            if hasattr(self, 'camera_manager') and self.camera_manager:
                self.camera_manager.capture_image()
                if self.error_handler:
                    self.error_handler.log_info("📸 Image capture requested via UI")
            else:
                QMessageBox.warning(self, "Camera Error", "Camera manager not available.")
        except Exception as e:
            if self.error_handler:
                self.error_handler.log_error("CaptureError", f"Image capture failed: {str(e)}\n{traceback.format_exc()}")
            QMessageBox.warning(self, "Capture Error", f"Failed to capture image: {str(e)}")
    
    def handle_play_video(self, video_path):
        """Handle playing a video using the system's default video player"""
        try:
            if not video_path or not Path(video_path).exists():
                if self.error_handler: 
                    self.error_handler.log_warning(f"Cannot play video: path does not exist: {video_path}")
                QMessageBox.warning(self, "Video Error", f"Cannot play video: file not found.")
                return
            
            # Get absolute path to the video file
            video_absolute_path = str(Path(video_path).resolve())
            
            # Use the system's default video player based on the platform
            sys_platform = platform.system()
            if sys_platform == "Windows":
                os.startfile(video_absolute_path)
            elif sys_platform == "Darwin":  # macOS
                subprocess.run(("open", video_absolute_path), check=False)
            else:  # Linux and other Unix-like systems
                subprocess.run(("xdg-open", video_absolute_path), check=False)
                
            if self.error_handler:
                self.error_handler.log_info(f"🎬 Playing video: {video_path}")
        except Exception as e:
            if self.error_handler:
                self.error_handler.log_error("VideoPlaybackError", f"Error playing video: {str(e)}\n{traceback.format_exc()}")
            QMessageBox.warning(self, "Video Playback Error", f"Error playing video: {str(e)}")

    def handle_settings(self): 
        if self.error_handler:
            self.error_handler.log_info("Settings action triggered.")
        if not getattr(self, "settings", None):
            QMessageBox.warning(self, "Settings", "Settings manager is not available.")
            return
        dialog = AISettingsDialog(self.settings, self)
        result = dialog.exec()
        if result == QDialog.Accepted:
            if not getattr(self, "ai_refinement_service", None):
                self.ai_refinement_service = AIRefinementService(self.settings, self.error_handler)
            if self.ai_refinement_service:
                self.ai_refinement_service.refresh_settings()
            QMessageBox.information(self, "Settings", "AI assistant settings updated.")

    def handle_exit(self):
        self.close() 
        
    def handle_help(self):
        QMessageBox.information(self,"Help","Endoscopy Reporting System v1.0\nHelp docs TBD.")
    
    def check_unsaved_changes(self): 
        try:
            if not getattr(self, 'data_dirty', False):
                return False
            if hasattr(self, 'left_panel') and self.left_panel:
                res = QMessageBox.question(
                    self,
                    "Unsaved Changes",
                    "Save changes before proceeding?", 
                    QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                    QMessageBox.Save
                )
                if res == QMessageBox.Save:
                    if self.handle_save_with_dropdown_history():
                        return False
                    return True
                elif res == QMessageBox.Cancel:
                    return True
                else:
                    self._set_data_clean()
            return False 
        except Exception as e:
            if self.error_handler:
                self.error_handler.log_error("UnsavedChangesError", f"Error checking unsaved changes: {str(e)}")
            return False 

    def closeEvent(self, event): 
        eh = getattr(self, 'error_handler', None)
        if eh:
            eh.log_info("Application close initiated via closeEvent.")
        if self.check_unsaved_changes():
            event.ignore()
            return
        if eh:
            eh.log_info("Proceeding with application shutdown via closeEvent.")
        if hasattr(self, 'camera_manager') and self.camera_manager:
            try:
                self.camera_manager.cleanup_camera()
                if hasattr(self.camera_manager, 'emergency_cleanup'):
                    self.camera_manager.emergency_cleanup()
                if eh:
                    eh.log_info("Camera resources released.")
            except Exception as e_cam:
                if eh:
                    eh.log_error("ShutdownError",f"Err cleanup cam:{e_cam}")
                else:
                    print(f"Err cleanup cam:{e_cam}")
        if eh:
            eh.log_info("App shutdown procedures from closeEvent completed.")
        event.accept()


def main(): 
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    pre_init_log_path = DATA_DIR_FOR_MAIN / "logs" / "pre_init.log" 
    try:
        pre_init_log_path.parent.mkdir(parents=True, exist_ok=True)
        if not logging.getLogger().handlers: 
            logging.basicConfig(
                filename=pre_init_log_path, 
                level=logging.INFO, 
                format="%(asctime)s - %(levelname)s - %(module)s - %(message)s"
            )
        logging.info("App pre-init log started (or appended).")
    except Exception as log_e:
        print(f"Fail pre-init logging: {log_e}")
    
    window = None
    try:
        window = MainWindow()
        window.show() 
    except SystemExit:
        logging.warning("SysExit during MainWindow init.")
        sys.exit(1)
    except Exception as e_create:
        logging.critical(f"Unhandled exception MainWindow create: {e_create}\n{traceback.format_exc()}")
        QMessageBox.critical(None, "App Startup Error", f"Fail create main window: {e_create}\nApp will exit.")
        sys.exit(1)
        
    if window is None:
        logging.critical("MainWindow obj is None after init. Exiting.")
        sys.exit(1)
    
    exit_code = app.exec()
    final_eh = getattr(window, 'error_handler', None) 
    if (window and hasattr(window, 'camera_manager') and 
        hasattr(window.camera_manager, 'emergency_cleanup')):
        try:
            if final_eh:
                final_eh.log_info("Final emergency camera cleanup post-loop.")
            window.camera_manager.emergency_cleanup()
        except Exception as e_final_cam: 
            if final_eh:
                final_eh.log_error("FinalCleanupErr",f"Err final cleanup:{e_final_cam}")
            else:
                print(f"Err final cleanup:{e_final_cam}")
    
    if final_eh:
        final_eh.log_info(f"App exiting code: {exit_code}")
    else:
        print(f"App exiting code: {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
