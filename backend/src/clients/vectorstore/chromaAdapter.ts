import { getEmbedding } from '../../services/embeddings';

export interface VectorItem {
  id: string;
  text: string;
  embedding?: number[];
  metadata?: Record<string, any>;
}

export interface VectorQueryResult {
  id: string;
  text: string;
  metadata?: Record<string, any>;
  score: number;
}

const CHROMA_BASE_URL = process.env.CHROMA_BASE_URL || 'http://localhost:8000';
const COLLECTION_NAME = 'aichief_kb';

let collectionId: string | null = null;

async function ensureCollection(): Promise<string> {
  if (collectionId) return collectionId;

  try {
    // Check if collection exists
    const listResponse = await fetch(`${CHROMA_BASE_URL}/api/v1/collections`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });

    if (listResponse.ok) {
      const collections = await listResponse.json() as Array<{ id: string; name: string }>;
      const existing = collections.find((c) => c.name === COLLECTION_NAME);
      if (existing) {
        collectionId = existing.id;
        return collectionId;
      }
    }

    // Create collection
    const createResponse = await fetch(`${CHROMA_BASE_URL}/api/v1/collections`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: COLLECTION_NAME,
        metadata: {},
      }),
    });

    if (createResponse.ok) {
      const data = await createResponse.json() as { id: string };
      collectionId = data.id;
      return collectionId;
    }

    throw new Error('Failed to create Chroma collection');
  } catch (error: any) {
    throw new Error(`Chroma collection error: ${error.message}`);
  }
}

export async function upsertToChroma(items: VectorItem[]): Promise<void> {
  const collId = await ensureCollection();

  // Generate embeddings if not provided
  const itemsWithEmbeddings = await Promise.all(
    items.map(async (item) => {
      if (!item.embedding) {
        item.embedding = await getEmbedding(item.text);
      }
      return item;
    })
  );

  const response = await fetch(
    `${CHROMA_BASE_URL}/api/v1/collections/${collId}/add`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ids: itemsWithEmbeddings.map((i) => i.id),
        embeddings: itemsWithEmbeddings.map((i) => i.embedding),
        documents: itemsWithEmbeddings.map((i) => i.text),
        metadatas: itemsWithEmbeddings.map((i) => i.metadata || {}),
      }),
    }
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Chroma upsert error: ${response.status} - ${errorText}`);
  }
}

export async function queryChroma(
  queryText: string,
  k: number = 3
): Promise<VectorQueryResult[]> {
  const collId = await ensureCollection();
  const queryEmbedding = await getEmbedding(queryText);

  const response = await fetch(
    `${CHROMA_BASE_URL}/api/v1/collections/${collId}/query`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query_embeddings: [queryEmbedding],
        n_results: k,
      }),
    }
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Chroma query error: ${response.status} - ${errorText}`);
  }

  const data = await response.json() as {
    ids?: string[][];
    documents?: string[][];
    metadatas?: Record<string, any>[][];
    distances?: number[][];
  };
  const results: VectorQueryResult[] = [];

  if (data.ids && data.ids[0]) {
    for (let i = 0; i < data.ids[0].length; i++) {
      results.push({
        id: data.ids[0][i],
        text: data.documents?.[0]?.[i] || '',
        metadata: data.metadatas?.[0]?.[i],
        score: data.distances?.[0]?.[i] ? 1 - data.distances[0][i] : 0,
      });
    }
  }

  return results;
}

export async function checkChromaHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${CHROMA_BASE_URL}/api/v1/heartbeat`, {
      method: 'GET',
      signal: AbortSignal.timeout(3000),
    });
    return response.ok;
  } catch {
    return false;
  }
}

