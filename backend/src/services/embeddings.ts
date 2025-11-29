import OpenAI from 'openai';

// Simple LRU cache for embeddings
class EmbeddingCache {
  private cache: Map<string, { embedding: number[]; timestamp: number }> = new Map();
  private maxSize = 1000;
  private ttl = 24 * 60 * 60 * 1000; // 24 hours

  get(key: string): number[] | null {
    const entry = this.cache.get(key);
    if (!entry) return null;
    if (Date.now() - entry.timestamp > this.ttl) {
      this.cache.delete(key);
      return null;
    }
    return entry.embedding;
  }

  set(key: string, embedding: number[]): void {
    if (this.cache.size >= this.maxSize) {
      // Remove oldest
      const firstKey = this.cache.keys().next().value;
      if (firstKey) {
        this.cache.delete(firstKey);
      }
    }
    this.cache.set(key, { embedding, timestamp: Date.now() });
  }
}

const cache = new EmbeddingCache();

let openaiClient: OpenAI | null = null;

function getOpenAIClient(): OpenAI {
  if (!openaiClient) {
    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) {
      throw new Error('OPENAI_API_KEY not configured for embeddings');
    }
    openaiClient = new OpenAI({ apiKey });
  }
  return openaiClient;
}

export async function getEmbedding(text: string): Promise<number[]> {
  // Check cache
  const cacheKey = `embed:${text.substring(0, 100)}`;
  const cached = cache.get(cacheKey);
  if (cached) {
    return cached;
  }

  // If using Ollama, try Ollama embeddings first
  if (process.env.USE_OLLAMA === 'true') {
    try {
      const baseUrl = process.env.LLM_BASE_URL || 'http://localhost:11434';
      const response = await fetch(`${baseUrl}/api/embeddings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: process.env.LLM_MODEL || 'tinyllama',
          prompt: text,
        }),
      });

      if (response.ok) {
        const data = await response.json() as { embedding?: number[] };
        if (data.embedding) {
          cache.set(cacheKey, data.embedding);
          return data.embedding;
        }
      }
    } catch (error) {
      console.warn('Ollama embeddings failed, falling back to simple hash-based embedding');
    }

    // Fallback: Generate simple hash-based embedding for demo
    // This is not a real embedding but works for demo purposes
    const simpleEmbedding = generateSimpleEmbedding(text);
    cache.set(cacheKey, simpleEmbedding);
    return simpleEmbedding;
  }

  // Generate embedding with OpenAI
  const client = getOpenAIClient();
  const response = await client.embeddings.create({
    model: 'text-embedding-3-small',
    input: text,
  });

  const embedding = response.data[0].embedding;
  cache.set(cacheKey, embedding);
  return embedding;
}

// Simple hash-based embedding for demo (not real embeddings but works for RAG demo)
function generateSimpleEmbedding(text: string): number[] {
  const embedding = new Array(384).fill(0);
  const words = text.toLowerCase().split(/\s+/);
  
  for (let i = 0; i < words.length; i++) {
    const word = words[i];
    let hash = 0;
    for (let j = 0; j < word.length; j++) {
      hash = ((hash << 5) - hash) + word.charCodeAt(j);
      hash = hash & hash;
    }
    const index = Math.abs(hash) % embedding.length;
    embedding[index] += 1 / (i + 1);
  }
  
  // Normalize
  const magnitude = Math.sqrt(embedding.reduce((sum, val) => sum + val * val, 0));
  if (magnitude > 0) {
    return embedding.map(val => val / magnitude);
  }
  return embedding;
}

export async function getEmbeddingsBatch(texts: string[]): Promise<number[][]> {
  // For now, process sequentially with caching
  // Could be optimized to batch API calls
  return Promise.all(texts.map((text) => getEmbedding(text)));
}

