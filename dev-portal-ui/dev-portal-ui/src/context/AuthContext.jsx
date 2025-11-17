import { createContext, useContext, useState } from 'react';

const AuthContext = createContext();

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(() => {
    const stored = localStorage.getItem('auth');
    return stored ? JSON.parse(stored) : null;
  });

  // State to track username during 2FA flow
  const [pendingUsername, setPendingUsername] = useState('');

  // State to manage 2FA requirement
  const [requires2fa, setRequires2fa] = useState(false);

  const login = (token, tier, username) => {
    const user = { token, tier };
    localStorage.setItem('auth', JSON.stringify(user));
    setAuth(user);

    // Clear 2FA state on successful login
    setPendingUsername('');
    setRequires2fa(false);
  };

  const logout = () => {
    localStorage.removeItem('auth');
    setAuth(null);

    // Clear 2FA state on logout
    setPendingUsername('');
    setRequires2fa(false);
  };

  return (
    <AuthContext.Provider value={{
      auth,
      login,
      logout,
      pendingUsername,
      setPendingUsername,
      requires2fa,
      setRequires2fa
    }}>
      {children}
    </AuthContext.Provider>
  );
}
