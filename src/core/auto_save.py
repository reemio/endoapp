from PySide6.QtCore import QTimer, Signal, QObject
import json
from pathlib import Path
import logging


class AutoSave(QObject):
    """Handles automatic saving of form data and application state"""

    save_triggered = Signal()  # Signal emitted when auto-save occurs

    def __init__(self, interval=300000):  # Default 5 minutes
        super().__init__()
        self.interval = interval
        self.auto_save_file = Path("data/auto_save/current_state.json")
        self.auto_save_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.perform_auto_save)
        self.timer.start(self.interval)

    def perform_auto_save(self):
        try:
            # Emit signal to collect current state from UI
            self.save_triggered.emit()
        except Exception as e:
            logging.error(f"Auto-save failed: {e}")

    def save_state(self, state_data):
        """Save current application state"""
        try:
            with open(self.auto_save_file, "w") as f:
                json.dump(state_data, f, indent=4)
            logging.info("Auto-save completed successfully")
        except Exception as e:
            logging.error(f"Failed to save state: {e}")

    def load_state(self):
        """Load last saved state"""
        try:
            if self.auto_save_file.exists():
                with open(self.auto_save_file, "r") as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load state: {e}")
        return None
