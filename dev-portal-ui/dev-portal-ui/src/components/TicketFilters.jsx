
import React from 'react';

export default function TicketFilters({ filterPriority, setFilterPriority, filterStatus, setFilterStatus }) {
    return (
        <div style={{ marginBottom: '20px', padding: '15px', background: '#f5f5f5', borderRadius: '6px' }}>
            <h4>Filters</h4>
            <div style={{ display: 'flex', gap: '20px' }}>
                <div>
                    <label style={{ marginRight: '10px' }}>Priority:</label>
                    <select value={filterPriority} onChange={e => setFilterPriority(e.target.value)}>
                        <option value="all">All</option>
                        <option value="low">Low</option>
                        <option value="medium">Medium</option>
                        <option value="high">High</option>
                        <option value="critical">Critical</option>
                    </select>
                </div>
                <div>
                    <label style={{ marginRight: '10px' }}>Status:</label>
                    <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
                        <option value="all">All</option>
                        <option value="open">Open</option>
                        <option value="closed">Closed</option>
                    </select>
                </div>
            </div>
        </div>
    );
}
