import { Router, Request, Response } from 'express';
import { seedDemoData } from '../scripts/seed';
import { seedEnrichedData } from '../scripts/enrichedSeed';

const router = Router();

// POST /api/seed/demo - Seed demo data
router.post('/demo', async (req: Request, res: Response) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '') || req.body.token;
    const expectedToken = process.env.DEMO_SEED_TOKEN;

    if (expectedToken && token !== expectedToken) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    // Use enriched seed data
    await seedEnrichedData();
    res.json({ success: true, message: 'Enriched demo data seeded successfully' });
  } catch (error: any) {
    console.error('Error seeding demo data:', error);
    res.status(500).json({ error: 'Failed to seed demo data', details: error.message });
  }
});

export default router;

