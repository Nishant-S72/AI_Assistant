import { VectorItem, VectorQueryResult } from './chromaAdapter';
import { upsertToChroma, queryChroma, checkChromaHealth } from './chromaAdapter';
import { upsertToJSON, queryJSON } from './jsonAdapter';

let adapter: 'chroma' | 'json' | null = null;

async function detectAdapter(): Promise<'chroma' | 'json'> {
  if (adapter) return adapter;

  const mode = process.env.VECTORSTORE_MODE;
  if (mode === 'json') {
    adapter = 'json';
    console.log('[VectorStore] Using JSON adapter (forced by env)');
    return adapter;
  }

  if (mode === 'chroma') {
    const isHealthy = await checkChromaHealth();
    if (isHealthy) {
      adapter = 'chroma';
      console.log('[VectorStore] Using Chroma adapter');
      return adapter;
    } else {
      console.warn('[VectorStore] Chroma not reachable, falling back to JSON');
      adapter = 'json';
      return adapter;
    }
  }

  // Auto-detect
  const isChromaHealthy = await checkChromaHealth();
  if (isChromaHealthy) {
    adapter = 'chroma';
    console.log('[VectorStore] Auto-detected: Chroma adapter');
  } else {
    adapter = 'json';
    console.log('[VectorStore] Auto-detected: JSON adapter (Chroma not available)');
  }

  return adapter;
}

export async function upsert(items: VectorItem[]): Promise<void> {
  const currentAdapter = await detectAdapter();
  if (currentAdapter === 'chroma') {
    try {
      await upsertToChroma(items);
    } catch (error: any) {
      console.warn('[VectorStore] Chroma upsert failed, falling back to JSON:', error.message);
      await upsertToJSON(items);
      adapter = 'json';
    }
  } else {
    await upsertToJSON(items);
  }
}

export async function query(
  queryText: string,
  k: number = 3
): Promise<VectorQueryResult[]> {
  const currentAdapter = await detectAdapter();
  if (currentAdapter === 'chroma') {
    try {
      return await queryChroma(queryText, k);
    } catch (error: any) {
      console.warn('[VectorStore] Chroma query failed, falling back to JSON:', error.message);
      adapter = 'json';
      return queryJSON(queryText, k);
    }
  } else {
    return queryJSON(queryText, k);
  }
}

export async function getAdapterName(): Promise<string> {
  const currentAdapter = await detectAdapter();
  return currentAdapter;
}

