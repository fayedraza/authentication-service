import { Routes, Route, Navigate } from '../routerShim';
import Login from '../pages/Login';
import Tickets from '../pages/Tickets';
import Dashboard from '../pages/Dashboard';
import APIKeys from '../pages/APIKeys';
import Account from '../pages/Account';
import ResetRequest from '../pages/ResetRequest';
import ResetConfirm from '../pages/ResetConfirm';
import { useAuth } from '../context/AuthContext';

export default function AppRoutes() {
  const { auth } = useAuth();

  return (
    <Routes>
      <Route path="/" element={auth ? <Navigate to="/tickets" /> : <Login />} />
      <Route path="/reset-request" element={<ResetRequest />} />
      <Route path="/reset-password" element={<ResetConfirm />} />
      <Route path="/tickets" element={auth ? <Tickets /> : <Navigate to="/" />} />
      <Route path="/account" element={auth ? <Account /> : <Navigate to="/" />} />
      <Route path="/dashboard" element={auth ? <Dashboard /> : <Navigate to="/" />} />
      <Route path="/apikeys" element={auth ? <APIKeys /> : <Navigate to="/" />} />
    </Routes>
  );
}
