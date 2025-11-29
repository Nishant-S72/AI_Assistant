import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import Home from '../app/page';

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
  }),
}));

// Mock framer-motion
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}));

describe('Landing Page', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('should render summary numbers and P0 list', async () => {
    const mockSummary = {
      totals: {
        totalMessages: 23,
        unread: 5,
        leads: 8,
        complaints: 3,
      },
      tasks: {
        counts: {
          P0: 2,
          P1: 4,
          P2: 6,
        },
        P0: [
          {
            id: 'task-1',
            title: 'Urgent task 1',
            due_at: new Date().toISOString(),
            contact_name: 'John Doe',
            priority: 'P0',
          },
          {
            id: 'task-2',
            title: 'Urgent task 2',
            due_at: new Date().toISOString(),
            contact_name: 'Jane Smith',
            priority: 'P0',
          },
        ],
        P1: [],
        P2: [],
      },
      topLeads: [
        {
          id: 'lead-1',
          name: 'Lead 1',
          company: 'Company 1',
          email: 'lead1@example.com',
        },
      ],
      simulated: false,
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockSummary,
    });

    render(<Home />);

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText('Loading')).not.toBeInTheDocument();
    });

    // Check summary numbers
    expect(screen.getByText('23')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('8')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();

    // Check P0 tasks
    expect(screen.getByText('Urgent task 1')).toBeInTheDocument();
    expect(screen.getByText('Urgent task 2')).toBeInTheDocument();
    expect(screen.getByText('P0 - Urgent')).toBeInTheDocument();

    // Check top leads
    expect(screen.getByText('Lead 1')).toBeInTheDocument();
    expect(screen.getByText('Company 1')).toBeInTheDocument();
  });

  it('should show error message and retry button on fetch failure', async () => {
    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

    render(<Home />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load summary/i)).toBeInTheDocument();
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });
  });

  it('should display simulated mode banner when simulated is true', async () => {
    const mockSummary = {
      totals: { totalMessages: 0, unread: 0, leads: 0, complaints: 0 },
      tasks: { counts: { P0: 0, P1: 0, P2: 0 }, P0: [], P1: [], P2: [] },
      topLeads: [],
      simulated: true,
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockSummary,
    });

    render(<Home />);

    await waitFor(() => {
      expect(screen.getByText(/Offline Demo Mode/i)).toBeInTheDocument();
    });
  });
});


