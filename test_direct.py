"""
Direct camera test - bypasses all app logic
Run this on Windows to verify OpenCV can access the camera
"""
import cv2
import time
import sys

print("=" * 50)
print("DIRECT CAMERA TEST")
print("=" * 50)
print(f"OpenCV: {cv2.__version__}")
print()

# Test Device 1 with DirectShow (what worked in diagnostic)
device_id = 1
backend = cv2.CAP_DSHOW

print(f"Opening Device {device_id} with DirectShow...")

cap = cv2.VideoCapture(device_id, backend)

if not cap.isOpened():
    print("FAILED to open!")
    print()
    print("Trying Device 0...")
    cap = cv2.VideoCapture(0, backend)
    if not cap.isOpened():
        print("Device 0 also failed!")
        print()
        print("Trying with CAP_ANY...")
        cap = cv2.VideoCapture(0, cv2.CAP_ANY)
        if not cap.isOpened():
            print("All attempts failed!")
            print()
            print("Possible causes:")
            print("1. Another app is using the camera (close OBS, Zoom, etc)")
            print("2. Camera driver issue")
            print("3. Camera not connected")
            sys.exit(1)

print("SUCCESS - Camera opened!")

# Get info
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)
print(f"Resolution: {w}x{h}, FPS: {fps}")

# Try to read
print()
print("Reading frames...")
for i in range(5):
    ret, frame = cap.read()
    if ret and frame is not None:
        print(f"  Frame {i+1}: OK - shape={frame.shape}, brightness={frame.mean():.1f}")
    else:
        print(f"  Frame {i+1}: FAILED")
    time.sleep(0.2)

cap.release()
print()
print("Camera released.")
print()

# Now test if we can reopen it
print("Testing re-open (simulating app startup)...")
time.sleep(0.5)

cap2 = cv2.VideoCapture(device_id, backend)
if cap2.isOpened():
    ret, frame = cap2.read()
    if ret:
        print("Re-open SUCCESS - camera works!")
    else:
        print("Re-open opened but can't read frames")
    cap2.release()
else:
    print("Re-open FAILED - device might need longer release time")

print()
print("Test complete!")
