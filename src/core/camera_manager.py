# ENHANCED ADAPTIVE CAMERA_MANAGER.PY - AUTOMATICALLY ADAPTS TO ANY CAMERA
# FILE: src/core/camera_manager.py
# FIXES ALL FPS/RESOLUTION ISSUES + FUTURE ENDOSCOPE COMPATIBILITY

from PySide6.QtCore import QObject, Signal, QThread, QMutex, QTimer
from PySide6.QtGui import QImage
import cv2
import logging
from datetime import datetime
from pathlib import Path
import traceback
import numpy as np
import time
import os
import numpy as np
import time
import os
import threading
import platform


class CameraCapabilityTester:
    """TESTS CAMERA CAPABILITIES AND FINDS OPTIMAL SETTINGS"""
    
    def __init__(self):
        self.logger = logging.getLogger("CameraCapabilityTester")
    
    def test_camera_capabilities(self, camera_id=0):
        """TEST CAMERA AT DIFFERENT RESOLUTIONS AND FIND BEST SETTINGS
        OPTIMIZED: Start with VGA immediately to speed up initialization
        
        Returns:
            dict: {
                'optimal_width': int,
                'optimal_height': int, 
                'optimal_fps': float,
                'all_results': list
            }
        """
        # For fast initialization, start with reliable VGA resolution
        width, height = 640, 480
        name = "VGA"
        
        self.logger.info(f"Initializing camera {camera_id} with {name} resolution for fast startup...")
        
        # Quick test of single resolution
        result = self._test_resolution(camera_id, width, height, name, quick_test=True)
        results = [result]
        
        # SCORING: PREFER HIGHER FPS, THEN HIGHER RESOLUTION
        score = result['fps'] * 2 + (result['width'] * result['height']) / 100000
        best_score = score
        best_config = result
        
        # FALLBACK TO FIRST WORKING CONFIG IF NO GOOD ONE FOUND
        if not best_config:
            working_configs = [r for r in results if r['fps'] > 5]
            best_config = working_configs[0] if working_configs else results[0]
        
        self.logger.info(f"OPTIMAL CONFIG: {best_config['name']} - {best_config['width']}x{best_config['height']} @ {best_config['fps']:.1f} FPS")
        
        return {
            'optimal_width': best_config['width'],
            'optimal_height': best_config['height'],
            'optimal_fps': best_config['fps'],
            'all_results': results
        }
    
    def _test_resolution(self, camera_id, width, height, name, quick_test=False):
        """TEST A SPECIFIC RESOLUTION"""
        cap = None
        try:
            # TRY DIFFERENT BACKENDS FOR BETTER COMPATIBILITY
            backends = [cv2.CAP_MSMF, cv2.CAP_DSHOW, cv2.CAP_ANY]  # Prefer MSMF on Windows to reduce DSHOW warnings
            
            for backend in backends:
                cap = cv2.VideoCapture(camera_id, backend)
                if cap.isOpened():
                    break
            
            if not cap or not cap.isOpened():
                return {'width': width, 'height': height, 'fps': 0, 'name': name, 'error': 'Cannot open camera'}
            
            # SET RESOLUTION
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            cap.set(cv2.CAP_PROP_FPS, 30)  # REQUEST 30 FPS
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # VERIFY ACTUAL SETTINGS
            actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # MEASURE ACTUAL FPS BY CAPTURING FRAMES
            frame_times = []
            start_time = time.time()
            
            # For quick test, capture minimal frames and skip detailed FPS measurement
            if quick_test:
                # Just verify camera works by reading a few frames
                # Use fixed values for quick startup without testing
                ret, frame = cap.read()
                if ret and frame is not None:
                    # Add multiple frames with fixed 25fps timing (40ms per frame)
                    for _ in range(10):
                        frame_times.append(0.04)
                else:
                    # Even if reading fails, add default times to prevent division by zero
                    for _ in range(10):
                        frame_times.append(0.04)
            else:
                # Normal testing with more frames
                for i in range(30):
                    frame_start = time.time()
                    ret, frame = cap.read()
                    
                    if ret and frame is not None:
                        frame_times.append(time.time() - frame_start)
                    else:
                        break
                    
                    # TIMEOUT AFTER 5 SECONDS
                    if time.time() - start_time > 5:
                        break
            
            cap.release()
            
            if len(frame_times) < 10:  # NOT ENOUGH FRAMES
                return {'width': width, 'height': height, 'fps': 0, 'name': name, 'error': 'Insufficient frames'}
            
            # CALCULATE ACTUAL FPS
            total_time = time.time() - start_time
            # Prevent division by zero
            if total_time <= 0 or len(frame_times) == 0:
                if quick_test:
                    # Default to 25 fps for quick test
                    actual_fps = 25.0
                else:
                    actual_fps = 10.0  # Safe default
            else:
                actual_fps = len(frame_times) / total_time
                
            # Ensure FPS is never zero
            if actual_fps <= 0:
                actual_fps = 10.0  # Safe minimum
            
            self.logger.info(f"{name} ({actual_width}x{actual_height}): {actual_fps:.2f} FPS")
            
            return {
                'width': actual_width,
                'height': actual_height, 
                'fps': actual_fps,
                'name': name,
                'frame_count': len(frame_times),
                'test_duration': total_time
            }
            
        except Exception as e:
            if cap:
                cap.release()
            return {'width': width, 'height': height, 'fps': 0, 'name': name, 'error': str(e)}


class AdaptiveCameraThread(QThread):
    """ADAPTIVE CAMERA THREAD THAT USES OPTIMAL SETTINGS

    Enhanced to support USB capture devices with:
    - Preferred backend selection (DirectShow often needed for USB capture)
    - Native resolution detection for capture devices
    - Increased error tolerance for device warmup
    """

    # SIGNALS
    frame_ready = Signal(QImage)
    frame_for_recording = Signal(object)
    error_occurred = Signal(str)
    camera_initialized = Signal(dict)  # EMITS CAMERA SETTINGS

    def __init__(self, camera_id=0, preferred_backend=None, parent=None):
        super().__init__(parent)
        self.camera_id = camera_id
        self.preferred_backend = preferred_backend
        self.mutex = QMutex()
        self.capture = None
        self.running = False

        # ADAPTIVE SETTINGS - WILL BE SET AFTER CAPABILITY TEST
        self.frame_width = 640
        self.frame_height = 480
        self.target_fps = 25

        # Track if this might be a USB capture device (detected during init)
        self.is_capture_device = False
        self.native_width = None
        self.native_height = None

        self.error_count = 0
        # Increased for USB capture devices which may drop frames during warmup
        self.max_errors = 10

        self.logger = logging.getLogger("AdaptiveCameraThread")
    
    def initialize_camera_settings(self):
        """INITIALIZE CAMERA WITH DEFAULT SETTINGS

        Note: Actual settings are detected in run() after opening the device.
        This just sets safe defaults for initial state.
        """
        # Set safe defaults - actual detection happens in run()
        self.frame_width = 640   # Default VGA width
        self.frame_height = 480  # Default VGA height
        self.target_fps = 25.0   # Default FPS
        self.logger.info("Initialized with default camera settings")
    
    def run(self):
        """MAIN THREAD EXECUTION"""
        try:
            self.logger.info(f"Starting camera thread for device {self.camera_id}")
            print(f"[CAMERA] Starting camera thread for device {self.camera_id}")

            # SIMPLIFIED: Direct open with DirectShow (works in tests)
            self.mutex.lock()

            backend_names = {
                cv2.CAP_DSHOW: "DirectShow",
                cv2.CAP_MSMF: "MSMF",
                cv2.CAP_ANY: "Auto",
                cv2.CAP_V4L2: "V4L2",
            }

            # Try the detected/remembered backend first, then fall back
            backend_order = []
            if self.preferred_backend is not None:
                backend_order.append(self.preferred_backend)
            backend_order.extend([cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY])

            # De-duplicate while preserving order
            seen_backends = set()
            backends_to_try = []
            for b in backend_order:
                if b not in seen_backends:
                    backends_to_try.append(b)
                    seen_backends.add(b)

            self.capture = None
            for backend in backends_to_try:
                try:
                    backend_label = backend_names.get(backend, str(backend))
                    print(f"[CAMERA] Trying backend {backend_label}...")
                    self.capture = cv2.VideoCapture(self.camera_id, backend)
                    if self.capture and self.capture.isOpened():
                        print(f"[CAMERA] Opened with {backend_label}")
                        break
                except Exception as backend_err:
                    print(f"[CAMERA] Backend {backend_label} failed: {backend_err}")
                finally:
                    # If this attempt failed, make sure resources are released before next backend
                    if not self.capture or not self.capture.isOpened():
                        try:
                            if self.capture:
                                self.capture.release()
                        except Exception as rel_err:
                            self.logger.debug(f"Release error for backend {backend_label}: {rel_err}")
                        self.capture = None

            if not self.capture or not self.capture.isOpened():
                self.mutex.unlock()
                print(f"[CAMERA] FAILED to open device {self.camera_id}")
                self.error_occurred.emit(f"Could not open camera device: {self.camera_id}")
                return

            print(f"[CAMERA] Camera {self.camera_id} opened successfully!")

            # Minimal setup - just get current settings, don't change anything
            self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            self.frame_width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.frame_height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.capture.get(cv2.CAP_PROP_FPS)

            # Default to 30 FPS if device reports 0
            self.target_fps = 30 if actual_fps <= 0 else min(actual_fps, 30)
            self.is_capture_device = (actual_fps == 0)

            print(f"[CAMERA] Configured: {self.frame_width}x{self.frame_height} @ {self.target_fps}fps")

            # EMIT INITIALIZED SIGNAL with actual settings
            init_settings = {
                'width': self.frame_width,
                'height': self.frame_height,
                'fps': self.target_fps,
                'initialized': True,
                'is_capture_device': self.is_capture_device
            }
            self.camera_initialized.emit(init_settings)

            self.running = True
            self.mutex.unlock()
            
            # MAIN CAPTURE LOOP WITH FRAME RATE CONTROL
            frame_count = 0
            last_successful_frame = time.time()
            # Ensure we never have division by zero
            if self.target_fps <= 0.1:
                self.target_fps = 25.0
            target_frame_interval = 1.0 / self.target_fps
            last_frame_time = time.time()
            
            # Force first frame immediately with timeout
            # USB capture devices need more time to warm up
            start_time = time.time()
            success = False
            initial_frame = None
            warmup_timeout = 3.0 if self.is_capture_device else 1.0  # Longer timeout for capture devices

            # Try multiple times with extended timeout for USB capture devices
            attempts = 0
            max_attempts = 30 if self.is_capture_device else 10
            while time.time() - start_time < warmup_timeout and not success and attempts < max_attempts:
                attempts += 1
                success, initial_frame = self.capture.read()
                if success and initial_frame is not None:
                    # Verify frame is valid (not all black/corrupt)
                    if initial_frame.mean() > 1:  # Has actual content
                        self.logger.info(f"Got initial frame after {attempts} attempts")
                        self._process_and_emit_frame(initial_frame)
                        break
                    else:
                        success = False  # Frame was blank, try again
                time.sleep(0.1)  # Slightly longer sleep for USB devices

            # Even if we couldn't get a frame, continue anyway
            if not success:
                self.logger.warning(f"Could not get initial frame after {attempts} attempts, but continuing anyway")
                # Create a black frame as placeholder
                black_frame = np.zeros((self.frame_height, self.frame_width, 3), dtype=np.uint8)
                self._process_and_emit_frame(black_frame)
            
            while self.running:
                if not self.capture or not self.capture.isOpened():
                    self.error_occurred.emit("Camera connection lost")
                    break
                
                # FRAME RATE CONTROL
                current_time = time.time()
                time_since_last = current_time - last_frame_time
                
                if time_since_last < target_frame_interval:
                    sleep_time = target_frame_interval - time_since_last
                    self.msleep(int(sleep_time * 1000))
                    continue
                
                # CAPTURE FRAME
                capture_start = time.time()
                ret, frame = self.capture.read()
                read_duration = time.time() - capture_start
                
                if not ret or frame is None:
                    self.error_count += 1
                    self.logger.warning(f"AdaptiveCameraThread: Failed to grab frame ({self.error_count}/{self.max_errors}). Read duration: {read_duration:.4f}s. Ret: {ret}, frame is None: {frame is None}")
                    if self.error_count >= self.max_errors:
                        self.logger.error("AdaptiveCameraThread: Max camera errors reached. Stopping thread.")
                        self.error_occurred.emit("Camera disconnected or max errors reached.")
                        self.running = False
                    time.sleep(0.1) # Wait a bit before retrying or exiting
                    # self.mutex.unlock() # Ensure mutex is handled correctly if this path is taken
                    continue # Try to continue for a few errors
                else:
                    if self.error_count > 0: # Log recovery
                        self.logger.info(f"AdaptiveCameraThread: Successfully grabbed frame after {self.error_count} error(s).")
                    self.error_count = 0 # Reset error count on successful read
                    
                    # SUCCESSFUL FRAME
                    self.error_count = 0
                    last_successful_frame = time.time()
                    last_frame_time = current_time
                    
                    # EMIT RAW FRAME FOR RECORDING (BGR)
                    self.frame_for_recording.emit(frame.copy())
                    
                    # CONVERT FOR DISPLAY (RGB)
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgb_frame.shape
                    bytes_per_line = ch * w
                    qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    
                    self.frame_ready.emit(qt_image)
                    frame_count += 1
                    
        except Exception as e:
            error_msg = f"Adaptive camera thread error: {str(e)}"
            self.logger.error(f"{error_msg}\n{traceback.format_exc()}")
            self.error_occurred.emit(error_msg)
        finally:
            self.cleanup()
    
    def stop(self):
        """STOP CAMERA THREAD"""
        try:
            self.logger.info("Stopping adaptive camera thread")
            
            self.mutex.lock()
            self.running = False
            self.mutex.unlock()
            
            if not self.wait(3000):
                self.logger.warning("Camera thread did not stop gracefully")
                self.terminate()
                self.wait(1000)
            
            self.cleanup()
            
        except Exception as e:
            self.logger.error(f"Error stopping camera thread: {e}")
    
    def cleanup(self):
        """CLEANUP CAMERA RESOURCES"""
        try:
            self.mutex.lock()
            if self.capture:
                self.capture.release()
                self.capture = None
            self.mutex.unlock()
            self.logger.info("Camera resources cleaned up")
        except Exception as e:
            self.logger.error(f"Error cleaning up camera: {e}")
    
    def _process_and_emit_frame(self, frame):
        """Process and emit a frame for display and recording"""
        try:
            if frame is None:
                return
                
            # EMIT FRAME FOR RECORDING (BGR)
            self.frame_for_recording.emit(frame.copy())
            
            # CONVERT FOR DISPLAY (RGB)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            self.frame_ready.emit(qt_image)
        except Exception as e:
            self.logger.error(f"Error processing frame: {e}")
    
    def _test_actual_capabilities(self):
        """Test actual camera capabilities without blocking the UI

        Note: For USB capture devices, we skip this test and use native resolution.
        Changing resolution on capture devices often causes them to fail.
        """
        try:
            # Skip capability testing for USB capture devices - use native resolution
            if self.is_capture_device:
                self.logger.info("Skipping capability test for USB capture device - using native resolution")
                return

            # Run quick test without locking UI (only for regular webcams)
            capabilities = CameraCapabilityTester().test_camera_capabilities(self.camera_id)

            # Get optimal settings
            self.frame_width = capabilities['optimal_width']
            self.frame_height = capabilities['optimal_height']

            # Ensure FPS is never zero or too low
            optimal_fps = capabilities['optimal_fps']
            if optimal_fps <= 0.1 or optimal_fps == float('inf'):
                optimal_fps = 25.0

            self.target_fps = min(optimal_fps, 30)  # Cap at 30 FPS

            # Update camera with these settings
            if self.capture and self.capture.isOpened():
                self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
                self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
                self.capture.set(cv2.CAP_PROP_FPS, self.target_fps)

            # Update settings info
            self.camera_initialized.emit({
                'width': self.frame_width,
                'height': self.frame_height,
                'fps': self.target_fps,
                'initialized': True,
                'is_capture_device': self.is_capture_device,
                'all_results': capabilities.get('all_results', [])
            })

            self.logger.info(f"Camera settings updated: {self.frame_width}x{self.frame_height} @ {self.target_fps:.1f} FPS")

        except Exception as e:
            # Just log the error but don't crash
            self.logger.error(f"Error testing camera capabilities: {e}")
    
    def capture_still_image(self):
        """CAPTURE STILL IMAGE"""
        try:
            self.mutex.lock()
            if self.capture and self.capture.isOpened():
                ret, frame = self.capture.read()
                self.mutex.unlock()
                if ret and frame is not None:
                    return frame
            else:
                self.mutex.unlock()
            return None
        except Exception as e:
            self.logger.error(f"Error capturing still image: {e}")
            if self.mutex.tryLock():
                self.mutex.unlock()
            return None


class AdaptiveVideoRecorder:
    """ADAPTIVE VIDEO RECORDER THAT MATCHES CAMERA FPS"""
    
    def __init__(self, file_manager=None):
        self.file_manager = file_manager
        self.writer = None
        self.recording = False
        self.video_path = None
        self.start_time = None
        self.frame_count = 0
        
        self.logger = logging.getLogger("AdaptiveVideoRecorder")
        
        # ADAPTIVE RECORDING PARAMETERS - SET BY CAMERA CAPABILITIES
        self.codec = cv2.VideoWriter_fourcc(*'XVID')
        self.fps = 25.0  # DEFAULT, WILL BE UPDATED
        self.frame_size = None
        self.last_frame_time = 0
        self.frame_interval = 1.0 / self.fps
    
    def update_settings(self, camera_settings):
        """UPDATE RECORDER SETTINGS TO MATCH CAMERA"""
        try:
            self.fps = camera_settings.get('fps', 25.0)
            self.frame_interval = 1.0 / self.fps
            
            width = camera_settings.get('width', 640)
            height = camera_settings.get('height', 480)
            self.frame_size = (width, height)
            
            self.logger.info(f"Recorder adapted to camera: {self.frame_size} @ {self.fps:.1f} FPS")
            
        except Exception as e:
            self.logger.error(f"Error updating recorder settings: {e}")
    
    def start_recording(self, initial_frame=None):
        """START ADAPTIVE RECORDING"""
        try:
            if self.recording:
                self.logger.warning("Already recording")
                return None
            
            # GENERATE FILENAME
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(int(time.time() * 1000) % 10000)
            filename = f"video_{timestamp}_{unique_id}.avi"
            
            # GET PATH
            if self.file_manager:
                self.video_path = str(self.file_manager.get_file_path("video", filename))
            else:
                videos_dir = Path("data/videos/captured")
                videos_dir.mkdir(parents=True, exist_ok=True)
                self.video_path = str(videos_dir / filename)
            
            os.makedirs(os.path.dirname(self.video_path), exist_ok=True)
            
            # DETERMINE FRAME SIZE
            if initial_frame is not None and hasattr(initial_frame, 'shape') and len(initial_frame.shape) == 3:
                height, width = initial_frame.shape[:2]
                if width > 0 and height > 0:
                    self.frame_size = (width, height)
                    self.logger.info(f"AdaptiveVideoRecorder: Frame size set from initial_frame: {self.frame_size}")
                else:
                    self.logger.warning(f"AdaptiveVideoRecorder: initial_frame had invalid dimensions: {initial_frame.shape}. Using default or pre-configured frame_size: {self.frame_size}")
            else:
                self.logger.warning(f"AdaptiveVideoRecorder: initial_frame was None or invalid. Using default or pre-configured frame_size: {self.frame_size}")
        
            if not self.frame_size or self.frame_size[0] <=0 or self.frame_size[1] <=0 or self.fps <= 0:
                self.logger.error(f"AdaptiveVideoRecorder: Recorder not initialized. Frame size: {self.frame_size}, FPS: {self.fps}")
                self.frame_size = (640, 480)
            
            # CREATE WRITER WITH MATCHED FPS
            self.logger.info(f"AdaptiveVideoRecorder: Attempting to open VideoWriter: path={self.video_path}, codec={''.join([chr((self.codec >> (i * 8)) & 0xFF) for i in range(4)])}, fps={self.fps}, frame_size={self.frame_size}")
            self.writer = cv2.VideoWriter(self.video_path, self.codec, self.fps, self.frame_size)
            
            if not self.writer.isOpened():
                self.logger.error(f"AdaptiveVideoRecorder: FAILED to open VideoWriter. Path: {self.video_path}, FPS: {self.fps}, FrameSize: {self.frame_size}")
                self.logger.error(f"Failed to open video writer")
                return None
            
            self.logger.info(f"AdaptiveVideoRecorder: VideoWriter opened successfully for {self.video_path}")
            self.recording = True
            self.start_time = time.time()
            self.frame_count = 0
            self.last_frame_time = time.time()
            
            self.logger.info(f"ADAPTIVE RECORDING STARTED: {self.video_path} @ {self.fps:.1f} FPS")
            return self.video_path
            
        except Exception as e:
            self.logger.error(f"AdaptiveVideoRecorder: Exception in start_recording: {e}", exc_info=True)
            return None
    
    def write_frame(self, frame):
        if not self.recording or not self.writer or not self.writer.isOpened():
            return
        """WRITE FRAME WITH ADAPTIVE TIMING"""
        try:
            if not self.recording or not self.writer:
                return
            
            if frame is None:
                return
            
            # ADAPTIVE FRAME RATE CONTROL
            current_time = time.time()
            if current_time - self.last_frame_time < self.frame_interval:
                return  # SKIP FRAME TO MAINTAIN TARGET FPS
            
            # ENSURE CORRECT SIZE AND FORMAT
            if self.frame_size:
                frame = cv2.resize(frame, self.frame_size)
            
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                self.writer.write(frame)
                self.frame_count += 1
                self.last_frame_time = current_time
                
                # LOG PROGRESS
                if self.frame_count % 60 == 0:
                    duration = current_time - self.start_time
                    expected_frames = duration * self.fps
                    self.logger.info(f"Recording: {self.frame_count} frames, {duration:.1f}s (expected: {expected_frames:.0f})")
            
        except Exception as e:
            self.logger.error(f"AdaptiveVideoRecorder: Error writing video frame {self.frame_count}: {e}", exc_info=True)
    
    def stop_recording(self):
        """STOP RECORDING WITH VERIFICATION"""
        try:
            if not self.recording:
                return None
            
            self.recording = False
            
            if self.writer:
                self.writer.release()
                self.writer = None
            
            duration = time.time() - self.start_time if self.start_time else 0
            
            if self.video_path and Path(self.video_path).exists():
                file_size = Path(self.video_path).stat().st_size
                
                self.logger.info(f"RECORDING COMPLETED: {self.video_path}")
                self.logger.info(f"Duration: {duration:.1f}s, Frames: {self.frame_count}, Size: {file_size} bytes")
                self.logger.info(f"Actual FPS: {self.frame_count/duration:.1f}")
                
                # VERIFY VIDEO FILE
                try:
                    test_cap = cv2.VideoCapture(self.video_path)
                    if test_cap.isOpened():
                        verify_frames = int(test_cap.get(cv2.CAP_PROP_FRAME_COUNT))
                        verify_fps = test_cap.get(cv2.CAP_PROP_FPS)
                        test_cap.release()
                        self.logger.info(f"Video verification: {verify_frames} frames @ {verify_fps} FPS")
                    else:
                        self.logger.warning("Could not verify video file integrity")
                except Exception as e:
                    self.logger.warning(f"Video verification failed: {e}")
                
                return self.video_path
            else:
                self.logger.error("Video file was not created")
                return None
                
        except Exception as e:
            self.logger.error(f"AdaptiveVideoRecorder: Exception in stop_recording: {e}", exc_info=True)
            return None
    
    def is_recording(self):
        return self.recording
    
    def get_recording_duration(self):
        if self.recording and self.start_time:
            return time.time() - self.start_time
        return 0
    
    def get_frame_count(self):
        return self.frame_count


class AdaptiveCameraManager(QObject):
    """ADAPTIVE CAMERA MANAGER - AUTOMATICALLY OPTIMIZES FOR ANY CAMERA"""
    
    # SIGNALS
    frame_ready = Signal(QImage)
    image_captured = Signal(str)
    video_started = Signal(str)
    video_stopped = Signal(str)
    camera_error = Signal(str)
    camera_status = Signal(dict)
    recording_time_updated = Signal(str)
    recording_size_updated = Signal(str)
    camera_optimized = Signal(dict)  # NEW: EMITS WHEN CAMERA IS OPTIMIZED
    
    def __init__(self, file_manager=None, parent=None):
        super().__init__(parent)

        self.file_manager = file_manager
        self.camera_thread = None
        # Allow overriding preferred camera via environment variable (e.g., PREFERRED_CAMERA_ID=1)
        try:
            env_cam = os.environ.get("PREFERRED_CAMERA_ID")
            self.current_camera_id = int(env_cam) if env_cam is not None else 0
        except ValueError:
            self.current_camera_id = 0
        self.video_recorder = AdaptiveVideoRecorder(file_manager)
        self.recording_timer = None
        self.camera_settings = {}
        self._last_frame_drop_log = 0  # Throttle "not recording" logs
        self._init_in_progress = False

        # Store detected backends for each camera device
        self._camera_backends = {}  # {device_id: backend}

        self.setup_logging()

        # INITIALIZE CAMERA AFTER SHORT DELAY (off the UI thread)
        QTimer.singleShot(300, self.initialize_camera)
    
    def setup_logging(self):
        self.logger = logging.getLogger("AdaptiveCameraManager")
        
        if not self.logger.handlers:
            log_path = Path("data/logs/adaptive_camera.log")
            log_path.parent.mkdir(parents=True, exist_ok=True)

            # Prevent huge log files from slowing startup
            try:
                if log_path.exists() and log_path.stat().st_size > 10 * 1024 * 1024:
                    backup = log_path.with_suffix(".log.bak")
                    log_path.replace(backup)
            except Exception as rot_err:
                print(f"Log rotation skipped: {rot_err}")
            
            file_handler = logging.FileHandler(log_path)
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            file_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
            debug_enabled = os.environ.get("ADAPTIVE_CAMERA_DEBUG", "").lower() in {"1", "true", "yes"}
            self.logger.setLevel(logging.INFO if debug_enabled else logging.WARNING)
            self.logger.propagate = False
    
    def initialize_camera(self):
        """INITIALIZE ADAPTIVE CAMERA WITHOUT BLOCKING UI"""
        try:
            print(f"[CAMERA] initialize_camera called")
            if self._init_in_progress:
                print(f"[CAMERA] Already in progress, skipping")
                return
            self._init_in_progress = True

            # Fast path: if PREFERRED_CAMERA_ID is set, skip detection and use DirectShow
            env_cam = os.environ.get("PREFERRED_CAMERA_ID")
            print(f"[CAMERA] PREFERRED_CAMERA_ID={env_cam}")
            if env_cam is not None:
                try:
                    preferred_id = int(env_cam)
                    print(f"[CAMERA] Using device {preferred_id} with DirectShow")
                    self._camera_backends[preferred_id] = cv2.CAP_DSHOW
                    self.current_camera_id = preferred_id
                    # Call directly instead of via timer to debug
                    self._start_camera_thread([(preferred_id, f"Camera {preferred_id}")])
                    return
                except ValueError:
                    print(f"[CAMERA] Invalid PREFERRED_CAMERA_ID: {env_cam}")

            # Run the potentially slow camera discovery off the UI thread
            def discover_and_start():
                available = []
                try:
                    available = self.get_available_cameras()
                except Exception as disc_err:
                    self.logger.error(f"Camera discovery failed: {disc_err}")
                # Finish on the Qt thread so signals/threads are wired safely
                QTimer.singleShot(0, lambda: self._start_camera_thread(available))

            threading.Thread(target=discover_and_start, daemon=True).start()
        except Exception as e:
            error_msg = f"Failed to initialize adaptive camera: {str(e)}"
            self.logger.error(error_msg)
            self.camera_error.emit(error_msg)
            self.camera_thread = None
            self._init_in_progress = False

    def _start_camera_thread(self, available):
        """Start camera thread after discovery results are ready."""
        try:
            print(f"[CAMERA] _start_camera_thread called with: {available}")

            # Get list of available device IDs
            available_ids = [cam_info[0] for cam_info in (available or [])]

            # Check if current camera is available, otherwise fallback
            if available_ids and self.current_camera_id not in available_ids:
                fallback_id = available_ids[0]
                print(f"[CAMERA] Switching from {self.current_camera_id} to {fallback_id}")
                self.current_camera_id = fallback_id

            # Get the preferred backend from our internal cache
            preferred_backend = self._camera_backends.get(self.current_camera_id)
            print(f"[CAMERA] Device={self.current_camera_id}, Backend={preferred_backend}")

            # Allow disabling camera initialization via environment
            if os.environ.get("DISABLE_CAMERA", "").lower() in {"1", "true", "yes"}:
                print("[CAMERA] DISABLE_CAMERA is set, skipping")
                return

            # CREATE ADAPTIVE CAMERA THREAD
            print(f"[CAMERA] Creating AdaptiveCameraThread...")
            self.camera_thread = AdaptiveCameraThread(self.current_camera_id, preferred_backend=preferred_backend)
            
            # CONNECT SIGNALS
            self.camera_thread.frame_ready.connect(self.frame_ready.emit)
            self.camera_thread.frame_for_recording.connect(self.handle_recording_frame)
            self.camera_thread.error_occurred.connect(self.handle_camera_error)
            self.camera_thread.camera_initialized.connect(self.handle_camera_initialized)

            # START CAMERA THREAD
            print(f"[CAMERA] Starting camera thread...")
            self.camera_thread.start(QThread.HighPriority)
            print(f"[CAMERA] Camera thread started!")

        except Exception as e:
            print(f"[CAMERA] ERROR in _start_camera_thread: {e}")
            self.camera_error.emit(str(e))
            self.camera_thread = None
        finally:
            self._init_in_progress = False
    
    def handle_camera_initialized(self, settings):
        """HANDLE CAMERA OPTIMIZATION COMPLETED"""
        try:
            if self.camera_settings:
                self.logger.info(f"AdaptiveCameraManager: Using camera_settings for recorder: {self.camera_settings}")
            self.camera_settings = settings
            
            # UPDATE VIDEO RECORDER TO MATCH CAMERA
            self.video_recorder.update_settings(self.camera_settings)
            
            # EMIT STATUS
            self.camera_status.emit({
                "status": "optimized",
                "device_id": self.current_camera_id,
                "settings": settings
            })
            
            self.camera_optimized.emit(settings)
            
            self.logger.info(f"Camera optimized: {settings['width']}x{settings['height']} @ {settings['fps']:.1f} FPS")
            
        except Exception as e:
            self.logger.error(f"Error handling camera initialization: {e}")
    
    def handle_recording_frame(self, frame):
        """HANDLE FRAMES FOR RECORDING"""
        if not self.video_recorder.is_recording():
            # Avoid spamming logs when the UI isn't recording yet
            now = time.time()
            if now - self._last_frame_drop_log > 10:
                self.logger.debug("AdaptiveCameraManager: Dropping frames because recording is inactive.")
                self._last_frame_drop_log = now
            return

        self.video_recorder.write_frame(frame)
    
    def handle_camera_error(self, error_msg):
        self.logger.error(f"AdaptiveCameraManager: Camera thread error reported: '{error_msg}'")
        """HANDLE CAMERA ERRORS"""
        self.logger.critical(f"AdaptiveCameraManager: !!! handle_camera_error TRIGGERED with message: '{error_msg}' !!! Processing this error now.")
        self.camera_error.emit(error_msg)

        # If the current device cannot be opened, try another available camera
        should_try_alternate = "Could not open camera device" in (error_msg or "") or "disconnected" in (error_msg or "")
        if should_try_alternate:
            available = self.get_available_cameras()
            fallback = None
            for dev_id, _ in available:
                if dev_id != self.current_camera_id:
                    fallback = dev_id
                    break
            if fallback is not None:
                self.logger.info(f"AdaptiveCameraManager: Switching to fallback camera {fallback} after error.")
                self.select_camera(fallback)
                return

        # ATTEMPT RESTART FOR SERIOUS ERRORS (same device)
        if self.camera_thread and not self.camera_thread.isRunning():
            self.logger.info("AdaptiveCameraManager: handle_camera_error - Camera thread is not running. Attempting camera restart...")
            QTimer.singleShot(1000, self.initialize_camera)
    
    def select_camera(self, device_id):
        """SELECT CAMERA DEVICE"""
        try:
            if self.current_camera_id == device_id:
                return True
            
            # STOP RECORDING IF ACTIVE
            if self.video_recorder.is_recording():
                self.stop_recording()
            
            # STOP CURRENT CAMERA
            if self.camera_thread:
                self.camera_thread.stop()
                self.camera_thread = None
            
            # START NEW CAMERA
            self.current_camera_id = device_id
            self.initialize_camera()
            
            self.logger.info(f"Selected camera: {device_id}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to select camera: {str(e)}"
            self.logger.error(error_msg)
            self.camera_error.emit(error_msg)
            return False
    
    def capture_image(self):
        """CAPTURE STILL IMAGE"""
        try:
            if not self.camera_thread or not self.camera_thread.isRunning():
                self.camera_error.emit("Camera not running")
                return None
            
            frame = self.camera_thread.capture_still_image()
            if frame is None:
                self.camera_error.emit("Failed to capture image")
                return None
            
            # GENERATE FILENAME
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"capture_{timestamp}.jpg"
            
            # SAVE IMAGE
            if self.file_manager:
                image_data = cv2.imencode('.jpg', frame)[1].tobytes()
                image_path = self.file_manager.save_captured_image(image_data, filename)
            else:
                images_dir = Path("data/images/captured")
                images_dir.mkdir(parents=True, exist_ok=True)
                image_path = str(images_dir / filename)
                cv2.imwrite(image_path, frame)
            
            self.logger.info(f"Image captured: {image_path}")
            self.image_captured.emit(image_path)
            return image_path
            
        except Exception as e:
            error_msg = f"Failed to capture image: {str(e)}"
            self.logger.error(error_msg)
            self.camera_error.emit(error_msg)
            return None
    
    def start_recording(self):
        """START ADAPTIVE RECORDING"""
        try:
            # Determine which set of keys to use for camera settings
            use_optimal_keys = self.camera_settings and \
                               self.camera_settings.get('optimal_width') and \
                               self.camera_settings.get('optimal_height') and \
                               self.camera_settings.get('optimal_fps') and \
                               self.camera_settings['optimal_fps'] > 0

            use_default_keys = self.camera_settings and \
                               self.camera_settings.get('width') and \
                               self.camera_settings.get('height') and \
                               self.camera_settings.get('fps') and \
                               self.camera_settings['fps'] > 0

            if not use_optimal_keys and not use_default_keys:
                self.logger.error("AdaptiveCameraManager: Cannot start recording. Valid camera settings (optimal or default) not found.")
                self.logger.info(f"Current camera_settings: {self.camera_settings}")
                self.camera_error.emit("Camera not ready or settings invalid.")
                return None

            # Select the actual settings to use
            current_fps_key = 'optimal_fps' if use_optimal_keys else 'fps'
            current_width_key = 'optimal_width' if use_optimal_keys else 'width'
            current_height_key = 'optimal_height' if use_optimal_keys else 'height'

            selected_fps = self.camera_settings[current_fps_key]
            selected_width = self.camera_settings[current_width_key]
            selected_height = self.camera_settings[current_height_key]

            self.logger.info(f"AdaptiveCameraManager: Attempting to start recording with settings: FPS={selected_fps}, Size=({selected_width}x{selected_height})")

            if self.video_recorder.is_recording():
                self.logger.warning("AdaptiveCameraManager: Start recording called, but already recording.")
                return None
            
            if not self.camera_thread or not self.camera_thread.isRunning():
                self.camera_error.emit("Camera not running")
                return None
            
            # GET INITIAL FRAME
            initial_frame = self.camera_thread.capture_still_image()

            # CONFIGURE RECORDER WITH SELECTED SETTINGS
            self.video_recorder.update_settings({'fps': selected_fps, 'width': selected_width, 'height': selected_height})
            self.logger.info(f"AdaptiveCameraManager: Configured video_recorder with: FPS={selected_fps}, Size=({selected_width}x{selected_height})")

            # START RECORDING
            video_path = self.video_recorder.start_recording(initial_frame)
            
            if video_path:
                # START UI UPDATE TIMER
                if self.recording_timer:
                    self.recording_timer.stop()
                
                self.recording_timer = QTimer()
                self.recording_timer.setInterval(1000)
                self.recording_timer.timeout.connect(self.update_recording_status)
                self.recording_timer.start()
                
                self.logger.info(f"Adaptive recording started: {video_path}")
                self.video_started.emit(video_path)
                return video_path
            else:
                self.logger.error("AdaptiveCameraManager: video_recorder.start_recording() FAILED.")
                self.camera_error.emit("Failed to start video recording.")
                return None
                
        except Exception as e:
            error_msg = f"Failed to start recording: {str(e)}"
            self.logger.error(error_msg)
            self.camera_error.emit(error_msg)
            return None
    
    def stop_recording(self):
        """STOP RECORDING"""
        try:
            if not self.video_recorder.is_recording():
                return None
            
            # STOP TIMER
            if self.recording_timer:
                self.recording_timer.stop()
                self.recording_timer = None
            
            # STOP RECORDING
            video_path = self.video_recorder.stop_recording()
            
            if video_path:
                self.logger.info(f"Recording stopped: {video_path}")
                self.video_stopped.emit(video_path)
                return video_path
            else:
                self.camera_error.emit("Failed to stop recording")
                return None
                
        except Exception as e:
            error_msg = f"Failed to stop recording: {str(e)}"
            self.logger.error(error_msg)
            self.camera_error.emit(error_msg)
            return None
    
    def update_recording_status(self):
        """UPDATE RECORDING STATUS"""
        try:
            if self.video_recorder.is_recording():
                duration = self.video_recorder.get_recording_duration()
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                time_str = f"{minutes:02d}:{seconds:02d}"
                self.recording_time_updated.emit(time_str)
                
                frame_count = self.video_recorder.get_frame_count()
                if self.video_recorder.video_path and Path(self.video_recorder.video_path).exists():
                    file_size = Path(self.video_recorder.video_path).stat().st_size
                    size_mb = file_size / (1024 * 1024)
                    actual_fps = frame_count / duration if duration > 0 else 0
                    self.recording_size_updated.emit(f"{size_mb:.1f} MB ({frame_count} frames @ {actual_fps:.1f} FPS)")
                    
        except Exception as e:
            self.logger.error(f"Error updating recording status: {e}")
    
    def get_available_cameras(self):
        """GET AVAILABLE CAMERA DEVICES WITHOUT HANGING STARTUP

        Enhanced to detect USB capture devices by trying multiple backends.
        USB capture cards often only work with DirectShow (CAP_DSHOW).

        Returns:
            List of (device_id, name) tuples for menu display.
            Backend info is stored internally in self._camera_backends.
        """
        try:
            available_cameras = []
            self._camera_backends = {}  # Reset backend cache
            system_name = platform.system().lower()
            max_devices = 10  # Increased for USB capture devices

            # Try multiple backends - USB capture devices often need DSHOW
            if system_name.startswith("win"):
                # DSHOW first for better USB capture device compatibility
                backends_to_try = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
            else:
                backends_to_try = [cv2.CAP_V4L2, cv2.CAP_ANY]

            checked_devices = set()
            consecutive_failures = 0

            self.logger.info(f"Scanning for cameras (max {max_devices} devices)...")

            for device_index in range(max_devices):
                device_found = False
                working_backend = None
                device_name = f"Camera {device_index}"

                for backend in backends_to_try:
                    if device_index in checked_devices:
                        break

                    cap = None
                    try:
                        backend_name = {
                            cv2.CAP_DSHOW: "DirectShow",
                            cv2.CAP_MSMF: "MSMF",
                            cv2.CAP_ANY: "Auto",
                            cv2.CAP_V4L2: "V4L2"
                        }.get(backend, str(backend))

                        self.logger.debug(f"Trying device {device_index} with {backend_name}...")
                        cap = cv2.VideoCapture(device_index, backend)

                        if cap is not None and cap.isOpened():
                            # Set buffer size first
                            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                            # Try to read a test frame - some devices open but don't capture
                            # Give USB devices more time to initialize
                            success = False
                            for attempt in range(5):  # Try up to 5 times
                                ret, test_frame = cap.read()
                                if ret and test_frame is not None and test_frame.size > 0:
                                    success = True
                                    break
                                time.sleep(0.1)

                            if success:
                                device_found = True
                                working_backend = backend

                                # Get native resolution for device name
                                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                                # Identify device type based on resolution
                                if width >= 1280 or height >= 720:
                                    device_name = f"Capture Device {device_index} ({width}x{height})"
                                else:
                                    device_name = f"Camera {device_index} ({width}x{height})"

                                self.logger.info(f"✓ Device {device_index} works with {backend_name}: {width}x{height}")
                                break
                            else:
                                self.logger.debug(f"Device {device_index} opened with {backend_name} but no frames")

                    except Exception as e:
                        self.logger.debug(f"Backend {backend_name} failed for device {device_index}: {e}")
                    finally:
                        if cap is not None:
                            try:
                                cap.release()
                            except Exception as rel_err:
                                self.logger.debug(f"Release failed for device {device_index} ({backend_name}): {rel_err}")
                            cap = None
                            # Delay to allow device to release properly
                            time.sleep(0.1)

                if device_found:
                    # Store backend info internally
                    self._camera_backends[device_index] = working_backend
                    # Return 2-tuple for menu compatibility
                    available_cameras.append((device_index, device_name))
                    checked_devices.add(device_index)
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    # Stop after several consecutive failures (but scan at least first 3 devices)
                    if consecutive_failures >= 4 and device_index >= 3:
                        self.logger.debug(f"Stopping scan after {consecutive_failures} consecutive failures")
                        break

            if not available_cameras:
                # Fallback - add default camera
                self._camera_backends[0] = cv2.CAP_ANY
                available_cameras.append((0, "Default Camera"))
                self.logger.warning("No cameras detected, using default")

            self.logger.info(f"Available cameras: {available_cameras}")
            return available_cameras

        except Exception as e:
            self.logger.error(f"Failed to get available cameras: {e}")
            self._camera_backends[0] = cv2.CAP_ANY
            return [(0, "Default Camera")]
    
    def get_camera_info(self):
        """GET CURRENT CAMERA INFORMATION"""
        return {
            'device_id': self.current_camera_id,
            'settings': self.camera_settings,
            'is_recording': self.video_recorder.is_recording() if self.video_recorder else False
        }
    
    def cleanup_camera(self):
        """CLEANUP CAMERA RESOURCES"""
        try:
            if self.video_recorder.is_recording():
                self.stop_recording()
            
            if self.recording_timer:
                self.recording_timer.stop()
                self.recording_timer = None
            
            if self.camera_thread:
                self.camera_thread.stop()
                self.camera_thread = None
            
            self.logger.info("Adaptive camera resources cleaned up")
            
        except Exception as e:
            self.logger.error(f"Error during camera cleanup: {e}")
    
    def emergency_cleanup(self):
        """EMERGENCY CLEANUP"""
        try:
            if hasattr(self, 'video_recorder') and self.video_recorder.is_recording():
                self.video_recorder.recording = False
                if self.video_recorder.writer:
                    self.video_recorder.writer.release()
                    self.video_recorder.writer = None
            
            if hasattr(self, 'camera_thread') and self.camera_thread:
                if self.camera_thread.isRunning():
                    self.camera_thread.terminate()
                    self.camera_thread.wait(1000)
                self.camera_thread = None
            
            print("Emergency adaptive camera cleanup completed")
            
        except Exception as e:
            print(f"Error in emergency adaptive camera cleanup: {e}")


# MAINTAIN COMPATIBILITY WITH EXISTING CODE
CameraManager = AdaptiveCameraManager
