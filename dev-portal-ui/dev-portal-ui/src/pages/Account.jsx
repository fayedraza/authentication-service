import { useState, useEffect } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import config from '../config';

export default function Account() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [otpauthUri, setOtpauthUri] = useState('');
  const [error, setError] = useState('');
  const [is2faEnabled, setIs2faEnabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showReenrollConfirm, setShowReenrollConfirm] = useState(false);
  const [enrolling, setEnrolling] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [showManualEntry, setShowManualEntry] = useState(false);
  const [showDisableConfirm, setShowDisableConfirm] = useState(false);
  const [disablePassword, setDisablePassword] = useState('');
  const [disabling, setDisabling] = useState(false);

  // Fetch 2FA status on component mount
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const token = localStorage.getItem('token');
        if (!token) {
          setLoading(false);
          return;
        }

        const resp = await fetch(`${config.API_BASE_URL}/2fa/status`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (resp.ok) {
          const data = await resp.json();
          setIs2faEnabled(data.is_2fa_enabled);
        }
      } catch (err) {
        console.error('Failed to fetch 2FA status:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchStatus();
  }, []);

  const handleEnroll = async (e) => {
    e.preventDefault();
    setError('');
    setOtpauthUri('');
    setSuccessMessage('');
    setEnrolling(true);

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
        setIs2faEnabled(true);
        setSuccessMessage('2FA enrollment successful! Scan the QR code with your authenticator app.');
        setPassword(''); // Clear password for security
      } else {
        setError('Unexpected response from server');
      }
    } catch (err) {
      setError('Network error during enrollment');
    } finally {
      setEnrolling(false);
    }
  };

  const handleReenrollClick = () => {
    setShowReenrollConfirm(true);
  };

  const handleReenrollConfirm = async () => {
    setShowReenrollConfirm(false);
    setError('');
    setOtpauthUri('');
    setSuccessMessage('');
    setEnrolling(true);

    try {
      const resp = await fetch(`${config.API_BASE_URL}/2fa/enroll`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        setError(data.detail || 'Failed to re-enroll for 2FA');
        return;
      }
      const data = await resp.json();
      if (data.otpauth_uri) {
        setOtpauthUri(data.otpauth_uri);
        setSuccessMessage('2FA re-enrollment successful! Scan the new QR code with your authenticator app.');
        setPassword(''); // Clear password for security
      } else {
        setError('Unexpected response from server');
      }
    } catch (err) {
      setError('Network error during re-enrollment');
    } finally {
      setEnrolling(false);
    }
  };

  const handleReenrollCancel = () => {
    setShowReenrollConfirm(false);
  };

  const handleDisableClick = () => {
    setShowDisableConfirm(true);
    setError('');
    setDisablePassword('');
  };

  const handleDisableConfirm = async (e) => {
    e.preventDefault();
    setError('');
    setSuccessMessage('');
    setDisabling(true);

    try {
      const resp = await fetch(`${config.API_BASE_URL}/2fa/disable`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password: disablePassword }),
      });

      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        setError(data.detail || 'Failed to disable 2FA');
        return;
      }

      const data = await resp.json();
      setIs2faEnabled(false);
      setShowDisableConfirm(false);
      setDisablePassword('');
      setOtpauthUri(''); // Clear any displayed QR code
      setSuccessMessage(data.message || '2FA has been disabled successfully');
    } catch (err) {
      setError('Network error while disabling 2FA');
    } finally {
      setDisabling(false);
    }
  };

  const handleDisableCancel = () => {
    setShowDisableConfirm(false);
    setDisablePassword('');
    setError('');
  };

  // Extract secret from otpauth URI for manual entry
  const extractSecret = (uri) => {
    try {
      const url = new URL(uri);
      return url.searchParams.get('secret') || '';
    } catch {
      return '';
    }
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div>
      <h2>Account Settings</h2>
      <section>
        <h3>Two-Factor Authentication (TOTP)</h3>

        {is2faEnabled && (
          <div style={{ marginBottom: '20px', padding: '10px', backgroundColor: '#e8f5e9', borderRadius: '4px' }}>
            <p style={{ margin: 0, color: '#2e7d32', fontWeight: 'bold' }}>✓ 2FA Enabled</p>
          </div>
        )}

        {!is2faEnabled && (
          <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: '#f5f5f5', borderRadius: '4px' }}>
            <p style={{ margin: '0 0 10px 0', fontSize: '14px', color: '#666' }}>
              <strong>Enable Two-Factor Authentication</strong>
            </p>
            <p style={{ margin: '0', fontSize: '13px', color: '#666' }}>
              Two-factor authentication adds an extra layer of security to your account.
              You'll need an authenticator app like Google Authenticator, Authy, or Microsoft Authenticator.
            </p>
          </div>
        )}

        <form onSubmit={handleEnroll}>
          <input
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={enrolling}
            required
          />
          <input
            placeholder="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={enrolling}
            required
          />
          <button type="submit" disabled={enrolling}>
            {enrolling ? 'Enrolling...' : (is2faEnabled ? 'Enable 2FA' : 'Enable 2FA')}
          </button>
        </form>

        {is2faEnabled && (
          <div style={{ marginTop: '10px', display: 'flex', gap: '10px' }}>
            <button
              type="button"
              onClick={handleReenrollClick}
              style={{
                backgroundColor: '#ff9800',
                color: 'white',
                border: 'none',
                padding: '8px 16px',
                cursor: 'pointer',
                borderRadius: '4px'
              }}
            >
              Re-enroll 2FA
            </button>
            <button
              type="button"
              onClick={handleDisableClick}
              style={{
                backgroundColor: '#f44336',
                color: 'white',
                border: 'none',
                padding: '8px 16px',
                cursor: 'pointer',
                borderRadius: '4px'
              }}
            >
              Disable 2FA
            </button>
          </div>
        )}

        {showReenrollConfirm && (
          <div style={{
            marginTop: '15px',
            padding: '15px',
            backgroundColor: '#fff3e0',
            borderRadius: '4px',
            border: '1px solid #ff9800'
          }}>
            <p style={{ margin: '0 0 10px 0', fontWeight: 'bold' }}>
              Are you sure you want to re-enroll?
            </p>
            <p style={{ margin: '0 0 15px 0', fontSize: '14px' }}>
              This will generate a new secret and invalidate your current authenticator setup.
              You'll need to scan the new QR code with your authenticator app.
            </p>
            <div>
              <button
                onClick={handleReenrollConfirm}
                style={{
                  backgroundColor: '#ff9800',
                  color: 'white',
                  border: 'none',
                  padding: '8px 16px',
                  cursor: 'pointer',
                  borderRadius: '4px',
                  marginRight: '10px'
                }}
              >
                Yes, Re-enroll
              </button>
              <button
                onClick={handleReenrollCancel}
                style={{
                  backgroundColor: '#9e9e9e',
                  color: 'white',
                  border: 'none',
                  padding: '8px 16px',
                  cursor: 'pointer',
                  borderRadius: '4px'
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {showDisableConfirm && (
          <div style={{
            marginTop: '15px',
            padding: '15px',
            backgroundColor: '#ffebee',
            borderRadius: '4px',
            border: '1px solid #f44336'
          }}>
            <p style={{ margin: '0 0 10px 0', fontWeight: 'bold', color: '#c62828' }}>
              Disable Two-Factor Authentication
            </p>
            <p style={{ margin: '0 0 15px 0', fontSize: '14px' }}>
              This will remove 2FA protection from your account. You'll only need your password to log in.
              Enter your password to confirm:
            </p>
            <form onSubmit={handleDisableConfirm}>
              <input
                type="password"
                placeholder="Enter your password"
                value={disablePassword}
                onChange={(e) => setDisablePassword(e.target.value)}
                disabled={disabling}
                required
                style={{
                  width: '100%',
                  padding: '8px',
                  marginBottom: '15px',
                  borderRadius: '4px',
                  border: '1px solid #ccc'
                }}
              />
              <div>
                <button
                  type="submit"
                  disabled={disabling}
                  style={{
                    backgroundColor: '#f44336',
                    color: 'white',
                    border: 'none',
                    padding: '8px 16px',
                    cursor: disabling ? 'not-allowed' : 'pointer',
                    borderRadius: '4px',
                    marginRight: '10px',
                    opacity: disabling ? 0.6 : 1
                  }}
                >
                  {disabling ? 'Disabling...' : 'Yes, Disable 2FA'}
                </button>
                <button
                  type="button"
                  onClick={handleDisableCancel}
                  disabled={disabling}
                  style={{
                    backgroundColor: '#9e9e9e',
                    color: 'white',
                    border: 'none',
                    padding: '8px 16px',
                    cursor: disabling ? 'not-allowed' : 'pointer',
                    borderRadius: '4px',
                    opacity: disabling ? 0.6 : 1
                  }}
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {error && (
          <div style={{
            marginTop: '15px',
            padding: '12px',
            backgroundColor: '#ffebee',
            borderRadius: '4px',
            border: '1px solid #ef5350'
          }}>
            <p style={{ margin: 0, color: '#c62828' }}>{error}</p>
          </div>
        )}

        {successMessage && (
          <div style={{
            marginTop: '15px',
            padding: '12px',
            backgroundColor: '#e8f5e9',
            borderRadius: '4px',
            border: '1px solid #66bb6a'
          }}>
            <p style={{ margin: 0, color: '#2e7d32', fontWeight: 'bold' }}>✓ {successMessage}</p>
          </div>
        )}

        {otpauthUri && (
          <div style={{
            marginTop: '20px',
            padding: '20px',
            backgroundColor: '#fff',
            borderRadius: '8px',
            border: '2px solid #4caf50'
          }}>
            <h4 style={{ marginTop: 0, color: '#2e7d32' }}>Setup Your Authenticator App</h4>

            <div style={{ marginBottom: '20px' }}>
              <p style={{ margin: '0 0 10px 0', fontSize: '14px' }}>
                <strong>Step 1:</strong> Open your authenticator app (Google Authenticator, Authy, Microsoft Authenticator, etc.)
              </p>
              <p style={{ margin: '0 0 10px 0', fontSize: '14px' }}>
                <strong>Step 2:</strong> Scan the QR code below, or enter the secret key manually
              </p>
              <p style={{ margin: '0 0 15px 0', fontSize: '14px' }}>
                <strong>Step 3:</strong> Your app will start generating 6-digit codes for login
              </p>
            </div>

            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              padding: '20px',
              backgroundColor: '#f5f5f5',
              borderRadius: '8px',
              marginBottom: '15px'
            }}>
              <p style={{ margin: '0 0 15px 0', fontWeight: 'bold' }}>Scan this QR code:</p>
              <QRCodeSVG value={otpauthUri} size={200} level="M" />
            </div>

            <div style={{ textAlign: 'center', marginBottom: '15px' }}>
              <button
                type="button"
                onClick={() => setShowManualEntry(!showManualEntry)}
                style={{
                  backgroundColor: 'transparent',
                  color: '#1976d2',
                  border: 'none',
                  padding: '8px 16px',
                  cursor: 'pointer',
                  textDecoration: 'underline',
                  fontSize: '14px'
                }}
              >
                {showManualEntry ? 'Hide manual entry' : 'Can\'t scan? Enter manually'}
              </button>
            </div>

            {showManualEntry && (
              <div style={{
                padding: '15px',
                backgroundColor: '#f9f9f9',
                borderRadius: '4px',
                border: '1px solid #ddd'
              }}>
                <p style={{ margin: '0 0 10px 0', fontSize: '13px', fontWeight: 'bold' }}>
                  Manual Entry Instructions:
                </p>
                <p style={{ margin: '0 0 10px 0', fontSize: '13px' }}>
                  1. In your authenticator app, choose "Enter a setup key" or "Manual entry"
                </p>
                <p style={{ margin: '0 0 10px 0', fontSize: '13px' }}>
                  2. Enter your account name (e.g., your username)
                </p>
                <p style={{ margin: '0 0 10px 0', fontSize: '13px' }}>
                  3. Copy and paste the secret key below:
                </p>
                <div style={{
                  padding: '10px',
                  backgroundColor: '#fff',
                  borderRadius: '4px',
                  border: '1px solid #ccc',
                  marginBottom: '10px'
                }}>
                  <code style={{
                    fontSize: '14px',
                    fontFamily: 'monospace',
                    wordBreak: 'break-all',
                    color: '#d32f2f'
                  }}>
                    {extractSecret(otpauthUri)}
                  </code>
                </div>
                <p style={{ margin: '0', fontSize: '13px' }}>
                  4. Select "Time-based" as the key type
                </p>
              </div>
            )}

            <div style={{
              marginTop: '15px',
              padding: '12px',
              backgroundColor: '#e3f2fd',
              borderRadius: '4px',
              fontSize: '13px'
            }}>
              <p style={{ margin: 0 }}>
                <strong>💡 Tip:</strong> Keep your authenticator app accessible. You'll need it every time you log in.
              </p>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
