import OpenAI from 'openai';

export interface LLMMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface LLMOptions {
  model: string;
  messages: LLMMessage[];
  max_tokens?: number;
  temperature?: number;
}

export interface LLMResponse {
  content: string;
  model: string;
  usage?: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
  };
}

export async function generateWithOpenAI(
  options: LLMOptions
): Promise<LLMResponse> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    throw new Error('OPENAI_API_KEY not configured');
  }

  const client = new OpenAI({ apiKey });

  const response = await client.chat.completions.create({
    model: options.model,
    messages: options.messages as any,
    max_tokens: options.max_tokens,
    temperature: options.temperature ?? 0.7,
  });

  return {
    content: response.choices[0]?.message?.content || '',
    model: response.model,
    usage: {
      prompt_tokens: response.usage?.prompt_tokens,
      completion_tokens: response.usage?.completion_tokens,
      total_tokens: response.usage?.total_tokens,
    },
  };
}

