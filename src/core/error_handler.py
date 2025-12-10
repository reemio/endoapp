# ERROR HANDLING AND LOGGING SYSTEM
import logging
import traceback
import sys
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QObject, Signal


class ErrorHandler(QObject):
    """Comprehensive error handling and logging system
    
    This class provides centralized error handling and logging
    functionality for the entire application.
    """
    
    # SIGNALS
    error_occurred = Signal(str, str)  # error_type, error_message
    critical_error = Signal(str, str)  # error_type, error_message
    
    def __init__(self, parent=None):
        """Initialize the error handler
        
        Args:
            parent: Parent QObject
        """
        super().__init__(parent)
        self.setup_logging()
        self.install_exception_hook()
    
    def setup_logging(self):
        """Setup the logging system"""
        # Create logs directory
        logs_dir = Path("data/logs")
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate log filename with date
        current_date = datetime.now().strftime("%Y-%m-%d")
        log_file = logs_dir / f"application_{current_date}.log"
        
        # Configure root logger
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        
        # Clear existing handlers to avoid duplicates
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # File handler for all logs
        file_handler = logging.FileHandler(log_file)
        file_format = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
        )
        file_handler.setFormatter(file_format)
        self.logger.addHandler(file_handler)
        
        # Error log for warnings and above
        error_log = logs_dir / f"errors_{current_date}.log"
        error_handler = logging.FileHandler(error_log)
        error_handler.setLevel(logging.WARNING)
        error_format = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(message)s\n"
            "File: %(pathname)s\nLine: %(lineno)d\n"
        )
        error_handler.setFormatter(error_format)
        self.logger.addHandler(error_handler)
        
        # Console handler for development
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            "%(levelname)s - %(name)s: %(message)s"
        )
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)
        
        # Application-specific logger
        self.app_logger = logging.getLogger("EndoscopyReporter")
        
        self.app_logger.info("Logging system initialized")
    
    def install_exception_hook(self):
        """Install global exception hook"""
        self.original_hook = sys.excepthook
        sys.excepthook = self.exception_hook
        
        self.app_logger.info("Global exception hook installed")

    @staticmethod
    def _sanitize_message(message):
        """Convert message to ASCII-safe string to avoid encoding errors on some consoles."""
        try:
            if isinstance(message, str):
                return message.encode("ascii", errors="replace").decode("ascii")
        except Exception:
            pass
        return str(message)
    
    def exception_hook(self, exc_type, exc_value, exc_traceback):
        """Global exception hook
        
        Args:
            exc_type: Exception type
            exc_value: Exception value
            exc_traceback: Exception traceback
        """
        # Format traceback
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        tb_text = ''.join(tb_lines)
        
        # Log the error
        self.app_logger.critical(
            f"Unhandled exception: {exc_type.__name__}: {exc_value}\n{tb_text}"
        )
        
        # Emit signal for UI notification
        self.critical_error.emit(exc_type.__name__, str(exc_value))
        
        # Call original hook
        self.original_hook(exc_type, exc_value, exc_traceback)
    
    def log_error(self, error_type, message, traceback_obj=None):
        """Log an error
        
        Args:
            error_type: Type of error
            message: Error message
            traceback_obj: Traceback object (optional)
        """
        error_details = self._sanitize_message(message)
        
        if traceback_obj:
            tb_text = ''.join(traceback.format_tb(traceback_obj))
            error_details = f"{message}\n{tb_text}"
        
        self.app_logger.error(f"{error_type}: {error_details}")
        self.error_occurred.emit(error_type, error_details)
    
    def log_warning(self, message):
        """Log a warning
        
        Args:
            message: Warning message
        """
        safe_message = self._sanitize_message(message)
        self.app_logger.warning(safe_message)
    
    def log_info(self, message):
        """Log an info message
        
        Args:
            message: Info message
        """
        safe_message = self._sanitize_message(message)
        self.app_logger.info(safe_message)
    
    def show_error_dialog(self, title, message, details=None):
        """Show error dialog
        
        Args:
            title: Dialog title
            message: Error message
            details: Detailed error information (optional)
        """
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        
        if details:
            msg_box.setDetailedText(details)
            
        msg_box.exec()
    
    def show_warning_dialog(self, title, message, details=None):
        """Show warning dialog
        
        Args:
            title: Dialog title
            message: Warning message
            details: Detailed warning information (optional)
        """
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        
        if details:
            msg_box.setDetailedText(details)
            
        msg_box.exec()
    
    # ERROR RECOVERY METHODS
    
    def recover_database(self):
        """Attempt to recover database from backup"""
        try:
            from pathlib import Path
            import sqlite3
            import shutil
            
            # Log recovery attempt
            self.app_logger.warning("Attempting database recovery")
            
            # Find main database file
            db_path = Path("data/database/endoscopy.db")
            if not db_path.exists():
                raise FileNotFoundError("Database file not found")
                
            # Find the most recent backup
            backup_dir = Path("data/database/backups")
            if not backup_dir.exists():
                raise FileNotFoundError("Backup directory not found")
                
            # List backups and sort by modification time (newest first)
            backups = list(backup_dir.glob("*.db"))
            if not backups:
                raise FileNotFoundError("No database backups found")
                
            backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            latest_backup = backups[0]
            
            # Backup current database (even if corrupted)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            corrupted_path = backup_dir / f"corrupted_{timestamp}.db"
            shutil.copy2(db_path, corrupted_path)
            
            # Restore from backup
            shutil.copy2(latest_backup, db_path)
            
            self.app_logger.info(
                f"Database recovery successful. Restored from {latest_backup.name}"
            )
            
            return True, f"Database successfully recovered from {latest_backup.name}"
            
        except Exception as e:
            error_msg = f"Database recovery failed: {str(e)}"
            self.app_logger.error(f"{error_msg}\n{traceback.format_exc()}")
            return False, error_msg
    
    def recover_auto_save(self):
        """Recover from auto-save if available"""
        try:
            from pathlib import Path
            import json
            
            # Log recovery attempt
            self.app_logger.warning("Attempting to recover from auto-save")
            
            # Find auto-save file
            auto_save_path = Path("data/auto_save/current_state.json")
            if not auto_save_path.exists():
                raise FileNotFoundError("Auto-save file not found")
                
            # Validate JSON
            with open(auto_save_path, "r") as f:
                state_data = json.load(f)
                
            if not state_data:
                raise ValueError("Auto-save file is empty or invalid")
                
            self.app_logger.info("Auto-save recovery successful")
            
            return True, state_data
            
        except Exception as e:
            error_msg = f"Auto-save recovery failed: {str(e)}"
            self.app_logger.error(f"{error_msg}\n{traceback.format_exc()}")
            return False, error_msg
    
    def repair_corrupted_images(self):
        """Attempt to repair corrupted image references"""
        try:
            import sqlite3
            from pathlib import Path
            
            # Log repair attempt
            self.app_logger.warning("Attempting to repair corrupted image references")
            
            db_path = Path("data/database/endoscopy.db")
            if not db_path.exists():
                raise FileNotFoundError("Database file not found")
                
            # Connect to database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Find images with non-existent paths
            cursor.execute("SELECT id, report_id, image_path FROM images")
            all_images = cursor.fetchall()
            
            repaired_count = 0
            removed_count = 0
            
            for image_id, report_id, image_path in all_images:
                if not Path(image_path).exists():
                    # Try to find the image in captured images directory
                    image_name = Path(image_path).name
                    captured_dir = Path("data/images/captured")
                    
                    # Search for the image by name
                    matches = list(captured_dir.glob(f"*{image_name}*"))
                    
                    if matches:
                        # Update with found path
                        cursor.execute(
                            "UPDATE images SET image_path = ? WHERE id = ?",
                            (str(matches[0]), image_id)
                        )
                        repaired_count += 1
                        self.app_logger.info(f"Repaired image path: {image_id} -> {matches[0]}")
                    else:
                        # Mark as missing but don't delete
                        cursor.execute(
                            "UPDATE images SET image_path = ? WHERE id = ?",
                            ("MISSING_" + image_path, image_id)
                        )
                        removed_count += 1
                        self.app_logger.warning(f"Marked missing image: {image_id}")
            
            conn.commit()
            conn.close()
            
            self.app_logger.info(
                f"Image repair completed: {repaired_count} repaired, {removed_count} marked as missing"
            )
            
            return True, f"Image repair completed: {repaired_count} repaired, {removed_count} marked as missing"
            
        except Exception as e:
            error_msg = f"Image repair failed: {str(e)}"
            self.app_logger.error(f"{error_msg}\n{traceback.format_exc()}")
            return False, error_msg
    
    # CONTEXT MANAGER FOR ERROR HANDLING
    
    def error_context(self, context_name):
        """Context manager for error handling
        
        Usage:
            with error_handler.error_context("Operation Name"):
                # code that might raise an exception
        
        Args:
            context_name: Name of the operation context
            
        Returns:
            Context manager object
        """
        return ErrorContext(self, context_name)


class ErrorContext:
    """Context manager for error handling"""
    
    def __init__(self, error_handler, context_name):
        """Initialize the error context
        
        Args:
            error_handler: ErrorHandler instance
            context_name: Name of the operation context
        """
        self.error_handler = error_handler
        self.context_name = context_name
    
    def __enter__(self):
        """Enter the context"""
        self.error_handler.log_info(f"Starting: {self.context_name}")
        return self
    
    def __exit__(self, exc_type, exc_value, exc_traceback):
        """Exit the context
        
        Args:
            exc_type: Exception type
            exc_value: Exception value
            exc_traceback: Exception traceback
            
        Returns:
            True if exception handled, False otherwise
        """
        if exc_type is not None:
            # An exception occurred
            self.error_handler.log_error(
                exc_type.__name__,
                f"Error in {self.context_name}: {exc_value}",
                exc_traceback
            )
            return True  # Suppress exception
            
        # No exception occurred
        self.error_handler.log_info(f"Completed: {self.context_name}")
        return False  # Don't suppress exception
