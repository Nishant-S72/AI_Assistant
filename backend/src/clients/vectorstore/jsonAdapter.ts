import * as fs from 'fs';
import * as path from 'path';
import { getEmbedding } from '../../services/embeddings';
import { VectorItem, VectorQueryResult } from './chromaAdapter';

interface StoredVector {
  id: string;
  text: string;
  embedding: number[];
  metadata: Record<string, any>;
  createdAt: string;
}

class JSONVectorStore {
  private filePath: string;
  private vectors: Map<string, StoredVector> = new Map();
  private maxVectors = 10000; // Limit to prevent memory issues

  constructor() {
    this.filePath = path.join(__dirname, '../../../storage/vectors.json');
    this.load();
  }

  private load() {
    try {
      const dir = path.dirname(this.filePath);
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }

      if (fs.existsSync(this.filePath)) {
        const data = fs.readFileSync(this.filePath, 'utf-8');
        const stored: StoredVector[] = JSON.parse(data);
        stored.forEach((v) => this.vectors.set(v.id, v));
        console.log(`[VectorStore] Loaded ${this.vectors.size} vectors from JSON`);
      }
    } catch (error) {
      console.warn('[VectorStore] Could not load JSON store, starting fresh:', error);
      this.vectors = new Map();
    }
  }

  private save() {
    try {
      const data = Array.from(this.vectors.values());
      fs.writeFileSync(this.filePath, JSON.stringify(data, null, 2));
    } catch (error) {
      console.error('[VectorStore] Error saving JSON store:', error);
    }
  }

  private cosineSimilarity(a: number[], b: number[]): number {
    if (a.length !== b.length) return 0;
    let dotProduct = 0;
    let normA = 0;
    let normB = 0;
    for (let i = 0; i < a.length; i++) {
      dotProduct += a[i] * b[i];
      normA += a[i] * a[i];
      normB += b[i] * b[i];
    }
    const denominator = Math.sqrt(normA) * Math.sqrt(normB);
    return denominator === 0 ? 0 : dotProduct / denominator;
  }

  async upsert(items: VectorItem[]): Promise<void> {
    for (const item of items) {
      // Limit total vectors
      if (this.vectors.size >= this.maxVectors && !this.vectors.has(item.id)) {
        // Remove oldest
        const oldest = Array.from(this.vectors.values()).sort(
          (a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
        )[0];
        this.vectors.delete(oldest.id);
      }

      let embedding = item.embedding;
      if (!embedding) {
        embedding = await getEmbedding(item.text);
      }

      this.vectors.set(item.id, {
        id: item.id,
        text: item.text,
        embedding,
        metadata: item.metadata || {},
        createdAt: new Date().toISOString(),
      });
    }
    this.save();
  }

  async query(queryText: string, k: number = 3): Promise<VectorQueryResult[]> {
    const queryEmbedding = await getEmbedding(queryText);

    const results = Array.from(this.vectors.values())
      .map((vec) => ({
        id: vec.id,
        text: vec.text,
        metadata: vec.metadata,
        score: this.cosineSimilarity(queryEmbedding, vec.embedding),
      }))
      .sort((a, b) => b.score - a.score)
      .slice(0, k);

    return results;
  }
}

const jsonStore = new JSONVectorStore();

export async function upsertToJSON(items: VectorItem[]): Promise<void> {
  await jsonStore.upsert(items);
}

export async function queryJSON(
  queryText: string,
  k: number = 3
): Promise<VectorQueryResult[]> {
  return jsonStore.query(queryText, k);
}

