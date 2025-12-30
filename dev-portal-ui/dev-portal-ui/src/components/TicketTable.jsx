
import React from 'react';

export default function TicketTable({ tickets }) {
    if (!tickets || tickets.length === 0) {
        return <p>No tickets found.</p>;
    }

    return (
        <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '10px' }} border="1">
            <thead>
                <tr style={{ background: '#eee' }}>
                    <th style={{ padding: '8px' }}>ID</th>
                    <th style={{ padding: '8px' }}>Title</th>
                    <th style={{ padding: '8px' }}>Status</th>
                    <th style={{ padding: '8px' }}>AI Priority</th>
                    <th style={{ padding: '8px' }}>Category</th>
                    <th style={{ padding: '8px' }}>Escalated</th>
                    <th style={{ padding: '8px' }}>Created</th>
                </tr>
            </thead>
            <tbody>
                {tickets.map(t => (
                    <tr key={t.id} style={{ background: t.escalated ? '#fff0f0' : 'white' }}>
                        <td style={{ padding: '8px' }}>#{t.id}</td>
                        <td style={{ padding: '8px' }}>
                            <div style={{ fontWeight: 'bold' }}>{t.title}</div>
                            <div style={{ fontSize: '0.85em', color: '#666' }}>{t.description.substring(0, 50)}...</div>
                        </td>
                        <td style={{ padding: '8px' }}>
                            <span style={{
                                padding: '2px 6px',
                                borderRadius: '4px',
                                background: t.status === 'open' ? '#e6f7ff' : '#eee',
                                color: t.status === 'open' ? '#0050b3' : '#666',
                                fontSize: '0.9em'
                            }}>
                                {t.status.toUpperCase()}
                            </span>
                        </td>
                        <td style={{ padding: '8px' }}>
                            <span style={{
                                color: t.priority === 'critical' ? 'red' :
                                    t.priority === 'high' ? 'orange' : 'black',
                                fontWeight: 'bold'
                            }}>
                                {t.priority ? t.priority.toUpperCase() : 'MED'}
                            </span>
                        </td>
                        <td style={{ padding: '8px' }}>{t.category || '-'}</td>
                        <td style={{ padding: '8px' }}>
                            {t.escalated ? (
                                <span title={t.escalation_reason || 'AI Escalation'}>
                                    🚨 YES
                                </span>
                            ) : 'No'}
                        </td>
                        <td style={{ padding: '8px' }}>
                            {t.created_at ? new Date(t.created_at).toLocaleDateString() : '-'}
                        </td>
                    </tr>
                ))}
            </tbody>
        </table>
    );
}
