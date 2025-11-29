/**
 * Priority computation logic for tasks
 * Returns 'P0' | 'P1' | 'P2' based on deterministic rules
 */

export interface TaskInput {
  due_at?: string | Date | null;
  title?: string;
  status?: string;
}

export interface MessageInput {
  body?: string;
  sender?: string;
}

export interface ContactInput {
  tags?: string[] | string;
  last_order_amount?: number;
  email?: string;
}

export interface PriorityInput {
  task?: TaskInput;
  message?: MessageInput;
  contact?: ContactInput;
}

/**
 * Compute priority based on rules:
 * - P0: Overdue, legal/urgent keywords, VIP, high-value orders
 * - P1: Due within 3 days, complaints, high-value leads
 * - P2: Everything else
 */
export function computePriority(input: PriorityInput): 'P0' | 'P1' | 'P2' {
  const { task, message, contact } = input;

  // P0 Rules
  // 1. Task overdue (due_at <= today)
  if (task?.due_at) {
    const dueDate = new Date(task.due_at);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    dueDate.setHours(0, 0, 0, 0);
    if (dueDate <= today && task.status !== 'completed') {
      return 'P0';
    }
  }

  // 2. Legal/urgent keywords in message
  const urgentKeywords = ['refund', 'lawsuit', 'urgent', 'immediately', 'chargeback', 'sue'];
  if (message?.body) {
    const bodyLower = message.body.toLowerCase();
    if (urgentKeywords.some(keyword => bodyLower.includes(keyword))) {
      return 'P0';
    }
  }

  // 3. VIP contact
  const tags = Array.isArray(contact?.tags) 
    ? contact.tags 
    : typeof contact?.tags === 'string' 
      ? JSON.parse(contact.tags || '[]') 
      : [];
  if (tags.includes('vip')) {
    return 'P0';
  }

  // 4. High-value order (>= 50000)
  if (contact?.last_order_amount && contact.last_order_amount >= 50000) {
    return 'P0';
  }

  // P1 Rules
  // 1. Due within 3 days
  if (task?.due_at) {
    const dueDate = new Date(task.due_at);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    dueDate.setHours(0, 0, 0, 0);
    const daysUntilDue = Math.ceil((dueDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
    if (daysUntilDue <= 3 && daysUntilDue > 0 && task.status !== 'completed') {
      return 'P1';
    }
  }

  // 2. Complaint keywords
  const complaintKeywords = ['delay', 'late', 'not happy', 'angry', 'complaint'];
  if (message?.body) {
    const bodyLower = message.body.toLowerCase();
    if (complaintKeywords.some(keyword => bodyLower.includes(keyword))) {
      return 'P1';
    }
  }

  // 3. Lead with estimated value (tags contain 'lead' and has high order amount)
  if (tags.includes('lead') && contact?.last_order_amount && contact.last_order_amount >= 10000) {
    return 'P1';
  }

  // Default: P2
  return 'P2';
}


