# Running tests (React Testing Library)

This project uses Create React App's test runner (Jest) and React Testing Library.

Prerequisites
- Node.js (14+ recommended)
- npm (or use your preferred node package manager)

Quick steps (from the project folder)

1. Open a terminal and change into the UI app folder (note the space in the path):

```bash
cd "/Users/fayedraza/Authenication Service/dev-portal-ui/dev-portal-ui"
```

2. Install dependencies (only needed once or after package changes):

```bash
npm install
```

3. Run the full test suite (one-shot, non-watch):

```bash
npm test -- --watchAll=false
```

4. Run tests in watch mode (interactive):

```bash
npm test
```

Run a single file or pattern
- Run a single test file by path (example):

```bash
npm test -- src/__tests__/Login.test.jsx -- --watchAll=false
```

- Run tests that match a name/pattern (example):

```bash
npm test -- -t "toggles to register form" --watchAll=false
```

Notes and troubleshooting
- If you see errors about missing testing libraries (e.g. `@testing-library/jest-dom`), install dev dependencies:

```bash
npm install --save-dev @testing-library/react @testing-library/user-event @testing-library/jest-dom
```

- There is a small test-friendly shim in `src/routerShim.js` and a CommonJS mock at `__mocks__/react-router-dom.js` to make Jest + react-router imports work reliably in this environment. If you'd prefer to resolve `react-router-dom`'s ESM bundle instead, consider configuring Jest's `moduleNameMapper` or updating Babel/Jest settings in `package.json`/`jest.config.js` instead of using the shim.

- For CI, prefer `npm ci` (clean install) and then run the non-watch test command.

Helpful commands summary

```bash
# install
npm install

# run tests once (CI style)
npm test -- --watchAll=false

# run tests in watch mode (dev)
npm test

# run a single file
npm test -- src/__tests__/Login.test.jsx -- --watchAll=false

# run tests matching a string
npm test -- -t "part of test name" --watchAll=false
```

If you'd like, I can add a small npm script shortcut (for example: `npm run test:once`) or add CI configuration (GitHub Actions) to run the tests automatically on push/PR.

---
File added by automated test setup assistant.
