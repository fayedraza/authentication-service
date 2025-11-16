import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ResetRequest from '../pages/ResetRequest';

jest.mock('../config', () => ({ API_BASE_URL: 'http://test.local' }));

describe('Password Reset Request', () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('submits email and shows confirmation message', async () => {
    const resp = { ok: true, json: async () => ({ message: 'If the account exists, a reset link has been sent.' }) };
    global.fetch = jest.fn().mockResolvedValue(resp);

    render(<ResetRequest />);

    fireEvent.change(screen.getByPlaceholderText(/Your email/i), { target: { value: 'user@example.com' } });
    fireEvent.click(screen.getByRole('button', { name: /Send reset link/i }));

    await waitFor(() => expect(global.fetch).toHaveBeenCalledWith(
      'http://test.local/password-reset/request',
      expect.objectContaining({ method: 'POST' })
    ));

    expect(await screen.findByText(/If the account exists/i)).toBeInTheDocument();
  });
});
