import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Account from '../pages/Account';

// Mock config so we don't depend on actual env
jest.mock('../config', () => ({ API_BASE_URL: 'http://test.local' }));

describe('Account 2FA Enrollment', () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('renders QR code after successful enrollment', async () => {
    const otpauth = 'otpauth://totp/AuthService:alice?secret=ABCDEF&issuer=AuthService';
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ otpauth_uri: otpauth }) });

    render(<Account />);

    fireEvent.change(screen.getByPlaceholderText(/Username/i), { target: { value: 'alice' } });
    fireEvent.change(screen.getByPlaceholderText(/Password/i), { target: { value: 'secret' } });
    fireEvent.click(screen.getByRole('button', { name: /Enable 2FA/i }));

    await waitFor(() => expect(global.fetch).toHaveBeenCalled());

    // The QRCodeSVG renders an <svg>, we can assert it's present and the otpauth text is shown
    expect(await screen.findByText(otpauth)).toBeInTheDocument();
    const svgs = document.getElementsByTagName('svg');
    expect(svgs.length).toBeGreaterThan(0);
  });
});
