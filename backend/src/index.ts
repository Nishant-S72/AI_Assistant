import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { initDatabase, pool } from './db';
import { startEmailWorker } from './workers/emailWorker';

// Routes
import messagesRouter from './routes/messages';
import suggestionsRouter from './routes/suggestions';
import contactsRouter from './routes/contacts';
import tasksRouter from './routes/tasks';
import connectRouter from './routes/connect';
import uploadRouter from './routes/upload';
import seedRouter from './routes/seed';
import adminRouter from './routes/admin';
import healthRouter from './routes/health';
import demoRouter from './routes/demo';
import summaryRouter from './routes/summary';
import chatRouter from './routes/chat';
import calendarRouter from './routes/calendar';
import { loadDummyInbox } from './utils/loadDummyInbox';
import { autoTagContacts } from './utils/autoTagContacts';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Health check with readiness
app.get('/health', async (req, res) => {
  const health: any = {
    status: 'ok',
    timestamp: new Date().toISOString(),
  };

  try {
    // Check database
    await pool.query('SELECT 1');
    health.database = 'connected';
  } catch (error) {
    health.database = 'disconnected';
    health.status = 'degraded';
  }

  try {
    // Check Redis (via ioredis if available)
    const Redis = (await import('ioredis')).default;
    const redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');
    await redis.ping();
    redis.disconnect();
    health.redis = 'connected';
  } catch (error) {
    health.redis = 'disconnected';
    health.status = 'degraded';
  }

  // Check vector store
  try {
    const vectorStoreModule = await import('./clients/vectorstore');
    health.vectorstore = await vectorStoreModule.getAdapterName();
  } catch (error) {
    health.vectorstore = 'unknown';
    health.status = 'degraded';
  }

  // Check LLM availability
  try {
    const llmModule = await import('./clients/llm');
    const useOllama = process.env.USE_OLLAMA === 'true';
    if (useOllama) {
      health.llm = (await llmModule.checkOllamaHealth()) ? 'ollama_available' : 'ollama_unavailable';
    } else if (process.env.OPENAI_API_KEY) {
      health.llm = 'openai_configured';
    } else {
      health.llm = 'not_configured';
    }
  } catch (error) {
    health.llm = 'unknown';
  }

  const statusCode = health.status === 'ok' ? 200 : 503;
  res.status(statusCode).json(health);
});

// API health check
app.get('/api/health', async (req, res) => {
  const health: any = {
    status: 'ok',
    timestamp: new Date().toISOString(),
  };

  try {
    await pool.query('SELECT 1');
    health.database = 'connected';
  } catch (error) {
    health.database = 'disconnected';
    health.status = 'degraded';
  }

  try {
    const vectorStoreModule = await import('./clients/vectorstore');
    health.vectorstore = await vectorStoreModule.getAdapterName();
  } catch (error) {
    health.vectorstore = 'unknown';
  }

  res.json(health);
});

// API routes
app.use('/api/messages', messagesRouter);
app.use('/api/suggestions', suggestionsRouter);
app.use('/api/contacts', contactsRouter);
app.use('/api/tasks', tasksRouter);
app.use('/api/connect', connectRouter);
app.use('/api/upload', uploadRouter);
app.use('/api/seed', seedRouter);
app.use('/api/admin', adminRouter);
app.use('/api/metrics', adminRouter); // Metrics also available at /api/metrics
app.use('/api/health', healthRouter);
app.use('/api/demo', demoRouter);
app.use('/api/summary', summaryRouter);
app.use('/api/chat', chatRouter);
app.use('/api/calendar', calendarRouter);

// Start server
async function start() {
  try {
    // Initialize database
    await initDatabase();
    
    // Auto-tag contacts on startup
    try {
      await autoTagContacts();
    } catch (error) {
      console.warn('⚠️  Auto-tagging failed (non-critical):', error);
    }

    // Load dummy inbox if in offline mode
    if (process.env.USE_DUMMY_INBOX === 'true') {
      try {
        await loadDummyInbox();
      } catch (error) {
        console.warn('⚠️  Could not load dummy inbox:', error);
      }
    }

// Start email worker (only if Redis is available)
try {
  const worker = startEmailWorker();
  if (worker) {
    console.log('📧 Email worker started');
  }
} catch (error: any) {
  console.warn('⚠️  Email worker not started:', error.message);
}

    app.listen(PORT, () => {
      console.log(`🚀 Backend server running on http://localhost:${PORT}`);
      if (process.env.USE_OLLAMA === 'true') {
        console.log(`🧠 Offline mode: Using local LLM (${process.env.LLM_MODEL || 'tinyllama'})`);
      }
    });
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

start();

