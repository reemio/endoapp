#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Test the RightPanel initialization
try:
    from PySide6.QtWidgets import QApplication
    app = QApplication([])
    
    from ui.right_panel import RightPanel
    
    # Create an instance and check what happens
    print("Creating RightPanel instance...")
    right_panel = RightPanel()
    
    print("Checking for method existence...")
    print(f"Has handle_captured_image_selected_for_report: {hasattr(right_panel, 'handle_captured_image_selected_for_report')}")
    print(f"Has captured_media_tab: {hasattr(right_panel, 'captured_media_tab')}")
    
    if hasattr(right_panel, 'captured_media_tab'):
        print(f"captured_media_tab type: {type(right_panel.captured_media_tab)}")
        print(f"captured_media_tab has image_selected_for_report: {hasattr(right_panel.captured_media_tab, 'image_selected_for_report')}")
    
    print("Test completed successfully!")
    
except Exception as e:
    print(f"Error during test: {e}")
    import traceback
    traceback.print_exc()