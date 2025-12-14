'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';

export default function CalendarConnectPage() {
  const [providers, setProviders] = useState<Array<{
    id: string;
    name: string;
    connected: boolean;
  }>>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    // Check connection status
    // TODO: Fetch from API
    setProviders([
      { id: 'google', name: 'Google Calendar', connected: false },
      { id: 'outlook', name: 'Microsoft Outlook', connected: false },
    ]);
    setLoading(false);
  }, []);

  const handleConnect = async (provider: string) => {
    try {
      const redirectUri = `${window.location.origin}/calendar-connect/callback`;
      let response;
      if (provider === 'google') {
        response = await api.scheduler.connectGoogle(redirectUri);
      } else if (provider === 'outlook') {
        response = await api.scheduler.connectOutlook(redirectUri);
      } else {
        throw new Error(`Unknown provider: ${provider}`);
      }
      
      if (response.oauth_url) {
        // Store state for validation
        sessionStorage.setItem('oauth_state', response.state);
        window.location.href = response.oauth_url;
      }
    } catch (error) {
      console.error('Error connecting calendar:', error);
      alert('Failed to connect calendar. Please try again.');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-8">
          Connect Calendar
        </h1>

        <div className="space-y-4">
          {loading ? (
            <div className="text-center py-8">Loading...</div>
          ) : (
            providers.map((provider) => (
              <div
                key={provider.id}
                className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 flex items-center justify-between"
              >
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    {provider.name}
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {provider.connected ? 'Connected' : 'Not connected'}
                  </p>
                </div>
                <button
                  onClick={() => handleConnect(provider.id)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  {provider.connected ? 'Reconnect' : 'Connect'}
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}


