import { Router, Request, Response } from 'express';
import { pool } from '../db';

const router = Router();

// Simple auth middleware
function requireAuth(req: Request, res: Response, next: any) {
  const token = req.headers.authorization?.replace('Bearer ', '') || req.query.token;
  const expectedToken = process.env.DEMO_SEED_TOKEN || process.env.ADMIN_API_KEY;

  if (!expectedToken || token !== expectedToken) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  next();
}

// GET /api/admin/audit - Get audit logs
router.get('/audit', requireAuth, async (req: Request, res: Response) => {
  try {
    const limit = parseInt(req.query.limit as string) || 50;
    const offset = parseInt(req.query.offset as string) || 0;

    const result = await pool.query(
      `SELECT 
        id,
        type,
        correlation_id,
        request_path,
        user_id,
        prompt_ref,
        retrieved_ids,
        raw_model_response,
        final_text,
        latency_ms,
        payload,
        created_at
       FROM events
       ORDER BY created_at DESC
       LIMIT $1 OFFSET $2`,
      [limit, offset]
    );

    const countResult = await pool.query(`SELECT COUNT(*) as total FROM events`);
    const total = parseInt(countResult.rows[0].total);

    res.json({
      events: result.rows,
      total,
      limit,
      offset,
    });
  } catch (error) {
    console.error('Error fetching audit logs:', error);
    res.status(500).json({ error: 'Failed to fetch audit logs' });
  }
});

// GET /api/admin/metrics - Get metrics
router.get('/metrics', requireAuth, async (req: Request, res: Response) => {
  try {
    // Suggestions generated
    const suggestionsResult = await pool.query(
      `SELECT COUNT(*) as count FROM suggestions`
    );
    const suggestionsGenerated = parseInt(suggestionsResult.rows[0].count);

    // Acceptance rate (suggestions with final_text that matches model_response = accepted)
    const acceptedResult = await pool.query(
      `SELECT COUNT(*) as count 
       FROM suggestions 
       WHERE final_text IS NOT NULL 
       AND final_text = model_response 
       AND edited = false`
    );
    const accepted = parseInt(acceptedResult.rows[0].count);
    const acceptanceRate = suggestionsGenerated > 0 ? accepted / suggestionsGenerated : 0;

    // Average latency
    const latencyResult = await pool.query(
      `SELECT AVG(latency_ms) as avg_latency 
       FROM events 
       WHERE latency_ms IS NOT NULL 
       AND type = 'suggestion_generated'`
    );
    const avgLatency = latencyResult.rows[0].avg_latency
      ? Math.round(parseFloat(latencyResult.rows[0].avg_latency))
      : null;

    // Messages sent
    const sentResult = await pool.query(
      `SELECT COUNT(*) as count FROM events WHERE type = 'message_sent'`
    );
    const messagesSent = parseInt(sentResult.rows[0].count);

    res.json({
      suggestionsGenerated,
      acceptanceRate: Math.round(acceptanceRate * 100) / 100,
      avgLatencyMs: avgLatency,
      messagesSent,
    });
  } catch (error) {
    console.error('Error fetching metrics:', error);
    res.status(500).json({ error: 'Failed to fetch metrics' });
  }
});

// GET /api/metrics - Public metrics endpoint (no auth required for POC)
router.get('/metrics', async (req: Request, res: Response) => {
  try {
    // Suggestions generated
    const suggestionsResult = await pool.query(
      `SELECT COUNT(*) as count FROM suggestions`
    );
    const suggestionsGenerated = parseInt(suggestionsResult.rows[0].count);

    // Acceptance rate
    const acceptedResult = await pool.query(
      `SELECT COUNT(*) as count 
       FROM suggestions 
       WHERE final_text IS NOT NULL 
       AND final_text = model_response 
       AND edited = false`
    );
    const accepted = parseInt(acceptedResult.rows[0].count);
    const acceptanceRate = suggestionsGenerated > 0 ? accepted / suggestionsGenerated : 0;

    // Average latency
    const latencyResult = await pool.query(
      `SELECT AVG(latency_ms) as avg_latency 
       FROM events 
       WHERE latency_ms IS NOT NULL 
       AND type = 'suggestion_generated'`
    );
    const avgLatency = latencyResult.rows[0].avg_latency
      ? Math.round(parseFloat(latencyResult.rows[0].avg_latency))
      : null;

    // Messages sent
    const sentResult = await pool.query(
      `SELECT COUNT(*) as count FROM events WHERE type = 'message_sent'`
    );
    const messagesSent = parseInt(sentResult.rows[0].count);

    res.json({
      suggestionsGenerated,
      acceptanceRate: Math.round(acceptanceRate * 100) / 100,
      avgLatencyMs: avgLatency,
      messagesSent,
    });
  } catch (error) {
    console.error('Error fetching metrics:', error);
    res.status(500).json({ error: 'Failed to fetch metrics' });
  }
});

export default router;

