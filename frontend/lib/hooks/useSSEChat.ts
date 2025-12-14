import { useState, useRef, useEffect, useCallback } from 'react';

interface SSEMessage {
  type: 'token' | 'done' | 'error';
  text?: string;
}

interface UseSSEChatOptions {
  onComplete?: (fullText: string) => void;
  onError?: (error: Error) => void;
}

export function useSSEChat(options: UseSSEChatOptions = {}) {
  const [text, setText] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const startStream = useCallback(async (
    messages: Array<{ role: string; content: string }>,
    conversationId?: string
  ) => {
    // Cancel any existing stream
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    setText('');
    setError(null);
    setIsStreaming(true);

    try {
      // Use fetch with AbortController for better control
      abortControllerRef.current = new AbortController();
      
      const response = await fetch('/api/v1/stream_chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages,
          conversation_id: conversationId,
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('Response body is not readable');
      }

      let buffer = '';
      let fullText = '';

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.type === 'token' && data.text) {
                fullText += data.text;
                setText(fullText);
              } else if (data.type === 'done') {
                setIsStreaming(false);
                options.onComplete?.(fullText);
                return;
              } else if (data.type === 'error') {
                throw new Error(data.text || 'Streaming error');
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e);
            }
          }
        }
      }

      setIsStreaming(false);
      options.onComplete?.(fullText);
    } catch (err) {
      if (err instanceof Error && err.name !== 'AbortError') {
        setError(err);
        setIsStreaming(false);
        options.onError?.(err);
      }
    }
  }, [options]);

  const cancel = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  useEffect(() => {
    return () => {
      cancel();
    };
  }, [cancel]);

  return {
    text,
    isStreaming,
    error,
    startStream,
    cancel,
  };
}


