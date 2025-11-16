import { useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import config from '../config';

export default function Account() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [otpauthUri, setOtpauthUri] = useState('');
  const [error, setError] = useState('');

  const handleEnroll = async (e) => {
    e.preventDefault();
    setError('');
    setOtpauthUri('');
    try {
      const resp = await fetch(`${config.API_BASE_URL}/2fa/enroll`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        setError(data.detail || 'Failed to enroll for 2FA');
        return;
      }
      const data = await resp.json();
      if (data.otpauth_uri) {
        setOtpauthUri(data.otpauth_uri);
      } else {
        setError('Unexpected response from server');
      }
    } catch (err) {
      setError('Network error during enrollment');
    }
  };

  return (
    <div>
      <h2>Account Settings</h2>
      <section>
        <h3>Enable Two-Factor Authentication (TOTP)</h3>
        <form onSubmit={handleEnroll}>
          <input placeholder="Username" value={username} onChange={(e) => setUsername(e.target.value)} />
          <input placeholder="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <button type="submit">Enable 2FA</button>
        </form>
        {error && <p style={{ color: 'red' }}>{error}</p>}
        {otpauthUri && (
          <div>
            <p>Scan this QR code with Google Authenticator or a compatible app:</p>
            <QRCodeSVG value={otpauthUri} size={192} />
            <p style={{ wordBreak: 'break-all' }}>{otpauthUri}</p>
          </div>
        )}
      </section>
    </div>
  );
}
