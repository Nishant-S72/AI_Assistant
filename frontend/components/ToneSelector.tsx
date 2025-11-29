/**
 * ToneSelector Component
 * Allows user to select tone (Formal, Warm, Crisp) for AI suggestions
 */

'use client';

import { cn } from '@/lib/utils';

export type Tone = 'formal' | 'warm' | 'crisp';

interface ToneSelectorProps {
  value: Tone;
  onChange: (tone: Tone) => void;
  disabled?: boolean;
}

export default function ToneSelector({
  value,
  onChange,
  disabled = false,
}: ToneSelectorProps) {
  const tones: { value: Tone; label: string; description: string }[] = [
    { value: 'formal', label: 'Formal', description: 'Professional and courteous' },
    { value: 'warm', label: 'Warm', description: 'Friendly and approachable' },
    { value: 'crisp', label: 'Crisp', description: 'Direct and action-oriented' },
  ];

  return (
    <div className="flex items-center gap-2">
      <label className="text-sm font-medium text-gray-700">
        Tone:
      </label>
      <div className="flex gap-2">
        {tones.map((tone) => (
          <button
            key={tone.value}
            onClick={() => !disabled && onChange(tone.value)}
            disabled={disabled}
            className={cn(
              'px-3 py-1.5 text-sm rounded-full border transition-all',
              value === tone.value
                ? 'bg-[var(--primary)] text-white border-[var(--primary)] shadow-sm'
                : 'bg-white/80 backdrop-blur-sm text-gray-700 border-[var(--glass-border)] hover:bg-white hover:border-[var(--primary)]/30',
              disabled && 'opacity-50 cursor-not-allowed'
            )}
            aria-pressed={value === tone.value}
            aria-label={`Select ${tone.label} tone: ${tone.description}`}
            title={tone.description}
          >
            {tone.label}
          </button>
        ))}
      </div>
    </div>
  );
}

