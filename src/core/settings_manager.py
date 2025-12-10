# FILE: src/core/settings_manager.py
# Ensures robust ID generation.

from PySide6.QtCore import QObject, Signal
from pathlib import Path
from typing import Optional
import json
import logging
from datetime import datetime

class SettingsManager(QObject):
    settings_changed = Signal(dict)
    theme_changed = Signal(str)
    camera_settings_changed = Signal(dict)
    path_changed = Signal(str, Path)
    error_occurred = Signal(str)
    footswitch_config_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.paths = {} # Initialize before setup_paths
        self.settings = {} # Initialize before load_settings
        self.setup_logging() # Logging can start early
        self.setup_paths()   # Defines self.paths and self.settings_file
        self.load_settings() # Loads or creates default settings

    def setup_logging(self):
        self.logger = logging.getLogger("SettingsManager")
        # Basic config if handlers not set, actual file handler setup in setup_paths
        if not self.logger.handlers:
            logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
            self.logger.info("SettingsManager basic logging initialized.")


    def setup_paths(self):
        # Determine project root more robustly if possible, or assume a structure
        # Assuming this file is in src/core/
        project_root_path = Path(__file__).resolve().parent.parent.parent 
        data_dir = project_root_path / "data"

        self.paths = {
            "base": data_dir,
            "settings": data_dir / "settings",
            "database": data_dir / "database",
            "reports": data_dir / "reports",
            "images": data_dir / "images" / "captured",
            "videos": data_dir / "videos" / "captured",
            "temp": data_dir / "temp",
            "logs": data_dir / "logs",
            "backup": data_dir / "backup",
        }
        for path_key in self.paths:
            self.paths[path_key].mkdir(parents=True, exist_ok=True)
        
        self.settings_file = self.paths["settings"] / "settings.json"
        self.backup_settings_dir = self.paths["settings"] / "backup"
        self.backup_settings_dir.mkdir(exist_ok=True)

        # Re-initialize logger with correct file path now that paths are defined
        # This overwrites basicConfig if it was called.
        log_file_path = self.paths["logs"] / "settings.log"
        self.logger.handlers.clear() # Remove any default handlers
        fh = logging.FileHandler(log_file_path)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
        self.logger.setLevel(logging.INFO) # Ensure level is set after adding handler
        self.logger.propagate = False # Prevent logging to root if ErrorHandler also configures root
        self.logger.info("SettingsManager logging initialized with file handler.")


    def load_settings(self):
        self.default_settings = {
            "application": {"theme": "dark", "language": "en", "auto_save_interval": 300, "warning_on_exit": True, "max_recent_files": 10, "default_report_format": "pdf"},
            "hospital": {"name": "Medical Center", "logo_path": "", "address": "", "contact": "", "default_doctor": ""},
            "camera": {"default_device": 0, "resolution": "1920x1080", "format": "MJPG", "fps": 30, "auto_exposure": True, "exposure": 0, "white_balance": "auto", "contrast": 0, "brightness": 0, "saturation": 0},
            "paths": {key: str(val) for key, val in self.paths.items()}, # Ensure paths are strings for JSON
            "sequence_numbers": {"last_patient_id": 0, "last_report_id": 0},
            "patient_id_counters": {},
            "ui": {"font_size": 10, "show_toolbar": True, "show_statusbar": True, "panel_ratio": 40},
            "footswitch": {"enabled": False, "selected_device_path": None, "capture_pedal_input_code": None, "record_pedal_input_code": None},
            "ai_refinement": {
                "enabled": True,
                "provider": "openai",
                "model": "gpt-4.1",
                "temperature": 0.2,
                "max_tokens": 900,
                "brevity_default": True,
                "api_key_env": "OPENAI_API_KEY",
                "stored_api_key": ""
            }
        }
        try:
            if self.settings_file.exists() and self.settings_file.stat().st_size > 0:
                with open(self.settings_file, "r") as f:
                    saved_settings = json.load(f)
                    self.settings = self.merge_settings(self.default_settings, saved_settings)
                self.logger.info("Settings loaded successfully.")
            else:
                self.settings = self.default_settings.copy()
                self.save_settings()
                self.logger.info("Default settings created and saved as file was missing or empty.")
        except json.JSONDecodeError as e:
            self.logger.error(f"Error decoding settings.json: {e}. Attempting to use backup or defaults.")
            self.settings = self.default_settings.copy() # Fallback
            self.error_occurred.emit(f"Settings file corrupted. Defaults loaded. Error: {e}")
        except Exception as e:
            self.logger.error(f"Error loading settings: {e}. Using default settings.")
            self.settings = self.default_settings.copy()
            self.error_occurred.emit(f"Error loading settings: {e}. Defaults loaded.")

    def merge_settings(self, defaults, saved):
        merged = defaults.copy()
        for key, value in saved.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self.merge_settings(merged[key], value)
            else:
                merged[key] = value
        for key, default_value in defaults.items(): # Ensure all top-level default sections exist
            if key not in merged: merged[key] = default_value
            elif isinstance(default_value, dict): # Ensure sub-keys for dict sections
                 if not isinstance(merged.get(key), dict): merged[key] = default_value.copy()
                 else:
                    for sub_key, sub_default_value in default_value.items():
                        if sub_key not in merged[key]: merged[key][sub_key] = sub_default_value
        return merged

    def save_settings(self):
        try:
            if self.settings_file.exists() and self.settings_file.stat().st_size > 0:
                self.backup_settings_dir.mkdir(parents=True, exist_ok=True)
                backup_file = self.backup_settings_dir / f"settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                try:
                    with open(self.settings_file, "r") as src_f: current_data = json.load(src_f) # ensure valid before backup
                    with open(backup_file, "w") as dst_f: json.dump(current_data, dst_f, indent=4)
                    self.logger.info(f"Settings backup created: {backup_file}")
                except (IOError, json.JSONDecodeError) as backup_err:
                    self.logger.error(f"Failed to create settings backup (source invalid or unwritable): {backup_err}")
            
            with open(self.settings_file, "w") as f:
                json.dump(self.settings, f, indent=4)
            self.logger.info("Settings saved successfully.")
        except Exception as e:
            self.logger.error(f"Error saving settings: {e}"); self.error_occurred.emit(f"Error saving settings: {e}")

    def get(self, *keys, default=None):
        try:
            value = self.settings
            for key in keys:
                if not isinstance(value, dict): return default
                value = value[key]
            return value
        except KeyError: return default
        except Exception as e: self.logger.warning(f"Error getting setting '{'.'.join(keys)}': {e}"); return default

    def set(self, *keys, value):
        try:
            target = self.settings
            for key in keys[:-1]:
                target = target.setdefault(key, {}) # Ensure path exists
                if not isinstance(target, dict): # Path became non-dict, error
                    self.logger.error(f"Cannot set nested key; '{key}' in '{'.'.join(keys)}' is not a dictionary."); return False
            
            last_key = keys[-1]
            current_value = target.get(last_key)
            if current_value == value: return True # No change

            target[last_key] = value
            self.save_settings()
            if keys[0] == "ai_refinement" and last_key == "stored_api_key":
                display_val = "***"
            else:
                display_val = value
            self.logger.info(f"Setting updated: {'.'.join(keys)} = {display_val}")
            self.settings_changed.emit(self.settings.copy())
            
            if keys[0] == "application" and last_key == "theme": self.theme_changed.emit(value)
            elif keys[0] == "camera": self.camera_settings_changed.emit(self.get("camera", default={}).copy())
            elif keys[0] == "paths" and len(keys) > 1: self.path_changed.emit(keys[1], Path(value))
            elif keys[0] == "footswitch": self.footswitch_config_changed.emit(self.get("footswitch", default={}).copy())
            return True
        except Exception as e:
            self.logger.error(f"Error setting value for {'.'.join(keys)}: {e}"); self.error_occurred.emit(f"Error setting {'.'.join(keys)}: {e}")
            return False

    def get_theme(self): return self.get("application", "theme", default="dark")
    def set_theme(self, theme_name):
        return self.set("application", "theme", value=theme_name) if theme_name in ["light", "dark", "professional"] else False
    
    def get_camera_settings(self): return self.get("camera", default={}).copy()
    def set_camera_device(self, device_id): return self.set("camera", "default_device", value=int(device_id))
    def set_camera_resolution(self, width, height): return self.set("camera", "resolution", value=f"{width}x{height}")

    def get_path(self, path_type: str) -> Path:
        if not self.paths: self.setup_paths() # Should be already done by init
        default_path_str = str(self.paths.get(path_type, Path("data") / path_type)) # Fallback if not in self.paths
        # Get path from settings, use default from self.paths if not found in settings
        path_str = self.get("paths", path_type, default=default_path_str)
        return Path(path_str)

    def set_path(self, path_type, new_path): return self.set("paths", path_type, value=str(new_path))

    def get_next_patient_id(self, hospital: Optional[str] = None) -> Optional[str]:
        try:
            current_year = datetime.now().strftime("%y")
            hospital_name = (hospital or self.get("hospital", "name", default="General Hospital") or "General Hospital").strip()
            if not hospital_name:
                hospital_name = "General Hospital"

            counters = self.settings.setdefault("patient_id_counters", {})
            normalized_key = hospital_name.lower()
            existing_record = counters.get(normalized_key, {})

            record_year = existing_record.get("year")
            record_counter = existing_record.get("counter", 0)
            if record_year != current_year or not isinstance(record_counter, int):
                record_counter = 0

            record_counter += 1
            updated_record = {
                "year": current_year,
                "counter": record_counter,
                "display_name": hospital_name,
            }
            if not self.set("patient_id_counters", normalized_key, value=updated_record):
                self.logger.error(f"Failed to persist patient ID counter for hospital '{hospital_name}'")
                return f"ERR_PID_SAVE_{datetime.now().strftime('%S%f')}"

            return f"{record_counter:04d}/{current_year}"
        except Exception as e:
            self.logger.error(f"Error generating next patient ID: {e}\n{traceback.format_exc()}")
            return f"ERR_PID_EXC_{datetime.now().strftime('%S%f')}"

    def get_next_report_id(self) -> Optional[str]:
        try:
            if "sequence_numbers" not in self.settings:
                self.settings["sequence_numbers"] = self.default_settings["sequence_numbers"].copy()

            current_val = self.settings["sequence_numbers"].get("last_report_id", 0)
            if not isinstance(current_val, int):
                try: current_val = int(current_val)
                except ValueError: current_val = 0
            
            next_id_num = current_val + 1
            success = self.set("sequence_numbers", "last_report_id", value=next_id_num)
            if not success:
                self.logger.error("Failed to save incremented report ID to settings.")
                return f"ERR_RID_SAVE_{datetime.now().strftime('%S%f')}"

            year_str = datetime.now().strftime("%y")
            return f"R-{next_id_num:04d}/{year_str}"
        except Exception as e:
            self.logger.error(f"Error generating next report ID: {e}\n{traceback.format_exc()}")
            return f"ERR_RID_EXC_{datetime.now().strftime('%S%f')}"

    def export_settings(self, file_path=None): # ... (same as before) ...
        try:
            export_path = Path(file_path) if file_path else \
                          self.backup_settings_dir / f"settings_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            export_path.parent.mkdir(parents=True, exist_ok=True)
            with open(export_path, "w") as f: json.dump(self.settings, f, indent=4)
            self.logger.info(f"Settings exported to: {export_path}"); return str(export_path)
        except Exception as e: self.logger.error(f"Err export settings: {e}"); self.error_occurred.emit(f"Err export: {e}"); return None

    def import_settings(self, file_path): # ... (same as before) ...
        try:
            import_path = Path(file_path)
            if not import_path.exists(): self.logger.error(f"Import file N/F: {import_path}"); self.error_occurred.emit(f"Import file N/F: {import_path}"); return False
            with open(import_path, "r") as f: imported_settings = json.load(f)
            self.export_settings() # Backup current
            self.settings = self.merge_settings(self.default_settings.copy(), imported_settings)
            self.save_settings(); self.logger.info(f"Settings imported from: {import_path}"); return True
        except Exception as e: self.logger.error(f"Err import settings: {e}"); self.error_occurred.emit(f"Err import: {e}"); return False

    def reset_to_defaults(self, section=None): # ... (same as before) ...
        try:
            self.export_settings() 
            if section:
                if section in self.default_settings: self.settings[section] = json.loads(json.dumps(self.default_settings[section]))
                else: self.logger.warning(f"Attempted reset non-existent section: {section}"); return False
            else: self.settings = json.loads(json.dumps(self.default_settings))
            self.save_settings(); self.logger.info(f"Settings reset: {section or 'all'}"); return True
        except Exception as e: self.logger.error(f"Err reset settings: {e}"); self.error_occurred.emit(f"Err reset: {e}"); return False

    def get_footswitch_config(self):
        return self.get("footswitch", default=self.default_settings["footswitch"].copy()).copy()

    def set_footswitch_config_value(self, key, value):
        if key not in self.default_settings["footswitch"]:
            self.logger.warning(f"Attempted to set invalid footswitch config key: {key}"); return False
        return self.set("footswitch", key, value=value)

    def is_footswitch_enabled(self):
        return bool(self.get("footswitch", "enabled", default=False))
