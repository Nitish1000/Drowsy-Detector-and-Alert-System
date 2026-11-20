"""Unit tests for the detection logic (no camera needed).  Run:  python -m unittest -v"""
import unittest

from monitor import DrowsinessMonitor, State, eye_aspect_ratio


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds


def make_monitor(clock):
    return DrowsinessMonitor(clock=clock)


def calibrate(monitor, clock, open_ear=0.30):
    """Feed ~3.5 s of open-eye frames at 30 fps."""
    for _ in range(105):
        monitor.update(open_ear)
        clock.advance(1 / 30)


def run(monitor, clock, ear, seconds, fps=30):
    for _ in range(int(seconds * fps)):
        monitor.update(ear)
        clock.advance(1 / fps)


class EarTests(unittest.TestCase):
    def test_open_eye_has_higher_ear_than_closed_eye(self):
        open_eye = [(0, 0), (3, -2), (7, -2), (10, 0), (7, 2), (3, 2)]
        closed_eye = [(0, 0), (3, -0.3), (7, -0.3), (10, 0), (7, 0.3), (3, 0.3)]
        self.assertAlmostEqual(eye_aspect_ratio(open_eye), 0.4, places=3)
        self.assertLess(eye_aspect_ratio(closed_eye), 0.1)

    def test_zero_width_eye_does_not_crash(self):
        self.assertEqual(eye_aspect_ratio([(1, 1)] * 6), 0.0)


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.m = make_monitor(self.clock)

    def test_starts_calibrating_then_sets_threshold(self):
        self.assertEqual(self.m.state, State.CALIBRATING)
        calibrate(self.m, self.clock, 0.30)
        self.assertEqual(self.m.state, State.ALERT)
        self.assertAlmostEqual(self.m.threshold, 0.225, places=3)  # 0.30 * 0.75

    def test_threshold_is_clamped(self):
        calibrate(self.m, self.clock, 0.10)  # unusually low baseline
        self.assertEqual(self.m.threshold, 0.12)

    def test_calibration_ignores_blinks(self):
        for i in range(105):
            self.m.update(0.02 if i % 30 == 0 else 0.30)  # a "blink" frame every second
            self.clock.advance(1 / 30)
        self.assertAlmostEqual(self.m.threshold, 0.225, places=3)

    def test_quick_blink_is_counted_and_not_drowsy(self):
        calibrate(self.m, self.clock)
        run(self.m, self.clock, 0.05, 0.2)  # eyes closed 0.2 s
        run(self.m, self.clock, 0.30, 1.0)
        self.assertEqual(self.m.blinks, 1)
        self.assertEqual(self.m.drowsy_events, 0)
        self.assertEqual(self.m.state, State.ALERT)

    def test_long_closure_is_drowsy_and_counted_once(self):
        calibrate(self.m, self.clock)
        run(self.m, self.clock, 0.05, 1.0)
        self.assertEqual(self.m.state, State.EYES_CLOSED)
        run(self.m, self.clock, 0.05, 2.0)
        self.assertEqual(self.m.state, State.DROWSY)
        self.assertEqual(self.m.drowsy_events, 1)  # not one per frame
        run(self.m, self.clock, 0.30, 1.0)
        self.assertEqual(self.m.state, State.ALERT)
        self.assertEqual(self.m.blinks, 0)  # a drowsy episode is not a blink

    def test_two_separate_episodes_count_twice(self):
        calibrate(self.m, self.clock)
        for _ in range(2):
            run(self.m, self.clock, 0.05, 2.0)
            run(self.m, self.clock, 0.30, 1.0)
        self.assertEqual(self.m.drowsy_events, 2)

    def test_medium_closure_is_neither_blink_nor_drowsy(self):
        calibrate(self.m, self.clock)
        run(self.m, self.clock, 0.05, 1.0)  # longer than a blink, shorter than drowsy
        run(self.m, self.clock, 0.30, 1.0)
        self.assertEqual(self.m.blinks, 0)
        self.assertEqual(self.m.drowsy_events, 0)

    def test_losing_the_face_resets_the_closure_timer(self):
        calibrate(self.m, self.clock)
        run(self.m, self.clock, 0.05, 1.0)
        self.m.update(None)
        self.assertEqual(self.m.state, State.NO_FACE)
        run(self.m, self.clock, 0.05, 1.0)  # closed again, but the timer restarted
        self.assertEqual(self.m.drowsy_events, 0)

    def test_no_face_before_calibration_keeps_calibrating(self):
        self.m.update(None)
        self.assertEqual(self.m.state, State.CALIBRATING)


if __name__ == "__main__":
    unittest.main()
