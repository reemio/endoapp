"""
Thorough USB Capture Device Diagnostic
"""
import cv2
import time
import subprocess

print("=" * 60)
print("USB CAPTURE DEVICE DIAGNOSTIC")
print("=" * 60)
print(f"OpenCV Version: {cv2.__version__}")
print()

# Check what video devices Windows sees
print("Checking Windows video devices...")
try:
    result = subprocess.run(
        ['powershell', '-Command',
         'Get-PnpDevice -Class Camera,Image -Status OK | Select-Object FriendlyName,InstanceId | Format-List'],
        capture_output=True, text=True, timeout=10
    )
    print(result.stdout if result.stdout else "No devices found via PnpDevice")
except Exception as e:
    print(f"Could not query Windows devices: {e}")

print()
print("-" * 60)
print("Testing OpenCV backends...")
print("-" * 60)

# Test more device indices and backends
backends = [
    (cv2.CAP_DSHOW, "DirectShow"),
    (cv2.CAP_MSMF, "Media Foundation"),
    (cv2.CAP_ANY, "Auto"),
]

found_devices = []

for device_id in range(5):
    for backend_id, backend_name in backends:
        try:
            # Suppress OpenCV warnings temporarily
            cap = cv2.VideoCapture(device_id, backend_id)

            if cap.isOpened():
                # Give it time to initialize
                time.sleep(0.3)

                # Try multiple reads
                success = False
                for attempt in range(5):
                    ret, frame = cap.read()
                    if ret and frame is not None and frame.size > 0:
                        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        fps = cap.get(cv2.CAP_PROP_FPS)
                        fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
                        fourcc_str = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])

                        print(f"✓ Device {device_id} + {backend_name}:")
                        print(f"    Resolution: {w}x{h}")
                        print(f"    FPS: {fps}")
                        print(f"    FourCC: {fourcc_str}")
                        print(f"    Brightness: {frame.mean():.1f}")

                        found_devices.append({
                            'id': device_id,
                            'backend': backend_name,
                            'backend_id': backend_id,
                            'resolution': f"{w}x{h}"
                        })
                        success = True
                        break
                    time.sleep(0.1)

                if not success:
                    print(f"✗ Device {device_id} + {backend_name}: Opens but no frames")

                cap.release()
                time.sleep(0.2)
                break  # Found working backend for this device
            else:
                cap.release()

        except Exception as e:
            print(f"✗ Device {device_id} + {backend_name}: Error - {e}")

print()
print("=" * 60)
print("SUMMARY")
print("=" * 60)

if found_devices:
    print(f"\nFound {len(found_devices)} working device(s):")
    for dev in found_devices:
        print(f"  - Device {dev['id']} via {dev['backend']} ({dev['resolution']})")

    print("\nTo use in the app, edit run_windows.bat:")
    print(f"  set PREFERRED_CAMERA_ID={found_devices[0]['id']}")
else:
    print("\nNO WORKING DEVICES FOUND!")
    print()
    print("Troubleshooting steps:")
    print("1. Unplug and replug the USB capture device")
    print("2. Check Device Manager for any warning icons")
    print("3. Try a different USB port")
    print("4. Make sure no other app is using the camera")
    print("5. Restart the computer")
    print()
    print("If device appears in Device Manager but not here,")
    print("the device may need specific drivers or may not")
    print("be compatible with OpenCV/DirectShow.")
