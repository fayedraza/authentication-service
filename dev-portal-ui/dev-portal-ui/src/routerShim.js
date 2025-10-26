// routerShim: Try to load react-router-dom; if not available (Jest/Esm issues),
// provide lightweight fallbacks so tests can run without resolving the ESM bundle.
let rr;
try {
  // Try to require the real package first
  rr = require('react-router-dom');
} catch (e) {
  const React = require('react');
  rr = {
    BrowserRouter: ({ children }) => React.createElement(React.Fragment, null, children),
    MemoryRouter: ({ children }) => React.createElement(React.Fragment, null, children),
    Routes: ({ children }) => React.createElement(React.Fragment, null, children),
    Route: ({ element }) => element || null,
    Link: ({ to, children }) => React.createElement('a', { href: to }, children),
    Navigate: ({ to }) => null,
    useNavigate: () => () => {},
    useLocation: () => ({ pathname: '/' }),
    useParams: () => ({}),
  };
}

module.exports = rr;
