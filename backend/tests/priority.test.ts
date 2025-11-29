import { computePriority, PriorityInput } from '../src/lib/priority';

describe('computePriority', () => {
  it('should return P0 for overdue tasks', () => {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);

    const input: PriorityInput = {
      task: {
        due_at: yesterday.toISOString(),
        title: 'Test task',
        status: 'pending',
      },
    };

    expect(computePriority(input)).toBe('P0');
  });

  it('should return P0 for tasks with urgent keywords', () => {
    const input: PriorityInput = {
      message: {
        body: 'I need a refund immediately!',
      },
    };

    expect(computePriority(input)).toBe('P0');
  });

  it('should return P0 for VIP contacts', () => {
    const input: PriorityInput = {
      contact: {
        tags: ['vip', 'enterprise'],
      },
    };

    expect(computePriority(input)).toBe('P0');
  });

  it('should return P0 for high-value orders', () => {
    const input: PriorityInput = {
      contact: {
        last_order_amount: 60000,
      },
    };

    expect(computePriority(input)).toBe('P0');
  });

  it('should return P1 for tasks due within 3 days', () => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);

    const input: PriorityInput = {
      task: {
        due_at: tomorrow.toISOString(),
        title: 'Test task',
        status: 'pending',
      },
    };

    expect(computePriority(input)).toBe('P1');
  });

  it('should return P1 for messages with complaint keywords', () => {
    const input: PriorityInput = {
      message: {
        body: 'I am not happy with the delay in shipping',
      },
    };

    expect(computePriority(input)).toBe('P1');
  });

  it('should return P1 for high-value leads', () => {
    const input: PriorityInput = {
      contact: {
        tags: ['lead'],
        last_order_amount: 15000,
      },
    };

    expect(computePriority(input)).toBe('P1');
  });

  it('should return P2 as default', () => {
    const input: PriorityInput = {
      task: {
        title: 'Normal task',
        status: 'pending',
      },
    };

    expect(computePriority(input)).toBe('P2');
  });

  it('should prioritize P0 over P1', () => {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);

    const input: PriorityInput = {
      task: {
        due_at: yesterday.toISOString(),
        title: 'Overdue task',
        status: 'pending',
      },
      message: {
        body: 'This is a complaint about delay',
      },
    };

    // Should be P0 (overdue) not P1 (complaint)
    expect(computePriority(input)).toBe('P0');
  });
});


