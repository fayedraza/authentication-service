import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ResetConfirm from '../pages/ResetConfirm';

jest.mock('../config', () => ({ API_BASE_URL: 'http://test.local' }));

describe('Password Reset Confirm', () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('submits token and new password and shows success', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ message: 'Password updated successfully' }) });

    render(<ResetConfirm />);

    fireEvent.change(screen.getByPlaceholderText(/Reset token/i), { target: { value: 'abc123' } });
    fireEvent.change(screen.getByPlaceholderText(/New password/i), { target: { value: 'newpass' } });
    fireEvent.click(screen.getByRole('button', { name: /Update password/i }));

    await waitFor(() => expect(global.fetch).toHaveBeenCalledWith(
      'http://test.local/password-reset/confirm',
      expect.objectContaining({ method: 'POST' })
    ));

    expect(await screen.findByText(/Password updated successfully/i)).toBeInTheDocument();
  });
});
