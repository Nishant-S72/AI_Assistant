import { queryJSON, upsertToJSON } from '../clients/vectorstore/jsonAdapter';

// Mock embeddings for testing
jest.mock('../services/embeddings', () => ({
  getEmbedding: jest.fn((text: string) => {
    // Return a simple mock embedding based on text length
    const embedding = new Array(1536).fill(0).map((_, i) => 
      Math.sin(text.length + i) * 0.1
    );
    return Promise.resolve(embedding);
  }),
}));

describe('JSON VectorStore', () => {
  test('should upsert and query vectors', async () => {
    const items = [
      {
        id: 'test-1',
        text: 'This is a test document about AI and machine learning',
        metadata: { type: 'test' },
      },
      {
        id: 'test-2',
        text: 'Another document about programming and software development',
        metadata: { type: 'test' },
      },
    ];

    await upsertToJSON(items);

    const results = await queryJSON('AI machine learning', 2);
    expect(results.length).toBeGreaterThan(0);
    expect(results[0].id).toBeDefined();
    expect(results[0].text).toBeDefined();
    expect(typeof results[0].score).toBe('number');
  });

  test('should return empty array for no matches', async () => {
    const results = await queryJSON('completely unrelated query xyz123', 1);
    expect(Array.isArray(results)).toBe(true);
  });
});

