# SEARCH AND FIND FUNCTIONALITY IMPLEMENTATION
from PySide6.QtCore import QObject, Signal, Qt, QDate
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QLabel, QLineEdit, QComboBox, QDateEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QCheckBox, QGroupBox, QAbstractItemView
)
from pathlib import Path
import logging
from datetime import datetime, timedelta


class SearchManager(QObject):
    """Search functionality manager for Endoscopy Reporting application"""
    
    RECENT_PATIENT_LIMIT = 0  # 0 = no limit
    RECENT_REPORT_LIMIT = 0
    
    # SIGNALS
    patient_selected = Signal(str)  # Emits patient_id
    report_selected = Signal(str)  # Emits report_id
    
    def __init__(self, db_manager, parent=None):
        """Initialize the search manager
        
        Args:
            db_manager: DatabaseManager instance
            parent: Parent QObject
        """
        super().__init__(parent)
        self.db = db_manager
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging configuration"""
        self.logger = logging.getLogger("SearchManager")
        
        if not self.logger.handlers:
            log_path = Path("data/logs/search.log")
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_path)
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            file_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
            self.logger.setLevel(logging.INFO)
    
    def search_patients(self, criteria, limit=None, offset=None):
        """Search for patients based on criteria
        
        Args:
            criteria: Dictionary of search criteria
            limit: Optional maximum number of records
            offset: Optional offset for pagination
            
        Returns:
            List of matching patient records
        """
        try:
            self.logger.info(f"Searching patients with criteria: {criteria}")
            results = self.db.search_patients(criteria, limit=limit, offset=offset)
            self.logger.info(f"Found {len(results)} patients")
            return results
        except Exception as e:
            self.logger.error(f"Error searching patients: {e}")
            return []
    
    def search_reports(self, criteria, limit=None, offset=None):
        """Search for reports based on criteria
        
        Args:
            criteria: Dictionary of search criteria
            
        Returns:
            List of matching report records
        """
        try:
            self.logger.info(f"Searching reports with criteria: {criteria}")
            results = self.db.search_reports(criteria, limit=limit, offset=offset)
            self.logger.info(f"Found {len(results)} reports")
            return results
        except Exception as e:
            self.logger.error(f"Error searching reports: {e}")
            return []
    
    def get_recent_patients(self, limit=10):
        """Get most recently added patients
        
        Args:
            limit: Maximum number of patients to return
            
        Returns:
            List of recent patient records
        """
        try:
            # Empty criteria returns recent patients
            effective_limit = limit if limit and limit > 0 else None
            results = self.db.search_patients({}, limit=effective_limit)
            return results
        except Exception as e:
            self.logger.error(f"Error getting recent patients: {e}")
            return []
    
    def get_recent_reports(self, limit=10):
        """Get most recently added reports
        
        Args:
            limit: Maximum number of reports to return
            
        Returns:
            List of recent report records
        """
        try:
            # Empty criteria returns recent reports
            effective_limit = limit if limit and limit > 0 else None
            results = self.db.search_reports({}, limit=effective_limit)
            return results
        except Exception as e:
            self.logger.error(f"Error getting recent reports: {e}")
            return []
    
    def show_patient_search_dialog(self, parent=None):
        """Show patient search dialog
        
        Args:
            parent: Parent widget
            
        Returns:
            Selected patient_id or None if cancelled
        """
        dialog = PatientSearchDialog(self.db, parent, recent_limit=self.RECENT_PATIENT_LIMIT)
        if dialog.exec() == QDialog.Accepted and dialog.selected_patient_id:
            self.patient_selected.emit(dialog.selected_patient_id)
            return dialog.selected_patient_id
        return None
    
    def show_report_search_dialog(self, parent=None):
        """Show report search dialog
        
        Args:
            parent: Parent widget
            
        Returns:
            Selected report_id or None if cancelled
        """
        dialog = ReportSearchDialog(self.db, parent, recent_limit=self.RECENT_REPORT_LIMIT)
        if dialog.exec() == QDialog.Accepted and dialog.selected_report_id:
            self.report_selected.emit(dialog.selected_report_id)
            return dialog.selected_report_id
        return None


class PatientSearchDialog(QDialog):
    """Dialog for searching and selecting patients"""
    
    def __init__(self, db_manager, parent=None, recent_limit=200):
        """Initialize the patient search dialog
        
        Args:
            db_manager: DatabaseManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.db = db_manager
        self.selected_patient_id = None
        self.recent_limit = recent_limit
        self.setup_ui()
        self.load_recent_patients()
    
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Patient Search")
        self.setMinimumWidth(900)
        self.setMinimumHeight(520)
        
        layout = QVBoxLayout(self)
        
        # SEARCH CRITERIA SECTION
        criteria_group = QGroupBox("Search Criteria")
        criteria_layout = QGridLayout(criteria_group)
        criteria_layout.setHorizontalSpacing(12)
        criteria_layout.setVerticalSpacing(10)
        criteria_layout.setColumnStretch(0, 0)
        criteria_layout.setColumnStretch(1, 1)
        criteria_layout.setColumnStretch(2, 0)
        criteria_layout.setColumnStretch(3, 1)
        
        # Patient ID
        criteria_layout.addWidget(QLabel("Patient ID:"), 0, 0)
        self.patient_id_edit = QLineEdit()
        self.patient_id_edit.setPlaceholderText("e.g. 0007/25")
        criteria_layout.addWidget(self.patient_id_edit, 0, 1)
        
        # Patient Name
        criteria_layout.addWidget(QLabel("Name:"), 0, 2)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Full or partial name")
        criteria_layout.addWidget(self.name_edit, 0, 3)
        
        # Doctor
        criteria_layout.addWidget(QLabel("Doctor:"), 1, 0)
        self.doctor_edit = QLineEdit()
        self.doctor_edit.setPlaceholderText("Doctor or consultant name")
        criteria_layout.addWidget(self.doctor_edit, 1, 1)
        
        # Date Range
        criteria_layout.addWidget(QLabel("Date From:"), 1, 2)
        self.date_from_edit = QDateEdit(QDate.currentDate().addMonths(-1))
        self.date_from_edit.setCalendarPopup(True)
        self.date_from_edit.setDisplayFormat("dd/MM/yyyy")
        criteria_layout.addWidget(self.date_from_edit, 1, 3)
        
        # Hospital filter
        criteria_layout.addWidget(QLabel("Hospital:"), 2, 0)
        self.hospital_edit = QLineEdit()
        self.hospital_edit.setPlaceholderText("Hospital or facility name")
        criteria_layout.addWidget(self.hospital_edit, 2, 1)
        
        criteria_layout.addWidget(QLabel("Date To:"), 2, 2)
        self.date_to_edit = QDateEdit(QDate.currentDate())
        self.date_to_edit.setCalendarPopup(True)
        self.date_to_edit.setDisplayFormat("dd/MM/yyyy")
        criteria_layout.addWidget(self.date_to_edit, 2, 3)
        
        # Use Date Range checkbox
        self.use_date_checkbox = QCheckBox("Use Date Range")
        criteria_layout.addWidget(self.use_date_checkbox, 3, 0, 1, 2)
        self.use_date_checkbox.toggled.connect(self.handle_date_toggle)
        self.handle_date_toggle(False)
        
        # Search button
        button_layout = QHBoxLayout()
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.perform_search)
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_search)
        button_layout.addWidget(self.search_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()
        
        criteria_layout.addLayout(button_layout, 4, 0, 1, 4)
        
        layout.addWidget(criteria_group)
        
        self.results_summary_label = QLabel()
        self.results_summary_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.results_summary_label)
        
        # RESULTS TABLE
        self.results_table = QTableWidget(0, 7)
        self.results_table.setHorizontalHeaderLabels([
            "Patient ID", "Hospital", "Name", "Gender", "Age", "Doctor", "Date"
        ])
        header_font = self.results_table.horizontalHeader().font()
        header_font.setBold(True)
        self.results_table.horizontalHeader().setFont(header_font)
        self.results_table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.results_table.horizontalHeader().setMinimumHeight(30)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setShowGrid(True)
        self.results_table.verticalHeader().setDefaultSectionSize(34)
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.SingleSelection)
        self.results_table.doubleClicked.connect(self.handle_row_double_clicked)
        layout.addWidget(self.results_table)
        
        # BUTTON ROW
        button_row = QHBoxLayout()
        self.select_button = QPushButton("Select")
        self.select_button.clicked.connect(self.handle_select_clicked)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_row.addStretch()
        button_row.addWidget(self.select_button)
        button_row.addWidget(self.cancel_button)
        
        layout.addLayout(button_row)
    
    def load_recent_patients(self):
        """Load recent patients into the results table"""
        try:
            # Empty criteria gets recent patients
            effective_limit = self.recent_limit if self.recent_limit and self.recent_limit > 0 else None
            patients = self.db.search_patients({}, limit=effective_limit)
            self.populate_results(
                patients,
                context="recent",
                limited=bool(effective_limit)
            )
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error loading recent patients: {e}")
    
    def perform_search(self):
        """Perform patient search based on criteria"""
        try:
            criteria = {}
            
            # Collect search criteria
            patient_id = self.patient_id_edit.text().strip()
            if patient_id:
                criteria["patient_id"] = patient_id
                
            name = self.name_edit.text().strip()
            if name:
                criteria["name"] = name
                
            doctor = self.doctor_edit.text().strip()
            if doctor:
                criteria["doctor"] = doctor
            
            hospital = self.hospital_edit.text().strip()
            if hospital:
                criteria["hospital"] = hospital
                
            # Add date range if checked
            if self.use_date_checkbox.isChecked():
                criteria["date_from"] = self.date_from_edit.date().toString("yyyy-MM-dd")
                criteria["date_to"] = self.date_to_edit.date().toString("yyyy-MM-dd")
            
            # Perform search
            patients = self.db.search_patients(criteria)
            self.populate_results(patients, context="search")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error performing search: {e}")
    
    def clear_search(self):
        """Clear search criteria and reload recent patients"""
        self.patient_id_edit.clear()
        self.name_edit.clear()
        self.doctor_edit.clear()
        self.hospital_edit.clear()
        self.use_date_checkbox.setChecked(False)
        
        # Reset date range to default
        self.date_from_edit.setDate(QDate.currentDate().addMonths(-1))
        self.date_to_edit.setDate(QDate.currentDate())
        
        # Reload recent patients
        self.load_recent_patients()
    
    def populate_results(self, patients, context="search", limited=False):
        """Populate the results table with patients
        
        Args:
            patients: List of patient records
        """
        # Clear table
        self.results_table.setSortingEnabled(False)
        self.results_table.setRowCount(0)
        
        # Add patients to table
        for row, patient in enumerate(patients):
            self.results_table.insertRow(row)
            
            # Add data to cells
            self.results_table.setItem(row, 0, QTableWidgetItem(patient.get("patient_id", "")))
            self.results_table.setItem(row, 1, QTableWidgetItem(patient.get("hospital_name", "")))
            self.results_table.setItem(row, 2, QTableWidgetItem(patient.get("name", "")))
            self.results_table.setItem(row, 3, QTableWidgetItem(patient.get("gender", "")))
            self.results_table.setItem(row, 4, QTableWidgetItem(str(patient.get("age", ""))))
            self.results_table.setItem(row, 5, QTableWidgetItem(patient.get("doctor", "")))
            
            # Format date for display
            date_str = patient.get("visit_date") or patient.get("date_created", "")
            if date_str:
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                    formatted_date = date_obj.strftime("%d/%m/%Y %H:%M")
                    self.results_table.setItem(row, 6, QTableWidgetItem(formatted_date))
                except Exception:
                    self.results_table.setItem(row, 6, QTableWidgetItem(date_str))
            else:
                self.results_table.setItem(row, 6, QTableWidgetItem(""))
            
        self.results_table.setSortingEnabled(True)
        self.update_results_summary(len(patients), context=context, limited=limited)
    
    def handle_row_double_clicked(self, index):
        """Handle double-click on a result row
        
        Args:
            index: Table model index
        """
        self.handle_select_clicked()

    def handle_date_toggle(self, checked):
        """Enable/disable date pickers based on checkbox."""
        self.date_from_edit.setEnabled(checked)
        self.date_to_edit.setEnabled(checked)
        if checked:
            self.date_from_edit.setStyleSheet("")
            self.date_to_edit.setStyleSheet("")

    def update_results_summary(self, count, context="search", limited=False):
        """Update the summary label and dialog title."""
        if context == "recent":
            if count == 0:
                summary = "No patients have been saved yet."
            elif limited and self.recent_limit and count >= self.recent_limit:
                summary = f"Showing latest {count} patients (refine your search to narrow results)"
            else:
                summary = f"Showing latest {count} patient{'s' if count != 1 else ''}"
        else:
            if count == 0:
                summary = "No patients match the current filters."
            else:
                summary = f"{count} patient{'s' if count != 1 else ''} match the current filters."
        self.results_summary_label.setText(summary)
        self.setWindowTitle(f"Patient Search - {count} result{'s' if count != 1 else ''}")
    
    def handle_select_clicked(self):
        """Handle select button clicked"""
        selected_rows = self.results_table.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a patient from the results.")
            return
            
        # Get patient ID from the first cell (column 0)
        row = selected_rows[0].row()
        patient_id_item = self.results_table.item(row, 0)
        
        if patient_id_item and patient_id_item.text():
            self.selected_patient_id = patient_id_item.text()
            self.accept()
        else:
            QMessageBox.warning(self, "Invalid Selection", "The selected row has no patient ID.")


class ReportSearchDialog(QDialog):
    """Dialog for searching and selecting reports"""
    
    def __init__(self, db_manager, parent=None, recent_limit=200):
        """Initialize the report search dialog
        
        Args:
            db_manager: DatabaseManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.db = db_manager
        self.selected_report_id = None
        self.recent_limit = recent_limit
        self.setup_ui()
        self.load_recent_reports()
    
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Report Search")
        self.setMinimumWidth(800)
        self.setMinimumHeight(500)
        
        layout = QVBoxLayout(self)
        
        # SEARCH CRITERIA SECTION
        criteria_group = QGroupBox("Search Criteria")
        criteria_layout = QGridLayout(criteria_group)
        
        # Report ID
        criteria_layout.addWidget(QLabel("Report ID:"), 0, 0)
        self.report_id_edit = QLineEdit()
        criteria_layout.addWidget(self.report_id_edit, 0, 1)
        
        # Patient ID
        criteria_layout.addWidget(QLabel("Patient ID:"), 0, 2)
        self.patient_id_edit = QLineEdit()
        criteria_layout.addWidget(self.patient_id_edit, 0, 3)
        
        # Status
        criteria_layout.addWidget(QLabel("Status:"), 1, 0)
        self.status_combo = QComboBox()
        self.status_combo.addItem("Any", "")
        self.status_combo.addItem("Draft", "draft")
        self.status_combo.addItem("Final", "final")
        self.status_combo.addItem("Amended", "amended")
        criteria_layout.addWidget(self.status_combo, 1, 1)
        
        # Date Range
        criteria_layout.addWidget(QLabel("Date From:"), 1, 2)
        self.date_from_edit = QDateEdit(QDate.currentDate().addMonths(-1))
        self.date_from_edit.setCalendarPopup(True)
        criteria_layout.addWidget(self.date_from_edit, 1, 3)
        
        criteria_layout.addWidget(QLabel("Date To:"), 2, 2)
        self.date_to_edit = QDateEdit(QDate.currentDate())
        self.date_to_edit.setCalendarPopup(True)
        criteria_layout.addWidget(self.date_to_edit, 2, 3)
        
        # Use Date Range checkbox
        self.use_date_checkbox = QCheckBox("Use Date Range")
        criteria_layout.addWidget(self.use_date_checkbox, 2, 0, 1, 2)
        
        # Search button
        button_layout = QHBoxLayout()
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.perform_search)
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_search)
        button_layout.addWidget(self.search_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()
        
        criteria_layout.addLayout(button_layout, 3, 0, 1, 4)
        
        layout.addWidget(criteria_group)
        
        # RESULTS TABLE
        self.results_table = QTableWidget(0, 6)
        self.results_table.setHorizontalHeaderLabels([
            "Report ID", "Patient ID", "Date", "Status", "Findings", "Conclusions"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.SingleSelection)
        self.results_table.doubleClicked.connect(self.handle_row_double_clicked)
        layout.addWidget(self.results_table)
        
        # BUTTON ROW
        button_row = QHBoxLayout()
        self.select_button = QPushButton("Select")
        self.select_button.clicked.connect(self.handle_select_clicked)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_row.addStretch()
        button_row.addWidget(self.select_button)
        button_row.addWidget(self.cancel_button)
        
        layout.addLayout(button_row)
    
    def load_recent_reports(self):
        """Load recent reports into the results table"""
        try:
            # Empty criteria gets recent reports
            effective_limit = self.recent_limit if self.recent_limit and self.recent_limit > 0 else None
            reports = self.db.search_reports({}, limit=effective_limit)
            self.populate_results(reports)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error loading recent reports: {e}")
    
    def perform_search(self):
        """Perform report search based on criteria"""
        try:
            criteria = {}
            
            # Collect search criteria
            report_id = self.report_id_edit.text().strip()
            if report_id:
                criteria["report_id"] = report_id
                
            patient_id = self.patient_id_edit.text().strip()
            if patient_id:
                criteria["patient_id"] = patient_id
                
            status = self.status_combo.currentData()
            if status:
                criteria["status"] = status
                
            # Add date range if checked
            if self.use_date_checkbox.isChecked():
                criteria["date_from"] = self.date_from_edit.date().toString("yyyy-MM-dd")
                criteria["date_to"] = self.date_to_edit.date().toString("yyyy-MM-dd")
            
            # Perform search
            reports = self.db.search_reports(criteria)
            self.populate_results(reports)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error performing search: {e}")
    
    def clear_search(self):
        """Clear search criteria and reload recent reports"""
        self.report_id_edit.clear()
        self.patient_id_edit.clear()
        self.status_combo.setCurrentIndex(0)
        self.use_date_checkbox.setChecked(False)
        
        # Reset date range to default
        self.date_from_edit.setDate(QDate.currentDate().addMonths(-1))
        self.date_to_edit.setDate(QDate.currentDate())
        
        # Reload recent reports
        self.load_recent_reports()
    
    def populate_results(self, reports):
        """Populate the results table with reports
        
        Args:
            reports: List of report records
        """
        # Clear table
        self.results_table.setRowCount(0)
        
        # Add reports to table
        for row, report in enumerate(reports):
            self.results_table.insertRow(row)
            
            # Add data to cells
            self.results_table.setItem(row, 0, QTableWidgetItem(report.get("report_id", "")))
            self.results_table.setItem(row, 1, QTableWidgetItem(report.get("patient_id", "")))
            
            # Format date for display
            date_str = report.get("report_date", "")
            if date_str:
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                    formatted_date = date_obj.strftime("%d/%m/%Y %H:%M")
                    self.results_table.setItem(row, 2, QTableWidgetItem(formatted_date))
                except:
                    self.results_table.setItem(row, 2, QTableWidgetItem(date_str))
            
            # Status with capitalization
            status = report.get("status", "").capitalize()
            self.results_table.setItem(row, 3, QTableWidgetItem(status))
            
            # Truncate findings and conclusions for display
            findings = report.get("findings", "")
            if len(findings) > 50:
                findings = findings[:47] + "..."
            self.results_table.setItem(row, 4, QTableWidgetItem(findings))
            
            conclusions = report.get("conclusions", "")
            if len(conclusions) > 50:
                conclusions = conclusions[:47] + "..."
            self.results_table.setItem(row, 5, QTableWidgetItem(conclusions))
            
        # Update status message
        self.setWindowTitle(f"Report Search - {len(reports)} results")
    
    def handle_row_double_clicked(self, index):
        """Handle double-click on a result row
        
        Args:
            index: Table model index
        """
        self.handle_select_clicked()
    
    def handle_select_clicked(self):
        """Handle select button clicked"""
        selected_rows = self.results_table.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a report from the results.")
            return
            
        # Get report ID from the first cell (column 0)
        row = selected_rows[0].row()
        report_id_item = self.results_table.item(row, 0)
        
        if report_id_item and report_id_item.text():
            self.selected_report_id = report_id_item.text()
            self.accept()
        else:
            QMessageBox.warning(self, "Invalid Selection", "The selected row has no report ID.")
