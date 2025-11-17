import { useState, useEffect, useRef } from 'react';
import { useNavigate } from '../routerShim';
import { useAuth } from '../context/AuthContext';
import config from '../config';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [needs2fa, setNeeds2fa] = useState(false);
  const [totpCode, setTotpCode] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [isPro, setIsPro] = useState(false); // Checkbox for Pro tier
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [showQRCode, setShowQRCode] = useState(false);
  const [qrCodeUri, setQrCodeUri] = useState('');
  const [registrationToken, setRegistrationToken] = useState('');
  const totpInputRef = useRef(null);
  const { login } = useAuth();
  const navigate = useNavigate();

  // Auto-focus TOTP input when 2FA is required
  useEffect(() => {
    if (needs2fa && totpInputRef.current) {
      totpInputRef.current.focus();
    }
  }, [needs2fa]);

  const handleLogin = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMessage('');
    try {
      const response = await fetch(`${config.API_BASE_URL}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      if (response.ok) {
        const data = await response.json();
        if (data.requires2fa) {
          setNeeds2fa(true);
          setErrorMessage('');
        } else if (data.access_token) {
          // Backend returns access_token; UI stores token + tier. Tier isn't returned, default to 'dev'.
          login(data.access_token, 'dev');
          navigate('/tickets');
        } else {
          setErrorMessage('Unexpected response from server. Please try again or contact support.');
        }
      } else {
        const errorData = await response.json().catch(() => ({}));
        const message = errorData.detail || 'Invalid username or password. Please check your credentials and try again.';
        setErrorMessage(message);
      }
    } catch (error) {
      setErrorMessage('Network error. Please check your internet connection and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyTOTP = async (e) => {
    e.preventDefault();

    // Validate TOTP code format
    if (!totpCode || totpCode.length !== 6 || !/^\d{6}$/.test(totpCode)) {
      setErrorMessage('Please enter a valid 6-digit code from your authenticator app.');
      return;
    }

    setIsLoading(true);
    setErrorMessage('');
    try {
      const response = await fetch(`${config.API_BASE_URL}/2fa/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, code: totpCode }),
      });
      if (response.ok) {
        const data = await response.json();
        if (data.access_token) {
          login(data.access_token, 'dev');
          navigate('/tickets');
        } else {
          setErrorMessage('Unexpected response from server. Please try again or contact support.');
        }
      } else {
        const errorData = await response.json().catch(() => ({}));

        // Handle rate limiting error with time remaining
        if (response.status === 429) {
          let message = errorData.detail || 'Too many failed attempts. Please try again later.';

          // Extract time remaining from error message if present
          // Backend format: "Too many failed attempts. Try again in X minutes"
          const timeMatch = message.match(/(\d+)\s+minute/i);
          if (timeMatch) {
            const minutes = timeMatch[1];
            message = `Too many failed attempts. Please wait ${minutes} minute${minutes !== '1' ? 's' : ''} before trying again.`;
          } else {
            message = 'Too many failed attempts. Please wait 15 minutes before trying again.';
          }

          setErrorMessage(message);
        } else if (response.status === 400) {
          const message = errorData.detail || 'Invalid request. Please ensure 2FA is enabled for your account.';
          setErrorMessage(message);
        } else if (response.status === 401) {
          setErrorMessage('Invalid TOTP code. Please check your authenticator app and try again.');
        } else {
          setErrorMessage(errorData.detail || 'An error occurred. Please try again.');
        }
      }
    } catch (err) {
      setErrorMessage('Network error. Please check your internet connection and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleTotpCodeChange = (e) => {
    const value = e.target.value;
    // Only allow numeric input, max 6 digits
    if (/^\d{0,6}$/.test(value)) {
      setTotpCode(value);
      // Clear error when user starts typing
      if (errorMessage) {
        setErrorMessage('');
      }
    }
  };

  const handleTotpPaste = (e) => {
    e.preventDefault();
    const pastedText = e.clipboardData.getData('text').trim();

    // Validate pasted content is 6 digits
    if (/^\d{6}$/.test(pastedText)) {
      setTotpCode(pastedText);
      // Clear any existing error
      setErrorMessage('');

      // Auto-submit after paste if code is valid
      setTimeout(() => {
        if (totpInputRef.current) {
          totpInputRef.current.form.requestSubmit();
        }
      }, 100);
    } else {
      setErrorMessage('Please paste a valid 6-digit code');
    }
  };

  const handleTryAgain = () => {
    setTotpCode('');
    setErrorMessage('');
    if (totpInputRef.current) {
      totpInputRef.current.focus();
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMessage('');
    try {
      const payload = {
        username,
        first_name: firstName,
        last_name: lastName,
        email,
        password,
        tier: isPro ? 'pro' : 'dev',
      };

      console.log('Sending payload:', payload); // Debugging log

      const response = await fetch(`${config.API_BASE_URL}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        const data = await response.json();

        // Check if 2FA setup is required
        if (data.requires_2fa_setup && data.otpauth_uri) {
          setQrCodeUri(data.otpauth_uri);
          setRegistrationToken(data.access_token);
          setShowQRCode(true);
          setSuccessMessage('Registration successful! Please set up 2FA to continue.');
        } else {
          // Fallback for old response format
          setSuccessMessage('Registration successful! You can now log in.');
          setIsRegistering(false);
        }
      } else {
        const errorData = await response.json();
        setErrorMessage(errorData.detail || 'Registration failed. Please try again.');
      }
    } catch (error) {
      setErrorMessage('An error occurred during registration');
    } finally {
      setIsLoading(false);
    }
  };

  const handleComplete2FASetup = () => {
    // Log the user in with the token from registration
    login(registrationToken, isPro ? 'pro' : 'dev');
    navigate('/tickets');
  };

  return (
    <div>
      {showQRCode ? (
        <div style={{ textAlign: 'center', padding: '20px' }}>
          <h2>Set Up Two-Factor Authentication</h2>
          <p style={{ fontSize: '14px', color: '#666', marginBottom: '20px' }}>
            Scan this QR code with your authenticator app (Google Authenticator, Authy, Microsoft Authenticator, etc.)
          </p>
          <div style={{
            display: 'flex',
            justifyContent: 'center',
            marginBottom: '20px',
            padding: '20px',
            backgroundColor: '#f5f5f5',
            borderRadius: '8px'
          }}>
            <img
              src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(qrCodeUri)}`}
              alt="2FA QR Code"
              style={{ border: '2px solid #ddd', borderRadius: '4px' }}
            />
          </div>
          <p style={{ fontSize: '12px', color: '#999', marginBottom: '20px' }}>
            Can't scan? Manual entry key: <code style={{
              backgroundColor: '#f0f0f0',
              padding: '4px 8px',
              borderRadius: '4px',
              fontSize: '11px'
            }}>
              {qrCodeUri.match(/secret=([A-Z0-9]+)/)?.[1] || 'N/A'}
            </code>
          </p>
          <button
            onClick={handleComplete2FASetup}
            style={{
              backgroundColor: '#4CAF50',
              color: 'white',
              border: 'none',
              padding: '12px 24px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '16px',
              fontWeight: 'bold'
            }}
          >
            I've Scanned the QR Code - Continue
          </button>
          <p style={{ fontSize: '12px', color: '#d32f2f', marginTop: '20px' }}>
            ⚠️ Important: You'll need this code every time you log in. Make sure to save it in your authenticator app before continuing.
          </p>
        </div>
      ) : isRegistering ? (
        <form onSubmit={handleRegister}>
          <h2>Register</h2>
          <input
            placeholder="First Name"
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            disabled={isLoading}
            required
          />
          <input
            placeholder="Last Name"
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
            disabled={isLoading}
            required
          />
          <input
            placeholder="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={isLoading}
            required
          />
          <input
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={isLoading}
            required
          />
          <input
            placeholder="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={isLoading}
            required
          />
          <label>
            <input
              type="checkbox"
              checked={isPro}
              onChange={(e) => setIsPro(e.target.checked)}
              disabled={isLoading}
            />
            Pro Tier
          </label>
          <button type="submit" disabled={isLoading}>
            {isLoading ? 'Registering...' : 'Register'}
          </button>
          <button type="button" onClick={() => setIsRegistering(false)} disabled={isLoading}>
            Back to Login
          </button>
        </form>
      ) : needs2fa ? (
        <form onSubmit={handleVerifyTOTP}>
          <h2>Enter TOTP Code</h2>
          <p style={{ fontSize: '14px', color: '#666', marginBottom: '10px' }}>
            Enter the 6-digit code from your authenticator app
          </p>
          <input
            ref={totpInputRef}
            placeholder="6-digit code"
            value={totpCode}
            onChange={handleTotpCodeChange}
            onPaste={handleTotpPaste}
            maxLength={6}
            inputMode="numeric"
            pattern="\d{6}"
            autoComplete="one-time-code"
            disabled={isLoading}
          />
          <button type="submit" disabled={isLoading || totpCode.length !== 6}>
            {isLoading ? 'Verifying...' : 'Verify'}
          </button>
          {errorMessage && (
            <button
              type="button"
              onClick={handleTryAgain}
              style={{
                backgroundColor: '#2196F3',
                color: 'white',
                border: 'none',
                padding: '10px 20px',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '14px'
              }}
            >
              Try Again
            </button>
          )}
          <button type="button" onClick={() => setNeeds2fa(false)} disabled={isLoading}>
            Back
          </button>
        </form>
      ) : (
        <form onSubmit={handleLogin}>
          <h2>Login</h2>
          <input
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={isLoading}
          />
          <input
            placeholder="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={isLoading}
          />
          <button type="submit" disabled={isLoading}>
            {isLoading ? 'Logging in...' : 'Login'}
          </button>
          <button type="button" onClick={() => setIsRegistering(true)} disabled={isLoading}>
            Register
          </button>
          <div>
            <a href="/reset-request">Forgot password?</a>
          </div>
        </form>
      )}
      {errorMessage && (
        <div style={{
          color: '#d32f2f',
          backgroundColor: '#ffebee',
          padding: '12px',
          borderRadius: '4px',
          marginTop: '10px',
          border: '1px solid #ef5350'
        }}>
          <strong>Error:</strong> {errorMessage}
        </div>
      )}
      {successMessage && (
        <div style={{
          color: '#2e7d32',
          backgroundColor: '#e8f5e9',
          padding: '12px',
          borderRadius: '4px',
          marginTop: '10px',
          border: '1px solid #66bb6a'
        }}>
          <strong>Success:</strong> {successMessage}
        </div>
      )}
    </div>
  );
}
