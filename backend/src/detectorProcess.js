// Starts and stops the Python detector (detector/main.py) for a monitoring session.
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const DETECTOR_DIR = process.env.DETECTOR_DIR || path.join(__dirname, '..', '..', 'detector');
const running = new Map(); // sessionId -> child process

function resolvePython() {
  if (process.env.PYTHON_CMD) return process.env.PYTHON_CMD;
  const venvPython =
    process.platform === 'win32'
      ? path.join(DETECTOR_DIR, 'venv', 'Scripts', 'python.exe')
      : path.join(DETECTOR_DIR, 'venv', 'bin', 'python');
  if (fs.existsSync(venvPython)) return venvPython;
  return process.platform === 'win32' ? 'python' : 'python3';
}

/**
 * onExit(code, detail) is called exactly once when the detector ends.
 * code is 0 for a clean exit; detail holds the last error text, if any.
 */
function startDetector(sessionId, apiUrl, onExit) {
  const id = String(sessionId);
  let finished = false;
  const finish = (code, detail) => {
    if (finished) return;
    finished = true;
    running.delete(id);
    onExit(code, detail);
  };

  const child = spawn(resolvePython(), ['main.py'], {
    cwd: DETECTOR_DIR,
    env: { ...process.env, SESSION_ID: id, API_URL: apiUrl },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  running.set(id, child);

  let stderrTail = '';
  child.stdout.on('data', (d) => process.stdout.write(`[detector] ${d}`));
  child.stderr.on('data', (d) => {
    const text = d.toString();
    stderrTail = (stderrTail + text).slice(-500);
    process.stderr.write(`[detector] ${text}`);
  });
  child.on('error', (err) =>
    finish(-1, `Could not start Python (${err.message}). Set PYTHON_CMD in backend/.env.`)
  );
  child.on('exit', (code) => finish(code, stderrTail.trim()));
}

function stopDetector(sessionId) {
  const child = running.get(String(sessionId));
  if (child) child.kill();
}

module.exports = { startDetector, stopDetector };
