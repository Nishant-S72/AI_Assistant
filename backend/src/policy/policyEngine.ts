import * as fs from 'fs';
import * as path from 'path';

export interface PolicyResult {
  action: 'ALLOW' | 'ESCALATE';
  reasons: string[];
  confidence: number;
}

interface PolicyRule {
  keywords: string[];
  action: 'ESCALATE';
  reason: string;
  confidence: number;
}

let rules: PolicyRule[] = [];

function loadRules() {
  const rulesPath = path.join(__dirname, '../../policy.json');
  try {
    if (fs.existsSync(rulesPath)) {
      const data = fs.readFileSync(rulesPath, 'utf-8');
      const config = JSON.parse(data);
      rules = config.rules || [];
    } else {
      // Default rules
      rules = [
        {
          keywords: ['refund', 'refunds', 'money back'],
          action: 'ESCALATE',
          reason: 'Contains refund-related keywords',
          confidence: 0.9,
        },
        {
          keywords: ['lawsuit', 'sue', 'suing', 'legal action', 'attorney', 'lawyer'],
          action: 'ESCALATE',
          reason: 'Contains legal action keywords',
          confidence: 0.95,
        },
        {
          keywords: ['legal', 'litigation', 'court', 'breach of contract'],
          action: 'ESCALATE',
          reason: 'Contains legal terminology',
          confidence: 0.85,
        },
        {
          keywords: ['chargeback', 'dispute', 'fraud'],
          action: 'ESCALATE',
          reason: 'Contains payment dispute keywords',
          confidence: 0.9,
        },
        {
          keywords: ['ssn', 'social security', 'credit card number', 'cvv'],
          action: 'ESCALATE',
          reason: 'Contains sensitive personal information',
          confidence: 1.0,
        },
      ];
    }
  } catch (error) {
    console.error('[Policy] Error loading rules:', error);
    // Use default rules instead of recursive call to prevent infinite recursion
    rules = [
      {
        keywords: ['refund', 'refunds', 'money back'],
        action: 'ESCALATE',
        reason: 'Contains refund-related keywords',
        confidence: 0.9,
      },
      {
        keywords: ['lawsuit', 'sue', 'suing', 'legal action', 'attorney', 'lawyer'],
        action: 'ESCALATE',
        reason: 'Contains legal action keywords',
        confidence: 0.95,
      },
      {
        keywords: ['legal', 'litigation', 'court', 'breach of contract'],
        action: 'ESCALATE',
        reason: 'Contains legal terminology',
        confidence: 0.85,
      },
      {
        keywords: ['chargeback', 'dispute', 'fraud'],
        action: 'ESCALATE',
        reason: 'Contains payment dispute keywords',
        confidence: 0.9,
      },
      {
        keywords: ['ssn', 'social security', 'credit card number', 'cvv'],
        action: 'ESCALATE',
        reason: 'Contains sensitive personal information',
        confidence: 1.0,
      },
    ];
  }
}

// Load rules on module init
loadRules();

export function checkPolicy(
  text: string,
  metadata?: Record<string, any>
): PolicyResult {
  const lowerText = text.toLowerCase();
  const reasons: string[] = [];
  let maxConfidence = 0;

  for (const rule of rules) {
    const matched = rule.keywords.some((keyword) => lowerText.includes(keyword.toLowerCase()));
    if (matched) {
      reasons.push(rule.reason);
      maxConfidence = Math.max(maxConfidence, rule.confidence);
    }
  }

  const confidenceThreshold = parseFloat(
    process.env.POLICY_CONFIDENCE_THRESHOLD || '0.8'
  );

  if (reasons.length > 0 && maxConfidence >= confidenceThreshold) {
    return {
      action: 'ESCALATE',
      reasons,
      confidence: maxConfidence,
    };
  }

  return {
    action: 'ALLOW',
    reasons: [],
    confidence: 0,
  };
}

export function reloadRules() {
  loadRules();
}

