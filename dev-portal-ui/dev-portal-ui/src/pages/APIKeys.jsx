import { useAuth } from '../context/AuthContext';

export default function APIKeys() {
  const { auth } = useAuth();
  if (auth.tier !== 'Pro') return <p>Access denied.</p>;

  return (
    <div>
      <h2>API Key Manager</h2>
      <button>Issue New Key</button>
      <ul>
        <li>Key1 - Active</li>
        <li>Key2 - Revoked</li>
      </ul>
    </div>
  );
}
