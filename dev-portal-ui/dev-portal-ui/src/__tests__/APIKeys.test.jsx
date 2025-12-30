
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import APIKeys from '../pages/APIKeys';
import { useAuth } from '../context/AuthContext';

// Mock the AuthContext
jest.mock('../context/AuthContext');

// Mock config
jest.mock('../config', () => ({
    API_BASE_URL: 'http://localhost:8000'
}));

describe('APIKeys Component', () => {
    const mockAuthDev = { token: 'fake-token', tier: 'dev' };
    const mockAuthPro = { token: 'fake-token', tier: 'pro' };

    beforeEach(() => {
        // Default fetch mock implementation
        global.fetch = jest.fn();
        global.prompt = jest.fn();
        global.confirm = jest.fn();
        global.alert = jest.fn();
        jest.clearAllMocks();
    });

    test('renders loading state initially', () => {
        useAuth.mockReturnValue({ auth: mockAuthDev });
        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => []
        });

        render(<APIKeys />);
        expect(screen.getByText(/Loading API Keys.../i)).toBeInTheDocument();
    });

    test('renders keys list after loading', async () => {
        useAuth.mockReturnValue({ auth: mockAuthPro });
        const mockKeys = [
            { id: 1, label: 'Test Key', key_prefix: 'mcp_123', status: 'active', created_at: new Date().toISOString() }
        ];

        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => mockKeys
        });

        render(<APIKeys />);

        await waitFor(() => expect(screen.queryByText(/Loading/i)).not.toBeInTheDocument());

        expect(screen.getByText('Test Key')).toBeInTheDocument();
        expect(screen.getByText(/mcp_123/i)).toBeInTheDocument();
        expect(screen.getByText('active')).toBeInTheDocument();
    });

    test('enforces dev tier limit (1 key max)', async () => {
        useAuth.mockReturnValue({ auth: mockAuthDev });
        const mockKeys = [
            { id: 1, label: 'Dev Key', key_prefix: 'mcp_dev', status: 'active', created_at: new Date().toISOString() }
        ];

        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => mockKeys
        });

        render(<APIKeys />);

        await waitFor(() => expect(screen.queryByText(/Loading/i)).not.toBeInTheDocument());

        // Check for limit warning
        expect(screen.getByText(/Dev Limit Reached/i)).toBeInTheDocument();

        // Check button disabled
        const btn = screen.getByText('+ New API Key');
        expect(btn).toBeDisabled();
    });

    test('allows pro tier to create multiple keys', async () => {
        useAuth.mockReturnValue({ auth: mockAuthPro });
        const mockKeys = [
            { id: 1, label: 'Pro Key 1', key_prefix: 'mcp_pro1', status: 'active', created_at: new Date().toISOString() }
        ];

        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => mockKeys
        });

        render(<APIKeys />);

        await waitFor(() => expect(screen.queryByText(/Loading/i)).not.toBeInTheDocument());

        // Check NO limit warning
        expect(screen.queryByText(/Dev Limit Reached/i)).not.toBeInTheDocument();

        // Check button enable
        const btn = screen.getByText('+ New API Key');
        expect(btn).not.toBeDisabled();
    });

    test('creates a new key successfully', async () => {
        useAuth.mockReturnValue({ auth: mockAuthPro });
        // Initial load empty
        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => []
        });

        render(<APIKeys />);
        await waitFor(() => expect(screen.queryByText(/Loading/i)).not.toBeInTheDocument());

        // Mock prompt and API responses BEFORE action
        global.prompt.mockReturnValue('My New Key');

        // Mock Create API Response
        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({ key: 'mcp_SECRET_KEY_123', id: 2, label: 'My New Key', status: 'active' })
        });

        // Mock Reload Keys Call (happens after create)
        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => [{ id: 2, label: 'My New Key', key_prefix: 'mcp_SEC', status: 'active', created_at: new Date().toISOString() }]
        });

        // Click create
        const btn = screen.getByText('+ New API Key');
        fireEvent.click(btn);

        // Trigger the effect by waiting? The prompt is synchronous in test environment usually if mocked?
        // Actually prompt calls happens, then fetch.
        expect(global.alert).not.toHaveBeenCalled();

        await waitFor(() => expect(screen.getByText('mcp_SECRET_KEY_123')).toBeInTheDocument());
        expect(screen.getByText('New Key Generated:')).toBeInTheDocument();
    });

    test('rotates a key', async () => {
        useAuth.mockReturnValue({ auth: mockAuthPro });
        const mockKeys = [
            { id: 1, label: 'Old Key', key_prefix: 'mcp_old', status: 'active', created_at: new Date().toISOString() }
        ];

        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => mockKeys
        });

        render(<APIKeys />);
        await waitFor(() => expect(screen.queryByText(/Loading/i)).not.toBeInTheDocument());

        // Click rotate
        const rotateBtn = screen.getByText('Rotate');

        // Mock confirm true
        global.confirm.mockReturnValue(true);

        // Mock Rotate API Response
        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({ key: 'mcp_NEW_ROTATED_KEY' })
        });

        // Mock Reload
        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => [{ id: 1, label: 'Old Key', key_prefix: 'mcp_NEW', status: 'active', created_at: new Date().toISOString() }]
        });

        // Mock Alert
        global.alert = jest.fn();

        fireEvent.click(rotateBtn);

        await waitFor(() => expect(screen.getByText('mcp_NEW_ROTATED_KEY')).toBeInTheDocument());
        expect(global.alert).toHaveBeenCalledWith(expect.stringContaining('Key rotated successfully'));
    });

    test('revokes a key', async () => {
        useAuth.mockReturnValue({ auth: mockAuthPro });
        const mockKeys = [
            { id: 1, label: 'To Revoke', key_prefix: 'mcp_rev', status: 'active', created_at: new Date().toISOString() }
        ];

        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => mockKeys
        });

        render(<APIKeys />);
        await waitFor(() => expect(screen.queryByText(/Loading/i)).not.toBeInTheDocument());

        const revokeBtn = screen.getByText('Revoke');
        global.confirm.mockReturnValue(true);

        // Mock Revoke API
        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({})
        });

        // Mock Reload (should verify it's gone or status changed, let's say status changed to revoked)
        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => [{ id: 1, label: 'To Revoke', key_prefix: 'mcp_rev', status: 'revoked', created_at: new Date().toISOString() }]
        });

        fireEvent.click(revokeBtn);

        await waitFor(() => expect(screen.getByText('revoked')).toBeInTheDocument());
        // Verify Revoke button is gone for revoked key
        expect(screen.queryByText('Revoke')).not.toBeInTheDocument();
    });
});
