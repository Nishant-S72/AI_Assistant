import { Router, Request, Response } from 'express';

const router = Router();

// POST /api/connect/gmail - Stub endpoint
router.post('/gmail', async (req: Request, res: Response) => {
  // TODO: Implement Gmail OAuth flow
  // For now, return demo account info
  res.json({
    success: true,
    account: {
      email: 'demo@example.com',
      name: 'Demo Account',
      connected: false,
      simulated: true,
    },
    message: 'Gmail integration not configured. Using simulated mode.',
  });
});

export default router;

