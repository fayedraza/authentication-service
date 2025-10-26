const React = require('react');

// Minimal commonjs mock of react-router-dom for test environment.
// This avoids resolving the ESM bundle during Jest runs.
module.exports = {
  BrowserRouter: ({ children }) => React.createElement(React.Fragment, null, children),
  MemoryRouter: ({ children }) => React.createElement(React.Fragment, null, children),
  Routes: ({ children }) => React.createElement(React.Fragment, null, children),
  Route: ({ element }) => element || null,
  Link: ({ to, children }) => React.createElement('a', { href: to }, children),
  Navigate: ({ to }) => React.createElement('div', null),
  useNavigate: () => {
    // return a no-op navigate function; tests can override by mocking where needed
    return () => {};
  },
};
