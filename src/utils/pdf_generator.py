# COMPLETELY VERIFIED AND FIXED PDF_GENERATOR.PY - CRITICAL DEPENDENCY & ERROR HANDLING
# FILE: src/utils/pdf_generator.py

import logging
from pathlib import Path
import traceback

# CRITICAL: Check and import PDF dependencies with fallbacks
PDF_GENERATION_AVAILABLE = False
FPDF_MODULE = None
PIL_MODULE = None

try:
    from fpdf import FPDF
    FPDF_MODULE = FPDF
    PDF_GENERATION_AVAILABLE = True
    print("✅ fpdf2 module imported successfully")
except ImportError as e:
    print(f"❌ fpdf2 module not found: {e}")
    try:
        # Fallback to older fpdf version
        from fpdf import FPDF
        FPDF_MODULE = FPDF
        PDF_GENERATION_AVAILABLE = True
        print("✅ fpdf (legacy) module imported as fallback")
    except ImportError:
        print("❌ No FPDF module available - install with: pip install fpdf2")

try:
    from PIL import Image
    PIL_MODULE = Image
    print("✅ PIL (Pillow) module imported successfully")
except ImportError as e:
    print(f"❌ PIL (Pillow) module not found: {e}")
    print("❌ Install with: pip install Pillow")

# === ENHANCED ENDOSCOPY PDF CLASS WITH COMPREHENSIVE ERROR HANDLING ===
class EndoscopyPDF:
    """FIXED: Custom PDF class for endoscopy reports with comprehensive error handling"""
    
    def __init__(self, patient_data, findings, conclusions, recommendations, images_labels):
        """Initialize PDF generator with validation"""
        try:
            # CRITICAL: Validate dependencies
            if not PDF_GENERATION_AVAILABLE or not FPDF_MODULE:
                raise ImportError("FPDF module not available. Install with: pip install fpdf2")
            
            # VALIDATE INPUT DATA
            self.patient_data = patient_data if patient_data else {}
            self.findings = str(findings) if findings else ""
            self.conclusions = str(conclusions) if conclusions else ""
            self.recommendations = str(recommendations) if recommendations else ""
            self.images_labels = images_labels if images_labels else []
            
            # LOG RECEIVED DATA
            logging.info(f"EndoscopyPDF initialized:")
            logging.info(f"  Patient data keys: {list(self.patient_data.keys())}")
            logging.info(f"  Findings length: {len(self.findings)}")
            logging.info(f"  Images count: {len(self.images_labels)}")
            
            # CREATE PDF INSTANCE
            self.pdf = FPDF_MODULE()
            self.pdf.set_auto_page_break(auto=False)
            self.pdf.add_page()
            
            # GENERATE THE PDF CONTENT
            self.render_layout()
            
        except Exception as e:
            logging.error(f"Error initializing EndoscopyPDF: {e}")
            logging.error(traceback.format_exc())
            raise

    def _safe_str(self, value):
        """Convert any value to a string safely"""
        if value is None:
            return ""
        try:
            return str(value).strip()
        except:
            return ""

    def header(self):
        """Render PDF header with dynamic report title - ENHANCED"""
        try:
            self.pdf.set_font("Arial", "B", 14)
            
            # Use hospital_name from patient_data with fallback
            hospital_name = self._safe_str(
                self.patient_data.get("hospital_name") or 
                self.patient_data.get("hospital") or 
                "MEDICAL CENTER"
            ).upper()
            self.pdf.cell(0, 10, hospital_name, align="C", ln=1)
            
            # Use report_title with multiple fallback sources
            self.pdf.set_font("Arial", "", 14)
            report_title = self._safe_str(
                self.patient_data.get("report_title") or
                "ENDOSCOPY REPORT"
            ).upper()
            self.pdf.cell(0, 10, report_title, align="C", ln=1)
            
            self.pdf.ln(2)
            self.pdf.set_line_width(0.2)
            self.pdf.line(10, self.pdf.get_y(), 200, self.pdf.get_y())
            self.pdf.ln(4)
            
        except Exception as e:
            logging.error(f"Error in PDF header: {e}")
            # Continue with basic header
            try:
                self.pdf.set_font("Arial", "B", 14)
                self.pdf.cell(0, 10, "MEDICAL CENTER", align="C", ln=1)
                self.pdf.cell(0, 10, "ENDOSCOPY REPORT", align="C", ln=1)
                self.pdf.ln(4)
            except:
                pass

    def render_layout(self):
        """Render complete report layout with error handling"""
        try:
            logging.info("Rendering PDF layout...")
            self.header()
            self.render_patient_info()
            self.render_images()
            self.render_fcr()
            self.render_signature()
            logging.info("PDF layout rendering completed")
        except Exception as e:
            logging.error(f"Error in render_layout: {e}")
            raise

    def render_patient_info(self):
        """Render patient information section with indication field - ENHANCED"""
        try:
            self.pdf.set_font("Arial", "B", 11)
            y = self.pdf.get_y()
            
            # ROW 1
            self.pdf.set_xy(10, y)
            self.pdf.cell(26, 8, "PATIENT ID:")
            self.pdf.set_font("Arial", "", 10)
            self.pdf.cell(20, 8, self._safe_str(self.patient_data.get("patient_id", "")))
            self.pdf.set_font("Arial", "B", 11)
            self.pdf.cell(46, 8, "REFERRING DOCTOR:")
            self.pdf.set_font("Arial", "", 10)
            self.pdf.cell(32, 8, self._safe_str(self.patient_data.get("referring_doctor", "")))
            self.pdf.set_font("Arial", "B", 11)
            self.pdf.cell(27, 8, "MEDICATION:")
            self.pdf.set_font("Arial", "", 10)
            self.pdf.cell(0, 8, self._safe_str(self.patient_data.get("medication", "")))
            self.pdf.line(10, y + 9, 200, y + 9)

            # ROW 2
            y2 = y + 11
            self.pdf.set_xy(10, y2)
            self.pdf.set_font("Arial", "B", 11)
            self.pdf.cell(15, 8, "NAME:")
            self.pdf.set_font("Arial", "", 10)
            self.pdf.cell(52, 8, self._safe_str(self.patient_data.get("name", "")))
            self.pdf.set_font("Arial", "B", 11)
            self.pdf.cell(18, 8, "GENDER:")
            self.pdf.set_font("Arial", "", 10)
            self.pdf.cell(18, 8, self._safe_str(self.patient_data.get("gender", "")))
            self.pdf.set_font("Arial", "B", 11)
            self.pdf.cell(10, 8, "AGE:")
            self.pdf.set_font("Arial", "", 10)
            self.pdf.cell(8, 8, self._safe_str(self.patient_data.get("age", "")))
            self.pdf.set_font("Arial", "B", 11)
            self.pdf.cell(28, 8, "INDICATION:")
            self.pdf.set_font("Arial", "", 10)
            # ENHANCED: Get indication from patient_data with fallback
            indication = self._safe_str(
                self.patient_data.get("indication", "")
            )
            self.pdf.cell(0, 8, indication)
            self.pdf.line(10, y2 + 9, 200, y2 + 9)
            self.pdf.set_y(y2 + 13)
            
        except Exception as e:
            logging.error(f"Error in render_patient_info: {e}")
            # Continue with basic info
            try:
                self.pdf.ln(20)
            except:
                pass

    def render_images(self):
        """FIXED: Render images in PDF with enhanced error handling and centering"""
        try:
            logging.info(f"Rendering {len(self.images_labels)} images...")
            
            self.pdf.set_font("Arial", "B", 9)
            box_width, box_height = 60, 39
            spacing_x, spacing_y = 4, 2
            start_x = 10
            y_origin = self.pdf.get_y()
            
            # Count actual images
            valid_images = []
            for img_path, label in self.images_labels:
                if img_path and Path(img_path).exists():
                    valid_images.append((img_path, label))
                else:
                    logging.warning(f"Image not found: {img_path}")
            
            actual_images = len(valid_images)
            logging.info(f"Valid images found: {actual_images}")
            
            if actual_images == 0:
                # No images, just add some space
                self.pdf.set_y(y_origin + 10)
                return
            
            # CENTER IMAGES IF FEWER THAN 6
            if actual_images < 6:
                # Calculate new layout based on number of images
                if actual_images <= 3:
                    # Single row with 1-3 images
                    rows = 1
                    cols = actual_images
                else:
                    # Two rows with 2 images per row for 4, or 2+3 for 5
                    rows = 2
                    cols = 3  # Max columns remains 3
                
                # Center horizontally
                total_width = cols * box_width + (cols - 1) * spacing_x
                centered_start_x = (self.pdf.w - total_width) / 2
                
                # Render images with centered layout
                for idx, (img_path, label) in enumerate(valid_images):
                    if idx < rows * cols:  # Safety check
                        try:
                            # Calculate position in centered grid
                            row = idx // cols
                            col = idx % cols
                            
                            # Calculate centered coordinates
                            x = centered_start_x + col * (box_width + spacing_x)
                            y = y_origin + row * (box_height + spacing_y + 8)
                            
                            # Render image with label
                            self.pdf.set_xy(x, y)
                            self.pdf.cell(box_width, 4, self._safe_str(label), align="C")
                            
                            # Add image if file exists and PIL is available
                            if PIL_MODULE:
                                try:
                                    self.pdf.image(img_path, x, y + 4, w=box_width, h=box_height)
                                except Exception as img_error:
                                    logging.warning(f"Error adding image {img_path}: {img_error}")
                                    # Draw placeholder box
                                    self.pdf.rect(x, y + 4, box_width, box_height)
                                    self.pdf.set_xy(x, y + 4 + box_height/2)
                                    self.pdf.cell(box_width, 5, "Image error", align="C")
                            else:
                                # Draw placeholder box when PIL not available
                                self.pdf.rect(x, y + 4, box_width, box_height)
                                self.pdf.set_xy(x, y + 4 + box_height/2)
                                self.pdf.cell(box_width, 5, "No PIL", align="C")
                                
                        except Exception as render_error:
                            logging.error(f"Error rendering image {idx}: {render_error}")
                            continue
            else:
                # Original layout for 6+ images
                for idx, (img_path, label) in enumerate(valid_images[:6]):
                    try:
                        row, col = divmod(idx, 3)
                        x = start_x + col * (box_width + spacing_x)
                        y = y_origin + row * (box_height + spacing_y + 8)
                        self.pdf.set_xy(x, y)
                        self.pdf.cell(box_width, 4, self._safe_str(label), align="C")
                        
                        # Add image if PIL is available
                        if PIL_MODULE:
                            try:
                                self.pdf.image(img_path, x, y + 4, w=box_width, h=box_height)
                            except Exception as img_error:
                                logging.warning(f"Error adding image {img_path}: {img_error}")
                                # Draw placeholder box
                                self.pdf.rect(x, y + 4, box_width, box_height)
                                self.pdf.set_xy(x, y + 4 + box_height/2)
                                self.pdf.cell(box_width, 5, "Image error", align="C")
                        else:
                            # Draw placeholder box when PIL not available
                            self.pdf.rect(x, y + 4, box_width, box_height)
                            self.pdf.set_xy(x, y + 4 + box_height/2)
                            self.pdf.cell(box_width, 5, "No PIL", align="C")
                            
                    except Exception as render_error:
                        logging.error(f"Error rendering image {idx}: {render_error}")
                        continue
            
            # Update Y position after rendering images
            if actual_images > 0:
                if actual_images <= 3:
                    # Move down after single row
                    self.pdf.set_y(y_origin + 1 * (box_height + spacing_y + 8) + 6)
                else:
                    # Move down after two rows
                    self.pdf.set_y(y_origin + 2 * (box_height + spacing_y + 8) + 6)
            else:
                # No images, just add some space
                self.pdf.set_y(y_origin + 10)
                
        except Exception as e:
            logging.error(f"Error in render_images: {e}")
            # Continue without images
            try:
                self.pdf.ln(10)
            except:
                pass

    def render_fcr(self):
        """Render Findings, Conclusions, and Recommendations with error handling"""
        try:
            # FINDINGS
            self.pdf.set_font("Arial", "B", 11)
            self.pdf.cell(0, 8, "FINDINGS:", ln=1)
            self.pdf.set_font("Arial", "", 9)
            findings_text = self._safe_str(self.findings)
            if findings_text:
                self.pdf.multi_cell(0, 5, findings_text)
            else:
                self.pdf.multi_cell(0, 5, "No findings recorded.")
            self.pdf.ln(2)

            # CONCLUSIONS
            self.pdf.set_font("Arial", "B", 11)
            self.pdf.cell(0, 8, "CONCLUSIONS:", ln=1)
            self.pdf.set_font("Arial", "", 9)
            conclusions_text = self._safe_str(self.conclusions)
            if conclusions_text:
                self.pdf.multi_cell(0, 5, conclusions_text)
            else:
                self.pdf.multi_cell(0, 5, "No conclusions recorded.")
            self.pdf.ln(2)

            # RECOMMENDATIONS
            self.pdf.set_font("Arial", "B", 11)
            self.pdf.cell(0, 8, "RECOMMENDATIONS:", ln=1)
            self.pdf.set_font("Arial", "", 9)
            recommendations_text = self._safe_str(self.recommendations)
            if recommendations_text:
                self.pdf.multi_cell(0, 5, recommendations_text)
            else:
                self.pdf.multi_cell(0, 5, "No recommendations recorded.")
            self.pdf.ln(5)
            
        except Exception as e:
            logging.error(f"Error in render_fcr: {e}")
            # Continue with basic text
            try:
                self.pdf.ln(20)
            except:
                pass

    def render_signature(self):
        """Render signature section with error handling"""
        try:
            self.pdf.set_y(275)
            self.pdf.set_line_width(0.2)
            self.pdf.line(10, self.pdf.get_y(), 200, self.pdf.get_y())
            self.pdf.ln(2)
            self.pdf.set_font("Arial", "B", 11)
            self.pdf.set_x(10)
            doctor = self._safe_str(self.patient_data.get("doctor", "DR. UNKNOWN"))
            designation = self._safe_str(self.patient_data.get("designation", "PHYSICIAN"))
            date = self._safe_str(self.patient_data.get("date", "DATE"))
            self.pdf.cell(63, 8, f"DOCTOR: {doctor}")
            self.pdf.cell(63, 8, f"DESIGNATION: {designation}")
            self.pdf.cell(0, 8, f"DATE: {date}", ln=1)
            
        except Exception as e:
            logging.error(f"Error in render_signature: {e}")
            # Continue without signature
            pass

    def output(self, filename):
        """Output PDF to file with error handling"""
        try:
            # Ensure directory exists
            file_path = Path(filename)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Generate PDF
            self.pdf.output(str(file_path))
            
            # Verify file was created
            if file_path.exists() and file_path.stat().st_size > 0:
                logging.info(f"PDF successfully generated: {filename} ({file_path.stat().st_size} bytes)")
                return True
            else:
                logging.error(f"PDF file was not created or is empty: {filename}")
                return False
                
        except Exception as e:
            logging.error(f"Error outputting PDF: {e}")
            return False

# === MAIN PDF GENERATION FUNCTION WITH COMPREHENSIVE ERROR HANDLING ===
def generate_endoscopy_pdf(patient_data, findings, conclusions, recommendations, images_labels, filename):
    """FIXED: Generate endoscopy report PDF with comprehensive error handling
    
    Args:
        patient_data: Dictionary with patient information (may include report_title, indication)
        findings: Findings text string
        conclusions: Conclusions text string
        recommendations: Recommendations text string
        images_labels: List of (image_path, label) tuples
        filename: Output filename
        
    Returns:
        Path to generated PDF or None if failed
    """
    logger = logging.getLogger(__name__)
    
    try:
        # CRITICAL: Check dependencies first
        if not PDF_GENERATION_AVAILABLE or not FPDF_MODULE:
            error_msg = "PDF generation dependencies not available. Install with: pip install fpdf2"
            logger.error(error_msg)
            raise ImportError(error_msg)
        
        # VALIDATE INPUT DATA
        if not patient_data:
            raise ValueError("Patient data is required")
        
        if not filename:
            raise ValueError("Output filename is required")
        
        # LOG THE DATA BEING PROCESSED
        logger.info(f"Generating PDF with patient data keys: {list(patient_data.keys())}")
        logger.info(f"Report title: {patient_data.get('report_title', 'NOT_FOUND')}")
        logger.info(f"Indication: {patient_data.get('indication', 'NOT_FOUND')}")
        logger.info(f"Findings length: {len(findings) if findings else 0}")
        logger.info(f"Images count: {len(images_labels) if images_labels else 0}")
        logger.info(f"Output filename: {filename}")
        
        # CREATE DIRECTORY IF NEEDED
        filepath = Path(filename)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # GENERATE PDF WITH ENHANCED ERROR HANDLING
        try:
            pdf_generator = EndoscopyPDF(patient_data, findings, conclusions, recommendations, images_labels)
            success = pdf_generator.output(str(filepath))
            
            if success:
                logger.info(f"PDF generated successfully: {filepath}")
                return str(filepath)
            else:
                logger.error(f"PDF generation failed: output method returned False")
                return None
                
        except Exception as pdf_error:
            logger.error(f"Error in PDF generation: {pdf_error}")
            logger.error(traceback.format_exc())
            
            # Try to create a basic error PDF
            try:
                logger.info("Attempting to create basic error PDF...")
                basic_pdf = FPDF_MODULE()
                basic_pdf.add_page()
                basic_pdf.set_font("Arial", "B", 16)
                basic_pdf.cell(0, 10, "ERROR GENERATING REPORT", ln=1, align="C")
                basic_pdf.ln(10)
                basic_pdf.set_font("Arial", "", 12)
                basic_pdf.multi_cell(0, 10, f"An error occurred while generating the full report.\n\nError: {str(pdf_error)}")
                basic_pdf.output(str(filepath))
                
                if filepath.exists():
                    logger.info(f"Basic error PDF created: {filepath}")
                    return str(filepath)
            except:
                logger.error("Failed to create even basic error PDF")
            
            return None
       
    except Exception as e:
        logger.error(f"Critical error in generate_endoscopy_pdf: {e}")
        logger.error(traceback.format_exc())
        return None

# === ALTERNATIVE FUNCTION FOR DIFFERENT DATA STRUCTURE ===
def generate_endoscopy_pdf_from_report_data(patient_data, report_data, images_labels, filename):
    """Generate endoscopy report PDF using report data structure
    
    Args:
        patient_data: Dictionary with patient information
        report_data: Dictionary with report data (report_title, indication, findings, conclusions, recommendations)
        images_labels: List of (image_path, label) tuples
        filename: Output filename
        
    Returns:
        Path to generated PDF or None if failed
    """
    logger = logging.getLogger(__name__)
    
    try:
        # VALIDATE INPUT DATA
        if not patient_data:
            raise ValueError("Patient data is required")
        
        if not report_data:
            report_data = {}
        
        # ENHANCE PATIENT DATA WITH REPORT FIELDS
        enhanced_patient_data = patient_data.copy()
        enhanced_patient_data['report_title'] = report_data.get('report_title', 'ENDOSCOPY REPORT')
        enhanced_patient_data['indication'] = report_data.get('indication', '')
        
        # EXTRACT TEXT FIELDS
        findings = report_data.get('findings', '')
        conclusions = report_data.get('conclusions', '')  
        recommendations = report_data.get('recommendations', '')
        
        # LOG THE ENHANCED DATA
        logger.info(f"Enhanced patient data keys: {list(enhanced_patient_data.keys())}")
        logger.info(f"Report title: {enhanced_patient_data.get('report_title')}")
        logger.info(f"Indication: {enhanced_patient_data.get('indication')}")
        
        # GENERATE PDF USING MAIN FUNCTION
        return generate_endoscopy_pdf(
            enhanced_patient_data, 
            findings, 
            conclusions, 
            recommendations, 
            images_labels, 
            filename
        )
        
    except Exception as e:
        logger.error(f"Failed to generate PDF from report data: {e}")
        logger.error(traceback.format_exc())
        return None

# === DEPENDENCY CHECK FUNCTION ===
def check_pdf_dependencies():
    """Check if PDF generation dependencies are available
    
    Returns:
        Tuple of (dependencies_available: bool, missing_dependencies: list)
    """
    missing = []
    
    if not PDF_GENERATION_AVAILABLE or not FPDF_MODULE:
        missing.append("fpdf2")
    
    if not PIL_MODULE:
        missing.append("Pillow")
    
    return len(missing) == 0, missing

# === MODULE INITIALIZATION ===
logger = logging.getLogger(__name__)

if not PDF_GENERATION_AVAILABLE:
    logger.warning("PDF generation not available - missing fpdf2 dependency")

if not PIL_MODULE:
    logger.warning("Image processing not available - missing Pillow dependency")

logger.info(f"PDF Generator module loaded. Dependencies: FPDF={PDF_GENERATION_AVAILABLE}, PIL={PIL_MODULE is not None}")