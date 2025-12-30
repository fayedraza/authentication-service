
import { useAuth } from '../context/AuthContext';

export default function FeatureGate({ children, fallback = null, requiredTier = 'pro' }) {
    const { auth } = useAuth();

    if (!auth) return null;

    // Simple tier check: 'pro' includes 'dev' features? No, tiers are distinct or progressive.
    // Assumption: Pro > Dev. If required is 'dev', both can see?
    // Usually gating is "Requires Pro".

    if (requiredTier === 'pro' && auth.tier !== 'pro') {
        return fallback;
    }

    return children;
}
