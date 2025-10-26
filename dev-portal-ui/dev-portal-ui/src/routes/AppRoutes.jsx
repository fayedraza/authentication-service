import { Routes, Route, Navigate } from '../routerShim';
import Login from '../pages/Login';
import Tickets from '../pages/Tickets';
import Dashboard from '../pages/Dashboard';
import APIKeys from '../pages/APIKeys';
import { useAuth } from '../context/AuthContext';

export default function AppRoutes() {
  const { auth } = useAuth();

  return (
    <Routes>
      <Route path="/" element={auth ? <Navigate to="/tickets" /> : <Login />} />
      <Route path="/tickets" element={auth ? <Tickets /> : <Navigate to="/" />} />
      <Route path="/dashboard" element={auth ? <Dashboard /> : <Navigate to="/" />} />
      <Route path="/apikeys" element={auth ? <APIKeys /> : <Navigate to="/" />} />
    </Routes>
  );
}
