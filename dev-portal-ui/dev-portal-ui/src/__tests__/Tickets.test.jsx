import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Tickets from '../pages/Tickets';
import { AuthProvider } from '../context/AuthContext';
import * as AuthContextModule from '../context/AuthContext';

jest.mock('../config', () => ({ API_BASE_URL: 'http://test.local' }));

const mockAuth = {
  auth: { token: 'fake-token', tier: 'dev' },
  login: jest.fn(),
  logout: jest.fn(),
};

describe('Tickets', () => {
  beforeEach(() => {
    // Mock the useAuth hook
    jest.spyOn(AuthContextModule, 'useAuth').mockReturnValue(mockAuth);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('loads and displays existing tickets', async () => {
    const mockTickets = [
      { id: 1, title: 'Bug Report', description: 'Found a bug', status: 'open' },
      { id: 2, title: 'Feature Request', description: 'Need new feature', status: 'closed' },
    ];

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => mockTickets,
    });

    render(<Tickets />);

    await waitFor(() => expect(global.fetch).toHaveBeenCalledWith(
      'http://test.local/support/tickets',
      expect.objectContaining({
        headers: { Authorization: 'Bearer fake-token' },
      })
    ));

    expect(await screen.findByText('Bug Report')).toBeInTheDocument();
    expect(screen.getByText('Feature Request')).toBeInTheDocument();
  });

  test('submits a new ticket and reloads list', async () => {
    const newTicket = { id: 3, title: 'Help Needed', description: 'I need assistance', status: 'open' };

    global.fetch = jest
      .fn()
      // First call: load tickets
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      })
      // Second call: create ticket
      .mockResolvedValueOnce({
        ok: true,
        json: async () => newTicket,
      })
      // Third call: reload tickets
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [newTicket],
      });

    render(<Tickets />);

    // Wait for initial load
    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(1));

    // Fill in form
    fireEvent.change(screen.getByPlaceholderText(/Title/i), { target: { value: 'Help Needed' } });
    fireEvent.change(screen.getByPlaceholderText(/Describe your issue/i), { target: { value: 'I need assistance' } });
    fireEvent.click(screen.getByRole('button', { name: /Submit ticket/i }));

    // Verify create call
    await waitFor(() => expect(global.fetch).toHaveBeenCalledWith(
      'http://test.local/support/ticket',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
          Authorization: 'Bearer fake-token',
        }),
        body: JSON.stringify({ title: 'Help Needed', description: 'I need assistance' }),
      })
    ));

    // Verify success message and reload
    expect(await screen.findByText(/Ticket created/i)).toBeInTheDocument();
    expect(await screen.findByText('Help Needed')).toBeInTheDocument();
  });

  test('shows error when ticket creation fails', async () => {
    global.fetch = jest
      .fn()
      // Initial load
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      })
      // Failed creation
      .mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'Unauthorized' }),
      });

    render(<Tickets />);

    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(1));

    fireEvent.change(screen.getByPlaceholderText(/Title/i), { target: { value: 'Test' } });
    fireEvent.change(screen.getByPlaceholderText(/Describe your issue/i), { target: { value: 'Test desc' } });
    fireEvent.click(screen.getByRole('button', { name: /Submit ticket/i }));

    expect(await screen.findByText(/Failed to create ticket/i)).toBeInTheDocument();
  });
});
