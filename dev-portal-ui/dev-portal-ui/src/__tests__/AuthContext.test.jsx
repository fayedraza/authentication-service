import { render, screen, fireEvent } from '@testing-library/react';
import { AuthProvider, useAuth } from '../context/AuthContext';

function TestConsumer() {
  const { auth, login, logout, pendingUsername, setPendingUsername, requires2fa, setRequires2fa } = useAuth();
  return (
    <div>
      <div>token:{auth ? auth.token : 'none'}</div>
      <div>tier:{auth ? auth.tier : 'none'}</div>
      <div>pendingUsername:{pendingUsername || 'none'}</div>
      <div>requires2fa:{requires2fa ? 'true' : 'false'}</div>
      <button onClick={() => login('mytoken', 'Pro', 'testuser')}>doLogin</button>
      <button onClick={logout}>doLogout</button>
      <button onClick={() => setPendingUsername('testuser')}>setPending</button>
      <button onClick={() => setRequires2fa(true)}>setRequires2fa</button>
    </div>
  );
}

describe('AuthProvider', () => {
  beforeEach(() => localStorage.clear());

  test('initializes with no auth and login/logout update state and localStorage', () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    expect(screen.getByText(/token:none/i)).toBeInTheDocument();
    expect(screen.getByText(/tier:none/i)).toBeInTheDocument();

    fireEvent.click(screen.getByText('doLogin'));

    expect(screen.getByText(/token:mytoken/i)).toBeInTheDocument();
    expect(JSON.parse(localStorage.getItem('auth'))).toEqual({ token: 'mytoken', tier: 'Pro' });

    fireEvent.click(screen.getByText('doLogout'));

    expect(screen.getByText(/token:none/i)).toBeInTheDocument();
    expect(localStorage.getItem('auth')).toBeNull();
  });

  test('manages 2FA state during authentication flow', () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    // Initially, 2FA state should be empty
    expect(screen.getByText(/pendingUsername:none/i)).toBeInTheDocument();
    expect(screen.getByText(/requires2fa:false/i)).toBeInTheDocument();

    // Set pending username and requires2fa flag
    fireEvent.click(screen.getByText('setPending'));
    fireEvent.click(screen.getByText('setRequires2fa'));

    expect(screen.getByText(/pendingUsername:testuser/i)).toBeInTheDocument();
    expect(screen.getByText(/requires2fa:true/i)).toBeInTheDocument();

    // Login should clear 2FA state
    fireEvent.click(screen.getByText('doLogin'));

    expect(screen.getByText(/pendingUsername:none/i)).toBeInTheDocument();
    expect(screen.getByText(/requires2fa:false/i)).toBeInTheDocument();
  });

  test('clears 2FA state on logout', () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    // Set 2FA state
    fireEvent.click(screen.getByText('setPending'));
    fireEvent.click(screen.getByText('setRequires2fa'));

    expect(screen.getByText(/pendingUsername:testuser/i)).toBeInTheDocument();
    expect(screen.getByText(/requires2fa:true/i)).toBeInTheDocument();

    // Logout should clear 2FA state
    fireEvent.click(screen.getByText('doLogout'));

    expect(screen.getByText(/pendingUsername:none/i)).toBeInTheDocument();
    expect(screen.getByText(/requires2fa:false/i)).toBeInTheDocument();
  });
});
