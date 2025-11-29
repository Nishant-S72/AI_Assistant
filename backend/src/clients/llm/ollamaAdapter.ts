import { LLMMessage, LLMOptions, LLMResponse } from './openaiAdapter';

export async function generateWithOllama(
  options: LLMOptions
): Promise<LLMResponse> {
  const baseUrl = process.env.LLM_BASE_URL || 'http://localhost:11434';
  const model = options.model || process.env.LLM_MODEL || 'phi3';

  const response = await fetch(`${baseUrl}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model,
      messages: options.messages.map((msg) => ({
        role: msg.role,
        content: msg.content,
      })),
      stream: false, // Request non-streaming response
      options: {
        temperature: options.temperature ?? 0.7, // Balanced for lightweight model
        num_predict: options.max_tokens || 500, // Reduced for lighter model
        num_ctx: 2048, // Reduced context window for lighter model (was 8192)
        top_k: 20, // Reduced for lighter model
        top_p: 0.9, // Slightly reduced for lighter model
        repeat_penalty: 1.1, // Prevent repetition
        num_thread: 2, // Reduced threads for lighter system load (was 8)
        numa: false, // Disable NUMA for lighter systems
      },
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Ollama API error: ${response.status} - ${errorText}`);
  }

  // Ollama may return streaming JSON (multiple lines) even with stream:false
  // Handle both single JSON and streaming formats
  const text = await response.text();
  let data: {
    message?: { content?: string };
    model?: string;
    prompt_eval_count?: number;
    eval_count?: number;
    done?: boolean;
  };

  try {
    // Try parsing as single JSON first
    data = JSON.parse(text);
  } catch (parseError) {
    // If it's streaming format (multiple JSON lines), parse all chunks
    const lines = text.trim().split('\n').filter(line => line.trim());
    if (lines.length === 0) {
      throw new Error('Ollama returned empty response');
    }

    // Accumulate content from all chunks
    let fullContent = '';
    let finalData: typeof data | null = null;
    let modelName = model;
    let promptTokens = 0;
    let completionTokens = 0;

    for (const line of lines) {
      try {
        const chunk = JSON.parse(line);
        
        // Accumulate message content
        if (chunk.message?.content) {
          fullContent += chunk.message.content;
        }
        
        // Track model and tokens
        if (chunk.model) modelName = chunk.model;
        if (chunk.prompt_eval_count) promptTokens = chunk.prompt_eval_count;
        if (chunk.eval_count) completionTokens = chunk.eval_count;
        
        // Last chunk with done:true is the final one
        if (chunk.done) {
          finalData = chunk;
        }
      } catch (e) {
        // Skip invalid JSON lines
        console.warn('Skipping invalid JSON line from Ollama:', line.substring(0, 50));
      }
    }

    // Use final chunk if available, otherwise construct from accumulated data
    if (finalData) {
      data = {
        ...finalData,
        message: { content: fullContent || finalData.message?.content || '' },
        model: modelName,
        prompt_eval_count: promptTokens,
        eval_count: completionTokens,
      };
    } else if (fullContent) {
      // Fallback: construct response from accumulated content
      data = {
        message: { content: fullContent },
        model: modelName,
        prompt_eval_count: promptTokens,
        eval_count: completionTokens,
      };
    } else {
      // Last resort: try to parse the last line
      try {
        data = JSON.parse(lines[lines.length - 1]);
      } catch (e) {
        throw new Error(`Ollama response parse error: ${text.substring(0, 200)}`);
      }
    }
  }

  return {
    content: data.message?.content || '',
    model: data.model || model,
    usage: {
      prompt_tokens: data.prompt_eval_count,
      completion_tokens: data.eval_count,
      total_tokens: (data.prompt_eval_count || 0) + (data.eval_count || 0),
    },
  };
}

export async function checkOllamaHealth(): Promise<boolean> {
  try {
    const baseUrl = process.env.LLM_BASE_URL || 'http://localhost:11434';
    const response = await fetch(`${baseUrl}/api/tags`, {
      method: 'GET',
      signal: AbortSignal.timeout(3000),
    });
    return response.ok;
  } catch {
    return false;
  }
}
