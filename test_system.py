# COMPLETE TEST_SYSTEM.PY CODE
# Save this as test_system.py in your project root directory

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, Qt

# Import main window
sys.path.append(str(Path(__file__).parent))
from src.main import MainWindow

class SystemTester:
    """Test core functionality of the Endoscopy Reporting System"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.window = MainWindow()
        self.schedule_tests()
        
    def schedule_tests(self):
        """Schedule tests to run after application starts"""
        QTimer.singleShot(1000, self.test_startup)
        QTimer.singleShot(2000, self.test_save_patient)
        QTimer.singleShot(3000, self.test_find_patient)
        QTimer.singleShot(4000, self.test_image_capture)
        QTimer.singleShot(5000, self.test_report_generation)
        QTimer.singleShot(6000, self.cleanup)
        
    def run(self):
        """Run the application"""
        self.window.show()
        return self.app.exec()
    
    # TEST FUNCTIONS
    
    def test_startup(self):
        """Test application startup"""
        print("\n=== TESTING STARTUP ===")
        
        # Check if core components are initialized
        components = [
            ("Settings Manager", hasattr(self.window, "settings")),
            ("Database Manager", hasattr(self.window, "db")),
            ("Error Handler", hasattr(self.window, "error_handler")),
            ("File Manager", hasattr(self.window, "file_manager")),
            ("Camera Manager", hasattr(self.window, "camera_manager")),
            ("Search Manager", hasattr(self.window, "search_manager")),
            ("Left Panel", hasattr(self.window, "left_panel")),
            ("Right Panel", hasattr(self.window, "right_panel")),
            ("Menu System", hasattr(self.window, "menu_system")),
        ]
        
        for name, exists in components:
            status = "✓" if exists else "✗"
            print(f"{status} {name} initialization")
        
    def test_save_patient(self):
        """Test patient save functionality"""
        print("\n=== TESTING SAVE PATIENT ===")
        
        try:
            # Check if left panel has necessary methods
            has_get_info = hasattr(self.window.left_panel, "get_patient_info")
            has_get_report = hasattr(self.window.left_panel, "get_report_data")
            
            print(f"{'✓' if has_get_info else '✗'} Left panel has get_patient_info method")
            print(f"{'✓' if has_get_report else '✗'} Left panel has get_report_data method")
            
            # Check if save button exists
            save_btn = getattr(self.window.left_panel, "save_btn", None)
            print(f"{'✓' if save_btn else '✗'} Save button exists")
            
            # Test if the save button has a clicked signal
            has_clicked = hasattr(save_btn, "clicked") if save_btn else False
            print(f"{'✓' if has_clicked else '✗'} Save button has clicked signal")
            
            # Test database methods
            has_add_patient = hasattr(self.window.db, "add_patient")
            has_update_patient = hasattr(self.window.db, "update_patient")
            
            print(f"{'✓' if has_add_patient else '✗'} Database has add_patient method")
            print(f"{'✓' if has_update_patient else '✗'} Database has update_patient method")
            
        except Exception as e:
            print(f"Error testing save functionality: {str(e)}")
    
    def test_find_patient(self):
        """Test patient find functionality"""
        print("\n=== TESTING FIND PATIENT ===")
        
        try:
            # Check if search manager has necessary methods
            has_search_dialog = hasattr(self.window.search_manager, "show_patient_search_dialog")
            
            print(f"{'✓' if has_search_dialog else '✗'} Search manager has show_patient_search_dialog method")
            
            # Check if find button exists
            find_btn = getattr(self.window.left_panel, "find_btn", None)
            print(f"{'✓' if find_btn else '✗'} Find button exists")
            
            # Test if the find button has a clicked signal
            has_clicked = hasattr(find_btn, "clicked") if find_btn else False
            print(f"{'✓' if has_clicked else '✗'} Find button has clicked signal")
            
            # Test database methods
            has_get_patient = hasattr(self.window.db, "get_patient")
            has_search_patients = hasattr(self.window.db, "search_patients")
            
            print(f"{'✓' if has_get_patient else '✗'} Database has get_patient method")
            print(f"{'✓' if has_search_patients else '✗'} Database has search_patients method")
            
        except Exception as e:
            print(f"Error testing find functionality: {str(e)}")
    
    def test_image_capture(self):
        """Test image capture functionality"""
        print("\n=== TESTING IMAGE CAPTURE ===")
        
        try:
            # Check if camera manager has necessary methods
            has_capture = hasattr(self.window.camera_manager, "capture_image")
            
            print(f"{'✓' if has_capture else '✗'} Camera manager has capture_image method")
            
            # Check if capture button exists
            video_feed = getattr(self.window.right_panel, "video_feed", None)
            capture_btn = getattr(video_feed, "capture_btn", None) if video_feed else None
            print(f"{'✓' if capture_btn else '✗'} Capture button exists")
            
            # Test if the capture button has a clicked signal
            has_clicked = hasattr(capture_btn, "clicked") if capture_btn else False
            print(f"{'✓' if has_clicked else '✗'} Capture button has clicked signal")
            
            # Check if image captured signal exists
            has_image_captured = hasattr(self.window.camera_manager, "image_captured")
            print(f"{'✓' if has_image_captured else '✗'} Image captured signal exists")
            
            # Check if captured media tab has add_image method
            captured_tab = getattr(self.window.right_panel, "captured_tab", None)
            has_add_image = hasattr(captured_tab, "add_image") if captured_tab else False
            print(f"{'✓' if has_add_image else '✗'} Captured media tab has add_image method")
            
        except Exception as e:
            print(f"Error testing image capture functionality: {str(e)}")
    
    def test_report_generation(self):
        """Test report generation functionality with enhanced debugging"""
        print("\n=== TESTING REPORT GENERATION ===")
        
        try:
            # Check if report button exists
            report_btn = getattr(self.window.left_panel, "report_btn", None)
            print(f"{'✓' if report_btn else '✗'} Report button exists")
            
            # Test if the report button has a clicked signal
            has_clicked = hasattr(report_btn, "clicked") if report_btn else False
            print(f"{'✓' if has_clicked else '✗'} Report button has clicked signal")
            
            # Enhanced debugging for report_tab
            if hasattr(self.window.right_panel, "report_tab"):
                print("✓ Right panel has report_tab attribute")
                report_tab = self.window.right_panel.report_tab
                
                # Print the class type
                print(f"Report tab class: {type(report_tab).__name__}")
                
                # Print available methods
                methods = [method for method in dir(report_tab) if not method.startswith('_')]
                print(f"Available methods: {', '.join(methods)}")
                
                # Check specifically for get_images
                has_get_images = hasattr(report_tab, "get_images")
                print(f"{'✓' if has_get_images else '✗'} Report tab has get_images method")
                
                # Try to access the method directly
                if has_get_images:
                    try:
                        images = report_tab.get_images()
                        print(f"✓ get_images method returns: {type(images)}")
                    except Exception as e:
                        print(f"✗ Error calling get_images: {e}")
                
            else:
                print("✗ Right panel does not have report_tab attribute")
                
            # Check if database has methods for report images
            has_add_report_image = hasattr(self.window.db, "add_report_image")
            has_get_report_images = hasattr(self.window.db, "get_report_images")
            
            print(f"{'✓' if has_add_report_image else '✗'} Database has add_report_image method")
            print(f"{'✓' if has_get_report_images else '✗'} Database has get_report_images method")
            
            # Check for handle_generate_report method
            has_generate_report = hasattr(self.window, "handle_generate_report")
            print(f"{'✓' if has_generate_report else '✗'} Main window has handle_generate_report method")
            
        except Exception as e:
            print(f"Error testing report generation functionality: {str(e)}")
    
    def cleanup(self):
        """Clean up resources and exit"""
        print("\n=== TESTS COMPLETED ===")
        # Exit application after a short delay
        QTimer.singleShot(500, self.app.quit)


if __name__ == "__main__":
    tester = SystemTester()
    sys.exit(tester.run())