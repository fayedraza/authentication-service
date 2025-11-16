import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import config from '../config';

export default function Tickets() {
  const { auth } = useAuth();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [tickets, setTickets] = useState([]);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const loadTickets = async () => {
    setError('');
    try {
      const resp = await fetch(`${config.API_BASE_URL}/support/tickets`, {
        headers: { Authorization: `Bearer ${auth.token}` },
      });
      if (!resp.ok) {
        setError('Failed to load tickets');
        return;
      }
      const data = await resp.json();
      setTickets(data);
    } catch (_) {
      setError('Network error while loading tickets');
    }
  };

  useEffect(() => {
    loadTickets();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage('');
    setError('');
    try {
      const resp = await fetch(`${config.API_BASE_URL}/support/ticket`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${auth.token}`,
        },
        body: JSON.stringify({ title, description }),
      });
      if (!resp.ok) {
        setError('Failed to create ticket');
        return;
      }
      await resp.json();
      setTitle('');
      setDescription('');
      setMessage('Ticket created');
      loadTickets();
    } catch (_) {
      setError('Network error while creating ticket');
    }
  };

  return (
    <div>
      <h2>Tickets ({auth.tier})</h2>
      <form onSubmit={handleSubmit}>
        <input
          placeholder="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <textarea
          placeholder="Describe your issue"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <button type="submit">Submit ticket</button>
      </form>
      {message && <p style={{ color: 'green' }}>{message}</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <ul>
        {tickets.map((t) => (
          <li key={t.id}>
            <strong>{t.title}</strong> — {t.description} [{t.status}]
          </li>
        ))}
      </ul>
    </div>
  );
}
