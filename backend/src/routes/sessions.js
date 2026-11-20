const express = require('express');
const mongoose = require('mongoose');

const Session = require('../models/Session');
const { startDetector, stopDetector } = require('../detectorProcess');

const router = express.Router();
const ACTIVE = ['running', 'stopping'];
const STOP_GRACE_MS = 8000; // how long the detector gets to stop by itself

function validId(req, res, next) {
  if (!mongoose.isValidObjectId(req.params.id)) {
    return res.status(400).json({ error: 'Invalid session id' });
  }
  next();
}

// Close a session exactly once and record its length.
async function finalizeSession(id, { failed = false, error } = {}) {
  const session = await Session.findById(id);
  if (!session || !ACTIVE.includes(session.status)) return session;
  session.endTime = new Date();
  session.durationSec = Math.max(0, Math.round((session.endTime - session.startTime) / 1000));
  session.status = failed ? 'failed' : 'completed';
  if (error) session.error = error;
  await session.save();
  return session;
}

// GET /api/sessions - newest first
router.get('/', async (req, res, next) => {
  try {
    res.json(await Session.find().sort({ startTime: -1 }).limit(50));
  } catch (err) {
    next(err);
  }
});

// POST /api/sessions/start - create a session and launch the detector
router.post('/start', async (req, res, next) => {
  try {
    const active = await Session.findOne({ status: { $in: ACTIVE } });
    if (active) {
      return res.status(409).json({ error: 'A session is already running.', session: active });
    }
    const session = await Session.create({});
    const apiUrl = `http://127.0.0.1:${process.env.PORT || 5000}/api`;

    startDetector(session.id, apiUrl, (code, detail) => {
      const failed = code !== 0 && code !== null;
      const error = failed ? detail || `The detector stopped unexpectedly (code ${code}).` : undefined;
      finalizeSession(session.id, { failed, error }).catch(console.error);
    });

    res.status(201).json(session);
  } catch (err) {
    next(err);
  }
});

// POST /api/sessions/:id/stop - ask the detector to stop
router.post('/:id/stop', validId, async (req, res, next) => {
  try {
    const session = await Session.findById(req.params.id);
    if (!session) return res.status(404).json({ error: 'Session not found' });

    if (session.status === 'running') {
      session.status = 'stopping';
      await session.save();
      // The detector notices "stopping" on its next progress report (about 1 second).
      // If it does not, close the session and end the process anyway.
      setTimeout(async () => {
        try {
          const latest = await Session.findById(session.id);
          if (latest && latest.status === 'stopping') {
            await finalizeSession(session.id);
            stopDetector(session.id);
          }
        } catch (err) {
          console.error(err);
        }
      }, STOP_GRACE_MS);
    }
    res.json(session);
  } catch (err) {
    next(err);
  }
});

// PATCH /api/sessions/:id/progress - called by the detector about once per second
router.patch('/:id/progress', validId, async (req, res, next) => {
  try {
    const { drowsyEvents, blinks, state, final } = req.body;
    const session = await Session.findById(req.params.id);
    if (!session) return res.status(404).json({ error: 'Session not found' });

    if (ACTIVE.includes(session.status)) {
      if (Number.isInteger(drowsyEvents)) session.drowsyEvents = drowsyEvents;
      if (Number.isInteger(blinks)) session.blinks = blinks;
      if (typeof state === 'string') session.state = state;
      await session.save();
    }

    if (final) {
      const done = await finalizeSession(session.id);
      return res.json({ status: done.status });
    }
    res.json({ status: session.status });
  } catch (err) {
    next(err);
  }
});

// DELETE /api/sessions/:id - remove a finished session from the history
router.delete('/:id', validId, async (req, res, next) => {
  try {
    const session = await Session.findById(req.params.id);
    if (!session) return res.status(404).json({ error: 'Session not found' });
    if (ACTIVE.includes(session.status)) {
      return res.status(409).json({ error: 'Stop the session before deleting it.' });
    }
    await session.deleteOne();
    res.json({ deleted: true });
  } catch (err) {
    next(err);
  }
});

module.exports = router;
