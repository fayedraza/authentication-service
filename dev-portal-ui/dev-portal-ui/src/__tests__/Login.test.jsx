import { render, screen, fireEvent, waitFor } from '@testing-library/react';

import Login from '../pages/Login';
import { AuthProvider } from '../context/AuthContext';

// Mock config to point to a dummy base URL
jest.mock('../config', () => ({ API_BASE_URL: 'http://test.local' }));

describe('Login page', () => {
  afterEach(() => {
    jest.restoreAllMocks();
    localStorage.clear();
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
});
