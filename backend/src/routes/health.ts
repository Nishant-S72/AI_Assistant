import { Router, Request, Response } from 'express';
import * as fs from 'fs';
import * as path from 'path';

const router = Router();

// GET /api/health/local - Local mode health check
router.get('/local', async (req: Request, res: Response) => {
  try {
    const ollamaUrl = process.env.LLM_BASE_URL || 'http://localhost:11434';
    let ollamaStatus = 'not_running';
    let models: string[] = [];

    // Check Ollama
    try {
      const response = await fetch(`${ollamaUrl}/api/tags`, {
        method: 'GET',
        signal: AbortSignal.timeout(3000),
      });

      if (response.ok) {
        ollamaStatus = 'running';
        const data = await response.json() as { models?: Array<{ name: string }> };
        models = data.models?.map((m) => m.name.split(':')[0]) || [];
      }
    } catch (error) {
      ollamaStatus = 'not_running';
    }

    // Count dummy threads
    const inboxPath = process.env.DUMMY_INBOX_PATH || './demo-inbox';
    const fullPath = path.resolve(process.cwd(), inboxPath);
    let dummyThreadsLoaded = 0;

    if (fs.existsSync(fullPath)) {
      const files = fs.readdirSync(fullPath).filter((f) => f.endsWith('.json'));
      dummyThreadsLoaded = files.length;
    }

    res.json({
      ollama_status: ollamaStatus,
      models: [...new Set(models)], // Remove duplicates
      dummy_threads_loaded: dummyThreadsLoaded,
      mode: process.env.USE_OLLAMA === 'true' ? 'offline' : 'online',
    });
  } catch (error: any) {
    res.status(500).json({
      error: 'Health check failed',
      details: error.message,
    });
  }
});

export default router;

