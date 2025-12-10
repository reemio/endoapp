import sys
print("Python executable:", sys.executable)
print("Python version:", sys.version)
print("\nPython path:")
for path in sys.path:
    print(f"  {path}")

print("\nTrying to import PySide6...")
try:
    import PySide6
    print(f"SUCCESS! PySide6 imported from: {PySide6.__file__}")
    print(f"PySide6 version: {PySide6.__version__}")
except ImportError as e:
    print(f"FAILED! Error: {e}")

print("\nChecking pip list...")
import subprocess
result = subprocess.run([sys.executable, "-m", "pip", "list"], capture_output=True, text=True)
if "PySide6" in result.stdout:
    print("PySide6 is installed according to pip")
else:
    print("PySide6 NOT found in pip list")