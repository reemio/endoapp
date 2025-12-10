"""
Camera Diagnostic Script - Tests all backends and devices
Run this to identify USB capture device issues
"""
import cv2
import sys
import time

print("=" * 60)
print("CAMERA DIAGNOSTIC TOOL")
print("=" * 60)
print(f"OpenCV version: {cv2.__version__}")
print()

# All available backends on Windows
backends = [
    (cv2.CAP_DSHOW, "DirectShow (DSHOW)"),
    (cv2.CAP_MSMF, "Media Foundation (MSMF)"),
    (cv2.CAP_ANY, "Auto (ANY)"),
]

# Check if running on Windows
if sys.platform == 'win32':
    print("Platform: Windows")
else:
    print(f"Platform: {sys.platform}")
    backends = [
        (cv2.CAP_V4L2, "V4L2"),
        (cv2.CAP_ANY, "Auto (ANY)"),
    ]

print()
print("Scanning devices 0-9 with all backends...")
print("-" * 60)

found_devices = []

for device_idx in range(10):
    for backend_id, backend_name in backends:
        try:
            print(f"Testing device {device_idx} with {backend_name}...", end=" ", flush=True)

            # Try to open
            cap = cv2.VideoCapture(device_idx, backend_id)

            if not cap.isOpened():
                print("FAILED (can't open)")
                continue

            # Set small buffer
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            # Get properties before reading
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)

            # Try to read frames (multiple attempts for USB devices)
            success = False
            frame = None
            for attempt in range(10):
                ret, frame = cap.read()
                if ret and frame is not None and frame.size > 0:
                    success = True
                    break
                time.sleep(0.2)

            cap.release()

            if success:
                print(f"SUCCESS! {width}x{height} @ {fps}fps")
                found_devices.append({
                    'index': device_idx,
                    'backend': backend_name,
                    'backend_id': backend_id,
                    'width': width,
                    'height': height,
                    'fps': fps
                })
                # Found working backend for this device, skip others
                break
            else:
                print(f"OPENED but no frames ({width}x{height})")

        except Exception as e:
            print(f"ERROR: {e}")

        # Small delay between attempts
        time.sleep(0.1)

print()
print("=" * 60)
print("RESULTS")
print("=" * 60)

if found_devices:
    print(f"\nFound {len(found_devices)} working device(s):\n")
    for dev in found_devices:
        print(f"  Device {dev['index']}:")
        print(f"    Backend: {dev['backend']}")
        print(f"    Resolution: {dev['width']}x{dev['height']}")
        print(f"    FPS: {dev['fps']}")
        print()

    print("\nRECOMMENDATION:")
    print("-" * 40)
    # Find USB capture device (usually higher resolution)
    capture_devices = [d for d in found_devices if d['width'] >= 1280 or d['height'] >= 720]
    if capture_devices:
        dev = capture_devices[0]
        print(f"Set environment variable before running app:")
        print(f"  set PREFERRED_CAMERA_ID={dev['index']}")
    else:
        dev = found_devices[0]
        print(f"Use device {dev['index']} with {dev['backend']}")
else:
    print("\nNO WORKING DEVICES FOUND!")
    print()
    print("Troubleshooting:")
    print("1. Check if USB capture device is plugged in")
    print("2. Check Device Manager for the device")
    print("3. Try unplugging and replugging the device")
    print("4. Check if OBS or another app is using the device")
    print("5. Install device drivers if needed")
    print()
    print("Since OBS works, the device might need:")
    print("- A specific backend not supported by OpenCV")
    print("- DirectShow filter registration")

print()
print("=" * 60)
input("Press Enter to exit...")
