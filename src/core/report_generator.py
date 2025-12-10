# COMPLETE REPORT_GENERATOR.PY - FIXED AND WORKING
# FILE: src/core/report_generator.py

from PySide6.QtCore import QObject, Signal, QDateTime
from PySide6.QtWidgets import QFileDialog, QProgressDialog, QMessageBox
from PySide6.QtGui import QPainter, QPdfWriter, QPageLayout, QPageSize
import logging
from pathlib import Path
from datetime import datetime
import traceback
import os
import platform

# Import the PDF generation function from your utils/pdf_generator.py
from src.utils.pdf_generator import generate_endoscopy_pdf

class ReportGenerator(QObject):
    """PDF Report Generator for Endoscopy reporting system"""
    
    # SIGNALS
    report_generated = Signal(str)  # Emits report path
    generation_failed = Signal(str)  # Emits error message
    progress_updated = Signal(int)  # Emits progress percentage
    
    def __init__(self, db_manager=None, parent=None):
        """Initialize the report generator
        
        Args:
            db_manager: DatabaseManager instance for data access (optional)
            parent: Parent QObject
        """
        super().__init__(parent)
        self.db = db_manager
        self.setup_directories()
        self.configure_logging()
    
    def setup_directories(self):
        """Create necessary directories for report storage"""
        self.reports_path = Path("data/reports")
        self.reports_path.mkdir(parents=True, exist_ok=True)
        
        # Create dated subdirectories for better organization
        current_date = datetime.now().strftime("%Y-%m")
        self.current_reports_path = self.reports_path / current_date
        self.current_reports_path.mkdir(parents=True, exist_ok=True)
        
        # Create directories for different report states
        self.draft_reports_path = self.reports_path / "drafts"
        self.final_reports_path = self.reports_path / "final"
        self.exported_reports_path = self.reports_path / "exported"
        
        for path in [self.draft_reports_path, self.final_reports_path, 
                     self.exported_reports_path]:
            path.mkdir(parents=True, exist_ok=True)
    
    def configure_logging(self):
        """Setup logging for the report generator"""
        self.logger = logging.getLogger("ReportGenerator")
        
        if not self.logger.handlers:
            log_path = Path("data/logs/reports.log")
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_path)
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            file_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
            self.logger.setLevel(logging.INFO)
            
            self.logger.info("Report Generator initialized")
    
    # REPORT GENERATION METHODS
    
    def generate_report(self, report_id=None, patient_id=None, custom_path=None, is_final=False):
        """Generate a PDF report from database
        
        Args:
            report_id: ID of the report to generate (optional)
            patient_id: ID of the patient if report_id not provided (optional)
            custom_path: Custom save path for the PDF (optional)
            is_final: Whether this is a final report (default: False)
            
        Returns:
            Path to the generated PDF report or None if failed
        """
        try:
            # Track generation progress
            self.progress_updated.emit(10)
            
            # Determine which report to generate
            if not report_id and not patient_id:
                raise ValueError("Either report_id or patient_id must be provided")
            
            report_data = None
            if report_id and self.db:
                report_data = self.db.get_report(report_id=report_id)
            elif patient_id and self.db:
                report_data = self.db.get_report(patient_id=patient_id)
            
            if not report_data:
                raise ValueError(f"No report found for the provided ID")
            
            # Get actual report ID for further processing
            report_id = report_data["report_id"]
            patient_id = report_data["patient_id"]
            
            self.progress_updated.emit(30)
            
            # Get patient data
            patient_data = None
            if self.db:
                patient_data = self.db.get_patient(patient_id)
            
            if not patient_data:
                raise ValueError(f"Patient not found: {patient_id}")
            
            self.progress_updated.emit(50)
            
            # Get images for the report
            images_data = []
            if self.db:
                images_data = self.db.get_report_images(report_id)
            
            self.progress_updated.emit(70)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if custom_path:
                filename = Path(custom_path)
            else:
                # Determine appropriate directory
                current_date = datetime.now().strftime("%Y-%m")
                base_dir = self.final_reports_path if is_final else self.draft_reports_path
                patient_name = patient_data.get("name", "").replace(" ", "_").lower()
                
                filename = base_dir / current_date / f"report_{patient_id}_{patient_name}_{timestamp}.pdf"
                filename.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare data for the PDF generation
            findings = report_data.get("findings", "")
            conclusions = report_data.get("conclusions", "")
            recommendations = report_data.get("recommendations", "")
            
            # Add derived fields to patient data
            complete_patient_data = {**patient_data}
            complete_patient_data["report_title"] = report_data.get("report_title", "ENDOSCOPY REPORT")
            complete_patient_data["indication"] = report_data.get("indication", "")
            complete_patient_data["Date"] = datetime.now().strftime("%d/%m/%Y")
            
            # Format doctor and designation if needed
            if "doctor" in patient_data and "designation" in patient_data:
                complete_patient_data["Doctor"] = patient_data["doctor"].upper()
                complete_patient_data["Designation"] = patient_data["designation"].upper()
            
            self.progress_updated.emit(80)
            
            # Generate the PDF
            self.logger.info(f"Generating report for patient {patient_id}")
            pdf_path = generate_endoscopy_pdf(
                complete_patient_data,
                findings,
                conclusions,
                recommendations,
                images_data,
                str(filename)
            )
            
            self.progress_updated.emit(100)
            self.logger.info(f"Report generated successfully: {pdf_path}")
            
            # Update database if this is a final report
            if is_final and self.db:
                self.db.update_report_status(report_id, "final")
            
            # Emit success signal
            self.report_generated.emit(pdf_path)
            return pdf_path
            
        except Exception as e:
            error_msg = f"Report generation failed: {str(e)}"
            self.logger.error(f"{error_msg}\n{traceback.format_exc()}")
            self.generation_failed.emit(error_msg)
            return None
    
    def generate_pdf_from_data(self, patient_data, findings, conclusions, recommendations, 
                              images_labels, filename):
        """Generate PDF directly from provided data without database access - FIXED
        
        Args:
            patient_data: Dictionary of patient information
            findings: Findings text
            conclusions: Conclusions text
            recommendations: Recommendations text
            images_labels: List of (image_path, label) tuples
            filename: Output filename
            
        Returns:
            Path to the generated PDF or None if failed
        """
        try:
            # Validate patient data
            if not patient_data:
                raise ValueError("Patient data is required")
            
            # Create directory if needed
            filepath = Path(filename)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare patient data with any additional fields
            complete_patient_data = dict(patient_data)
            
            # ENSURE REPORT_TITLE AND INDICATION ARE PROPERLY SET
            if "report_title" not in complete_patient_data:
                complete_patient_data["report_title"] = "ENDOSCOPY REPORT"
            
            if "indication" not in complete_patient_data:
                complete_patient_data["indication"] = ""
            
            if "Date" not in complete_patient_data:
                complete_patient_data["Date"] = datetime.now().strftime("%d/%m/%Y")
            
            # Format doctor and designation if needed
            if "doctor" in patient_data:
                complete_patient_data["Doctor"] = patient_data["doctor"].upper()
            
            if "designation" in patient_data:
                complete_patient_data["Designation"] = patient_data["designation"].upper()
            
            # LOG THE DATA BEING PASSED TO PDF GENERATOR
            self.logger.info(f"Generating PDF to: {filepath}")
            self.logger.info(f"Patient data keys: {list(complete_patient_data.keys())}")
            self.logger.info(f"Report title: {complete_patient_data.get('report_title')}")
            self.logger.info(f"Indication: {complete_patient_data.get('indication')}")
            self.logger.info(f"Findings length: {len(findings) if findings else 0}")
            self.logger.info(f"Images count: {len(images_labels) if images_labels else 0}")
            
            # IMPORT AND USE THE CORRECT PDF GENERATOR FUNCTION
            from src.utils.pdf_generator import generate_endoscopy_pdf
            
            pdf_path = generate_endoscopy_pdf(
                complete_patient_data,
                findings,
                conclusions,
                recommendations,
                images_labels,
                str(filepath)
            )
            
            self.logger.info(f"PDF generated successfully: {pdf_path}")
            self.report_generated.emit(pdf_path)
            
            return pdf_path
            
        except Exception as e:
            error_msg = f"Failed to generate PDF from data: {str(e)}"
            self.logger.error(f"{error_msg}\n{traceback.format_exc()}")
            self.generation_failed.emit(f"Failed to generate PDF: {str(e)}")
            return None
    
    def save_report_dialog(self, report_id=None, patient_id=None, patient_data=None, 
                          report_data=None, images=None):
        """Show save dialog and generate report with custom path
        
        Can work with either database IDs or direct data.
        
        Args:
            report_id: ID of the report to generate (optional)
            patient_id: ID of the patient if report_id not provided (optional)
            patient_data: Patient data dictionary (optional, for direct data mode)
            report_data: Report data dictionary (optional, for direct data mode)
            images: List of image tuples (optional, for direct data mode)
            
        Returns:
            Path to the generated PDF report or None if cancelled/failed
        """
        try:
            # Determine if using database or direct data
            using_database = (report_id is not None or patient_id is not None) and self.db is not None
            using_direct_data = patient_data is not None and report_data is not None
            
            if not using_database and not using_direct_data:
                raise ValueError("Either database IDs or direct data must be provided")
            
            # Get patient name for default filename
            patient_name = "report"
            if using_database:
                # Get patient info from database
                if patient_id is None and report_id is not None:
                    report_data_db = self.db.get_report(report_id=report_id)
                    if report_data_db:
                        patient_id = report_data_db["patient_id"]
                
                if patient_id:
                    patient_data_db = self.db.get_patient(patient_id)
                    if patient_data_db and "name" in patient_data_db:
                        patient_name = patient_data_db["name"].replace(" ", "_").lower()
            elif using_direct_data:
                # Get patient name from provided data
                if "name" in patient_data:
                    patient_name = patient_data["name"].replace(" ", "_").lower()
            
            # Create default filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"{patient_name}_{timestamp}.pdf"
            
            # Show save dialog
            file_path, _ = QFileDialog.getSaveFileName(
                None,
                "Save Endoscopy Report",
                str(self.exported_reports_path / default_filename),
                "PDF Files (*.pdf)"
            )
            
            if not file_path:
                # User cancelled
                return None
            
            # Show progress dialog
            progress = QProgressDialog("Generating report...", "Cancel", 0, 100)
            progress.setWindowTitle("PDF Generation")
            progress.setMinimumDuration(500)  # Show after 500ms delay
            
            # Connect progress signal
            self.progress_updated.connect(progress.setValue)
            
            # Generate report with custom path
            result = None
            if using_database:
                result = self.generate_report(report_id, patient_id, file_path)
            elif using_direct_data:
                # Show intermediate progress
                progress.setValue(50)
                
                result = self.generate_pdf_from_data(
                    patient_data,
                    report_data.get("findings", ""),
                    report_data.get("conclusions", ""),
                    report_data.get("recommendations", ""),
                    images or [],
                    file_path
                )
            
            # Disconnect signal and close dialog
            self.progress_updated.disconnect(progress.setValue)
            progress.close()
            
            return result
            
        except Exception as e:
            error_msg = f"Report save dialog failed: {str(e)}"
            self.logger.error(f"{error_msg}\n{traceback.format_exc()}")
            QMessageBox.critical(None, "Report Generation Error", error_msg)
            return None
    
    def batch_generate_reports(self, report_ids):
        """Generate multiple reports in batch
        
        Args:
            report_ids: List of report IDs to generate
            
        Returns:
            List of (report_id, pdf_path) tuples for successful generations
        """
        try:
            if not self.db:
                raise ValueError("Database manager is required for batch report generation")
                
            results = []
            
            # Show progress dialog
            progress = QProgressDialog("Generating reports...", "Cancel", 0, len(report_ids) * 100)
            progress.setWindowTitle("Batch PDF Generation")
            progress.setMinimumDuration(500)  # Show after 500ms delay
            
            # Process each report
            for i, report_id in enumerate(report_ids):
                if progress.wasCanceled():
                    break
                
                # Update main progress
                progress.setLabelText(f"Generating report {i+1} of {len(report_ids)}...")
                
                # Define a translator function to map individual report progress to overall
                base_progress = i * 100
                def update_batch_progress(value):
                    overall_progress = base_progress + value
                    progress.setValue(min(overall_progress, len(report_ids) * 100))
                
                # Connect temporary signal translator
                self.progress_updated.connect(update_batch_progress)
                
                # Generate the report
                pdf_path = self.generate_report(report_id=report_id)
                
                # Disconnect translator
                self.progress_updated.disconnect(update_batch_progress)
                
                if pdf_path:
                    results.append((report_id, pdf_path))
            
            progress.close()
            
            # Show completion message
            success_count = len(results)
            total_count = len(report_ids)
            
            if success_count > 0:
                QMessageBox.information(
                    None,
                    "Batch Generation Complete",
                    f"Successfully generated {success_count} of {total_count} reports."
                )
            
            return results
            
        except Exception as e:
            error_msg = f"Batch report generation failed: {str(e)}"
            self.logger.error(f"{error_msg}\n{traceback.format_exc()}")
            QMessageBox.critical(None, "Batch Generation Error", error_msg)
            return []
    
    # HELPER METHODS
    
    def get_report_path(self, report_id):
        """Get the path for a specific report
        
        Args:
            report_id: ID of the report
            
        Returns:
            Path object for the expected report location or None if not found
        """
        # Find newest report for this ID
        report_files = []
        
        # Search in both draft and final directories
        for base_dir in [self.draft_reports_path, self.final_reports_path]:
            for path in base_dir.glob(f"**/*{report_id}*.pdf"):
                report_files.append(path)
        
        # Sort by modification time (newest first)
        report_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        
        if report_files:
            return report_files[0]
        
        return None
    
    def open_report(self, pdf_path):
        """Open a report with the default PDF viewer
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            pdf_path = Path(pdf_path)
            
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
            system = platform.system()
            
            if system == "Windows":
                os.startfile(str(pdf_path))
            elif system == "Darwin":  # macOS
                os.system(f"open '{pdf_path}'")
            else:  # Linux
                os.system(f"xdg-open '{pdf_path}'")
            
            self.logger.info(f"Opened PDF: {pdf_path}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to open PDF: {str(e)}"
            self.logger.error(f"{error_msg}\n{traceback.format_exc()}")
            QMessageBox.warning(None, "Open PDF Error", error_msg)
            return False
    
    def export_report(self, report_id, export_format="pdf"):
        """Export a report to different formats
        
        Args:
            report_id: ID of the report to export
            export_format: Format to export to ("pdf", "html", "docx")
            
        Returns:
            Path to the exported file or None if failed
        """
        try:
            # Currently only PDF is supported
            if export_format.lower() != "pdf":
                raise ValueError(f"Export format not supported: {export_format}")
            
            # Get report path
            report_path = self.get_report_path(report_id)
            if not report_path:
                raise ValueError(f"Report not found: {report_id}")
            
            # Use save dialog to get export location
            file_dialog = QFileDialog(None)
            file_dialog.setAcceptMode(QFileDialog.AcceptSave)
            file_dialog.setNameFilter("PDF Files (*.pdf)")
            
            # Suggest filename based on original
            export_name = f"export_{report_path.stem}.pdf"
            file_dialog.selectFile(str(self.exported_reports_path / export_name))
            
            if file_dialog.exec() != QFileDialog.Accepted:
                return None
            
            export_path = file_dialog.selectedFiles()[0]
            if not export_path.endswith(".pdf"):
                export_path += ".pdf"
            
            # Copy the file to export location
            import shutil
            shutil.copy2(report_path, export_path)
            
            self.logger.info(f"Exported report to: {export_path}")
            return export_path
            
        except Exception as e:
            error_msg = f"Failed to export report: {str(e)}"
            self.logger.error(f"{error_msg}\n{traceback.format_exc()}")
            QMessageBox.warning(None, "Export Error", error_msg)
            return None