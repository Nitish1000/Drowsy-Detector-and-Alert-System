# Drowsy Detector and Alert System: Phase 1 (about 20% of the project)

A webcam-based system that detects drowsiness during study sessions and alerts the student.

**Stack:** Python (OpenCV + MediaPipe) for detection, Node.js + Express + MongoDB for the backend, React for the dashboard.

## What Phase 1 covers (from the Gantt chart)

| Gantt task | Where it is in this project |
|---|---|
| 2. Software architecture and module design | The folder structure and the flow below |
| 3. Camera setup, MediaPipe integration and prototype | `detector/` (webcam, face landmarks, EAR, blink and drowsy detection, alert) |
| About 20% coding: backend and database skeleton | `backend/` (sessions API, MongoDB model, starts and stops the detector) |
| About 20% coding: basic dashboard | `frontend/` (start/stop, live status, session history) |

**Left for Phase 2 (about 80%):** data collection and labeling, Random Forest model, yawning and head-movement detection, graphs and statistics, calibration and performance testing, full documentation.

## How it works

```
React dashboard  --(Start / Stop)-->  Express API  --(starts)-->  Python detector
      ^                                  |   ^                        |
      |                                  v   |                        |
      +------(live status, history)---  MongoDB  <--(progress, 1/sec)-+
```

1. **Start session** in the dashboard: the API creates a session in MongoDB and starts `detector/main.py`.
2. The detector opens the webcam. For the first 3 seconds it **calibrates** (measures your normal open-eye EAR).
3. **EAR (Eye Aspect Ratio)** is calculated every frame from 6 landmarks around each eye:
   `EAR = (|p2-p6| + |p3-p5|) / (2 * |p1-p4|)`. It is about 0.25-0.35 with eyes open and drops towards 0 when they close.
4. EAR below the limit (75% of your open-eye value) means the eyes are closed:
   - closed for less than 0.5 s: counted as a **blink**
   - closed for 1.5 s or more: **drowsy**, so the alarm beeps and the screen border turns red. Each episode is counted once as a **drowsy event**.
5. Every second the detector sends its stats to the API. The dashboard polls the API and shows them live.
6. **Stop session** (or press `q` in the camera window): the session is saved with its length, blinks and drowsy events.

## Setup

You need: **Python 3.9-3.12**, **Node.js 18+**, **MongoDB** (local, or a free MongoDB Atlas database) and a webcam.

### 1. Detector (Python)
```bash
cd detector
python -m venv venv
venv\Scripts\activate          # Windows      (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
```
Use the versions in `requirements.txt`. Newer MediaPipe releases removed the API this code uses.

**Try it on its own first** (no backend needed): `python main.py`. Press `q` to quit.

### 2. Backend (Node.js)
```bash
cd backend
copy .env.example .env         # macOS/Linux: cp .env.example .env
npm install
npm start
```
You should see `MongoDB connected` and `API running at http://localhost:5000`.
The backend uses `detector/venv` automatically if it exists. Otherwise set `PYTHON_CMD` in `backend/.env`.

### 3. Frontend (React)
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173 and press **Start session**.

## Tests

```bash
cd detector
python -m unittest -v
```
Checks the EAR formula, calibration, blink counting, drowsy detection (counted once per episode) and the no-face case. No camera needed.

## Tuning (`detector/config.py`)

| Setting | Meaning | Default |
|---|---|---|
| `DROWSY_SECONDS` | eyes closed this long = drowsy | 1.5 |
| `THRESHOLD_RATIO` | closed-eye limit as a fraction of your open-eye EAR | 0.75 |
| `FIXED_THRESHOLD` | set a number (e.g. 0.21) to skip calibration | None |
| `CAMERA_INDEX` | 0 = default webcam, 1 = second camera | 0 |

## Troubleshooting

- **"MediaPipe 'solutions' API not found"**: run `pip install -r requirements.txt` inside the detector venv.
- **"Could not open the webcam"**: close Zoom/Teams/browser tabs using the camera, or set `CAMERA_INDEX=1`.
- **Dashboard says it can't reach the backend**: run `npm start` in `backend/` and check MongoDB is running.
- **Session shows "Failed"**: the reason is shown under it. It is usually the Python environment or the webcam.
- **Always "No face found"**: improve the lighting and face the camera directly.
- **No beep on Linux**: the alert uses the terminal bell there. Windows and macOS play a sound.

## Screenshots to take for the Phase 1 report

1. The camera window in the **Alert** state (eye points and EAR visible)
2. The camera window in the **Drowsy** state (red border)
3. The dashboard while a session runs, and the session history table
4. The MongoDB `sessions` collection (MongoDB Compass)
5. The unit tests passing in the terminal
