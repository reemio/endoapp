from pathlib import Path

# Base directories
ROOT_DIR = Path(__file__).parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
SRC_DIR = ROOT_DIR / "src"

# Data subdirectories
IMAGES_DIR = DATA_DIR / "images" / "captured"
VIDEOS_DIR = DATA_DIR / "videos" / "captured"
CACHE_DIR = DATA_DIR / "cache" / "camera"
LOGS_DIR = DATA_DIR / "logs"
DB_DIR = DATA_DIR / "database"
SETTINGS_DIR = DATA_DIR / "settings"

# Ensure all directories exist
for directory in [IMAGES_DIR, VIDEOS_DIR, CACHE_DIR, LOGS_DIR, DB_DIR, SETTINGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
                                