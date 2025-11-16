import { Link, useNavigate } from '../routerShim';
import { useAuth } from '../context/AuthContext';

export default function Navbar() {
  const { auth, logout } = useAuth();
  const navigate = useNavigate();

  if (!auth) return null;

  return (
    <nav>
      <Link to="/tickets">Tickets</Link>{" | "}
      <Link to="/account">Account</Link>{" | "}
      {auth.tier === 'Pro' && (
        <>
          <Link to="/dashboard">Dashboard</Link>{" | "}
          <Link to="/apikeys">API Keys</Link>{" | "}
        </>
      )}
      <button onClick={() => { logout(); navigate('/'); }}>Logout</button>
    </nav>
  );
}
