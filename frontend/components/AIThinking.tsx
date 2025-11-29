'use client';

import { motion } from 'framer-motion';

interface AIThinkingProps {
  message: string;
}

export default function AIThinking({ message }: AIThinkingProps) {
  return (
    <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
      <motion.div
        animate={{ opacity: [0.5, 1, 0.5] }}
        transition={{ duration: 1.5, repeat: Infinity }}
        className="w-2 h-2 bg-blue-500 rounded-full"
      />
      <motion.div
        animate={{ opacity: [0.5, 1, 0.5] }}
        transition={{ duration: 1.5, repeat: Infinity, delay: 0.2 }}
        className="w-2 h-2 bg-blue-500 rounded-full"
      />
      <motion.div
        animate={{ opacity: [0.5, 1, 0.5] }}
        transition={{ duration: 1.5, repeat: Infinity, delay: 0.4 }}
        className="w-2 h-2 bg-blue-500 rounded-full"
      />
      <span className="ml-2">{message}</span>
    </div>
  );
}

