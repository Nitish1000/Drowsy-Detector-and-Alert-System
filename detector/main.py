"""Drowsy Detector - webcam loop.

Run on its own:      python main.py          (press q to quit)
Started by backend:  the backend sets SESSION_ID and API_URL and starts this file.
"""
import sys
import time

import cv2
import numpy as np

import config
from alert import Alarm
from api_client import SessionClient
from monitor import DrowsinessMonitor, State, eye_aspect_ratio

try:
    import mediapipe as mp
    face_mesh_module = mp.solutions.face_mesh
except (ImportError, AttributeError):
    sys.exit(
        "MediaPipe 'solutions' API not found. Install the pinned versions with:\n"
        "    pip install -r requirements.txt"
    )


LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]

WINDOW = "Drowsy Detector  (press q to quit)"
COLORS = {  # BGR
    State.CALIBRATING: (200, 160, 60),
    State.ALERT: (90, 170, 20),
    State.EYES_CLOSED: (0, 170, 240),
    State.DROWSY: (40, 40, 220),
    State.NO_FACE: (150, 150, 150),
}
LABELS = {
    State.CALIBRATING: "Calibrating",
    State.ALERT: "Alert",
    State.EYES_CLOSED: "Eyes closed",
    State.DROWSY: "DROWSY - take a break!",
    State.NO_FACE: "No face found",
}


def eye_points(landmarks, indices, width, height):
    return [(landmarks[i].x * width, landmarks[i].y * height) for i in indices]


def draw_overlay(frame, monitor, ear, session_start):
    h, w = frame.shape[:2]
    color = COLORS[monitor.state]

    if monitor.state == State.DROWSY:
        cv2.rectangle(frame, (0, 0), (w - 1, h - 1), color, 12)  # red border = visual alert

    cv2.rectangle(frame, (0, 0), (w, 92), (30, 30, 30), -1)
    cv2.putText(frame, LABELS[monitor.state], (16, 38), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)

    if monitor.state == State.CALIBRATING:
        text = f"Look at the camera with eyes open ({monitor.calibration_progress * 100:.0f}%)"
    else:
        minutes, seconds = divmod(int(time.time() - session_start), 60)
        ear_text = f"{ear:.2f}" if ear is not None else "-"
        text = (f"EAR {ear_text} (limit {monitor.threshold:.2f})   "
                f"Blinks {monitor.blinks}   Drowsy events {monitor.drowsy_events}   "
                f"{minutes:02d}:{seconds:02d}")
    cv2.putText(frame, text, (16, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (240, 240, 240), 1)


def open_camera():
    backend = cv2.CAP_DSHOW if sys.platform.startswith("win") else cv2.CAP_ANY
    cap = cv2.VideoCapture(config.CAMERA_INDEX, backend)
    if not cap.isOpened():
        sys.exit(f"Could not open the webcam (camera index {config.CAMERA_INDEX}). "
                 "Close other apps that use the camera, or set CAMERA_INDEX=1.")
    return cap


def main():
    client = SessionClient(config.API_URL, config.SESSION_ID, config.MAX_BACKEND_FAILURES)
    monitor = DrowsinessMonitor(
        calibration_seconds=config.CALIBRATION_SECONDS,
        drowsy_seconds=config.DROWSY_SECONDS,
        blink_max_seconds=config.BLINK_MAX_SECONDS,
        threshold_ratio=config.THRESHOLD_RATIO,
        min_threshold=config.MIN_THRESHOLD,
        max_threshold=config.MAX_THRESHOLD,
        fixed_threshold=config.FIXED_THRESHOLD,
    )
    alarm = Alarm(config.ALARM_INTERVAL_SECONDS)
    cap = open_camera()
    face_mesh = face_mesh_module.FaceMesh(
        max_num_faces=1, refine_landmarks=True,
        min_detection_confidence=0.5, min_tracking_confidence=0.5,
    )

    session_start = time.time()
    last_report = 0.0
    print("Detector started." + (f" Session {config.SESSION_ID}" if client.enabled else " (standalone mode)"))

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Camera frame could not be read.", file=sys.stderr)
                break
            frame = cv2.flip(frame, 1)  
            h, w = frame.shape[:2]

            result = face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            ear = None
            if result.multi_face_landmarks:
                lm = result.multi_face_landmarks[0].landmark
                left = eye_points(lm, LEFT_EYE, w, h)
                right = eye_points(lm, RIGHT_EYE, w, h)
                ear = (eye_aspect_ratio(left) + eye_aspect_ratio(right)) / 2.0
                for x, y in left + right:
                    cv2.circle(frame, (int(x), int(y)), 2, (0, 255, 255), -1)

            state = monitor.update(ear)
            if state == State.DROWSY:
                alarm.trigger()

            now = time.time()
            if now - last_report >= config.PROGRESS_INTERVAL_SECONDS:
                last_report = now
                if not client.send_progress(monitor.drowsy_events, monitor.blinks, state.value):
                    break  

            if config.SHOW_WINDOW:
                draw_overlay(frame, monitor, ear, session_start)
                cv2.imshow(WINDOW, frame)
                key = cv2.waitKey(1) & 0xFF
                closed = cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1
                if key == ord("q") or closed:
                    break
            else:
                time.sleep(0.01)
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        cv2.destroyAllWindows()
        face_mesh.close()
        client.send_progress(monitor.drowsy_events, monitor.blinks, monitor.state.value, final=True)
        print(f"Detector stopped. Blinks: {monitor.blinks}, drowsy events: {monitor.drowsy_events}")


if __name__ == "__main__":
    main()
