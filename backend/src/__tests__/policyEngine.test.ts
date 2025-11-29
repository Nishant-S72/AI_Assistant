import { checkPolicy } from '../policy/policyEngine';

describe('PolicyEngine', () => {
  test('should ESCALATE for refund keywords', () => {
    const result = checkPolicy('I need a refund for my order');
    expect(result.action).toBe('ESCALATE');
    expect(result.reasons.length).toBeGreaterThan(0);
  });

  test('should ESCALATE for legal keywords', () => {
    const result = checkPolicy('I will sue you if this is not resolved');
    expect(result.action).toBe('ESCALATE');
  });

  test('should ALLOW normal messages', () => {
    const result = checkPolicy('Thank you for your help with my order');
    expect(result.action).toBe('ALLOW');
  });

  test('should ESCALATE for SSN keywords', () => {
    const result = checkPolicy('My SSN is 123-45-6789');
    expect(result.action).toBe('ESCALATE');
    expect(result.confidence).toBe(1.0);
  });
});

