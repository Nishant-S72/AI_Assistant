import { PromptBuilder } from '../services/promptBuilder';

describe('PromptBuilder', () => {
  test('should build prompt with truncation', () => {
    const builder = new PromptBuilder('warm', 'John Doe', 'Acme Corp');
    builder.addThreadMessages([
      { sender: 'contact', body: 'Hello', created_at: '2024-01-01' },
      { sender: 'assistant', body: 'Hi there', created_at: '2024-01-01' },
    ]);

    const { promptString, metadata } = builder.build();
    expect(promptString).toContain('warm');
    expect(promptString).toContain('John Doe');
    expect(promptString).toContain('Acme Corp');
    expect(metadata.threadMessageCount).toBe(2);
  });

  test('should sanitize text', () => {
    const builder = new PromptBuilder('formal', 'Test', 'Test');
    builder.addThreadMessages([
      {
        sender: 'contact',
        body: 'Hello\x00\x01\x02World',
        created_at: '2024-01-01',
      },
    ]);

    const { promptString } = builder.build();
    expect(promptString).not.toContain('\x00');
  });
});

