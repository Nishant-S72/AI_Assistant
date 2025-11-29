import { LLMMessage, LLMOptions, LLMResponse } from './openaiAdapter';
import { generateWithOpenAI } from './openaiAdapter';
import { generateWithOllama, checkOllamaHealth } from './ollamaAdapter';
import { v4 as uuidv4 } from 'uuid';

export interface LLMRequestOptions extends LLMOptions {
  useLocal?: boolean;
  correlationId?: string;
}

export async function generateChatCompletion(
  options: LLMRequestOptions
): Promise<LLMResponse & { correlationId: string; adapter: string }> {
  const correlationId = options.correlationId || uuidv4();
  // Default to Ollama if useLocal is not explicitly false and USE_OLLAMA is not explicitly false
  const useOllama = options.useLocal !== false && (options.useLocal === true || process.env.USE_OLLAMA !== 'false');
  const errors: Array<{ adapter: string; error: string }> = [];
  
  console.log(`[LLM] useOllama=${useOllama}, useLocal=${options.useLocal}, USE_OLLAMA=${process.env.USE_OLLAMA}`);

  // Try Ollama first if configured
  if (useOllama) {
    try {
      const isHealthy = await checkOllamaHealth();
      if (isHealthy) {
        const startTime = Date.now();
        const result = await generateWithOllama(options);
        const latency = Date.now() - startTime;
        console.log(`[LLM] Ollama success (${latency}ms) - correlationId: ${correlationId}`);
        return { ...result, correlationId, adapter: 'ollama' };
      } else {
        errors.push({ adapter: 'ollama', error: 'Health check failed' });
      }
    } catch (error: any) {
      errors.push({ adapter: 'ollama', error: error.message || String(error) });
      console.warn(`[LLM] Ollama failed: ${error.message}`);
    }
  }

  // Fallback to OpenAI
  if (process.env.OPENAI_API_KEY) {
    try {
      const startTime = Date.now();
      const result = await generateWithOpenAI(options);
      const latency = Date.now() - startTime;
      console.log(`[LLM] OpenAI success (${latency}ms) - correlationId: ${correlationId}`);
      return { ...result, correlationId, adapter: 'openai' };
    } catch (error: any) {
      errors.push({ adapter: 'openai', error: error.message || String(error) });
      console.warn(`[LLM] OpenAI failed: ${error.message}`);
    }
  }

  // All adapters failed
  const errorMessage = `All LLM adapters failed:\n${errors
    .map((e) => `  - ${e.adapter}: ${e.error}`)
    .join('\n')}`;
  throw new Error(errorMessage);
}

