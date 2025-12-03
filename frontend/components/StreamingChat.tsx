/**
 * StreamingChat Component
 * Minimal consumer for SSE streaming chat endpoint
 */
'use client';

import { useState, useRef, useEffect } from 'react';

interface StreamingChatProps {
  onComplete?: (fullText: string) => void;
}

export default function StreamingChat({ onComplete }: StreamingChatProps) {
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([
    { role: 'user', content: 'Hello, how are you?' },
  ]);
  const [streamingText, setStreamingText] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  const startStream = async () => {
    if (isStreaming) return;

    setIsStreaming(true);
    setStreamingText('');

    // Convert messages to API format
    const apiMessages = [
      ...messages,
      { role: 'assistant', content: '' }, // Placeholder for streaming response
    ];

    try {
      const response = await fetch('http://localhost:3001/api/v1/stream_chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: apiMessages.slice(0, -1), // Exclude placeholder
          model: 'gpt-4o-mini',
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No response body');
      }

      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') {
              setIsStreaming(false);
              const fullText = streamingText;
              setStreamingText('');
              if (onComplete) {
                onComplete(fullText);
              }
              return;
            }

            try {
              const chunk = JSON.parse(data);
              if (chunk.type === 'token') {
                setStreamingText((prev) => prev + chunk.text);
              } else if (chunk.type === 'error') {
                console.error('Stream error:', chunk.text);
                setIsStreaming(false);
              }
            } catch (e) {
              console.error('Failed to parse chunk:', e);
            }
          }
        }
      }
    } catch (error) {
      console.error('Streaming error:', error);
      setIsStreaming(false);
    }
  };

  const cancelStream = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsStreaming(false);
  };

  return (
    <div className="p-4 border rounded-lg">
      <div className="mb-4">
        {messages.map((msg, idx) => (
          <div key={idx} className="mb-2">
            <strong>{msg.role}:</strong> {msg.content}
          </div>
        ))}
        {streamingText && (
          <div className="mb-2 text-blue-600">
            <strong>assistant:</strong> {streamingText}
            <span className="animate-pulse">▊</span>
          </div>
        )}
      </div>
      <div className="flex gap-2">
        <button
          onClick={startStream}
          disabled={isStreaming}
          className="px-4 py-2 bg-blue-500 text-white rounded disabled:bg-gray-400"
        >
          Start Stream
        </button>
        {isStreaming && (
          <button
            onClick={cancelStream}
            className="px-4 py-2 bg-red-500 text-white rounded"
          >
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}

