
import statistics
import time
from enum import Enum
from typing import Callable, List, Optional, Sequence

import numpy as np


class State(str, Enum):
    CALIBRATING = "calibrating"   
    ALERT = "alert"               
    EYES_CLOSED = "eyes_closed"   
    DROWSY = "drowsy"             
    NO_FACE = "no_face"           


def eye_aspect_ratio(points: Sequence[Sequence[float]]) -> float:
    """EAR from 6 eye landmarks p1..p6 (Soukupova & Cech, 2016).

    EAR = (|p2 - p6| + |p3 - p5|) / (2 * |p1 - p4|)
    It is roughly constant while the eye is open and falls towards 0 when it closes.
    """
    p = np.asarray(points, dtype=float)
    vertical = np.linalg.norm(p[1] - p[5]) + np.linalg.norm(p[2] - p[4])
    horizontal = 2.0 * np.linalg.norm(p[0] - p[3])
    return 0.0 if horizontal == 0 else float(vertical / horizontal)


class DrowsinessMonitor:
    """Feed it one EAR value per frame (or None when no face is found)."""

    def __init__(
        self,
        calibration_seconds: float = 3.0,
        drowsy_seconds: float = 1.5,
        blink_max_seconds: float = 0.5,
        blink_min_seconds: float = 0.03,
        threshold_ratio: float = 0.75,
        min_threshold: float = 0.12,
        max_threshold: float = 0.28,
        fixed_threshold: Optional[float] = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.calibration_seconds = calibration_seconds
        self.drowsy_seconds = drowsy_seconds
        self.blink_max_seconds = blink_max_seconds
        self.blink_min_seconds = blink_min_seconds
        self.threshold_ratio = threshold_ratio
        self.min_threshold = min_threshold
        self.max_threshold = max_threshold
        self._clock = clock

        self.threshold: Optional[float] = fixed_threshold
        self.state = State.CALIBRATING if fixed_threshold is None else State.ALERT
        self.blinks = 0
        self.drowsy_events = 0

        self._cal_start: Optional[float] = None
        self._cal_samples: List[float] = []
        self._closed_since: Optional[float] = None
        self._episode_counted = False

    # -- helpers -------------------------------------------------------------
    @property
    def calibration_progress(self) -> float:
        """0.0 - 1.0, used for the on-screen calibration message."""
        if self.threshold is not None:
            return 1.0
        if self._cal_start is None:
            return 0.0
        return min(1.0, (self._clock() - self._cal_start) / self.calibration_seconds)

    def _reset_closure(self) -> None:
        self._closed_since = None
        self._episode_counted = False

    def _calibrate(self, now: float, ear: float) -> None:
        if self._cal_start is None:
            self._cal_start = now
        self._cal_samples.append(ear)
        enough_time = now - self._cal_start >= self.calibration_seconds
        if enough_time and len(self._cal_samples) >= 10:
            
            baseline = statistics.median(self._cal_samples)
            raw = baseline * self.threshold_ratio
            self.threshold = max(self.min_threshold, min(self.max_threshold, raw))
            self.state = State.ALERT
        else:
            self.state = State.CALIBRATING

    # -- main entry point ------------------------------------------------------
    def update(self, ear: Optional[float]) -> State:
        now = self._clock()

        if ear is None:  # no face in this frame
            self._reset_closure()
            self.state = State.NO_FACE if self.threshold is not None else State.CALIBRATING
            return self.state

        if self.threshold is None:
            self._calibrate(now, ear)
            return self.state

        if ear < self.threshold: 
            if self._closed_since is None:
                self._closed_since = now
            if now - self._closed_since >= self.drowsy_seconds:
                self.state = State.DROWSY
                if not self._episode_counted:  
                    self.drowsy_events += 1
                    self._episode_counted = True
            else:
                self.state = State.EYES_CLOSED
        else:  
            if self._closed_since is not None and not self._episode_counted:
                closed_for = now - self._closed_since
                if self.blink_min_seconds <= closed_for <= self.blink_max_seconds:
                    self.blinks += 1
            self._reset_closure()
            self.state = State.ALERT

        return self.state
