"""
Test both Device 0 and Device 1 to see what's available
"""
import cv2
import time

print("=" * 50)
print("TESTING ALL DEVICES")
print("=" * 50)

for device_id in [0, 1, 2]:
    print(f"\n--- Device {device_id} ---")

    for backend, name in [(cv2.CAP_DSHOW, "DirectShow"), (cv2.CAP_MSMF, "MSMF")]:
        cap = cv2.VideoCapture(device_id, backend)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                print(f"  {name}: OK - {w}x{h}, brightness={frame.mean():.1f}")
            else:
                print(f"  {name}: Opened but no frames")
            cap.release()
        else:
            print(f"  {name}: Failed to open")
        time.sleep(0.2)

print("\n" + "=" * 50)
print("Which device is your USB capture card?")
print("Look for the one with video feed (brightness > 0)")
