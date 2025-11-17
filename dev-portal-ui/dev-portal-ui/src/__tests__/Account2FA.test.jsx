import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Account from '../pages/Account';

// Mock config so we don't depend on actual env
jest.mock('../config', () => ({ API_BASE_URL: 'http://test.local' }));

describe('Account 2FA Enrollment', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('displays enrollment form when 2FA is disabled', async () => {
    // Mock the status endpoint to return 2FA disabled
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ is_2fa_enabled: false })
    });

    localStorage.setItem('token', 'fake-token');

    render(<Account />);

    // Wait for loading to complete
    await waitFor(() => expect(screen.queryByText(/Loading/i)).not.toBeInTheDocument());

    // Check that enrollment form is displayed
    expect(screen.getByPlaceholderText(/Username/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Enable 2FA/i })).toBeInTheDocument();

    // Check that the instructional text is shown
    expect(screen.getByText(/Enable Two-Factor Authentication/i)).toBeInTheDocument();
    expect(screen.getByText(/adds an extra layer of security/i)).toBeInTheDocument();
  });

  test('displays QR code after successful enrollment', async () => {
    const otpauth = 'otpauth://totp/AuthService:alice?secret=ABCDEF&issuer=AuthService';

    // Mock status endpoint (2FA disabled initially)
    global.fetch = jest.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ is_2fa_enabled: false })
      })
      // Mock enrollment endpoint
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ otpauth_uri: otpauth })
      });

    localStorage.setItem('token', 'fake-token');

    render(<Account />);

    await waitFor(() => expect(screen.queryByText(/Loading/i)).not.toBeInTheDocument());

    fireEvent.change(screen.getByPlaceholderText(/Username/i), { target: { value: 'alice' } });
    fireEvent.change(screen.getByPlaceholderText(/Password/i), { target: { value: 'secret' } });
    fireEvent.click(screen.getByRole('button', { name: /Enable 2FA/i }));

    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(2));

    // Check that success message is displayed
    expect(await screen.findByText(/2FA enrollment successful/i)).toBeInTheDocument();

    // Check that QR code setup instructions are shown
    expect(screen.getByText(/Setup Your Authenticator App/i)).toBeInTheDocument();
    expect(screen.getByText(/Scan this QR code:/i)).toBeInTheDocument();

    // The QRCodeSVG renders an <svg>
    const svgs = document.getElementsByTagName('svg');
    expect(svgs.length).toBeGreaterThan(0);
  });

  test('shows 2FA status when enabled', async () => {
    // Mock the status endpoint to return 2FA enabled
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ is_2fa_enabled: true })
    });

    localStorage.setItem('token', 'fake-token');

    render(<Account />);

    // Wait for loading to complete
    await waitFor(() => expect(screen.queryByText(/Loading/i)).not.toBeInTheDocument());

    // Check that 2FA enabled status is displayed
    expect(await screen.findByText(/✓ 2FA Enabled/i)).toBeInTheDocument();

    // Check that re-enroll button is shown
    expect(screen.getByRole('button', { name: /Re-enroll 2FA/i })).toBeInTheDocument();
  });

  test('handles re-enrollment flow', async () => {
    const newOtpauth = 'otpauth://totp/AuthService:alice?secret=NEWKEY123&issuer=AuthService';

    // Mock status endpoint (2FA enabled)
    global.fetch = jest.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ is_2fa_enabled: true })
      })
      // Mock re-enrollment endpoint
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ otpauth_uri: newOtpauth })
      });

    localStorage.setItem('token', 'fake-token');

    render(<Account />);

    await waitFor(() => expect(screen.queryByText(/Loading/i)).not.toBeInTheDocument());

    // Click re-enroll button
    const reenrollButton = screen.getByRole('button', { name: /Re-enroll 2FA/i });
    fireEvent.click(reenrollButton);

    // Check that confirmation dialog is shown
    expect(await screen.findByText(/Are you sure you want to re-enroll/i)).toBeInTheDocument();
    expect(screen.getByText(/This will generate a new secret/i)).toBeInTheDocument();

    // Fill in credentials
    fireEvent.change(screen.getByPlaceholderText(/Username/i), { target: { value: 'alice' } });
    fireEvent.change(screen.getByPlaceholderText(/Password/i), { target: { value: 'secret' } });

    // Confirm re-enrollment
    const confirmButton = screen.getByRole('button', { name: /Yes, Re-enroll/i });
    fireEvent.click(confirmButton);

    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(2));

    // Check that success message is displayed
    expect(await screen.findByText(/2FA re-enrollment successful/i)).toBeInTheDocument();

    // Check that new QR code is shown
    expect(screen.getByText(/Setup Your Authenticator App/i)).toBeInTheDocument();
    const svgs = document.getElementsByTagName('svg');
    expect(svgs.length).toBeGreaterThan(0);
  });

  test('allows canceling re-enrollment', async () => {
    // Mock status endpoint (2FA enabled)
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ is_2fa_enabled: true })
    });

    localStorage.setItem('token', 'fake-token');

    render(<Account />);

    await waitFor(() => expect(screen.queryByText(/Loading/i)).not.toBeInTheDocument());

    // Click re-enroll button
    const reenrollButton = screen.getByRole('button', { name: /Re-enroll 2FA/i });
    fireEvent.click(reenrollButton);

    // Check that confirmation dialog is shown
    expect(await screen.findByText(/Are you sure you want to re-enroll/i)).toBeInTheDocument();

    // Click cancel
    const cancelButton = screen.getByRole('button', { name: /Cancel/i });
    fireEvent.click(cancelButton);

    // Check that confirmation dialog is hidden
    await waitFor(() => {
      expect(screen.queryByText(/Are you sure you want to re-enroll/i)).not.toBeInTheDocument();
    });
  });

  test('displays error message on enrollment failure', async () => {
    // Mock status endpoint (2FA disabled)
    global.fetch = jest.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ is_2fa_enabled: false })
      })
      // Mock enrollment endpoint with error
      .mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'Invalid credentials' })
      });

    localStorage.setItem('token', 'fake-token');

    render(<Account />);

    await waitFor(() => expect(screen.queryByText(/Loading/i)).not.toBeInTheDocument());

    fireEvent.change(screen.getByPlaceholderText(/Username/i), { target: { value: 'alice' } });
    fireEvent.change(screen.getByPlaceholderText(/Password/i), { target: { value: 'wrong' } });
    fireEvent.click(screen.getByRole('button', { name: /Enable 2FA/i }));

    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(2));

    // Check that error message is displayed
    expect(await screen.findByText(/Invalid credentials/i)).toBeInTheDocument();
  });

  test('shows manual entry option when requested', async () => {
    const otpauth = 'otpauth://totp/AuthService:alice?secret=TESTKEY123456&issuer=AuthService';

    // Mock status endpoint (2FA disabled)
    global.fetch = jest.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ is_2fa_enabled: false })
      })
      // Mock enrollment endpoint
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ otpauth_uri: otpauth })
      });

    localStorage.setItem('token', 'fake-token');

    render(<Account />);

    await waitFor(() => expect(screen.queryByText(/Loading/i)).not.toBeInTheDocument());

    fireEvent.change(screen.getByPlaceholderText(/Username/i), { target: { value: 'alice' } });
    fireEvent.change(screen.getByPlaceholderText(/Password/i), { target: { value: 'secret' } });
    fireEvent.click(screen.getByRole('button', { name: /Enable 2FA/i }));

    // Wait for enrollment to complete and QR code to appear
    await waitFor(() => expect(screen.getByText(/Setup Your Authenticator App/i)).toBeInTheDocument());

    // Click manual entry button
    const manualEntryButton = await screen.findByRole('button', { name: /Can't scan\? Enter manually/i });
    fireEvent.click(manualEntryButton);

    // Check that manual entry instructions are shown
    expect(await screen.findByText(/Manual Entry Instructions:/i)).toBeInTheDocument();
    expect(screen.getByText(/TESTKEY123456/i)).toBeInTheDocument();
    expect(screen.getByText(/Select "Time-based" as the key type/i)).toBeInTheDocument();
  });

  test('disables 2FA with password confirmation', async () => {
    // Mock status endpoint (2FA enabled)
    global.fetch = jest.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ is_2fa_enabled: true })
      })
      // Mock disable endpoint
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: '2FA has been disabled successfully' })
      });

    localStorage.setItem('token', 'fake-token');

    render(<Account />);

    await waitFor(() => expect(screen.queryByText(/Loading/i)).not.toBeInTheDocument());

    // Check that 2FA is enabled
    expect(await screen.findByText(/✓ 2FA Enabled/i)).toBeInTheDocument();

    // Click disable button
    const disableButton = screen.getByRole('button', { name: /Disable 2FA/i });
    fireEvent.click(disableButton);

    // Check that confirmation dialog is shown
    expect(await screen.findByText(/Disable Two-Factor Authentication/i)).toBeInTheDocument();
    expect(screen.getByText(/This will remove 2FA protection from your account/i)).toBeInTheDocument();

    // Fill in username and password
    fireEvent.change(screen.getByPlaceholderText(/Username/i), { target: { value: 'alice' } });
    fireEvent.change(screen.getByPlaceholderText(/Enter your password/i), { target: { value: 'secret' } });

    // Confirm disable
    const confirmButton = screen.getByRole('button', { name: /Yes, Disable 2FA/i });
    fireEvent.click(confirmButton);

    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(2));

    // Verify the API was called with correct data
    expect(global.fetch).toHaveBeenCalledWith(
      'http://test.local/2fa/disable',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: 'alice', password: 'secret' })
      })
    );

    // Check that success message is displayed
    expect(await screen.findByText(/2FA has been disabled successfully/i)).toBeInTheDocument();

    // Check that 2FA status is updated (no longer showing enabled status)
    await waitFor(() => {
      expect(screen.queryByText(/✓ 2FA Enabled/i)).not.toBeInTheDocument();
    });
  });

  test('allows canceling disable 2FA', async () => {
    // Mock status endpoint (2FA enabled)
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ is_2fa_enabled: true })
    });

    localStorage.setItem('token', 'fake-token');

    render(<Account />);

    await waitFor(() => expect(screen.queryByText(/Loading/i)).not.toBeInTheDocument());

    // Click disable button
    const disableButton = screen.getByRole('button', { name: /Disable 2FA/i });
    fireEvent.click(disableButton);

    // Check that confirmation dialog is shown
    expect(await screen.findByText(/Disable Two-Factor Authentication/i)).toBeInTheDocument();

    // Click cancel
    const cancelButton = screen.getByRole('button', { name: /Cancel/i });
    fireEvent.click(cancelButton);

    // Check that confirmation dialog is hidden
    await waitFor(() => {
      expect(screen.queryByText(/Disable Two-Factor Authentication/i)).not.toBeInTheDocument();
    });

    // Verify no API call was made (only the initial status check)
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  test('displays error message on disable failure', async () => {
    // Mock status endpoint (2FA enabled)
    global.fetch = jest.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ is_2fa_enabled: true })
      })
      // Mock disable endpoint with error
      .mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'Invalid credentials' })
      });

    localStorage.setItem('token', 'fake-token');

    render(<Account />);

    await waitFor(() => expect(screen.queryByText(/Loading/i)).not.toBeInTheDocument());

    // Click disable button
    const disableButton = screen.getByRole('button', { name: /Disable 2FA/i });
    fireEvent.click(disableButton);

    // Fill in credentials
    fireEvent.change(screen.getByPlaceholderText(/Username/i), { target: { value: 'alice' } });
    fireEvent.change(screen.getByPlaceholderText(/Enter your password/i), { target: { value: 'wrong' } });

    // Confirm disable
    const confirmButton = screen.getByRole('button', { name: /Yes, Disable 2FA/i });
    fireEvent.click(confirmButton);

    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(2));

    // Check that error message is displayed
    expect(await screen.findByText(/Invalid credentials/i)).toBeInTheDocument();
  });
});
