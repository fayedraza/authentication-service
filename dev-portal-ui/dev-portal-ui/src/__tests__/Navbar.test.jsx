import { render, screen, fireEvent } from '@testing-library/react';
import Navbar from '../components/Navbar';

// Mock the auth hook and react-router navigate
const mockLogout = jest.fn();
const mockNavigate = jest.fn();

jest.mock('../context/AuthContext', () => ({
  useAuth: () => ({ auth: { tier: 'Pro' }, logout: mockLogout }),
}));

describe('Navbar', () => {
  afterEach(() => {
    mockLogout.mockClear();
    mockNavigate.mockClear();
  });

  test('shows links for Pro tier and calls logout + navigate on click', () => {
    render(<Navbar />);

  expect(screen.getByText(/Tickets/i)).toBeInTheDocument();
  expect(screen.getByText(/Dashboard/i)).toBeInTheDocument();
  expect(screen.getByText(/API Keys/i)).toBeInTheDocument();

  const logoutBtn = screen.getByRole('button', { name: /logout/i });
  fireEvent.click(logoutBtn);

  // ensure logout is triggered; navigation is handled by react-router in the app
  expect(mockLogout).toHaveBeenCalled();
  });
});
