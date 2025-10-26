import { useState } from 'react';
import { useNavigate } from '../routerShim';
import { useAuth } from '../context/AuthContext';
import config from '../config';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [isPro, setIsPro] = useState(false); // Checkbox for Pro tier
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch(`${config.API_BASE_URL}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      if (response.ok) {
        const data = await response.json();
        login(data.token, data.tier);
        navigate('/tickets');
      } else {
        setErrorMessage('Invalid login credentials');
      }
    } catch (error) {
      setErrorMessage('An error occurred during login');
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
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
        setSuccessMessage('Registration successful! You can now log in.');
        setIsRegistering(false);
      } else {
        const errorData = await response.json();
        setErrorMessage(errorData.detail || 'Registration failed. Please try again.');
      }
    } catch (error) {
      setErrorMessage('An error occurred during registration');
    }
  };

  return (
    <div>
      {isRegistering ? (
        <form onSubmit={handleRegister}>
          <h2>Register</h2>
          <input placeholder="First Name" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
          <input placeholder="Last Name" value={lastName} onChange={(e) => setLastName(e.target.value)} />
          <input placeholder="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <input placeholder="Username" value={username} onChange={(e) => setUsername(e.target.value)} />
          <input placeholder="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <label>
            <input
              type="checkbox"
              checked={isPro}
              onChange={(e) => setIsPro(e.target.checked)}
            />
            Pro Tier
          </label>
          <button type="submit">Register</button>
          <button type="button" onClick={() => setIsRegistering(false)}>Back to Login</button>
        </form>
      ) : (
        <form onSubmit={handleLogin}>
          <h2>Login</h2>
          <input placeholder="Username" value={username} onChange={(e) => setUsername(e.target.value)} />
          <input placeholder="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <button type="submit">Login</button>
          <button type="button" onClick={() => setIsRegistering(true)}>Register</button>
        </form>
      )}
      {errorMessage && <p style={{ color: 'red' }}>{errorMessage}</p>}
      {successMessage && <p style={{ color: 'green' }}>{successMessage}</p>}
    </div>
  );
}
