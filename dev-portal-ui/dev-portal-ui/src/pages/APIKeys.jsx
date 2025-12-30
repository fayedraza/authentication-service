
import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import config from '../config';

export default function APIKeys() {
  const { auth } = useAuth();
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newToken, setNewToken] = useState(null);

  useEffect(() => {
    // Load keys for ALL tiers now
    if (auth && auth.token) {
      loadKeys();
    }
  }, [auth]);

  const loadKeys = async () => {
    try {
      const res = await fetch(`${config.API_BASE_URL}/api-keys`, {
        headers: { Authorization: `Bearer ${auth.token}` }
      });
      if (res.ok) {
        setKeys(await res.json());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const createKey = async () => {
    const label = prompt("Enter label for new key:");
    if (!label) return;

    try {
      const res = await fetch(`${config.API_BASE_URL}/api-keys`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${auth.token}`
        },
        body: JSON.stringify({ label })
      });

      if (res.ok) {
        const data = await res.json();
        setNewToken(data.key); // Show full key once
        loadKeys();
      } else {
        // Handle limits
        const err = await res.json();
        alert(`Failed: ${err.detail}`);
      }
    } catch (e) {
      alert("Failed to create key");
    }
  };

  const rotateKey = async (keyId) => {
    if (!window.confirm("Are you sure? This will invalidate the old key immediately.")) return;

    try {
      const res = await fetch(`${config.API_BASE_URL}/api-keys/${keyId}/rotate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${auth.token}`
        }
      });

      if (res.ok) {
        const data = await res.json();
        setNewToken(data.key); // Show new key
        loadKeys();
        alert("Key rotated successfully. Update your applications with the new key provided above.");
      } else {
        const err = await res.json();
        alert(`Rotate failed: ${err.detail}`);
      }
    } catch (e) {
      alert("Failed to rotate key");
    }
  };

  const revokeKey = async (keyId) => {
    if (!window.confirm("Are you sure? This action cannot be undone.")) return;

    try {
      const res = await fetch(`${config.API_BASE_URL}/api-keys/${keyId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${auth.token}` }
      });

      if (res.ok) {
        loadKeys();
      } else {
        alert("Failed to revoke key");
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Determine if user can create more keys
  const isDev = auth.tier === 'dev';
  const activeKeys = keys.filter(k => k.status === 'active').length;
  const canCreate = !isDev || activeKeys < 1;

  if (loading) return <p style={{ padding: '20px' }}>Loading API Keys...</p>;

  return (
    <div style={{ padding: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>API Key Manager</h2>

        <div>
          { /* Limit Warning for Dev */}
          {!canCreate && isDev && (
            <span style={{ marginRight: '15px', color: '#856404', background: '#fff3cd', padding: '5px 10px', borderRadius: '4px' }}>
              Dev Limit Reached (1/1). <a href="/billing">Upgrade to Pro</a>
            </span>
          )}

          <button
            onClick={createKey}
            disabled={!canCreate}
            style={{
              background: canCreate ? '#007bff' : '#ccc',
              color: 'white',
              border: 'none',
              padding: '10px 20px',
              borderRadius: '4px',
              cursor: canCreate ? 'pointer' : 'not-allowed'
            }}>
            + New API Key
          </button>
        </div>
      </div>

      {newToken && (
        <div style={{
          background: '#d4edda', color: '#155724', padding: '15px', borderRadius: '4px', margin: '20px 0', border: '1px solid #c3e6cb'
        }}>
          <strong>New Key Generated:</strong> <code style={{ userSelect: 'all', background: '#fff', padding: '2px 5px', borderRadius: '3px' }}>{newToken}</code>
          <br /><small>Copy this now. It will not be shown again.</small>
        </div>
      )}

      <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '20px' }} border="1">
        <thead>
          <tr>
            <th style={{ padding: '10px', textAlign: 'left' }}>Label</th>
            <th style={{ padding: '10px', textAlign: 'left' }}>Prefix</th>
            <th style={{ padding: '10px', textAlign: 'left' }}>Status</th>
            <th style={{ padding: '10px', textAlign: 'left' }}>Created</th>
            <th style={{ padding: '10px', textAlign: 'left' }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {keys.map(k => (
            <tr key={k.id} style={{ opacity: k.status !== 'active' ? 0.6 : 1, background: k.status !== 'active' ? '#f8f9fa' : 'white' }}>
              <td style={{ padding: '10px' }}>{k.label}</td>
              <td style={{ padding: '10px' }}><code>{k.key_prefix}...</code></td>
              <td style={{ padding: '10px' }}>
                <span style={{
                  padding: '3px 8px',
                  borderRadius: '10px',
                  fontSize: '0.85em',
                  background: k.status === 'active' ? '#28a745' : '#6c757d',
                  color: 'white'
                }}>
                  {k.status}
                </span>
              </td>
              <td style={{ padding: '10px' }}>{new Date(k.created_at).toLocaleDateString()}</td>
              <td style={{ padding: '10px' }}>
                {k.status === 'active' && (
                  <>
                    <button onClick={() => rotateKey(k.id)} style={{ cursor: 'pointer', padding: '5px 10px' }}>Rotate</button>
                    <button onClick={() => revokeKey(k.id)} style={{ marginLeft: '10px', color: 'red', cursor: 'pointer', padding: '5px 10px' }}>Revoke</button>
                  </>
                )}
              </td>
            </tr>
          ))}
          {keys.length === 0 && <tr><td colSpan="5" style={{ textAlign: 'center', padding: '20px' }}>No API keys found.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
