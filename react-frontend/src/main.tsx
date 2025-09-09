import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

// Disable React DevTools in production
if (process.env.NODE_ENV === 'production') {
  // @ts-ignore
  window.__REACT_DEVTOOLS_GLOBAL_HOOK__ = { isDisabled: true };
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
