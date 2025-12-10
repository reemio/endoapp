# FIXED FILE_MANAGER.PY - RESOLVED PATH CONCATENATION ISSUES
# FILE: src/core/file_manager.py

from PySide6.QtCore import QObject, Signal, QDateTime
from pathlib import Path
import os
import shutil
import logging
import traceback
from datetime import datetime
import json


class FileManager(QObject):
    """File management system with hospital-based folder structure - FIXED PATH ISSUES"""
    
    # SIGNALS
    file_created = Signal(str, str)  # file_type, file_path
    file_moved = Signal(str, str, str)  # file_type, old_path, new_path
    file_deleted = Signal(str, str)  # file_type, file_path
    import_completed = Signal(str, int)  # import_type, count
    export_completed = Signal(str, int)  # export_type, count
    error_occurred = Signal(str)  # error_message
    
    def __init__(self, settings_manager=None, parent=None):
        """Initialize the file manager
        
        Args:
            settings_manager: SettingsManager instance for path configuration
            parent: Parent QObject
        """
        super().__init__(parent)
        self.settings = settings_manager
        self.setup_logging()
        self.initialize_base_directories()
    
    def setup_logging(self):
        """Setup logging configuration"""
        self.logger = logging.getLogger("FileManager")
        
        if not self.logger.handlers:
            log_path = Path("data/logs/file_manager.log")
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_path)
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            file_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
            self.logger.setLevel(logging.INFO)
    
    def initialize_base_directories(self):
        """Create base directory structure"""
        self.base_dirs = {
            "data": Path("data"),
            "hospitals": Path("data/hospitals"),  # NEW: Hospital-based structure
            "temp": Path("data/temp"),
            "logs": Path("data/logs"),
            "backups": Path("data/backups"),
            "database": Path("data/database"),
            "settings": Path("data/settings"),
        }
        
        # Create base directories
        for path in self.base_dirs.values():
            path.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("Base directory structure initialized")
    
    def get_hospital_directory(self, hospital_name):
        """Get or create hospital directory structure
        
        Args:
            hospital_name: Name of the hospital
            
        Returns:
            Dictionary with hospital directory paths
        """
        if not hospital_name:
            hospital_name = "Default_Hospital"
        
        # Sanitize hospital name for filesystem
        safe_hospital_name = self.sanitize_filename(hospital_name)
        
        hospital_base = self.base_dirs["hospitals"] / safe_hospital_name
        
        hospital_dirs = {
            "base": hospital_base,
            "reports": hospital_base / "Reports",
            "media": hospital_base / "Media",
        }
        
        # Create hospital directories
        for path in hospital_dirs.values():
            path.mkdir(parents=True, exist_ok=True)
        
        return hospital_dirs
    
    def get_patient_media_directory(self, hospital_name, patient_name, patient_id):
        """Get or create patient media directory structure
        
        Args:
            hospital_name: Name of the hospital
            patient_name: Name of the patient
            patient_id: Patient ID
            
        Returns:
            Dictionary with patient media directory paths
        """
        hospital_dirs = self.get_hospital_directory(hospital_name)
        
        # Create patient identifier
        safe_patient_name = self.sanitize_filename(patient_name) if patient_name else "Unknown_Patient"
        safe_patient_id = self.sanitize_filename(patient_id) if patient_id else "No_ID"
        patient_folder = f"{safe_patient_name}_{safe_patient_id}"
        
        patient_base = hospital_dirs["media"] / patient_folder
        
        patient_dirs = {
            "base": patient_base,
            "images": patient_base / "Images",
            "videos": patient_base / "Videos",
        }
        
        # Create patient directories
        for path in patient_dirs.values():
            path.mkdir(parents=True, exist_ok=True)
        
        return patient_dirs
    
    def sanitize_filename(self, filename):
        """Sanitize filename for filesystem compatibility
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        if not filename:
            return "Unknown"
        
        # Convert to string if it's not
        filename = str(filename)
        
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        sanitized = filename
        
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Remove extra spaces and replace with underscores
        sanitized = '_'.join(sanitized.split())
        
        # Limit length
        if len(sanitized) > 50:
            sanitized = sanitized[:50]
        
        return sanitized
    
    def get_file_path(self, file_type, filename=None, hospital_name=None, 
                     patient_name=None, patient_id=None, use_timestamp=True):
        """Generate a path for a new file with hospital-based structure - FIXED PATH CONCATENATION
        
        Args:
            file_type: Type of file ('image', 'video', 'report')
            filename: Base filename (optional)
            hospital_name: Hospital name for organization
            patient_name: Patient name for media files
            patient_id: Patient ID for organization
            use_timestamp: Whether to add timestamp to filename
            
        Returns:
            Path object for the new file
        """
        try:
            if file_type in ["image", "video"]:
                # Media files go to patient directories
                if not hospital_name or not patient_name:
                    # Fallback to old structure if missing info
                    directory = self.base_dirs["data"] / f"{file_type}s" / "captured"  # FIXED: STRING CONCATENATION
                    directory.mkdir(parents=True, exist_ok=True)
                else:
                    patient_dirs = self.get_patient_media_directory(hospital_name, patient_name, patient_id)
                    directory = patient_dirs["images"] if file_type == "image" else patient_dirs["videos"]
                
            elif file_type == "report":
                # Reports go to hospital reports directory
                if not hospital_name:
                    directory = self.base_dirs["data"] / "reports"
                    directory.mkdir(parents=True, exist_ok=True)
                else:
                    hospital_dirs = self.get_hospital_directory(hospital_name)
                    directory = hospital_dirs["reports"]
                
            else:
                # Other files go to temp
                directory = self.base_dirs["temp"]
            
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                if file_type == "image":
                    filename = f"img_{timestamp}.jpg"
                elif file_type == "video":
                    filename = f"vid_{timestamp}.mp4"
                elif file_type == "report":
                    # Use patient name and date for report filename
                    if patient_name and patient_id:
                        safe_name = self.sanitize_filename(patient_name)
                        safe_id = self.sanitize_filename(patient_id)
                        date_str = datetime.now().strftime("%Y-%m-%d")
                        filename = f"{safe_name}_{safe_id}_{date_str}.pdf"
                    else:
                        filename = f"report_{timestamp}.pdf"
                else:
                    filename = f"file_{timestamp}.tmp"
            else:
                # Add timestamp to existing filename if requested
                if use_timestamp:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    # FIXED: PROPER STRING HANDLING
                    filename_str = str(filename)
                    name, ext = os.path.splitext(filename_str)
                    filename = f"{name}_{timestamp}{ext}"
            
            # FIXED: ENSURE BOTH DIRECTORY AND FILENAME ARE PROPER TYPES
            return Path(directory) / str(filename)
            
        except Exception as e:
            self.logger.error(f"Error generating file path: {e}")
            # Fallback to temp directory
            return self.base_dirs["temp"] / str(filename or "error_file.tmp")
    
    def save_captured_image(self, image_data, filename=None, hospital_name=None, 
                           patient_name=None, patient_id=None):
        """Save a captured image to the appropriate directory
        
        Args:
            image_data: Binary image data or file-like object
            filename: Filename to use (optional)
            hospital_name: Hospital name for organization
            patient_name: Patient name
            patient_id: Patient ID
            
        Returns:
            Path to the saved image
        """
        try:
            # Get target path
            image_path = self.get_file_path("image", filename, hospital_name, 
                                          patient_name, patient_id)
            
            # Ensure directory exists
            image_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save the image
            if isinstance(image_data, bytes):
                with open(image_path, "wb") as f:
                    f.write(image_data)
            else:
                # Assume file-like object
                with open(image_path, "wb") as f:
                    shutil.copyfileobj(image_data, f)
            
            self.logger.info(f"Saved captured image: {image_path}")
            self.file_created.emit("image", str(image_path))
            
            return str(image_path)
            
        except Exception as e:
            error_msg = f"Error saving captured image: {str(e)}"
            self.logger.error(f"{error_msg}\n{traceback.format_exc()}")
            self.error_occurred.emit(error_msg)
            return None
    
    def save_captured_video(self, video_data, filename=None, hospital_name=None,
                           patient_name=None, patient_id=None):
        """Save a captured video to the appropriate directory
        
        Args:
            video_data: Binary video data or file-like object
            filename: Filename to use (optional)
            hospital_name: Hospital name for organization
            patient_name: Patient name
            patient_id: Patient ID
            
        Returns:
            Path to the saved video
        """
        try:
            # Get target path
            video_path = self.get_file_path("video", filename, hospital_name,
                                          patient_name, patient_id)
            
            # Ensure directory exists
            video_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save the video
            if isinstance(video_data, bytes):
                with open(video_path, "wb") as f:
                    f.write(video_data)
            elif hasattr(video_data, 'read'):
                # File-like object
                with open(video_path, "wb") as f:
                    shutil.copyfileobj(video_data, f)
            else:
                # Assume it's a path to copy from
                shutil.copy2(str(video_data), str(video_path))  # FIXED: STRING CONVERSION
            
            self.logger.info(f"Saved captured video: {video_path}")
            self.file_created.emit("video", str(video_path))
            
            return str(video_path)
            
        except Exception as e:
            error_msg = f"Error saving captured video: {str(e)}"
            self.logger.error(f"{error_msg}\n{traceback.format_exc()}")
            self.error_occurred.emit(error_msg)
            return None
    
    def save_report(self, report_data, filename=None, hospital_name=None,
                   patient_name=None, patient_id=None):
        """Save a report to the appropriate directory
        
        Args:
            report_data: Binary report data or file-like object
            filename: Filename to use (optional)
            hospital_name: Hospital name for organization
            patient_name: Patient name
            patient_id: Patient ID
            
        Returns:
            Path to the saved report
        """
        try:
            # Get target path
            report_path = self.get_file_path("report", filename, hospital_name,
                                           patient_name, patient_id)
            
            # Ensure directory exists
            report_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save the report
            if isinstance(report_data, bytes):
                with open(report_path, "wb") as f:
                    f.write(report_data)
            elif hasattr(report_data, 'read'):
                # File-like object
                with open(report_path, "wb") as f:
                    shutil.copyfileobj(report_data, f)
            else:
                # Assume it's a path to copy from
                shutil.copy2(str(report_data), str(report_path))  # FIXED: STRING CONVERSION
            
            self.logger.info(f"Saved report: {report_path}")
            self.file_created.emit("report", str(report_path))
            
            return str(report_path)
            
        except Exception as e:
            error_msg = f"Error saving report: {str(e)}"
            self.logger.error(f"{error_msg}\n{traceback.format_exc()}")
            self.error_occurred.emit(error_msg)
            return None
    
    def import_image(self, source_path, hospital_name=None, patient_name=None, patient_id=None):
        """Import an image from an external source
        
        Args:
            source_path: Path to the source image
            hospital_name: Hospital name for organization
            patient_name: Patient name
            patient_id: Patient ID
            
        Returns:
            Path to the imported image
        """
        try:
            # Get source path as Path object
            source = Path(source_path)
            if not source.exists():
                raise FileNotFoundError(f"Source file not found: {source}")
            
            # Generate destination filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest_filename = f"imported_{timestamp}_{source.name}"
            
            # Get destination path
            dest_path = self.get_file_path("image", dest_filename, hospital_name,
                                         patient_name, patient_id, use_timestamp=False)
            
            # Copy the file
            shutil.copy2(str(source), str(dest_path))  # FIXED: STRING CONVERSION
            
            self.logger.info(f"Imported image: {source} -> {dest_path}")
            self.file_created.emit("image", str(dest_path))
            
            return str(dest_path)
            
        except Exception as e:
            error_msg = f"Error importing image: {str(e)}"
            self.logger.error(f"{error_msg}\n{traceback.format_exc()}")
            self.error_occurred.emit(error_msg)
            return None
    
    def move_image(self, image_path, destination_hospital=None, destination_patient=None):
        """Move an image to a different location
        
        Args:
            image_path: Path to the image
            destination_hospital: Destination hospital name
            destination_patient: Destination patient info (dict with name and id)
            
        Returns:
            New path to the image
        """
        try:
            # Get source path as Path object
            source = Path(image_path)
            if not source.exists():
                raise FileNotFoundError(f"Source file not found: {source}")
            
            # Determine destination
            if destination_hospital and destination_patient:
                dest_path = self.get_file_path(
                    "image", 
                    source.name,
                    destination_hospital,
                    destination_patient.get("name"),
                    destination_patient.get("id"),
                    use_timestamp=False
                )
            else:
                # Move to general images directory
                dest_dir = self.base_dirs["data"] / "images" / "imported"
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_path = dest_dir / source.name
            
            # Handle filename collisions
            if dest_path.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                name, ext = os.path.splitext(source.name)
                dest_path = dest_path.parent / f"{name}_{timestamp}{ext}"
            
            # Move the file
            shutil.move(str(source), str(dest_path))  # FIXED: STRING CONVERSION
            
            self.logger.info(f"Moved image: {source} -> {dest_path}")
            self.file_moved.emit("image", str(source), str(dest_path))
            
            return str(dest_path)
            
        except Exception as e:
            error_msg = f"Error moving image: {str(e)}"
            self.logger.error(f"{error_msg}\n{traceback.format_exc()}")
            self.error_occurred.emit(error_msg)
            return None
    
    def delete_image(self, image_path, move_to_trash=True):
        """Delete an image or move it to trash
        
        Args:
            image_path: Path to the image
            move_to_trash: Whether to move to trash instead of permanent deletion
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get source path as Path object
            source = Path(image_path)
            if not source.exists():
                raise FileNotFoundError(f"File not found: {source}")
            
            if move_to_trash:
                # Move to trash directory
                trash_dir = self.base_dirs["data"] / "trash" / "images"
                trash_dir.mkdir(parents=True, exist_ok=True)
                
                # Generate trash path
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                trash_path = trash_dir / f"{source.stem}_deleted_{timestamp}{source.suffix}"
                
                # Move to trash
                shutil.move(str(source), str(trash_path))  # FIXED: STRING CONVERSION
                self.logger.info(f"Moved image to trash: {source} -> {trash_path}")
            else:
                # Permanently delete
                os.remove(str(source))  # FIXED: STRING CONVERSION
                self.logger.info(f"Deleted image: {source}")
            
            self.file_deleted.emit("image", str(source))
            return True
            
        except Exception as e:
            error_msg = f"Error deleting image: {str(e)}"
            self.logger.error(f"{error_msg}\n{traceback.format_exc()}")
            self.error_occurred.emit(error_msg)
            return False
    
    def cleanup_temp_files(self, older_than_days=7):
        """Clean up temporary files older than specified days
        
        Args:
            older_than_days: Delete files older than this many days
            
        Returns:
            Number of files deleted
        """
        try:
            temp_dir = self.base_dirs["temp"]
            deleted_count = 0
            
            # Calculate cutoff time
            cutoff_time = datetime.now().timestamp() - (older_than_days * 86400)
            
            for item in temp_dir.glob("**/*"):
                if item.is_file():
                    # Check file age
                    file_time = item.stat().st_mtime
                    if file_time < cutoff_time:
                        os.remove(str(item))  # FIXED: STRING CONVERSION
                        deleted_count += 1
            
            self.logger.info(f"Cleaned up {deleted_count} temporary files")
            return deleted_count
            
        except Exception as e:
            error_msg = f"Error cleaning up temp files: {str(e)}"
            self.logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return 0
    
    def create_backup(self, include_media=False):
        """Create a backup of important data
        
        Args:
            include_media: Whether to include media files in backup
            
        Returns:
            Path to the backup archive
        """
        try:
            import zipfile
            
            # Create backup directory
            backup_dir = self.base_dirs["backups"]
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"backup_{timestamp}.zip"
            
            # Create zip file
            with zipfile.ZipFile(str(backup_path), "w", zipfile.ZIP_DEFLATED) as zipf:  # FIXED: STRING CONVERSION
                # Add database files
                db_dir = self.base_dirs["database"]
                if db_dir.exists():
                    for item in db_dir.glob("*.db"):
                        zipf.write(str(item), f"database/{item.name}")  # FIXED: STRING CONVERSION
                
                # Add settings files
                settings_dir = self.base_dirs["settings"]
                if settings_dir.exists():
                    for item in settings_dir.glob("*.json"):
                        zipf.write(str(item), f"settings/{item.name}")  # FIXED: STRING CONVERSION
                
                # Add hospital reports
                hospitals_dir = self.base_dirs["hospitals"]
                if hospitals_dir.exists():
                    for hospital_dir in hospitals_dir.iterdir():
                        if hospital_dir.is_dir():
                            reports_dir = hospital_dir / "Reports"
                            if reports_dir.exists():
                                for report in reports_dir.glob("**/*.pdf"):
                                    rel_path = report.relative_to(hospitals_dir)
                                    zipf.write(str(report), f"hospitals/{rel_path}")  # FIXED: STRING CONVERSION
                
                # Add media if requested
                if include_media:
                    if hospitals_dir.exists():
                        for hospital_dir in hospitals_dir.iterdir():
                            if hospital_dir.is_dir():
                                media_dir = hospital_dir / "Media"
                                if media_dir.exists():
                                    for media_file in media_dir.glob("**/*"):
                                        if media_file.is_file():
                                            rel_path = media_file.relative_to(hospitals_dir)
                                            zipf.write(str(media_file), f"hospitals/{rel_path}")  # FIXED: STRING CONVERSION
            
            self.logger.info(f"Created backup: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            error_msg = f"Error creating backup: {str(e)}"
            self.logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return None
    
    def cleanup(self):
        """Clean up file resources"""
        try:
            # Remove any temporary files
            temp_dir = self.base_dirs["temp"]
            if temp_dir.exists():
                for item in temp_dir.glob("*.*"):
                    try:
                        if item.is_file():
                            item.unlink()
                    except Exception as e:
                        self.logger.warning(f"Failed to remove temp file {item}: {e}")
            
            self.logger.info("File resources cleaned up")
            return True
            
        except Exception as e:
            error_msg = f"Error cleaning up file resources: {str(e)}"
            self.logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False