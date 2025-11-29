// Simple keyword-based policy engine
// Returns 'ESCALATE_TO_HUMAN' if message contains sensitive keywords

const ESCALATION_KEYWORDS = [
  'refund',
  'lawsuit',
  'legal',
  'attorney',
  'lawyer',
  'sue',
  'suing',
  'court',
  'litigation',
  'breach of contract',
  'violation',
];

export function checkPolicy(messageBody: string): {
  action: 'APPROVE' | 'ESCALATE_TO_HUMAN';
  reason?: string;
} {
  const lowerBody = messageBody.toLowerCase();
  
  for (const keyword of ESCALATION_KEYWORDS) {
    if (lowerBody.includes(keyword)) {
      return {
        action: 'ESCALATE_TO_HUMAN',
        reason: `Message contains sensitive keyword: "${keyword}"`,
      };
    }
  }
  
  return { action: 'APPROVE' };
}

