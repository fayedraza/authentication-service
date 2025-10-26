import { useAuth } from '../context/AuthContext';

export default function Dashboard() {
  const { auth } = useAuth();
  if (auth.tier !== 'Pro') return <p>Access denied.</p>;

  return (
    <div>
      <h2>Log Dashboard</h2>
      <ul>
        <li>User A logged in from new device</li>
        <li>Suspicious login at 3AM flagged</li>
      </ul>
    </div>
  );
}
