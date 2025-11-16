import { useEffect, useState } from 'react';
import config from '../config';

export default function ResetConfirm() {
  const [token, setToken] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  // Try to read token from URL if available (works when real router provides location.search)
  useEffect(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      const t = params.get('token');
      if (t) setToken(t);
    } catch (_) {
      // ignore if URLSearchParams not available in test shim
    }
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage('');
    setError('');
    try {
      const resp = await fetch(`${config.API_BASE_URL}/password-reset/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: password }),
      });
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        setError(data.detail || 'Invalid or expired token');
        return;
      }
      const data = await resp.json().catch(() => ({}));
      setMessage(data.message || 'Password updated successfully');
    } catch (err) {
      setError('Network error while resetting password');
    }
  };

  return (
    <div>
      <h2>Reset Password</h2>
      <form onSubmit={handleSubmit}>
        <input
          placeholder="Reset token"
          value={token}
          onChange={(e) => setToken(e.target.value)}
        />
        <input
          placeholder="New password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button type="submit">Update password</button>
      </form>
      {message && <p style={{ color: 'green' }}>{message}</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}
    </div>
  );
}
