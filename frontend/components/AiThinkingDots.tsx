/**
 * AI Thinking Dots Animation - Matte White Theme
 * Shows animated dots with electric blue glow and trailing line while AI is processing
 * To revert: restore original AiThinkingDots.tsx from git history
 */

'use client';

import { motion } from 'framer-motion';

interface AiThinkingDotsProps {
  message?: string;
  size?: 'sm' | 'md' | 'lg';
}

export default function AiThinkingDots({
  message = 'AI is thinking',
  size = 'md',
}: AiThinkingDotsProps) {
  const dotSize = size === 'sm' ? 'w-1.5 h-1.5' : size === 'lg' ? 'w-3 h-3' : 'w-2 h-2';

  return (
    <div className="flex items-center gap-3 text-sm text-[var(--muted)]">
      <div className="flex items-center gap-1.5 relative">
        {/* Trailing line animation */}
        <motion.div
          className="absolute left-0 top-1/2 h-0.5 bg-[var(--primary)] opacity-30"
          initial={{ width: 0 }}
          animate={{
            width: ['0%', '100%', '0%'],
            opacity: [0, 0.6, 0],
          }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
          style={{ transform: 'translateY(-50%)' }}
        />
        
        {/* Glowing dots */}
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className={`${dotSize} rounded-full bg-[var(--primary)] ai-glow`}
            animate={{
              opacity: [0.4, 1, 0.4],
              scale: [1, 1.3, 1],
            }}
            transition={{
              duration: 1.2,
              repeat: Infinity,
              delay: i * 0.2,
              ease: 'easeInOut',
            }}
            style={{
              boxShadow: '0 0 8px var(--primary), 0 0 12px var(--primary)',
            }}
          />
        ))}
      </div>
      <span className="font-medium">{message}</span>
    </div>
  );
}

