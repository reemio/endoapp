# COMPLETELY FIXED REPORT_PREVIEW_DIALOG.PY - CRITICAL SIGNAL & DATA HANDLING FIXES
# FILE: src/ui/report_preview_dialog.py

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QTabWidget, QFrame, QGridLayout,
    QFileDialog, QMessageBox, QSplitter, QTextEdit, QGroupBox,
    QProgressDialog
)
from PySide6.QtCore import Qt, Signal, QSize, QTimer
from PySide6.QtGui import QPixmap, QFont, QPainter
from pathlib import Path
import logging
from datetime import datetime
import traceback

class ReportPreviewDialog(QDialog):
    """FIXED: Dialog for previewing and generating PDF reports with comprehensive error handling"""
    
    # SIGNALS
    report_generated = Signal(str)  # Emits path to the generated report
    
    def __init__(self, patient_data, report_data, images, parent=None):
        """Initialize the report preview dialog
        
        Args:
            patient_data: Dictionary of patient information
            report_data: Dictionary of report content (findings, conclusions, recommendations)
            images: List of (image_path, label) tuples
            parent: Parent widget
        """
        super().__init__(parent)
        
        # CRITICAL FIX: Validate input data immediately
        try:
            self.patient_data = patient_data if patient_data else {}
            self.report_data = report_data if report_data else {}
            self.images = images if images else []
            
            # LOG RECEIVED DATA FOR DEBUGGING
            logging.info(f"ReportPreviewDialog initialized with:")
            logging.info(f"  Patient data keys: {list(self.patient_data.keys())}")
            logging.info(f"  Report data keys: {list(self.report_data.keys())}")
            logging.info(f"  Images count: {len(self.images)}")
            
            # VALIDATE CRITICAL FIELDS
            if not self.patient_data.get('patient_id'):
                logging.warning("Missing patient_id in patient_data")
            if not self.patient_data.get('name'):
                logging.warning("Missing name in patient_data")
                
        except Exception as e:
            logging.error(f"Error in ReportPreviewDialog.__init__: {e}")
            self.patient_data = {}
            self.report_data = {}
            self.images = []
        
        self.setup_ui()
        self.load_preview_data()
    
    def setup_ui(self):
        """Setup the dialog UI with enhanced error handling"""
        try:
            self.setWindowTitle("Report Preview")
            self.resize(900, 700)
            self.setModal(True)
            
            main_layout = QVBoxLayout(self)
            
            # PREVIEW AREA
            self.preview_scroll = QScrollArea()
            self.preview_scroll.setWidgetResizable(True)
            self.preview_scroll.setMinimumWidth(800)
            self.preview_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            
            self.preview_container = QWidget()
            self.preview_layout = QVBoxLayout(self.preview_container)
            self.preview_layout.setSpacing(20)
            self.preview_layout.setContentsMargins(40, 40, 40, 40)
            
            self.preview_scroll.setWidget(self.preview_container)
            
            # HEADER
            self.header_frame = QFrame()
            self.header_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
            self.header_frame.setStyleSheet("background-color: #f8f9fa; padding: 15px;")
            header_layout = QVBoxLayout(self.header_frame)
            
            self.hospital_label = QLabel()
            self.hospital_label.setAlignment(Qt.AlignCenter)
            self.hospital_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
            
            self.report_title = QLabel("ENDOSCOPY REPORT")
            self.report_title.setAlignment(Qt.AlignCenter)
            self.report_title.setStyleSheet("font-size: 14pt; font-weight: bold;")
            
            header_layout.addWidget(self.hospital_label)
            header_layout.addWidget(self.report_title)
            
            self.preview_layout.addWidget(self.header_frame)
            
            # PATIENT INFO
            self.patient_frame = QFrame()
            self.patient_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
            self.patient_frame.setStyleSheet("background-color: #f8f9fa; padding: 15px;")
            patient_layout = QGridLayout(self.patient_frame)
            
            # Row 1
            patient_layout.addWidget(QLabel("<b>PATIENT ID:</b>"), 0, 0)
            self.patient_id_label = QLabel()
            patient_layout.addWidget(self.patient_id_label, 0, 1)
            
            patient_layout.addWidget(QLabel("<b>REFERRING DOCTOR:</b>"), 0, 2)
            self.referring_doctor_label = QLabel()
            patient_layout.addWidget(self.referring_doctor_label, 0, 3)
            
            patient_layout.addWidget(QLabel("<b>MEDICATION:</b>"), 0, 4)
            self.medication_label = QLabel()
            patient_layout.addWidget(self.medication_label, 0, 5)
            
            # Row 2
            patient_layout.addWidget(QLabel("<b>NAME:</b>"), 1, 0)
            self.name_label = QLabel()
            patient_layout.addWidget(self.name_label, 1, 1)
            
            patient_layout.addWidget(QLabel("<b>GENDER:</b>"), 1, 2)
            self.gender_label = QLabel()
            patient_layout.addWidget(self.gender_label, 1, 3)
            
            patient_layout.addWidget(QLabel("<b>AGE:</b>"), 1, 4)
            self.age_label = QLabel()
            patient_layout.addWidget(self.age_label, 1, 5)
            
            # Row 3 - INDICATION FIELD
            patient_layout.addWidget(QLabel("<b>INDICATION:</b>"), 2, 0)
            self.indication_label = QLabel()
            patient_layout.addWidget(self.indication_label, 2, 1, 1, 5)  # Span multiple columns
            
            self.preview_layout.addWidget(self.patient_frame)
            
            # IMAGES
            self.images_frame = QFrame()
            self.images_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
            self.images_frame.setStyleSheet("background-color: #f8f9fa; padding: 15px;")
            
            self.images_layout = QGridLayout(self.images_frame)
            self.images_layout.setSpacing(10)
            
            self.preview_layout.addWidget(self.images_frame)
            
            # FINDINGS
            self.findings_group = QGroupBox("FINDINGS")
            self.findings_group.setStyleSheet("QGroupBox { font-weight: bold; }")
            findings_layout = QVBoxLayout(self.findings_group)
            
            self.findings_text = QTextEdit()
            self.findings_text.setReadOnly(True)
            self.findings_text.setMinimumHeight(100)
            findings_layout.addWidget(self.findings_text)
            
            self.preview_layout.addWidget(self.findings_group)
            
            # CONCLUSIONS
            self.conclusions_group = QGroupBox("CONCLUSIONS")
            self.conclusions_group.setStyleSheet("QGroupBox { font-weight: bold; }")
            conclusions_layout = QVBoxLayout(self.conclusions_group)
            
            self.conclusions_text = QTextEdit()
            self.conclusions_text.setReadOnly(True)
            self.conclusions_text.setMinimumHeight(100)
            conclusions_layout.addWidget(self.conclusions_text)
            
            self.preview_layout.addWidget(self.conclusions_group)
            
            # RECOMMENDATIONS
            self.recommendations_group = QGroupBox("RECOMMENDATIONS")
            self.recommendations_group.setStyleSheet("QGroupBox { font-weight: bold; }")
            recommendations_layout = QVBoxLayout(self.recommendations_group)
            
            self.recommendations_text = QTextEdit()
            self.recommendations_text.setReadOnly(True)
            self.recommendations_text.setMinimumHeight(100)
            recommendations_layout.addWidget(self.recommendations_text)
            
            self.preview_layout.addWidget(self.recommendations_group)
            
            # SIGNATURE
            self.signature_frame = QFrame()
            self.signature_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
            self.signature_frame.setStyleSheet("background-color: #f8f9fa; padding: 15px;")
            signature_layout = QHBoxLayout(self.signature_frame)
            
            self.doctor_label = QLabel()
            self.doctor_label.setStyleSheet("font-weight: bold;")
            signature_layout.addWidget(self.doctor_label)
            
            self.designation_label = QLabel()
            signature_layout.addWidget(self.designation_label)
            
            self.date_label = QLabel()
            signature_layout.addWidget(self.date_label)
            
            signature_layout.addStretch()
            
            self.preview_layout.addWidget(self.signature_frame)
            
            # Add preview to main layout
            main_layout.addWidget(self.preview_scroll)
            
            # BUTTONS - ENHANCED WITH PROGRESS INDICATION
            button_layout = QHBoxLayout()
            
            self.generate_pdf_btn = QPushButton("Save PDF Report")
            self.generate_pdf_btn.setStyleSheet("""
                QPushButton {
                    background-color: #007bff;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    min-width: 140px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #0056b3;
                }
                QPushButton:disabled {
                    background-color: #6c757d;
                }
            """)
            self.generate_pdf_btn.clicked.connect(self.generate_pdf)
            
            self.save_as_btn = QPushButton("Save As...")
            self.save_as_btn.setStyleSheet("""
                QPushButton {
                    background-color: #6c757d;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    min-width: 140px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #5a6268;
                }
            """)
            self.save_as_btn.clicked.connect(self.save_as_pdf)
            
            self.print_btn = QPushButton("Print")
            self.print_btn.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    min-width: 140px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
            """)
            self.print_btn.clicked.connect(self.print_report)
            
            self.close_btn = QPushButton("Close")
            self.close_btn.setStyleSheet("""
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    min-width: 140px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)
            self.close_btn.clicked.connect(self.reject)
            
            button_layout.addWidget(self.generate_pdf_btn)
            button_layout.addWidget(self.save_as_btn)
            button_layout.addWidget(self.print_btn)
            button_layout.addStretch()
            button_layout.addWidget(self.close_btn)
            
            main_layout.addLayout(button_layout)
            
            logging.info("ReportPreviewDialog UI setup completed successfully")
            
        except Exception as e:
            logging.error(f"Error in ReportPreviewDialog.setup_ui: {e}")
            logging.error(traceback.format_exc())
    
    def load_preview_data(self):
        """FIXED: Load data into the preview widgets with comprehensive error handling"""
        try:
            logging.info("Loading preview data...")
            
            # HOSPITAL AND REPORT TITLE
            try:
                hospital_name = self.patient_data.get("hospital_name", "MEDICAL CENTER")
                self.hospital_label.setText(str(hospital_name).upper())
                
                # ENHANCED: Use report_title from patient_data with multiple fallbacks
                report_title = (
                    self.patient_data.get("report_title") or 
                    self.report_data.get("report_title") or 
                    "ENDOSCOPY REPORT"
                )
                self.report_title.setText(str(report_title).upper())
                
                logging.info(f"Hospital: {hospital_name}, Report Title: {report_title}")
                
            except Exception as e:
                logging.error(f"Error setting hospital/title: {e}")
                self.hospital_label.setText("MEDICAL CENTER")
                self.report_title.setText("ENDOSCOPY REPORT")
            
            # PATIENT INFO
            try:
                self.patient_id_label.setText(str(self.patient_data.get("patient_id", "")))
                self.referring_doctor_label.setText(str(self.patient_data.get("referring_doctor", "")))
                self.medication_label.setText(str(self.patient_data.get("medication", "")))
                self.name_label.setText(str(self.patient_data.get("name", "")))
                self.gender_label.setText(str(self.patient_data.get("gender", "")))
                self.age_label.setText(str(self.patient_data.get("age", "")))
                
                # ENHANCED: Show indication field with multiple fallbacks
                indication = (
                    self.patient_data.get("indication") or
                    self.report_data.get("indication") or
                    ""
                )
                self.indication_label.setText(str(indication))
                
                logging.info(f"Patient info loaded: ID={self.patient_data.get('patient_id')}, Name={self.patient_data.get('name')}")
                
            except Exception as e:
                logging.error(f"Error setting patient info: {e}")
            
            # REPORT CONTENT
            try:
                findings = self.report_data.get("findings", "")
                conclusions = self.report_data.get("conclusions", "")
                recommendations = self.report_data.get("recommendations", "")
                
                self.findings_text.setText(str(findings))
                self.conclusions_text.setText(str(conclusions))
                self.recommendations_text.setText(str(recommendations))
                
                logging.info(f"Report content loaded: {len(findings)} chars findings, {len(conclusions)} chars conclusions")
                
            except Exception as e:
                logging.error(f"Error setting report content: {e}")
                self.findings_text.setText("")
                self.conclusions_text.setText("")
                self.recommendations_text.setText("")
            
            # DOCTOR INFO AND DATE
            try:
                doctor_name = self.patient_data.get("doctor", "")
                self.doctor_label.setText(f"DOCTOR: {doctor_name}")
                
                designation = self.patient_data.get("designation", "")
                self.designation_label.setText(f"DESIGNATION: {designation}")
                
                # Use date from patient data or current date
                date_str = self.patient_data.get("date")
                if not date_str:
                    date_str = datetime.now().strftime("%d/%m/%Y")
                self.date_label.setText(f"DATE: {date_str}")
                
            except Exception as e:
                logging.error(f"Error setting doctor info: {e}")
                current_date = datetime.now().strftime("%d/%m/%Y")
                self.date_label.setText(f"DATE: {current_date}")
            
            # LOAD IMAGES
            try:
                self.load_preview_images()
                logging.info("Images loaded successfully")
            except Exception as e:
                logging.error(f"Error loading images: {e}")
            
            logging.info("Preview data loading completed")
            
        except Exception as e:
            logging.error(f"Critical error in load_preview_data: {e}")
            logging.error(traceback.format_exc())
            QMessageBox.warning(
                self,
                "Preview Error",
                f"Error loading preview data: {str(e)}\n\nSome fields may be empty."
            )
    
    def load_preview_images(self):
        """Load images into the preview with enhanced error handling"""
        try:
            # Clear existing images
            for i in reversed(range(self.images_layout.count())):
                item = self.images_layout.itemAt(i)
                if item and item.widget():
                    item.widget().deleteLater()
            
            if not self.images:
                # Add message if no images
                empty_label = QLabel("No images selected for this report")
                empty_label.setAlignment(Qt.AlignCenter)
                empty_label.setStyleSheet("font-style: italic; color: gray; padding: 20px;")
                self.images_layout.addWidget(empty_label, 0, 0, 1, 3)
                return
            
            # Calculate grid layout
            max_cols = 3
            
            # Add images to grid
            for idx, (image_path, label) in enumerate(self.images):
                try:
                    row = idx // max_cols
                    col = idx % max_cols
                    
                    # Create image container
                    image_container = QFrame()
                    image_container.setFrameStyle(QFrame.Box | QFrame.Sunken)
                    image_container.setLineWidth(1)
                    image_layout = QVBoxLayout(image_container)
                    
                    # Add label
                    label_widget = QLabel(str(label) if label else f"Image {idx + 1}")
                    label_widget.setAlignment(Qt.AlignCenter)
                    label_widget.setStyleSheet("font-weight: bold; padding: 5px;")
                    image_layout.addWidget(label_widget)
                    
                    # Add image
                    image_widget = QLabel()
                    image_widget.setAlignment(Qt.AlignCenter)
                    
                    # Check if image exists and load it
                    if image_path and Path(image_path).exists():
                        try:
                            pixmap = QPixmap(str(image_path))
                            if not pixmap.isNull():
                                scaled_pixmap = pixmap.scaled(
                                    200, 150,
                                    Qt.KeepAspectRatio,
                                    Qt.SmoothTransformation
                                )
                                image_widget.setPixmap(scaled_pixmap)
                            else:
                                image_widget.setText("Invalid image")
                                image_widget.setStyleSheet("color: red; padding: 20px;")
                        except Exception as img_error:
                            logging.warning(f"Error loading image {image_path}: {img_error}")
                            image_widget.setText("Error loading image")
                            image_widget.setStyleSheet("color: red; padding: 20px;")
                    else:
                        image_widget.setText("Image not found")
                        image_widget.setStyleSheet("color: red; padding: 20px;")
                        logging.warning(f"Image file not found: {image_path}")
                    
                    image_layout.addWidget(image_widget)
                    
                    # Add to grid
                    self.images_layout.addWidget(image_container, row, col)
                    
                except Exception as img_container_error:
                    logging.error(f"Error creating image container {idx}: {img_container_error}")
                    continue
                
        except Exception as e:
            logging.error(f"Error in load_preview_images: {e}")
            # Add error message
            error_label = QLabel(f"Error loading images: {str(e)}")
            error_label.setAlignment(Qt.AlignCenter)
            error_label.setStyleSheet("color: red; font-style: italic; padding: 20px;")
            self.images_layout.addWidget(error_label, 0, 0, 1, 3)
    
    def generate_pdf(self):
        """FIXED: Generate the PDF report with comprehensive error handling and progress indication"""
        try:
            logging.info("🔄 Starting PDF generation...")
            
            # SHOW PROGRESS DIALOG
            progress = QProgressDialog("Generating PDF report...", "Cancel", 0, 100, self)
            progress.setWindowTitle("PDF Generation")
            progress.setMinimumDuration(0)
            progress.setModal(True)
            progress.setValue(10)
            
            # VALIDATE DATA
            if not self.patient_data.get("patient_id"):
                QMessageBox.warning(self, "Missing Data", "Patient ID is required to generate report.")
                return
            
            if not self.patient_data.get("name"):
                QMessageBox.warning(self, "Missing Data", "Patient name is required to generate report.")
                return
            
            progress.setValue(20)
            
            # AUTO-GENERATE FILE PATH BASED ON HOSPITAL/PATIENT INFO
            try:
                hospital_name = self.patient_data.get("hospital_name", "Default_Hospital")
                patient_name = self.patient_data.get("name", "Unknown_Patient")
                patient_id = self.patient_data.get("patient_id", "No_ID")
                
                # Sanitize names for filesystem
                def sanitize_name(name):
                    if not name:
                        return "Unknown"
                    invalid_chars = '<>:"/\\|?*'
                    sanitized = str(name)
                    for char in invalid_chars:
                        sanitized = sanitized.replace(char, '_')
                    return '_'.join(sanitized.split())
                
                safe_hospital = sanitize_name(hospital_name)
                safe_patient = sanitize_name(patient_name)
                safe_id = sanitize_name(patient_id)
                
                # CREATE HOSPITAL REPORTS DIRECTORY
                hospital_reports_dir = Path("data/hospitals") / safe_hospital / "Reports"
                hospital_reports_dir.mkdir(parents=True, exist_ok=True)
                
                # GENERATE FILENAME WITH TIMESTAMP
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{safe_id}_{safe_patient}_{timestamp}.pdf"
                pdf_path = hospital_reports_dir / filename
                
                logging.info(f"📁 PDF will be saved to: {pdf_path}")
                
            except Exception as path_error:
                logging.error(f"Error generating file path: {path_error}")
                QMessageBox.critical(self, "Path Error", f"Error creating file path: {str(path_error)}")
                progress.close()
                return
            
            progress.setValue(40)
            
            # ENHANCED DATA PREPARATION FOR PDF
            try:
                enhanced_patient_data = self.patient_data.copy()
                enhanced_patient_data['report_title'] = (
                    self.patient_data.get('report_title') or 
                    self.report_data.get('report_title') or 
                    'ENDOSCOPY REPORT'
                )
                enhanced_patient_data['indication'] = (
                    self.patient_data.get('indication') or
                    self.report_data.get('indication') or 
                    ''
                )
                
                # Ensure date is properly formatted
                if 'date' not in enhanced_patient_data or not enhanced_patient_data['date']:
                    enhanced_patient_data['date'] = datetime.now().strftime("%d/%m/%Y")
                
                logging.info(f"📊 Enhanced patient data prepared with {len(enhanced_patient_data)} fields")
                
            except Exception as data_error:
                logging.error(f"Error preparing data: {data_error}")
                QMessageBox.critical(self, "Data Error", f"Error preparing report data: {str(data_error)}")
                progress.close()
                return
            
            progress.setValue(60)
            
            # GENERATE PDF
            try:
                success = self._generate_pdf_file(str(pdf_path), progress)
                
                if success:
                    progress.setValue(100)
                    progress.close()
                    
                    QMessageBox.information(
                        self,
                        "PDF Generated Successfully",
                        f"Report PDF has been successfully saved to:\n\n{pdf_path}\n\n"
                        f"File size: {self._get_file_size_mb(pdf_path):.1f} MB"
                    )
                    
                    # Emit signal with path
                    self.report_generated.emit(str(pdf_path))
                    logging.info(f"✅ PDF generation completed successfully: {pdf_path}")
                    
                    # Close dialog
                    self.accept()
                else:
                    progress.close()
                    QMessageBox.critical(
                        self,
                        "PDF Generation Failed",
                        "Failed to generate PDF report. Please check the application logs for details."
                    )
                    
            except Exception as pdf_error:
                progress.close()
                logging.error(f"PDF generation error: {pdf_error}")
                logging.error(traceback.format_exc())
                QMessageBox.critical(
                    self,
                    "PDF Generation Error",
                    f"Error during PDF generation:\n\n{str(pdf_error)}\n\n"
                    f"Please check:\n"
                    f"• Write permissions to the data folder\n"
                    f"• Available disk space\n"
                    f"• Application logs for more details"
                )
                
        except Exception as e:
            logging.error(f"Critical error in generate_pdf: {e}")
            logging.error(traceback.format_exc())
            QMessageBox.critical(
                self,
                "Critical PDF Generation Error",
                f"A critical error occurred:\n\n{str(e)}\n\n"
                f"Please restart the application and try again."
            )
    
    def save_as_pdf(self):
        """Show save dialog for custom location with enhanced error handling"""
        try:
            # Suggest filename based on patient info
            patient_name = self.patient_data.get("name", "").replace(" ", "_").lower()
            patient_id = self.patient_data.get("patient_id", "").replace("/", "-")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            suggested_filename = f"{patient_id}_{patient_name}_{timestamp}.pdf"
            
            # Show save dialog
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Endoscopy Report",
                suggested_filename,
                "PDF Files (*.pdf);;All Files (*)"
            )
            
            if not file_path:
                return  # User cancelled
            
            if not file_path.lower().endswith(".pdf"):
                file_path += ".pdf"
            
            # Show progress dialog
            progress = QProgressDialog("Saving PDF report...", "Cancel", 0, 100, self)
            progress.setWindowTitle("Saving PDF")
            progress.setMinimumDuration(0)
            progress.setModal(True)
            
            # Generate PDF to custom location
            success = self._generate_pdf_file(file_path, progress)
            
            if success:
                progress.close()
                QMessageBox.information(
                    self,
                    "PDF Saved Successfully",
                    f"Report PDF has been successfully saved to:\n\n{file_path}\n\n"
                    f"File size: {self._get_file_size_mb(file_path):.1f} MB"
                )
                
                # Emit signal with path
                self.report_generated.emit(file_path)
                
                # Close dialog
                self.accept()
            else:
                progress.close()
                QMessageBox.critical(
                    self,
                    "Save Failed",
                    "Failed to save PDF report. Please check the application logs for details."
                )
                
        except Exception as e:
            logging.error(f"Error in save_as_pdf: {e}")
            logging.error(traceback.format_exc())
            QMessageBox.critical(
                self,
                "Save Error",
                f"Error saving PDF: {str(e)}"
            )
    
    def _generate_pdf_file(self, file_path, progress_dialog=None):
        """FIXED: Internal method to generate PDF file with progress tracking
        
        Args:
            file_path: Path where to save the PDF
            progress_dialog: Optional progress dialog to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if progress_dialog:
                progress_dialog.setValue(70)
                progress_dialog.setLabelText("Generating PDF content...")
            
            # ENHANCED: Prepare complete patient data for PDF generation
            enhanced_patient_data = self.patient_data.copy()
            
            # Ensure all required fields are present
            enhanced_patient_data['report_title'] = (
                self.patient_data.get('report_title') or 
                self.report_data.get('report_title') or 
                'ENDOSCOPY REPORT'
            )
            enhanced_patient_data['indication'] = (
                self.patient_data.get('indication') or
                self.report_data.get('indication') or 
                ''
            )
            
            # Ensure date is formatted correctly
            if not enhanced_patient_data.get('date'):
                enhanced_patient_data['date'] = datetime.now().strftime("%d/%m/%Y")
            
            logging.info(f"Generating PDF with enhanced data: {list(enhanced_patient_data.keys())}")
            
            if progress_dialog:
                progress_dialog.setValue(80)
                progress_dialog.setLabelText("Writing PDF file...")
            
            # GET PARENT TO ACCESS REPORT GENERATOR OR USE UTILITY DIRECTLY
            parent = self.parent()
            if parent and hasattr(parent, "report_generator"):
                # Use parent's report generator
                report_generator = parent.report_generator
                result_path = report_generator.generate_pdf_from_data(
                    enhanced_patient_data,
                    self.report_data.get("findings", ""),
                    self.report_data.get("conclusions", ""),
                    self.report_data.get("recommendations", ""),
                    self.images,
                    file_path
                )
                
                success = result_path is not None
                
            else:
                # USE UTILITY FUNCTION DIRECTLY
                try:
                    from src.utils.pdf_generator import generate_endoscopy_pdf
                    
                    result_path = generate_endoscopy_pdf(
                        enhanced_patient_data,
                        self.report_data.get("findings", ""),
                        self.report_data.get("conclusions", ""),
                        self.report_data.get("recommendations", ""),
                        self.images,
                        file_path
                    )
                    
                    success = result_path is not None
                    
                except ImportError as import_error:
                    logging.error(f"Failed to import PDF generator: {import_error}")
                    return False
            
            if progress_dialog:
                progress_dialog.setValue(95)
                progress_dialog.setLabelText("Finalizing PDF...")
            
            # VERIFY FILE WAS CREATED
            if success and Path(file_path).exists():
                file_size = Path(file_path).stat().st_size
                if file_size > 0:
                    logging.info(f"PDF generated successfully: {file_path} ({file_size} bytes)")
                    return True
                else:
                    logging.error(f"PDF file created but is empty: {file_path}")
                    return False
            else:
                logging.error(f"PDF generation failed: file not created at {file_path}")
                return False
                
        except Exception as e:
            logging.error(f"Error in _generate_pdf_file: {e}")
            logging.error(traceback.format_exc())
            return False
    
    def _get_file_size_mb(self, file_path):
        """Get file size in MB"""
        try:
            if Path(file_path).exists():
                size_bytes = Path(file_path).stat().st_size
                return size_bytes / (1024 * 1024)
        except:
            pass
        return 0.0
    
    def print_report(self):
        """Print the report directly with error handling"""
        try:
            # Import printer classes
            from PySide6.QtPrintSupport import QPrinter, QPrintDialog
            from PySide6.QtGui import QPageSize
            
            printer = QPrinter(QPrinter.HighResolution)
            printer.setPageSize(QPageSize.A4)
            
            # Show printer dialog
            dialog = QPrintDialog(printer, self)
            if dialog.exec() != QPrintDialog.Accepted:
                return
            
            # Setup painter
            painter = QPainter()
            if not painter.begin(printer):
                QMessageBox.warning(
                    self,
                    "Printing Error",
                    "Could not initialize printer"
                )
                return
            
            # Render preview content
            self.preview_container.render(painter)
            
            # End painting
            painter.end()
            
            QMessageBox.information(
                self,
                "Print Complete",
                "Report has been sent to the printer"
            )
            
        except Exception as e:
            logging.error(f"Error printing report: {e}")
            QMessageBox.critical(
                self,
                "Printing Error",
                f"Error printing report: {str(e)}"
            )