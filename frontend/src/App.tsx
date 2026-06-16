/**
 * MoodMarket — Main Application Component
 *
 * Routes the SPA to: Landing · Dashboard · Compare · Portfolio pages.
 * Uses a simple hash-based router (no react-router-dom dependency needed).
 */

import { useState, useEffect } from 'react';
import { LandingPage } from './pages/LandingPage';
import { Dashboard } from './pages/Dashboard';
import { ComparePage } from './pages/ComparePage';
import { PortfolioPage } from './pages/PortfolioPage';

type Route = 'landing' | 'dashboard' | 'compare' | 'portfolio';

const getRouteFromHash = (): Route => {
  const hash = window.location.hash.replace('#', '');
  if (hash === 'dashboard') return 'dashboard';
  if (hash === 'compare') return 'compare';
  if (hash === 'portfolio') return 'portfolio';
  return 'landing';
};

function App() {
  const [route, setRoute] = useState<Route>(getRouteFromHash);

  useEffect(() => {
    const handler = () => setRoute(getRouteFromHash());
    window.addEventListener('hashchange', handler);
    return () => window.removeEventListener('hashchange', handler);
  }, []);

  const navigate = (r: Route) => {
    window.location.hash = r === 'landing' ? '' : r;
    setRoute(r);
  };

  switch (route) {
    case 'landing':
      return <LandingPage onLaunch={() => navigate('dashboard')} />;
    case 'dashboard':
      return <Dashboard />;
    case 'compare':
      return <ComparePage />;
    case 'portfolio':
      return <PortfolioPage />;
    default:
      return <LandingPage onLaunch={() => navigate('dashboard')} />;
  }
}

export default App;
