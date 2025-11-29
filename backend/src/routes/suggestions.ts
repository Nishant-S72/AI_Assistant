import { Router, Request, Response } from 'express';
import { pool } from '../db';

const router = Router();

// POST /api/suggestions/:id/feedback
router.post('/:id/feedback', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const { accepted, editedText } = req.body;

    const updateData: any = {};
    if (editedText !== undefined) {
      updateData.final_text = editedText;
      updateData.edited = true;
      // Calculate simple diff (for demo)
      const originalResult = await pool.query(
        `SELECT model_response FROM suggestions WHERE id = $1`,
        [id]
      );
      if (originalResult.rows.length > 0) {
        updateData.edit_diff = `Original: ${originalResult.rows[0].model_response}\nEdited: ${editedText}`;
      }
    }

    if (Object.keys(updateData).length > 0) {
      const setClause = Object.keys(updateData)
        .map((key, idx) => `${key} = $${idx + 1}`)
        .join(', ');
      const values = Object.values(updateData);
      values.push(id);

      await pool.query(
        `UPDATE suggestions SET ${setClause} WHERE id = $${values.length}`,
        values
      );
    }

    // Log feedback event
    await pool.query(
      `INSERT INTO events (type, payload) VALUES ($1, $2)`,
      [
        'suggestion_feedback',
        JSON.stringify({
          suggestionId: id,
          accepted,
          edited: !!editedText,
        }),
      ]
    );

    res.json({ success: true });
  } catch (error) {
    console.error('Error saving feedback:', error);
    res.status(500).json({ error: 'Failed to save feedback' });
  }
});

export default router;

