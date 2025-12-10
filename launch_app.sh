#!/bin/bash

# Clear any Qt plugin paths that might conflict
unset QT_PLUGIN_PATH
export QT_DEBUG_PLUGINS=0

# Set the display for GUI
export DISPLAY=:0

# For WSL2 with Windows 10 (using X server), uncomment this instead:
# export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0.0

# Force Qt to not use the OpenCV plugins
export QT_QPA_PLATFORM_PLUGIN_PATH=/home/dq/.local/lib/python3.8/site-packages/PySide6/Qt/plugins/platforms

# Alternative: Use software rendering if hardware acceleration issues
# export QT_XCB_GL_INTEGRATION=none

echo "Starting Endoscopy Reporting System..."
echo "Display: $DISPLAY"

# Run the application
python3 run.py