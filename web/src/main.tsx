import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { App } from './App';
import './index.css';
import { MoviuProvider } from './state/MoviuProvider';
import { registerPWA } from './pwa';

const container = document.getElementById('root');

if (!container) {
  throw new Error('Root element not found');
}

createRoot(container).render(
  <StrictMode>
    <BrowserRouter>
      <MoviuProvider>
        <App />
      </MoviuProvider>
    </BrowserRouter>
  </StrictMode>
);

registerPWA();
