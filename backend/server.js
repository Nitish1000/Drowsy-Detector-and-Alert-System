require('dotenv').config();
const express = require('express');
const cors = require('cors');
const mongoose = require('mongoose');

const Session = require('./src/models/Session');
const sessionRoutes = require('./src/routes/sessions');

const PORT = process.env.PORT || 5000;
const MONGO_URI = process.env.MONGO_URI || 'mongodb://127.0.0.1:27017/drowsy_detector';

const app = express();
app.use(cors());
app.use(express.json());

app.get('/api/health', (req, res) => {
  res.json({ ok: true, database: mongoose.connection.readyState === 1 });
});
app.use('/api/sessions', sessionRoutes);


app.use((err, req, res, next) => {
  console.error(err);
  res.status(500).json({ error: 'Server error' });
});

async function main() {
  await mongoose.connect(MONGO_URI);
  console.log('MongoDB connected');


  await Session.updateMany(
    { status: { $in: ['running', 'stopping'] } },
    { $set: { status: 'failed', error: 'The server restarted during this session.', endTime: new Date() } }
  );

  app.listen(PORT, () => console.log(`API running at http://localhost:${PORT}`));
}

main().catch((err) => {
  console.error('Could not start the server:', err.message);
  console.error('Is MongoDB running, and is MONGO_URI in backend/.env correct?');
  process.exit(1);
});
