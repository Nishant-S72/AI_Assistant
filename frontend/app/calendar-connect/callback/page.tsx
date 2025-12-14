'use client';

import { useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';

export default function CalendarCallbackPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');

  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const provider = window.location.pathname.includes('google') ? 'google' : 'outlook';

    if (code) {
      // Callback is handled by backend
      // This page just shows status
      fetch(`/api/v1/scheduler/oauth2callback/${provider}?code=${code}&state=${state || ''}&redirect_uri=${encodeURIComponent(window.location.origin + window.location.pathname)}`, {
        headers: {
          'X-User-ID': 'demo-user', // TODO: Get from auth
        },
      })
        .then((res) => res.json())
        .then((data) => {
          if (data.success) {
            setStatus('success');
            setTimeout(() => {
              router.push('/calendar-connect');
            }, 2000);
          } else {
            setStatus('error');
          }
        })
        .catch(() => {
          setStatus('error');
        });
    }
  }, [searchParams, router]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
      <div className="text-center">
        {status === 'loading' && <p className="text-lg">Connecting calendar...</p>}
        {status === 'success' && (
          <div>
            <p className="text-lg text-green-600 mb-4">✅ Calendar connected successfully!</p>
            <p className="text-sm text-gray-500">Redirecting...</p>
          </div>
        )}
        {status === 'error' && (
          <div>
            <p className="text-lg text-red-600 mb-4">❌ Failed to connect calendar</p>
            <button
              onClick={() => router.push('/calendar-connect')}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg"
            >
              Try Again
            </button>
          </div>
        )}
      </div>
    </div>
  );
}


