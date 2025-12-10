"""
Quick test for Device 1 with DirectShow
"""
import cv2
import time

print("Testing Device 1 with DirectShow...")

cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("FAILED to open device 1")
    exit(1)

print("Device opened!")

# Try higher resolution
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)

print(f"Resolution: {w}x{h} @ {fps}fps")

print("\nTrying to read frames...")
for i in range(10):
    ret, frame = cap.read()
    if ret and frame is not None:
        print(f"Frame {i+1}: {frame.shape} - mean brightness: {frame.mean():.1f}")
    else:
        print(f"Frame {i+1}: FAILED")
    time.sleep(0.1)

cap.release()
print("\nDone! If you saw frames with brightness > 0, the device works.")
