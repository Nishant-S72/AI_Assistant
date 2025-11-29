/**
 * Intent Classifier
 * Classifies user messages into: policy_intent, action_intent, or general_intent
 */

import { generateChatCompletion, LLMMessage } from '../clients/llm';

export type IntentType = 'policy_intent' | 'action_intent' | 'general_intent';

export interface IntentResult {
  intent: IntentType;
  confidence: number;
  reasons: string[];
}

// Policy intent keywords
const POLICY_KEYWORDS = [
  'policy', 'policies', 'policy doc', 'policy document', 'guideline', 'guidelines',
  'rule', 'rules', 'procedure', 'procedures', 'compliance', 'compliant',
  'section', 'sections', 'clause', 'clauses', 'allowed', 'not allowed',
  'prohibited', 'permitted', 'eligibility', 'eligible', 'requirement', 'requirements',
  'standard', 'standards', 'protocol', 'protocols', 'regulation', 'regulations',
  'what does the', 'what is our', 'what are our', 'does our', 'can we', 'are we allowed',
  'refund policy', 'return policy', 'privacy policy', 'terms of service',
];

// Action intent keywords
const ACTION_KEYWORDS = [
  'schedule', 'scheduling', 'book', 'booking', 'plan', 'planning',
  'create', 'creating', 'add', 'adding', 'set up', 'set up a',
  'send', 'sending', 'generate', 'generating', 'make', 'making',
  'meeting', 'appointment', 'event', 'call', 'reminder',
  'invoice', 'quote', 'email', 'message',
  'please schedule', 'can you schedule', 'i need to schedule',
  'add to calendar', 'create event', 'set reminder',
];

/**
 * Quick rule-based classification
 * Returns intent if rules are confident, null if ambiguous
 */
function classifyWithRules(userMessage: string): { intent: IntentType; confidence: number; reasons: string[] } | null {
  const lowerMessage = userMessage.toLowerCase();
  const reasons: string[] = [];
  
  // Check for policy intent
  const policyMatches = POLICY_KEYWORDS.filter(keyword => lowerMessage.includes(keyword));
  if (policyMatches.length > 0) {
    reasons.push(`Contains policy keywords: ${policyMatches.slice(0, 2).join(', ')}`);
    return {
      intent: 'policy_intent',
      confidence: Math.min(0.9, 0.6 + (policyMatches.length * 0.1)),
      reasons,
    };
  }
  
  // Check for action intent
  const actionMatches = ACTION_KEYWORDS.filter(keyword => lowerMessage.includes(keyword));
  if (actionMatches.length > 0) {
    // Higher confidence if multiple action keywords or specific patterns
    const hasTimeReference = /\b(tomorrow|today|next|monday|tuesday|wednesday|thursday|friday|saturday|sunday|at \d|pm|am)\b/i.test(userMessage);
    const hasActionVerb = /\b(schedule|book|create|add|set|send|make)\b/i.test(userMessage);
    
    if (hasTimeReference || hasActionVerb) {
      reasons.push(`Contains action keywords: ${actionMatches.slice(0, 2).join(', ')}`);
      return {
        intent: 'action_intent',
        confidence: hasTimeReference && hasActionVerb ? 0.9 : 0.75,
        reasons,
      };
    }
  }
  
  // If no clear match, return null to use LLM fallback
  return null;
}

/**
 * LLM-assisted classification fallback
 */
async function classifyWithLLM(userMessage: string): Promise<IntentResult> {
  const classificationPrompt = `Classify the user message into one of three intents:

1. policy_intent - User asks about rules, compliance, procedures, or explicitly references policy documents
2. action_intent - User requests an agentic action (schedule meeting, create invoice, send email, etc.)
3. general_intent - Everything else (explanations, casual questions, how-tos, brainstorming, small talk)

User message: "${userMessage}"

Respond with ONLY a JSON object in this exact format:
{"intent": "policy_intent|action_intent|general_intent", "confidence": 0.0-1.0, "reason": "brief explanation"}`;

  try {
    const response = await generateChatCompletion({
      model: process.env.LLM_MODEL || 'tinyllama',
      messages: [
        {
          role: 'system',
          content: 'You are a classification assistant. Return only valid JSON.',
        },
        {
          role: 'user',
          content: classificationPrompt,
        },
      ],
      temperature: 0.0,
      max_tokens: 100,
      useLocal: process.env.USE_OLLAMA !== 'false',
    });

    const content = response.content.trim();
    
    // Try to extract JSON from response
    let jsonMatch = content.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      // Fallback: try to parse the whole response
      jsonMatch = [content];
    }

    try {
      const parsed = JSON.parse(jsonMatch[0]);
      return {
        intent: parsed.intent || 'general_intent',
        confidence: Math.max(0.5, Math.min(1.0, parsed.confidence || 0.7)),
        reasons: [parsed.reason || 'LLM classification'],
      };
    } catch (parseError) {
      // If JSON parse fails, use heuristics
      const lowerContent = content.toLowerCase();
      if (lowerContent.includes('policy')) {
        return { intent: 'policy_intent', confidence: 0.7, reasons: ['LLM suggested policy'] };
      }
      if (lowerContent.includes('action') || lowerContent.includes('schedule') || lowerContent.includes('create')) {
        return { intent: 'action_intent', confidence: 0.7, reasons: ['LLM suggested action'] };
      }
      return { intent: 'general_intent', confidence: 0.6, reasons: ['LLM fallback to general'] };
    }
  } catch (error: any) {
    console.warn('[IntentClassifier] LLM classification failed:', error.message);
    // Default to general intent if LLM fails
    return { intent: 'general_intent', confidence: 0.5, reasons: ['LLM classification failed, defaulting to general'] };
  }
}

/**
 * Main classification function
 */
export async function classifyIntent(userMessage: string): Promise<IntentResult> {
  // First try rule-based classification
  const ruleResult = classifyWithRules(userMessage);
  
  if (ruleResult) {
    const confidenceThreshold = parseFloat(
      process.env.INTENT_RULES_CONFIDENCE_THRESHOLD || '0.75'
    );
    
    // If rules are confident enough, use them
    if (ruleResult.confidence >= confidenceThreshold) {
      return ruleResult;
    }
    
    // If rules are ambiguous, use LLM to confirm
    const llmResult = await classifyWithLLM(userMessage);
    
    // If LLM agrees with rules, boost confidence
    if (llmResult.intent === ruleResult.intent) {
      return {
        intent: ruleResult.intent,
        confidence: Math.min(1.0, (ruleResult.confidence + llmResult.confidence) / 2),
        reasons: [...ruleResult.reasons, ...llmResult.reasons],
      };
    }
    
    // If LLM disagrees, use LLM result but lower confidence
    return {
      intent: llmResult.intent,
      confidence: Math.max(0.6, llmResult.confidence - 0.1),
      reasons: [...ruleResult.reasons, `LLM disagreed: ${llmResult.reasons.join(', ')}`],
    };
  }
  
  // No rule match, use LLM
  return await classifyWithLLM(userMessage);
}

