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

const ROUTE_TITLES: Record<Route, string> = {
  landing:   'MoodMarket — AI Financial Intelligence Platform',
  dashboard: 'MoodMarket — Live Intelligence Dashboard',
  compare:   'MoodMarket — Multi-Ticker Comparison',
  portfolio: 'MoodMarket — Portfolio Analytics',
};

function App() {
  const [route, setRoute] = useState<Route>(getRouteFromHash);

  useEffect(() => {
    const handler = () => setRoute(getRouteFromHash());
    window.addEventListener('hashchange', handler);
    return () => window.removeEventListener('hashchange', handler);
  }, []);

  // Update page title on every route change
  useEffect(() => {
    document.title = ROUTE_TITLES[route];
  }, [route]);

  const navigate = (r: Route) => {
    window.location.hash = r === 'landing' ? '' : r;
    setRoute(r);
  };

  switch (route) {
    case 'landing':
      return <LandingPage onLaunch={() => navigate('dashboard')} />;
    case 'dashboard':
      return <div key="dashboard" className="page-enter"><Dashboard /></div>;
    case 'compare':
      return <div key="compare" className="page-enter"><ComparePage /></div>;
    case 'portfolio':
      return <div key="portfolio" className="page-enter"><PortfolioPage /></div>;
    default:
      return <LandingPage onLaunch={() => navigate('dashboard')} />;
  }
}

export default App;

/* clean architecture alignment */
