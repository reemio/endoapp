# CAMERA FPS TESTER - Run this to check your camera's actual FPS
# Save as: test_camera_fps.py

import cv2
import time

def test_camera_fps(camera_id=0, test_duration=10):
    """Test actual camera FPS"""
    
    print(f"Testing Camera {camera_id} for {test_duration} seconds...")
    
    # Try different backends
    backends = [
        (cv2.CAP_DSHOW, "DirectShow"),
        (cv2.CAP_ANY, "Any Available")
    ]
    
    for backend, name in backends:
        print(f"\n--- Testing with {name} Backend ---")
        
        cap = cv2.VideoCapture(camera_id, backend)
        
        if not cap.isOpened():
            print(f"❌ Failed to open camera with {name}")
            continue
        
        # Try different resolutions
        resolutions = [
            (640, 480, "VGA"),
            (1280, 720, "HD 720p"),
            (1920, 1080, "Full HD 1080p")
        ]
        
        for width, height, res_name in resolutions:
            print(f"\n  📐 Testing {res_name} ({width}x{height})")
            
            # Set resolution
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            cap.set(cv2.CAP_PROP_FPS, 30)  # Request 30 FPS
            
            # Get actual settings
            actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps_setting = cap.get(cv2.CAP_PROP_FPS)
            
            print(f"     📋 Camera reports: {actual_width}x{actual_height} @ {actual_fps_setting} FPS")
            
            # Test actual FPS
            frame_count = 0
            start_time = time.time()
            test_end_time = start_time + test_duration
            
            while time.time() < test_end_time:
                ret, frame = cap.read()
                if ret:
                    frame_count += 1
                else:
                    print("     ❌ Failed to read frame")
                    break
            
            elapsed_time = time.time() - start_time
            actual_fps = frame_count / elapsed_time
            
            print(f"     ✅ ACTUAL FPS: {actual_fps:.2f}")
            print(f"     📊 Frames captured: {frame_count} in {elapsed_time:.2f}s")
            
            # Determine if good for video recording
            if actual_fps >= 25:
                print(f"     🎬 EXCELLENT for video recording!")
            elif actual_fps >= 15:
                print(f"     ⚠️  ACCEPTABLE but may cause short videos")
            else:
                print(f"     ❌ TOO LOW for smooth video recording")
        
        cap.release()
    
    print(f"\n🏁 Camera FPS test complete!")
    print(f"\n💡 RECOMMENDATIONS:")
    print(f"   • If FPS < 20: Consider USB 3.0 camera")
    print(f"   • If FPS > 25: Adjust codec FPS in your app")
    print(f"   • Try lower resolution for higher FPS")

if __name__ == "__main__":
    # Test default camera
    test_camera_fps(0, 5)  # Test for 5 seconds
    
    # Uncomment to test additional cameras
    # test_camera_fps(1, 5)  # Test camera 1
    # test_camera_fps(2, 5)  # Test camera 2
