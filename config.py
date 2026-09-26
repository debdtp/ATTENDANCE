import os
import json

# Base paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Default directories
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "attendance.db")
DEFAULT_ENCODINGS_PATH = os.path.join(BASE_DIR, "encodings_arcface.pkl")
DEFAULT_DATASET_DIR = os.path.join(BASE_DIR, "dataset")
DEFAULT_ATTENDANCE_DIR = os.path.join(BASE_DIR, "attendance")
DEFAULT_MODELS_DIR = os.path.join(BASE_DIR, "models")
SETTINGS_JSON_PATH = os.path.join(BASE_DIR, "settings.json")

# Ensure required directories exist
for directory in [DEFAULT_DATASET_DIR, DEFAULT_ATTENDANCE_DIR, DEFAULT_MODELS_DIR]:
    os.makedirs(directory, exist_ok=True)

# Default setting parameters
DEFAULTS = {
    "recognition_threshold": 0.60,
    "camera_index": 0,
    "camera_resolution": "640x480",
    "capture_count": 70,
    "dataset_dir": DEFAULT_DATASET_DIR,
    "attendance_dir": DEFAULT_ATTENDANCE_DIR,
    "models_dir": DEFAULT_MODELS_DIR,
    "database_path": DEFAULT_DB_PATH,
    "encodings_path": DEFAULT_ENCODINGS_PATH,
    "theme": "dark"
}

def load_settings() -> dict:
    """Loads settings from settings.json or returns default values."""
    if os.path.exists(SETTINGS_JSON_PATH):
        try:
            with open(SETTINGS_JSON_PATH, "r") as f:
                settings = json.load(f)
                # Fallback to default keys if not present
                loaded = {**DEFAULTS}
                loaded.update(settings)
                return loaded
        except Exception:
            return DEFAULTS
    return DEFAULTS

def save_settings(settings: dict) -> bool:
    """Saves settings dict to settings.json."""
    try:
        with open(SETTINGS_JSON_PATH, "w") as f:
            json.dump(settings, f, indent=4)
        return True
    except Exception:
        return False

# Initialize settings
current_settings = load_settings()

# Export config variables
DATABASE_PATH = current_settings.get("database_path", DEFAULT_DB_PATH)
ENCODINGS_PATH = current_settings.get("encodings_path", DEFAULT_ENCODINGS_PATH)
DATASET_DIR = current_settings.get("dataset_dir", DEFAULT_DATASET_DIR)
ATTENDANCE_DIR = current_settings.get("attendance_dir", DEFAULT_ATTENDANCE_DIR)
MODELS_DIR = current_settings.get("models_dir", DEFAULT_MODELS_DIR)

RECOGNITION_THRESHOLD = current_settings.get("recognition_threshold", 0.60)

raw_camera_index = current_settings.get("camera_index", 0)
try:
    CAMERA_INDEX = int(raw_camera_index)
except (ValueError, TypeError):
    CAMERA_INDEX = str(raw_camera_index).strip()

CAMERA_RESOLUTION = current_settings.get("camera_resolution", "640x480")
CAPTURE_COUNT = int(current_settings.get("capture_count", 35))
THEME = current_settings.get("theme", "dark")
