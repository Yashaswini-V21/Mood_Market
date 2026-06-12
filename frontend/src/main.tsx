import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { ThemeProvider } from './hooks/useTheme';
import { Dashboard } from './pages/Dashboard';
import './styles/globals.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <Dashboard />
    </ThemeProvider>
  </StrictMode>
);
