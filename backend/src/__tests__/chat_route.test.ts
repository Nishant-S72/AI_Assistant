/**
 * Integration tests for Chat Route with Intent-Based Routing
 */

import request from 'supertest';
import express from 'express';
import chatRouter from '../routes/chat';

// Mock dependencies
jest.mock('../clients/llm', () => ({
  generateChatCompletion: jest.fn(),
  LLMMessage: jest.fn(),
}));

jest.mock('../policy/intentClassifier', () => ({
  classifyIntent: jest.fn(),
}));

jest.mock('../clients/vectorstore', () => ({
  query: jest.fn(),
}));

jest.mock('../db', () => ({
  pool: {
    query: jest.fn(),
  },
}));

const app = express();
app.use(express.json());
app.use('/api/chat', chatRouter);

describe('Chat Route - Intent-Based Routing', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('POST /api/chat with general intent returns conversational response', async () => {
    const { classifyIntent } = require('../policy/intentClassifier');
    const { generateChatCompletion } = require('../clients/llm');

    classifyIntent.mockResolvedValue({
      intent: 'general_intent',
      confidence: 0.9,
      reasons: ['No policy keywords'],
    });

    generateChatCompletion.mockResolvedValue({
      content: 'RAG stands for Retrieval-Augmented Generation...',
      model: 'tinyllama',
      correlationId: 'test-123',
      adapter: 'ollama',
    });

    const response = await request(app)
      .post('/api/chat')
      .send({
        userMessage: 'How do I write a follow-up email after a meeting?',
      });

    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('kind', 'assistant');
    expect(response.body).toHaveProperty('text');
    expect(response.body).toHaveProperty('intent', 'general_intent');
    expect(response.body.text).not.toContain('(Policy');
    expect(response.body.citations).toBeUndefined();
  });

  test('POST /api/chat with policy intent returns policy-backed response with citations', async () => {
    const { classifyIntent } = require('../policy/intentClassifier');
    const { generateChatCompletion } = require('../clients/llm');
    const { query } = require('../clients/vectorstore');

    classifyIntent.mockResolvedValue({
      intent: 'policy_intent',
      confidence: 0.95,
      reasons: ['Contains policy keywords'],
    });

    query.mockResolvedValue([
      {
        id: 'chunk-1',
        text: 'Refund policy: refunds are processed within 5-7 business days...',
        score: 0.85,
        metadata: {},
      },
    ]);

    generateChatCompletion.mockResolvedValue({
      content: 'According to our policy (Policy §4.2), refunds are processed within 5-7 business days.',
      model: 'tinyllama',
      correlationId: 'test-123',
      adapter: 'ollama',
    });

    const response = await request(app)
      .post('/api/chat')
      .send({
        userMessage: 'Does our refund policy cover partial refunds?',
      });

    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('kind', 'policy');
    expect(response.body).toHaveProperty('text');
    expect(response.body).toHaveProperty('citations');
    expect(response.body).toHaveProperty('intent', 'policy_intent');
    expect(response.body.text).toContain('(Policy');
    expect(Array.isArray(response.body.citations)).toBe(true);
  });

  test('POST /api/chat with action intent returns action suggestion', async () => {
    const { classifyIntent } = require('../policy/intentClassifier');
    const { generateChatCompletion } = require('../clients/llm');

    classifyIntent.mockResolvedValue({
      intent: 'action_intent',
      confidence: 0.9,
      reasons: ['Contains action keywords'],
    });

    generateChatCompletion.mockResolvedValue({
      content: JSON.stringify({
        action_type: 'calendar_event',
        title: 'Call with John',
        start: '2025-12-04T15:00:00',
        end: '2025-12-04T16:00:00',
        attendees: ['john@example.com'],
        confirm_needed: false,
        reply_text: "I'll schedule a call with John next Thursday at 3pm.",
      }),
      model: 'tinyllama',
      correlationId: 'test-123',
      adapter: 'ollama',
    });

    const response = await request(app)
      .post('/api/chat')
      .send({
        userMessage: 'Please schedule a call with John next Thursday at 3pm',
      });

    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('kind', 'action');
    expect(response.body).toHaveProperty('intent', 'action_intent');
    expect(response.body).toHaveProperty('action_suggestion');
    expect(response.body.action_suggestion).toHaveProperty('action_type');
  });

  test('POST /api/chat/rag (deprecated) still works', async () => {
    const { query } = require('../clients/vectorstore');
    const { generateChatCompletion } = require('../clients/llm');

    query.mockResolvedValue([]);
    generateChatCompletion.mockResolvedValue({
      content: 'Policy response...',
      model: 'tinyllama',
      correlationId: 'test-123',
      adapter: 'ollama',
    });

    const response = await request(app)
      .post('/api/chat/rag')
      .send({
        userMessage: 'What is the policy?',
      });

    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('reply');
    expect(response.body).toHaveProperty('citations');
  });
});

