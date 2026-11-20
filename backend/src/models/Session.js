const mongoose = require('mongoose');

const sessionSchema = new mongoose.Schema(
  {
    startTime: { type: Date, default: Date.now },
    endTime: Date,
    durationSec: { type: Number, default: 0 },
    drowsyEvents: { type: Number, default: 0 },
    blinks: { type: Number, default: 0 },
    // Latest detector state: calibrating | alert | eyes_closed | drowsy | no_face
    state: { type: String, default: 'calibrating' },
    status: {
      type: String,
      enum: ['running', 'stopping', 'completed', 'failed'],
      default: 'running',
    },
    error: String,
  },
  { timestamps: true }
);

module.exports = mongoose.model('Session', sessionSchema);
