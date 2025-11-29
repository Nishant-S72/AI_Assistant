/**
 * Tests for Intent Classifier
 */

import { classifyIntent } from '../policy/intentClassifier';

describe('Intent Classifier', () => {
  jest.setTimeout(30000); // 30s timeout for LLM calls

  test('classifies policy intent correctly', async () => {
    const result = await classifyIntent('What does the return policy say about refunds?');
    expect(result.intent).toBe('policy_intent');
    expect(result.confidence).toBeGreaterThan(0.5);
    expect(result.reasons.length).toBeGreaterThan(0);
  });

  test('classifies action intent correctly', async () => {
    const result = await classifyIntent('Schedule a meeting next Tuesday with Alice at 4 PM');
    expect(result.intent).toBe('action_intent');
    expect(result.confidence).toBeGreaterThan(0.5);
  });

  test('classifies general intent correctly', async () => {
    const result = await classifyIntent('Explain how RAG works');
    expect(result.intent).toBe('general_intent');
    expect(result.confidence).toBeGreaterThan(0.3);
  });

  test('handles ambiguous queries with LLM fallback', async () => {
    const result = await classifyIntent('What should I do?');
    expect(['policy_intent', 'action_intent', 'general_intent']).toContain(result.intent);
    expect(result.confidence).toBeGreaterThan(0.0);
  });

  test('returns valid intent structure', async () => {
    const result = await classifyIntent('Hello');
    expect(result).toHaveProperty('intent');
    expect(result).toHaveProperty('confidence');
    expect(result).toHaveProperty('reasons');
    expect(['policy_intent', 'action_intent', 'general_intent']).toContain(result.intent);
    expect(result.confidence).toBeGreaterThanOrEqual(0.0);
    expect(result.confidence).toBeLessThanOrEqual(1.0);
  });
});

