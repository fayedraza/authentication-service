import { render, screen, fireEvent } from '@testing-library/react';
import { AuthProvider, useAuth } from '../context/AuthContext';

function TestConsumer() {
  const { auth, login, logout } = useAuth();
  return (
    <div>
      <div>token:{auth ? auth.token : 'none'}</div>
      <div>tier:{auth ? auth.tier : 'none'}</div>
      <button onClick={() => login('mytoken', 'Pro')}>doLogin</button>
      <button onClick={logout}>doLogout</button>
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
});
