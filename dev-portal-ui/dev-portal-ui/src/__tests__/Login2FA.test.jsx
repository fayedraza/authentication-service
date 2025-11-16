import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Login from '../pages/Login';
import { AuthProvider } from '../context/AuthContext';

jest.mock('../config', () => ({ API_BASE_URL: 'http://test.local' }));

describe('Login two-step with TOTP', () => {
  afterEach(() => {
    jest.restoreAllMocks();
    localStorage.clear();
  });

  test('prompts for TOTP when backend requires 2FA and logs in after verification', async () => {
    // First call to /login returns requires2fa
    // Second call to /2fa/verify returns access_token
    const fetchMock = jest.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ requires2fa: true }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ access_token: 'tok123' }) });

    global.fetch = fetchMock;

    render(
      <AuthProvider>
        <Login />
      </AuthProvider>
    );

    fireEvent.change(screen.getByPlaceholderText(/Username/i), { target: { value: 'alice' } });
    fireEvent.change(screen.getByPlaceholderText(/Password/i), { target: { value: 'secret' } });
    fireEvent.click(screen.getByRole('button', { name: /^Login$/i }));

    // After first call, it should show the TOTP form
    await screen.findByRole('heading', { name: /Enter TOTP Code/i });

    fireEvent.change(screen.getByPlaceholderText(/6-digit code/i), { target: { value: '123456' } });
    fireEvent.click(screen.getByRole('button', { name: /Verify/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));

    // Auth token should be stored in localStorage by AuthProvider
    const auth = JSON.parse(localStorage.getItem('auth'));
    expect(auth).toEqual({ token: 'tok123', tier: 'dev' });
  });
});
