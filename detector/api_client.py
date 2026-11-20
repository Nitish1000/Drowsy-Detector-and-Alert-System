"""Sends live session progress to the backend and learns when the user pressed Stop."""
from typing import Optional

import requests

STOP_STATUSES = {"stopping", "completed", "failed"}


class SessionClient:
    def __init__(self, api_url: str, session_id: str, max_failures: int = 15):
        self.api_url = api_url
        self.session_id = session_id
        self.max_failures = max_failures
        self._failures = 0

    @property
    def enabled(self) -> bool:
        return bool(self.session_id)

    def send_progress(self, drowsy_events: int, blinks: int, state: str, final: bool = False) -> bool:
        """Returns True if the detector should keep running."""
        if not self.enabled:
            return True
        url = f"{self.api_url}/sessions/{self.session_id}/progress"
        payload = {"drowsyEvents": drowsy_events, "blinks": blinks, "state": state, "final": final}
        try:
            response = requests.patch(url, json=payload, timeout=2)
            response.raise_for_status()
            self._failures = 0
            status: Optional[str] = response.json().get("status")
            return status not in STOP_STATUSES
        except (requests.RequestException, ValueError):
            self._failures += 1
            return self._failures < self.max_failures
