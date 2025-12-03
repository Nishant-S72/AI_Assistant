/**
 * SuggestionPanel Component
 * Displays AI-generated suggestion with edit/send functionality
 */

'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { api, Suggestion } from '@/lib/api';
import ToneSelector, { Tone } from './ToneSelector';
import AiThinkingDots from './AiThinkingDots';
import { useAppStore } from '@/lib/store';
import GlassCard from './GlassCard';

// Clear summary cache when actions occur
const invalidateSummaryCache = () => {
  const { clearSummaryCache } = useAppStore.getState();
  clearSummaryCache();
};

interface SuggestionPanelProps {
  messageId: string;
  initialSuggestion?: Suggestion | null;
  onSuggestionGenerated?: (suggestion: Suggestion) => void;
}

export default function SuggestionPanel({
  messageId,
  initialSuggestion,
  onSuggestionGenerated,
}: SuggestionPanelProps) {
  const [suggestion, setSuggestion] = useState<Suggestion | null>(initialSuggestion || null);
  const [tone, setTone] = useState<Tone>('warm');
  const [editedText, setEditedText] = useState<string>('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [policyEscalated, setPolicyEscalated] = useState(false);
  const [showPrompt, setShowPrompt] = useState(false);
  const { showToast } = useAppStore();
  const isInitialMount = useRef(true);
  const previousTone = useRef<Tone>(tone);
  // Cache suggestions by tone
  const suggestionCache = useRef<Map<Tone, Suggestion>>(new Map());

  // Normalize suggestion to ensure all fields are properly set
  const normalizeSuggestion = (suggestion: Suggestion | null): Suggestion | null => {
    if (!suggestion) return null;
    
    // Ensure retrieved_ids is always an array
    let retrieved_ids = suggestion.retrieved_ids;
    if (!Array.isArray(retrieved_ids)) {
      if (typeof retrieved_ids === 'string') {
        try {
          retrieved_ids = JSON.parse(retrieved_ids);
        } catch {
          retrieved_ids = [];
        }
      } else if (retrieved_ids === null || retrieved_ids === undefined) {
        retrieved_ids = [];
      } else {
        retrieved_ids = [];
      }
    }
    
    // Ensure prompt is always a string
    const prompt = suggestion.prompt || '';
    
    // Ensure final_text and model_response are strings
    const final_text = suggestion.final_text || suggestion.model_response || '';
    const model_response = suggestion.model_response || '';
    
    return {
      ...suggestion,
      retrieved_ids: retrieved_ids as string[],
      prompt,
      final_text,
      model_response,
    };
  };

  useEffect(() => {
    if (initialSuggestion) {
      const normalized = normalizeSuggestion(initialSuggestion);
      if (normalized) {
        setSuggestion(normalized);
        setEditedText(normalized.final_text || normalized.model_response || '');
        // Cache the normalized suggestion
        suggestionCache.current.set(tone, normalized);
      }
    }
  }, [initialSuggestion, tone]);

  // Auto-generate when tone changes (but not on initial mount)
  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false;
      previousTone.current = tone;
      return;
    }

    // Only generate if tone actually changed
    if (previousTone.current !== tone && !isGenerating) {
      previousTone.current = tone;
      
      // Check cache first
      const cached = suggestionCache.current.get(tone);
      if (cached) {
        const normalized = normalizeSuggestion(cached);
        if (normalized) {
          setSuggestion(normalized);
          setEditedText(normalized.final_text || normalized.model_response || '');
          setPolicyEscalated(normalized.prompt?.includes('ESCALATE') || false);
          onSuggestionGenerated?.(normalized);
        }
      } else {
        // Generate if not cached
        generateSuggestion(false);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tone]);

  const generateSuggestion = async (forceRegenerate = false) => {
    if (isGenerating) return; // Prevent concurrent generations
    
    // Check cache unless forcing regenerate
    if (!forceRegenerate) {
      const cached = suggestionCache.current.get(tone);
      if (cached) {
        const normalized = normalizeSuggestion(cached);
        if (normalized) {
          setSuggestion(normalized);
          setEditedText(normalized.final_text || normalized.model_response || '');
          setPolicyEscalated(normalized.prompt?.includes('ESCALATE') || false);
          onSuggestionGenerated?.(normalized);
          return;
        }
      }
    }
    
    setIsGenerating(true);
    setPolicyEscalated(false);
    try {
      const result = await api.generateSuggestion(messageId, tone);
      
      // The backend returns { suggestion: "text string", policy_check: {...}, id: "...", message_id: "..." }
      // But the frontend expects { suggestion: Suggestion object, policyCheck: {...} }
      // Convert the string response to a Suggestion object
      let suggestionData: Suggestion | null = null;
      
      if (result.suggestion) {
        // If suggestion is a string, convert it to a Suggestion object
        if (typeof result.suggestion === 'string') {
          suggestionData = {
            id: (result as any).id || '',
            message_id: messageId,
            prompt: '', // Backend doesn't return prompt in this endpoint
            retrieved_ids: [],
            model_response: result.suggestion,
            final_text: result.suggestion,
            edited: false,
            created_at: new Date().toISOString(),
          };
        } else {
          // It's already a Suggestion object
          suggestionData = result.suggestion;
        }
      }
      
      const newSuggestion = normalizeSuggestion(suggestionData);
      
      if (newSuggestion) {
        setSuggestion(newSuggestion);
        setEditedText(newSuggestion.final_text || newSuggestion.model_response || '');
        // Safely check policy escalation - handle both camelCase and snake_case
        const policyCheck = result?.policyCheck || (result as any)?.policy_check;
        const policyAction = policyCheck?.action || 'ALLOW';
        setPolicyEscalated(policyAction === 'ESCALATE_TO_HUMAN' || policyAction === 'ESCALATE');
        // Cache the normalized suggestion
        suggestionCache.current.set(tone, newSuggestion);
        onSuggestionGenerated?.(newSuggestion);
        // Invalidate summary cache since we generated a new suggestion
        invalidateSummaryCache();
      } else {
        showToast('Failed to generate suggestion: invalid response format', 'error');
      }
    } catch (error: any) {
      showToast(error.message || 'Failed to generate suggestion', 'error');
    } finally {
      setIsGenerating(false);
    }
  };

  const sendMessage = async () => {
    if (!editedText || !editedText.trim() || policyEscalated) return;

    setIsSending(true);
    try {
      await api.sendMessage(messageId, editedText, suggestion?.id);
      
      if (suggestion?.id) {
        await api.submitFeedback(suggestion.id, true, editedText);
      }

      showToast('Reply sent (simulated)', 'success');
      setEditedText('');
      setSuggestion(null);
      // Invalidate summary cache since data changed
      invalidateSummaryCache();
      // Invalidate summary cache since data changed
      invalidateSummaryCache();
    } catch (error: any) {
      if (error.message.includes('blocked by policy')) {
        setPolicyEscalated(true);
        showToast('Message blocked by policy', 'error');
      } else {
        showToast(error.message || 'Failed to send message', 'error');
      }
    } finally {
      setIsSending(false);
    }
  };

  const saveDraft = () => {
    // TODO: Implement draft saving
    showToast('Draft saved', 'success');
  };

  return (
    <div className="sticky bottom-0 border-t border-[var(--glass-border)] bg-white/90 backdrop-blur-md p-6 shadow-lg">
      <div className="max-w-4xl mx-auto space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              AI Suggested Reply
            </h3>
            <p className="text-xs text-[var(--muted)] mt-0.5">
              Drafted by Soraya AI — trained on your tone
            </p>
          </div>
          <ToneSelector value={tone} onChange={setTone} disabled={isGenerating} />
        </div>

        {/* Policy Escalation Banner */}
        {policyEscalated && (
          <div className="bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 p-4">
            <div className="flex items-center gap-2">
              <span className="text-red-500">⚠️</span>
              <div>
                <p className="font-medium text-red-800 dark:text-red-200">
                  ESCALATE TO HUMAN
                </p>
                <p className="text-sm text-red-700 dark:text-red-300">
                  This message contains sensitive content and requires human review.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Generating State */}
        {isGenerating && (
          <div className="py-8">
            <AiThinkingDots message="Analyzing conversation and generating reply..." />
          </div>
        )}

        {/* Suggestion Textarea - Always visible */}
        {!isGenerating && (
          <AnimatePresence>
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3 }}
            >
              <textarea
                value={editedText}
                onChange={(e) => setEditedText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                  }
                }}
                className="w-full h-48 p-4 border border-[var(--glass-border)] rounded-lg bg-white/80 backdrop-blur-sm text-gray-900 resize-none focus:ring-2 focus:ring-[var(--primary)] focus:border-transparent transition-all"
                placeholder={suggestion ? "Edit AI suggestion..." : "Click 'Generate AI Response' to create a reply..."}
                aria-label="Edit AI suggested reply"
              />
            </motion.div>
          </AnimatePresence>
        )}

        {/* Action Buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          {!suggestion && !isGenerating && (
            <button
              onClick={() => generateSuggestion(false)}
              className="px-6 py-2.5 bg-[var(--primary)] text-white rounded-lg hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity shadow-sm"
              aria-label="Generate AI suggestion"
            >
              Generate
            </button>
          )}
          {suggestion && (
            <>
              <button
                onClick={sendMessage}
                disabled={isSending || policyEscalated || !(editedText?.trim() || '')}
                className="px-6 py-2.5 bg-[var(--accent)] text-white rounded-lg hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity shadow-sm"
                aria-label="Send reply"
              >
                {isSending ? 'Sending...' : 'Send'}
              </button>
              <button
                onClick={() => generateSuggestion(true)}
                disabled={isGenerating}
                className="px-6 py-2.5 bg-[var(--primary)] text-white rounded-lg hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity shadow-sm"
                aria-label="Generate AI response"
              >
                {isGenerating ? 'Generating...' : 'Generate AI Response'}
              </button>
              <button
                onClick={saveDraft}
                className="px-6 py-2.5 bg-white/80 backdrop-blur-sm border border-[var(--glass-border)] text-gray-700 rounded-lg hover:bg-white transition-colors"
                aria-label="Save draft"
              >
                Save Draft
              </button>
              <button
                onClick={() => {
                  setSuggestion(null);
                  setEditedText('');
                  suggestionCache.current.clear(); // Clear cache when discarding
                }}
                className="px-6 py-2.5 bg-white/80 backdrop-blur-sm border border-[var(--glass-border)] text-gray-700 rounded-lg hover:bg-white transition-colors"
                aria-label="Discard suggestion"
              >
                Discard
              </button>
            </>
          )}
        </div>

        {/* Prompt & Sources Collapsible */}
        {suggestion && (
          <details className="mt-4">
            <summary className="cursor-pointer text-sm font-medium text-gray-700 hover:text-gray-900 transition-colors">
              Prompt & Sources
            </summary>
            <GlassCard className="mt-2 p-4 space-y-2">
              <div>
                <p className="text-xs font-medium text-[var(--muted)] mb-1">
                  Prompt (truncated):
                </p>
                <pre className="text-xs text-gray-700 whitespace-pre-wrap break-words max-h-32 overflow-y-auto custom-scrollbar">
                  {(suggestion.prompt || '').substring(0, 4000)}
                  {(suggestion.prompt || '').length > 4000 && '...'}
                </pre>
              </div>
              {suggestion.retrieved_ids && Array.isArray(suggestion.retrieved_ids) && suggestion.retrieved_ids.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-[var(--muted)] mb-1">
                    Retrieved Sources:
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {suggestion.retrieved_ids.map((id: string) => (
                      <button
                        key={id}
                        onClick={() => navigator.clipboard.writeText(id)}
                        className="text-xs px-2 py-1 bg-white/80 backdrop-blur-sm border border-[var(--glass-border)] rounded hover:bg-white transition-colors"
                        title="Click to copy"
                      >
                        {id.substring(0, 8)}...
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </GlassCard>
          </details>
        )}
      </div>
    </div>
  );
}

