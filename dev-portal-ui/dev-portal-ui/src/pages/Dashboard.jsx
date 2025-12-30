
import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import config from '../config';
import TicketFilters from '../components/TicketFilters';
import TicketTable from '../components/TicketTable';
import TicketAnalytics from '../components/TicketAnalytics';
import FeatureGate from '../components/FeatureGate';

export default function TicketDashboard() {
  const { auth } = useAuth();
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterPriority, setFilterPriority] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');

  useEffect(() => {
    loadTickets();
  }, [auth]);

  const loadTickets = async () => {
    try {
      const res = await fetch(`${config.API_BASE_URL}/support/tickets`, {
        headers: { Authorization: `Bearer ${auth.token}` }
      });
      if (res.ok) {
        setTickets(await res.json());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const filteredTickets = tickets.filter(t => {
    const priorityMatch = filterPriority === 'all' || t.priority.toLowerCase() === filterPriority;
    const statusMatch = filterStatus === 'all' || t.status.toLowerCase() === filterStatus;
    return priorityMatch && statusMatch;
  });

  return (
    <div className="dashboard-container" style={{ padding: '20px', background: '#f0f2f5', minHeight: '100vh' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2>Support Dashboard</h2>
        <span style={{
          background: auth.tier === 'pro' ? 'gold' : '#ddd',
          padding: '4px 12px',
          borderRadius: '12px',
          fontWeight: 'bold',
          fontSize: '0.9em',
          border: '1px solid rgba(0,0,0,0.1)'
        }}>
          {auth.tier.toUpperCase()} PLAN
        </span>
      </div>

      <FeatureGate requiredTier="pro">
        <TicketAnalytics tickets={tickets} />
      </FeatureGate>

      <TicketFilters
        filterPriority={filterPriority}
        setFilterPriority={setFilterPriority}
        filterStatus={filterStatus}
        setFilterStatus={setFilterStatus}
      />

      {loading ? <p>Loading tickets...</p> : (
        <TicketTable tickets={filteredTickets} />
      )}
    </div>
  );
}
