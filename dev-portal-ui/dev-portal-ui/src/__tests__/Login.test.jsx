import { render, screen, fireEvent, waitFor } from '@testing-library/react';

import Login from '../pages/Login';
import { AuthProvider } from '../context/AuthContext';

// Mock config to point to a dummy base URL
jest.mock('../config', () => ({ API_BASE_URL: 'http://test.local' }));

// Mock useNavigate
const mockNavigate = jest.fn();
jest.mock('../routerShim', () => ({
  useNavigate: () => mockNavigate,
}));

describe('Login page', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
    localStorage.clear();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('toggles to register form and shows success message on register', async () => {
    // mock fetch for register
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({}) });

    render(
      <AuthProvider>
        <Login />
      </AuthProvider>
    );

    // initially Login heading should be present (use heading role to avoid matching the button)
    expect(screen.getByRole('heading', { name: /Login/i })).toBeInTheDocument();

    // click Register to toggle
    fireEvent.click(screen.getByRole('button', { name: /Register/i }));

    expect(screen.getByRole('heading', { name: /Register/i })).toBeInTheDocument();

    // fill some register fields
    fireEvent.change(screen.getByPlaceholderText(/First Name/i), { target: { value: 'John' } });
    fireEvent.change(screen.getByPlaceholderText(/Last Name/i), { target: { value: 'Doe' } });
    fireEvent.change(screen.getByPlaceholderText(/Email/i), { target: { value: 'j@example.com' } });
    fireEvent.change(screen.getByPlaceholderText(/Username/i), { target: { value: 'jdoe' } });
    fireEvent.change(screen.getByPlaceholderText(/Password/i), { target: { value: 'pass' } });
    fireEvent.click(screen.getByLabelText(/Pro Tier/i));

    fireEvent.click(screen.getByRole('button', { name: /^Register$/i }));

    await waitFor(() => expect(global.fetch).toHaveBeenCalled());

    // wait for the success message to appear
    await screen.findByText(/Registration successful!/i);

    // After successful registration the component shows the login form and success message
    expect(screen.getByRole('heading', { name: /Login/i })).toBeInTheDocument();
  });

  describe('2FA Login Flow', () => {
    test('renders TOTP input when requires2fa is true', async () => {
      // Mock login response that requires 2FA
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ requires2fa: true }),
      });

      render(
        <AuthProvider>
          <Login />
        </AuthProvider>
      );

      // Fill in login credentials
      fireEvent.change(screen.getByPlaceholderText(/Username/i), { target: { value: 'testuser' } });
      fireEvent.change(screen.getByPlaceholderText(/Password/i), { target: { value: 'password123' } });

      // Submit login form
      fireEvent.click(screen.getByRole('button', { name: /^Login$/i }));

      // Wait for TOTP form to appear
      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /Enter TOTP Code/i })).toBeInTheDocument();
      });

      // Verify TOTP input is present
      expect(screen.getByPlaceholderText(/6-digit code/i)).toBeInTheDocument();
      expect(screen.getByText(/Enter the 6-digit code from your authenticator app/i)).toBeInTheDocument();
    });

    test('submits TOTP code and receives JWT', async () => {
      // Mock login response that requires 2FA
      global.fetch = jest.fn()
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ requires2fa: true }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ access_token: 'test-jwt-token' }),
        });

      render(
        <AuthProvider>
          <Login />
        </AuthProvider>
      );

      // Fill in login credentials
      fireEvent.change(screen.getByPlaceholderText(/Username/i), { target: { value: 'testuser' } });
      fireEvent.change(screen.getByPlaceholderText(/Password/i), { target: { value: 'password123' } });

      // Submit login form
      fireEvent.click(screen.getByRole('button', { name: /^Login$/i }));

      // Wait for TOTP form to appear
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/6-digit code/i)).toBeInTheDocument();
      });

      // Enter TOTP code
      fireEvent.change(screen.getByPlaceholderText(/6-digit code/i), { target: { value: '123456' } });

      // Submit TOTP form
      fireEvent.click(screen.getByRole('button', { name: /Verify/i }));

      // Wait for verification to complete
      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledTimes(2);
      });

      // Verify the TOTP verification request
      expect(global.fetch).toHaveBeenCalledWith(
        'http://test.local/2fa/verify',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: 'testuser', code: '123456' }),
        })
      );

      // Verify navigation to tickets page
      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/tickets');
      });

      // Verify JWT is stored in localStorage
      const auth = JSON.parse(localStorage.getItem('auth'));
      expect(auth.token).toBe('test-jwt-token');
    });

    test('displays error on invalid TOTP code', async () => {
      // Mock login response that requires 2FA
      global.fetch = jest.fn()
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ requires2fa: true }),
        })
        .mockResolvedValueOnce({
          ok: false,
          status: 401,
          json: async () => ({ detail: 'Invalid TOTP code' }),
        });

      render(
        <AuthProvider>
          <Login />
        </AuthProvider>
      );

      // Fill in login credentials
      fireEvent.change(screen.getByPlaceholderText(/Username/i), { target: { value: 'testuser' } });
      fireEvent.change(screen.getByPlaceholderText(/Password/i), { target: { value: 'password123' } });

      // Submit login form
      fireEvent.click(screen.getByRole('button', { name: /^Login$/i }));

      // Wait for TOTP form to appear
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/6-digit code/i)).toBeInTheDocument();
      });

      // Enter invalid TOTP code
      fireEvent.change(screen.getByPlaceholderText(/6-digit code/i), { target: { value: '999999' } });

      // Submit TOTP form
      fireEvent.click(screen.getByRole('button', { name: /Verify/i }));

      // Wait for error message to appear
      await waitFor(() => {
        expect(screen.getByText(/Invalid TOTP code/i)).toBeInTheDocument();
      });

      // Verify navigation did not occur
      expect(mockNavigate).not.toHaveBeenCalled();
    });

    test('displays rate limit error with time remaining', async () => {
      // Mock login response that requires 2FA
      global.fetch = jest.fn()
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ requires2fa: true }),
        })
        .mockResolvedValueOnce({
          ok: false,
          status: 429,
          json: async () => ({ detail: 'Too many failed attempts. Try again in 12 minutes' }),
        });

      render(
        <AuthProvider>
          <Login />
        </AuthProvider>
      );

      // Fill in login credentials
      fireEvent.change(screen.getByPlaceholderText(/Username/i), { target: { value: 'testuser' } });
      fireEvent.change(screen.getByPlaceholderText(/Password/i), { target: { value: 'password123' } });

      // Submit login form
      fireEvent.click(screen.getByRole('button', { name: /^Login$/i }));

      // Wait for TOTP form to appear
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/6-digit code/i)).toBeInTheDocument();
      });

      // Enter TOTP code
      fireEvent.change(screen.getByPlaceholderText(/6-digit code/i), { target: { value: '123456' } });

      // Submit TOTP form
      fireEvent.click(screen.getByRole('button', { name: /Verify/i }));

      // Wait for rate limit error message to appear
      await waitFor(() => {
        expect(screen.getByText(/Too many failed attempts.*12 minutes/i)).toBeInTheDocument();
      });

      // Verify navigation did not occur
      expect(mockNavigate).not.toHaveBeenCalled();
    });

    test('auto-focuses TOTP input when 2FA is required', async () => {
      // Mock login response that requires 2FA
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ requires2fa: true }),
      });

      render(
        <AuthProvider>
          <Login />
        </AuthProvider>
      );

      // Fill in login credentials
      fireEvent.change(screen.getByPlaceholderText(/Username/i), { target: { value: 'testuser' } });
      fireEvent.change(screen.getByPlaceholderText(/Password/i), { target: { value: 'password123' } });

      // Submit login form
      fireEvent.click(screen.getByRole('button', { name: /^Login$/i }));

      // Wait for TOTP form to appear
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/6-digit code/i)).toBeInTheDocument();
      });

      // Verify TOTP input has focus
      const totpInput = screen.getByPlaceholderText(/6-digit code/i);
      expect(totpInput).toHaveFocus();
    });

    test('clears error message when user starts typing TOTP code', async () => {
      // Mock login response that requires 2FA, then invalid code
      global.fetch = jest.fn()
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ requires2fa: true }),
        })
        .mockResolvedValueOnce({
          ok: false,
          status: 401,
          json: async () => ({ detail: 'Invalid TOTP code' }),
        });

      render(
        <AuthProvider>
          <Login />
        </AuthProvider>
      );

      // Fill in login credentials
      fireEvent.change(screen.getByPlaceholderText(/Username/i), { target: { value: 'testuser' } });
      fireEvent.change(screen.getByPlaceholderText(/Password/i), { target: { value: 'password123' } });

      // Submit login form
      fireEvent.click(screen.getByRole('button', { name: /^Login$/i }));

      // Wait for TOTP form to appear
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/6-digit code/i)).toBeInTheDocument();
      });

      // Enter invalid TOTP code
      fireEvent.change(screen.getByPlaceholderText(/6-digit code/i), { target: { value: '999999' } });

      // Submit TOTP form
      fireEvent.click(screen.getByRole('button', { name: /Verify/i }));

      // Wait for error message to appear
      await waitFor(() => {
        expect(screen.getByText(/Invalid TOTP code/i)).toBeInTheDocument();
      });

      // Start typing a new code
      fireEvent.change(screen.getByPlaceholderText(/6-digit code/i), { target: { value: '1' } });

      // Error message should be cleared
      expect(screen.queryByText(/Invalid TOTP code/i)).not.toBeInTheDocument();
    });

    test('validates TOTP code format before submission', async () => {
      // Mock login response that requires 2FA
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ requires2fa: true }),
      });

      render(
        <AuthProvider>
          <Login />
        </AuthProvider>
      );

      // Fill in login credentials
      fireEvent.change(screen.getByPlaceholderText(/Username/i), { target: { value: 'testuser' } });
      fireEvent.change(screen.getByPlaceholderText(/Password/i), { target: { value: 'password123' } });

      // Submit login form
      fireEvent.click(screen.getByRole('button', { name: /^Login$/i }));

      // Wait for TOTP form to appear
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/6-digit code/i)).toBeInTheDocument();
      });

      // Verify button is disabled with less than 6 digits
      fireEvent.change(screen.getByPlaceholderText(/6-digit code/i), { target: { value: '123' } });
      const verifyButton = screen.getByRole('button', { name: /Verify/i });
      expect(verifyButton).toBeDisabled();

      // Try to submit with empty code
      fireEvent.change(screen.getByPlaceholderText(/6-digit code/i), { target: { value: '' } });

      // Manually trigger form submission to test validation
      const form = screen.getByPlaceholderText(/6-digit code/i).closest('form');
      fireEvent.submit(form);

      // Should show validation error
      await waitFor(() => {
        expect(screen.getByText(/Please enter a valid 6-digit code/i)).toBeInTheDocument();
      });

      // Verify API was not called for verification
      expect(global.fetch).toHaveBeenCalledTimes(1); // Only the initial login call
    });

    test('shows Try Again button after error', async () => {
      // Mock login response that requires 2FA, then invalid code
      global.fetch = jest.fn()
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ requires2fa: true }),
        })
        .mockResolvedValueOnce({
          ok: false,
          status: 401,
          json: async () => ({ detail: 'Invalid TOTP code' }),
        });

      render(
        <AuthProvider>
          <Login />
        </AuthProvider>
      );

      // Fill in login credentials
      fireEvent.change(screen.getByPlaceholderText(/Username/i), { target: { value: 'testuser' } });
      fireEvent.change(screen.getByPlaceholderText(/Password/i), { target: { value: 'password123' } });

      // Submit login form
      fireEvent.click(screen.getByRole('button', { name: /^Login$/i }));

      // Wait for TOTP form to appear
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/6-digit code/i)).toBeInTheDocument();
      });

      // Enter invalid TOTP code
      fireEvent.change(screen.getByPlaceholderText(/6-digit code/i), { target: { value: '999999' } });

      // Submit TOTP form
      fireEvent.click(screen.getByRole('button', { name: /Verify/i }));

      // Wait for error message and Try Again button to appear
      await waitFor(() => {
        expect(screen.getByText(/Invalid TOTP code/i)).toBeInTheDocument();
      });

      const tryAgainButton = screen.getByRole('button', { name: /Try Again/i });
      expect(tryAgainButton).toBeInTheDocument();

      // Click Try Again button
      fireEvent.click(tryAgainButton);

      // Verify TOTP input is cleared and focused
      const totpInput = screen.getByPlaceholderText(/6-digit code/i);
      expect(totpInput.value).toBe('');
      expect(totpInput).toHaveFocus();
      expect(screen.queryByText(/Invalid TOTP code/i)).not.toBeInTheDocument();
    });
  });
});
