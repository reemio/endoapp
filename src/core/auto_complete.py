# COMPLETE AUTO-COMPLETE SYSTEM IMPLEMENTATION
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtWidgets import QCompleter, QComboBox, QLineEdit
import logging
from pathlib import Path
import json


class AutoCompleteManager(QObject):
    """Manager for auto-completion functionality in the application"""
    
    # SIGNALS
    entries_updated = Signal(str, list)  # field_name, entries
    
    def __init__(self, db_manager, parent=None):
        """Initialize the auto-complete manager
        
        Args:
            db_manager: DatabaseManager instance for access to history
            parent: Parent QObject
        """
        super().__init__(parent)
        self.db = db_manager
        self.setup_logging()
        self.load_common_entries()
        self.completer_widgets = {}  # Maps field_names to widgets
    
    def setup_logging(self):
        """Setup logging configuration"""
        self.logger = logging.getLogger("AutoCompleteManager")
        
        if not self.logger.handlers:
            log_path = Path("data/logs/autocomplete.log")
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_path)
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            file_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
            self.logger.setLevel(logging.INFO)
    
    def load_common_entries(self):
        """Load common entries from file"""
        try:
            common_entries_path = Path("data/settings/common_entries.json")
            
            if common_entries_path.exists():
                with open(common_entries_path, "r") as f:
                    self.common_entries = json.load(f)
            else:
                # Initialize with default common entries
                self.common_entries = {
                    "hospital_name": [
                        "Medical Center",
                        "General Hospital",
                        "University Hospital",
                        "Community Health Center",
                        "Specialty Clinic"
                    ],
                    "doctor": [
                        "Dr. Smith",
                        "Dr. Johnson",
                        "Dr. Williams",
                        "Dr. Brown",
                        "Dr. Davis"
                    ],
                    "referring_doctor": [
                        "Dr. Anderson",
                        "Dr. Wilson",
                        "Dr. Martinez",
                        "Dr. Taylor",
                        "Dr. Thomas"
                    ],
                    "designation": [
                        "Consultant Surgeon",
                        "Specialist",
                        "Resident",
                        "Attending Physician",
                        "Chief of Medicine"
                    ],
                    "medication": [
                        "Sedation + Local Spray",
                        "Local Spray Only",
                        "None",
                        "Midazolam",
                        "Propofol"
                    ],
                    "common_findings": [
                        "Normal examination",
                        "Mild inflammation",
                        "Moderate inflammation",
                        "Severe inflammation",
                        "Ulceration",
                        "Polyps",
                        "Erosive changes",
                        "Nodular mucosa",
                        "Vascular pattern normal",
                        "Vascular pattern distorted"
                    ],
                    "common_conclusions": [
                        "Normal study",
                        "Inflammatory changes",
                        "Erosive disease",
                        "Polyps detected",
                        "Suspected malignancy",
                        "Vascular abnormalities",
                        "Anatomical variant"
                    ],
                    "common_recommendations": [
                        "No follow-up needed",
                        "Repeat examination in 6 months",
                        "Repeat examination in 1 year",
                        "Biopsy recommended",
                        "Medical therapy recommended",
                        "Surgical consultation",
                        "Further imaging studies recommended"
                    ]
                }
                
                # Create file with defaults
                common_entries_path.parent.mkdir(parents=True, exist_ok=True)
                with open(common_entries_path, "w") as f:
                    json.dump(self.common_entries, f, indent=4)
            
            self.logger.info("Common entries loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Error loading common entries: {e}")
            
            # Fallback to empty defaults
            self.common_entries = {
                "hospital_name": [],
                "doctor": [],
                "referring_doctor": [],
                "designation": [],
                "medication": [],
                "common_findings": [],
                "common_conclusions": [],
                "common_recommendations": []
            }
    
    def save_common_entries(self):
        """Save common entries to file"""
        try:
            common_entries_path = Path("data/settings/common_entries.json")
            common_entries_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(common_entries_path, "w") as f:
                json.dump(self.common_entries, f, indent=4)
                
            self.logger.info("Common entries saved successfully")
            
        except Exception as e:
            self.logger.error(f"Error saving common entries: {e}")
    
    def add_common_entry(self, field_name, entry):
        """Add a new common entry
        
        Args:
            field_name: Field to add entry for
            entry: Entry to add
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not entry or not field_name:
                return False
                
            if field_name not in self.common_entries:
                self.common_entries[field_name] = []
                
            # Add only if not already in the list
            if entry not in self.common_entries[field_name]:
                self.common_entries[field_name].append(entry)
                self.save_common_entries()
                self.entries_updated.emit(field_name, self.get_entries(field_name))
                self.logger.info(f"Added common entry for {field_name}: {entry}")
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error adding common entry: {e}")
            return False
    
    def remove_common_entry(self, field_name, entry):
        """Remove a common entry
        
        Args:
            field_name: Field to remove entry from
            entry: Entry to remove
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not field_name in self.common_entries:
                return False
                
            if entry in self.common_entries[field_name]:
                self.common_entries[field_name].remove(entry)
                self.save_common_entries()
                self.entries_updated.emit(field_name, self.get_entries(field_name))
                self.logger.info(f"Removed common entry for {field_name}: {entry}")
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error removing common entry: {e}")
            return False
    
    def get_entries(self, field_name, limit=15):
        """Get auto-complete entries for a field
        
        Args:
            field_name: Field to get entries for
            limit: Maximum number of entries to return
            
        Returns:
            List of entries
        """
        try:
            entries = []
            
            # Add common entries first
            if field_name in self.common_entries:
                entries.extend(self.common_entries[field_name])
                
            # Then add database history entries
            if hasattr(self.db, 'get_dropdown_history'):
                history_entries = self.db.get_dropdown_history(field_name, limit)
                
                # Add unique entries from history
                for entry in history_entries:
                    if entry and entry not in entries:
                        entries.append(entry)
            
            # Limit total entries
            return entries[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting entries: {e}")
            return []
    
    def setup_completer(self, widget, field_name):
        """Setup auto-completion for a widget
        
        Args:
            widget: QComboBox or QLineEdit widget
            field_name: Field name for entries
            
        Returns:
            True if successful, False otherwise
        """
        try:
            entries = self.get_entries(field_name)
            
            # Create completer
            completer = QCompleter(entries)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            
            # Apply to widget
            if isinstance(widget, QComboBox):
                widget.clear()
                widget.addItems(entries)
                widget.setCompleter(completer)
                
                # Connect signal for adding new entries
                if hasattr(widget, 'currentTextChanged'):
                    widget.currentTextChanged.connect(
                        lambda text: self.handle_text_entered(field_name, text)
                    )
                
            elif isinstance(widget, QLineEdit):
                widget.setCompleter(completer)
                
                # Connect signal for adding new entries
                if hasattr(widget, 'editingFinished'):
                    widget.editingFinished.connect(
                        lambda: self.handle_text_entered(field_name, widget.text())
                    )
            
            # Store reference to update later
            self.completer_widgets[field_name] = widget
            
            # Connect signal to update widget when entries change
            self.entries_updated.connect(self.update_widget_entries)
            
            self.logger.info(f"Setup completer for {field_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting up completer: {e}")
            return False
    
    def update_widget_entries(self, field_name, entries):
        """Update entries for a specific widget
        
        Args:
            field_name: Field name to update
            entries: New entries
        """
        try:
            if field_name not in self.completer_widgets:
                return
                
            widget = self.completer_widgets[field_name]
            
            # Create new completer
            completer = QCompleter(entries)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            
            # Update widget
            if isinstance(widget, QComboBox):
                # Remember current text
                current_text = widget.currentText()
                
                widget.clear()
                widget.addItems(entries)
                
                # Restore current text
                if current_text:
                    index = widget.findText(current_text)
                    if index >= 0:
                        widget.setCurrentIndex(index)
                    else:
                        widget.setEditText(current_text)
                
                widget.setCompleter(completer)
                
            elif isinstance(widget, QLineEdit):
                widget.setCompleter(completer)
                
        except Exception as e:
            self.logger.error(f"Error updating widget entries: {e}")
    
    def handle_text_entered(self, field_name, text):
        """Handle text entered in a widget
        
        Args:
            field_name: Field name
            text: Entered text
        """
        if not text or not field_name:
            return
            
        try:
            # Update in database history
            if hasattr(self.db, 'update_dropdown_history'):
                self.db.update_dropdown_history(field_name, text)
                
        except Exception as e:
            self.logger.error(f"Error handling text entered: {e}")
    
    # SPECIALIZED AUTO-COMPLETE METHODS
    
    def setup_medical_text_completers(self, findings_widget, conclusions_widget, recommendations_widget):
        """Setup completers for medical text fields
        
        Args:
            findings_widget: QTextEdit for findings
            conclusions_widget: QTextEdit for conclusions
            recommendations_widget: QTextEdit for recommendations
        """
        # This requires custom implementation for QTextEdit widgets
        # Basic approach is to handle keyPressEvent and show a popup with suggestions
        pass
    
    def get_common_text_blocks(self, field_name):
        """Get common text blocks for a field
        
        Args:
            field_name: Field name (common_findings, common_conclusions, common_recommendations)
            
        Returns:
            List of text blocks
        """
        key_map = {
            "findings": "common_findings",
            "conclusions": "common_conclusions",
            "recommendations": "common_recommendations"
        }
        
        lookup_key = key_map.get(field_name, field_name)
        
        return self.common_entries.get(lookup_key, [])
    
    def add_common_text_block(self, field_name, text_block):
        """Add a common text block
        
        Args:
            field_name: Field name (findings, conclusions, recommendations)
            text_block: Text block to add
            
        Returns:
            True if successful, False otherwise
        """
        key_map = {
            "findings": "common_findings",
            "conclusions": "common_conclusions",
            "recommendations": "common_recommendations"
        }
        
        lookup_key = key_map.get(field_name, field_name)
        
        return self.add_common_entry(lookup_key, text_block)