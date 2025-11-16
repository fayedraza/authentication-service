import { useState } from 'react';
import config from '../config';

export default function ResetRequest() {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage('');
    setError('');
    try {
      const resp = await fetch(`${config.API_BASE_URL}/password-reset/request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      if (!resp.ok) {
        // Even on errors, backend returns generic message; but show a fallback
        setMessage('If the account exists, a reset link has been sent.');
        return;
      }
      const data = await resp.json().catch(() => ({}));
      setMessage(data.message || 'If the account exists, a reset link has been sent.');
    } catch (err) {
      setError('Network error while requesting reset');
    }
  };

  return (
    <div>
      <h2>Request Password Reset</h2>
      <form onSubmit={handleSubmit}>
        <input
          placeholder="Your email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <button type="submit">Send reset link</button>
      </form>
      {message && <p style={{ color: 'green' }}>{message}</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}
    </div>
  );
}
