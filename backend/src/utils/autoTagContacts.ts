/**
 * Auto-tag contacts based on their metrics and history
 * Assigns tags like "high value", "long standing", etc.
 */

import { pool } from '../db';

export async function autoTagContacts() {
  console.log('🏷️  Auto-tagging contacts...');

  try {
    // Get all contacts with their metrics
    const contactsResult = await pool.query(`
      SELECT 
        c.id,
        c.tags,
        (SELECT COUNT(*) FROM messages m WHERE m.contact_id = c.id) as message_count,
        (SELECT COUNT(*) FROM tasks t WHERE t.contact_id = c.id AND t.status = 'completed') as completed_tasks,
        (SELECT MIN(created_at) FROM messages m WHERE m.contact_id = c.id) as first_message_date,
        (SELECT MAX(created_at) FROM messages m WHERE m.contact_id = c.id) as last_message_date
      FROM contacts c
    `);

    let updatedCount = 0;

    for (const contact of contactsResult.rows) {
      const existingTags = Array.isArray(contact.tags)
        ? contact.tags
        : typeof contact.tags === 'string'
          ? JSON.parse(contact.tags || '[]')
          : [];

      const newTags = [...existingTags];
      const messageCount = parseInt(contact.message_count || '0');
      const completedTasks = parseInt(contact.completed_tasks || '0');
      const firstMessageDate = contact.first_message_date
        ? new Date(contact.first_message_date)
        : null;
      const lastMessageDate = contact.last_message_date
        ? new Date(contact.last_message_date)
        : null;

      // Calculate relationship duration
      const relationshipDuration = firstMessageDate
        ? Math.floor((Date.now() - firstMessageDate.getTime()) / (1000 * 60 * 60 * 24))
        : 0;
      const relationshipYears = relationshipDuration > 365 ? Math.floor(relationshipDuration / 365) : 0;

      // Auto-assign "long standing" tag if relationship > 1 year
      if (relationshipYears >= 1 && !newTags.includes('long standing')) {
        newTags.push('long standing');
      } else if (relationshipYears < 1 && newTags.includes('long standing')) {
        // Remove if no longer qualifies
        const index = newTags.indexOf('long standing');
        if (index > -1) newTags.splice(index, 1);
      }

      // Auto-assign "high value" tag based on multiple factors
      const isHighValue =
        messageCount >= 20 || // High message volume
        completedTasks >= 5 || // Multiple completed tasks
        relationshipYears >= 1 && messageCount >= 10 || // Long relationship with activity
        existingTags.includes('vip') || // Already marked as VIP
        existingTags.includes('enterprise'); // Enterprise contact

      if (isHighValue && !newTags.includes('high value')) {
        newTags.push('high value');
      } else if (!isHighValue && newTags.includes('high value')) {
        // Remove if no longer qualifies
        const index = newTags.indexOf('high value');
        if (index > -1) newTags.splice(index, 1);
      }

      // Only update if tags changed
      if (JSON.stringify(newTags.sort()) !== JSON.stringify(existingTags.sort())) {
        await pool.query(
          `UPDATE contacts SET tags = $1 WHERE id = $2`,
          [JSON.stringify(newTags), contact.id]
        );
        updatedCount++;
      }
    }

    console.log(`✅ Auto-tagged ${updatedCount} contacts`);
    return updatedCount;
  } catch (error) {
    console.error('Error auto-tagging contacts:', error);
    throw error;
  }
}


