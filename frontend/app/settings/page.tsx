/**
 * Settings Page
 * Configuration and preferences
 */

'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { useAppStore } from '@/lib/store';

export default function SettingsPage() {
  const { isOfflineMode, setIsOfflineMode } = useAppStore();
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    loadHealth();
  }, []);

  const loadHealth = async () => {
    try {
      const data = await api.getHealthLocal();
      setHealth(data);
    } catch (error) {
      console.error('Error loading health:', error);
    }
  };

  return (
    <div className="p-6 max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Settings</h1>

      <div className="space-y-6">
        {/* Mode Toggle */}
        <div className="p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Mode
          </h2>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-700 dark:text-gray-300">
                Simulated Mode
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Use local LLM and dummy inbox data
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={isOfflineMode}
                onChange={(e) => setIsOfflineMode(e.target.checked)}
                className="sr-only peer"
                aria-label="Toggle simulated mode"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 dark:peer-focus:ring-primary-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary-600"></div>
            </label>
          </div>
        </div>

        {/* Health Status */}
        {health && (
          <div className="p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              System Status
            </h2>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Status:</span>
                <span
                  className={`font-medium ${
                    health.status === 'ok'
                      ? 'text-green-600 dark:text-green-400'
                      : 'text-yellow-600 dark:text-yellow-400'
                  }`}
                >
                  {health.status || 'Unknown'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">LLM Provider:</span>
                <span
                  className={`font-medium ${
                    health.llm === 'openai_configured'
                      ? 'text-green-600 dark:text-green-400'
                      : 'text-yellow-600 dark:text-yellow-400'
                  }`}
                >
                  {health.llm === 'openai_configured' ? 'OpenAI' : health.llm || 'Not configured'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Database:</span>
                <span
                  className={`font-medium ${
                    health.database === 'connected'
                      ? 'text-green-600 dark:text-green-400'
                      : 'text-red-600 dark:text-red-400'
                  }`}
                >
                  {health.database || 'Unknown'}
                </span>
              </div>
              {health.vectorstore && (
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Vector Store:</span>
                  <span className="text-gray-900 dark:text-white">
                    {health.vectorstore.status} ({health.vectorstore.count_chunks || 0} chunks)
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Keyboard Shortcuts */}
        <div className="p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Keyboard Shortcuts
          </h2>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Command Palette:</span>
              <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs">
                Cmd/Ctrl + K
              </kbd>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Go to Inbox:</span>
              <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs">
                G I
              </kbd>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Go to Tasks:</span>
              <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs">
                G T
              </kbd>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Send Reply:</span>
              <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs">
                Shift + Enter
              </kbd>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

