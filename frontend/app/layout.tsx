/**
 * Root Layout - Matte White Theme
 * Provides global structure, header bar, navigation shortcuts, and offline mode detection
 * To revert: restore original layout.tsx from git history
 */

import type { Metadata } from 'next';
import '../styles/globals.css';
import Sidebar from '@/components/Sidebar';
import CommandPalette from '@/components/CommandPalette';
import Toast from '@/components/Toast';
import Header from '@/components/Header';
import FloatingChatbox from '@/components/FloatingChatbox';
import ThemeProvider from '@/components/ThemeProvider';

export const metadata: Metadata = {
  title: 'Soraya AI - Chief-of-Staff',
  description: 'AI-powered communication assistant',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <ThemeProvider>
        <body className="font-sans antialiased">
        <a href="#main-content" className="skip-nav">
          Skip to main content
        </a>
        <div className="flex h-screen overflow-hidden">
          <Sidebar />
          <main id="main-content" className="flex-1 flex flex-col overflow-hidden">
            <Header />
            <div className="flex-1 flex overflow-hidden">
              <div className="flex-1 overflow-hidden">{children}</div>
            </div>
          </main>
        </div>
        <CommandPalette />
        <Toast />
        <FloatingChatbox />
        </body>
      </ThemeProvider>
    </html>
  );
}
