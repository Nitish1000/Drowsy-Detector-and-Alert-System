import { useCallback, useEffect, useState } from 'react';
import { deleteSession, listSessions, startSession, stopSession } from './api.js';

// What the status panel shows for each detector state.
const STATES = {
  calibrating: { title: 'Calibrating', hint: 'Look at the webcam with your eyes open for a few seconds.', tone: 'neutral' },
  alert: { title: 'Alert', hint: 'Your eyes are open. Keep going.', tone: 'ok' },
  eyes_closed: { title: 'Eyes closed', hint: 'Open your eyes to stay on track.', tone: 'warn' },
  drowsy: { title: 'Drowsy', hint: 'You look tired. Take a short break.', tone: 'danger' },
  no_face: { title: 'No face found', hint: 'Move back into view of the webcam.', tone: 'neutral' },
};

function formatLength(totalSeconds) {
  const s = Math.max(0, Math.round(totalSeconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h > 0) return `${h}h ${String(m).padStart(2, '0')}m`;
  return `${m}m ${String(sec).padStart(2, '0')}s`;
}

function formatStart(iso) {
  return new Date(iso).toLocaleString(undefined, {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  });
}

function StatusPanel({ active, now, busy, onStart, onStop }) {
  let view = { title: 'Ready', hint: 'Start a session. A webcam window will open on your screen.', tone: 'idle' };
  if (active?.status === 'stopping') {
    view = { title: 'Stopping', hint: 'Saving your session.', tone: 'neutral' };
  } else if (active) {
    view = STATES[active.state] || STATES.calibrating;
  }

  const elapsed = active ? (now - new Date(active.startTime).getTime()) / 1000 : 0;

  return (
    <section className={`status status--${view.tone}`} aria-live="polite">
      <div className="status__main">
        <h2 className="status__title">{view.title}</h2>
        <p className="status__hint">{view.hint}</p>
      </div>

      {active && (
        <dl className="status__stats">
          <div><dt>Time</dt><dd>{formatLength(elapsed)}</dd></div>
          <div><dt>Drowsy events</dt><dd>{active.drowsyEvents}</dd></div>
          <div><dt>Blinks</dt><dd>{active.blinks}</dd></div>
        </dl>
      )}

      {active ? (
        <button className="btn btn--stop" onClick={() => onStop(active._id)} disabled={busy || active.status === 'stopping'}>
          Stop session
        </button>
      ) : (
        <button className="btn btn--start" onClick={onStart} disabled={busy}>
          Start session
        </button>
      )}
    </section>
  );
}

function History({ sessions, onDelete }) {
  const finished = sessions.filter((s) => s.status === 'completed' || s.status === 'failed');
  const totalEvents = finished.reduce((sum, s) => sum + s.drowsyEvents, 0);

  return (
    <section className="history">
      <h2>Past sessions</h2>
      {finished.length === 0 ? (
        <p className="muted">No sessions yet. Your finished sessions will be listed here.</p>
      ) : (
        <>
          <p className="muted">
            {finished.length} {finished.length === 1 ? 'session' : 'sessions'} with {totalEvents} drowsy{' '}
            {totalEvents === 1 ? 'event' : 'events'} in total.
          </p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Started</th>
                  <th>Length</th>
                  <th>Drowsy events</th>
                  <th>Blinks</th>
                  <th>Result</th>
                  <th><span className="sr-only">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {finished.map((s) => (
                  <tr key={s._id}>
                    <td>{formatStart(s.startTime)}</td>
                    <td>{formatLength(s.durationSec)}</td>
                    <td>{s.drowsyEvents}</td>
                    <td>{s.blinks}</td>
                    <td>
                      {s.status === 'completed' ? 'Completed' : 'Failed'}
                      {s.error && <span className="row-error" title={s.error}>{s.error}</span>}
                    </td>
                    <td className="actions">
                      <button className="link-btn" onClick={() => onDelete(s._id)}>Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}

export default function App() {
  const [sessions, setSessions] = useState([]);
  const [offline, setOffline] = useState(false);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [now, setNow] = useState(Date.now());

  const refresh = useCallback(async () => {
    try {
      setSessions(await listSessions());
      setOffline(false);
    } catch {
      setOffline(true);
    }
  }, []);

  useEffect(() => {
    refresh();
    const poll = setInterval(refresh, 1500);
    const tick = setInterval(() => setNow(Date.now()), 1000);
    return () => { clearInterval(poll); clearInterval(tick); };
  }, [refresh]);

  const active = sessions.find((s) => s.status === 'running' || s.status === 'stopping');

  async function run(action) {
    setBusy(true);
    setMessage('');
    try {
      await action();
      await refresh();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <header className="top">
        <h1>Drowsy detector</h1>
        <p className="muted">Watches for tired eyes during study sessions and alerts you.</p>
      </header>

      {offline && (
        <p className="notice notice--error" role="alert">
          Can't reach the backend. Open a terminal in the backend folder and run <code>npm start</code>.
        </p>
      )}
      {message && <p className="notice notice--error" role="alert">{message}</p>}

      <StatusPanel
        active={active}
        now={now}
        busy={busy || offline}
        onStart={() => run(startSession)}
        onStop={(id) => run(() => stopSession(id))}
      />

      <History sessions={sessions} onDelete={(id) => run(() => deleteSession(id))} />
    </div>
  );
}
