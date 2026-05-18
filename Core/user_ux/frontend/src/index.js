import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import ClaudeInterface from './components/ClaudeInterface';

// Error boundary component
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('React error:', error);
    console.error('Error info:', errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '20px', color: 'white', textAlign: 'center' }}>
          <h2>Something went wrong.</h2>
          <pre style={{ color: 'red' }}>{this.state.error?.toString()}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}

// Create root element if it doesn't exist
const rootElement = document.getElementById('root') || (() => {
  const el = document.createElement('div');
  el.id = 'root';
  document.body.appendChild(el);
  return el;
})();

const root = ReactDOM.createRoot(rootElement);

// Add error logging
window.onerror = function(msg, url, line) {
  console.error('Global error:', msg);
  console.error('URL:', url);
  console.error('Line:', line);
  return false;
};

root.render(
  <React.StrictMode>
    <ErrorBoundary>
      <ClaudeInterface />
    </ErrorBoundary>
  </React.StrictMode>
); 