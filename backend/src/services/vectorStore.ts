// Legacy compatibility - re-export from new abstraction
import { upsert, query } from '../clients/vectorstore';

export interface VectorDocument {
  id: string;
  text: string;
  embedding?: number[];
  metadata: {
    type: string;
    source?: string;
    contact_id?: string;
    created_at: string;
  };
}

// Compatibility wrapper for old code
export const vectorStore = {
  async addDocument(
    id: string,
    text: string,
    metadata: VectorDocument['metadata']
  ): Promise<void> {
    await upsert([
      {
        id,
        text,
        metadata: {
          ...metadata,
          created_at: metadata.created_at || new Date().toISOString(),
        },
      },
    ]);
  },

  async search(queryText: string, topK: number = 3): Promise<VectorDocument[]> {
    const results = await query(queryText, topK);
    return results.map((r) => ({
      id: r.id,
      text: r.text,
      metadata: (r.metadata || {}) as VectorDocument['metadata'],
    }));
  },

  getDocument(id: string): VectorDocument | undefined {
    // Not supported in new abstraction - would need to query all
    return undefined;
  },
};
