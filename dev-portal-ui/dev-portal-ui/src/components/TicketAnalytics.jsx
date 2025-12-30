
import React from 'react';

export default function TicketAnalytics({ tickets }) {
    const total = tickets.length;
    const critical = tickets.filter(t => t.priority === 'critical' || t.priority === 'high').length;
    const escalated = tickets.filter(t => t.escalated).length;
    const avgResTime = "2.4h"; // Mock calculation

    return (
        <div style={{ display: 'flex', gap: '15px', marginBottom: '20px' }}>
            <Card title="Total Tickets" value={total} color="#2196F3" />
            <Card title="High Priority" value={critical} color="#FF9800" />
            <Card title="Escalations" value={escalated} color="#F44336" />
            <Card title="Avg Resolution" value={avgResTime} color="#4CAF50" />
        </div>
    );
}

function Card({ title, value, color }) {
    return (
        <div style={{
            flex: 1,
            padding: '15px',
            borderRadius: '8px',
            background: 'white',
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
            borderTop: `4px solid ${color}`
        }}>
            <div style={{ fontSize: '0.9em', color: '#666' }}>{title}</div>
            <div style={{ fontSize: '1.8em', fontWeight: 'bold', marginTop: '5px' }}>{value}</div>
        </div>
    );
}
