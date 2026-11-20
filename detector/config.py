
import os


CALIBRATION_SECONDS = 3.0   
THRESHOLD_RATIO = 0.75      
MIN_THRESHOLD = 0.12        
MAX_THRESHOLD = 0.28
FIXED_THRESHOLD = None      
DROWSY_SECONDS = 1.5        
BLINK_MAX_SECONDS = 0.5     


ALARM_INTERVAL_SECONDS = 1.0  


CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
SHOW_WINDOW = os.getenv("SHOW_WINDOW", "1") != "0"


SESSION_ID = os.getenv("SESSION_ID", "").strip()
API_URL = os.getenv("API_URL", "http://127.0.0.1:5000/api").rstrip("/")
PROGRESS_INTERVAL_SECONDS = 1.0
MAX_BACKEND_FAILURES = 15   # stop if the backend is unreachable this many times in a row
