"""Audio alert. Beeps without freezing the video loop."""
import subprocess
import sys
import threading
import time

try:
    import winsound  
except ImportError:
    winsound = None


class Alarm:
    def __init__(self, interval_seconds: float = 1.0):
        self._interval = interval_seconds
        self._last = 0.0

    def trigger(self) -> None:
        """Call every frame while the user is drowsy; it beeps at most once per interval."""
        now = time.monotonic()
        if now - self._last < self._interval:
            return
        self._last = now
        threading.Thread(target=self._beep, daemon=True).start()

    @staticmethod
    def _beep() -> None:
        if winsound is not None:
            winsound.Beep(1200, 400)
        elif sys.platform == "darwin":
            subprocess.Popen(["afplay", "/System/Library/Sounds/Ping.aiff"])
        else:  
            sys.stdout.write("\a")
            sys.stdout.flush()
