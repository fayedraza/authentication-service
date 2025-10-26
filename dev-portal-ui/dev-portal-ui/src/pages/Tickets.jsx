import { useAuth } from '../context/AuthContext';

export default function Tickets() {
  const { auth } = useAuth();

  return (
    <div>
      <h2>Tickets ({auth.tier})</h2>
      <ul>
        {auth.tier === 'Pro' ? (
          <li>AI-assisted ticket: Login anomaly detected for user A</li>
        ) : (
          <li>Manual ticket: Reset password for user B</li>
        )}
      </ul>
    </div>
  );
}
