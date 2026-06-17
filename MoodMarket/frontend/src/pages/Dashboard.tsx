import { useState, useEffect } from 'react';
import { DashboardLayout } from '../layouts/DashboardLayout';
import { SentimentCard } from '../components/MainContent/SentimentCard';
import { ForecastCard } from '../components/MainContent/ForecastCard';
import { HypeStormCard } from '../components/MainContent/HypeStormCard';
import { AnomalyCard } from '../components/MainContent/AnomalyCard';
import { SignalCard } from '../components/TradingSignal/SignalCard';
import { ExplainabilityDashboard } from '../components/Explainability/ExplainabilityDashboard';
import { LiveEventFeed } from '../components/LiveEventFeed';
import { RealtimeProvider } from '../context/RealtimeContext';
import { useToast } from '../context/ToastContext';
import { TrendingUp, TrendingDown, Cpu, RefreshCw, Zap, Brain, BarChart2, GitCompare, TrendingUp as Portfolio } from 'lucide-react';
import { Button } from '../components/base/Button';
import { AIChatButton } from '../components/AIChat/AIChatPanel';

// Per-ticker seed data for realistic stats
const TICKER_DATA: Record<string, { price: number; change: number; sentiment: number; conf: number; dir: 'UP' | 'DOWN' }> = {
  AAPL:  { price: 192.53, change:  1.23, sentiment: 72, conf: 63, dir: 'UP'   },
  MSFT:  { price: 415.20, change:  0.89, sentiment: 68, conf: 61, dir: 'UP'   },
  TSLA:  { price: 248.42, change: -2.15, sentiment: 38, conf: 55, dir: 'DOWN' },
  GOOGL: { price: 172.90, change: -0.54, sentiment: 51, conf: 58, dir: 'DOWN' },
  NVDA:  { price: 875.39, change:  3.47, sentiment: 81, conf: 74, dir: 'UP'   },
  META:  { price: 526.68, change:  2.31, sentiment: 69, conf: 67, dir: 'UP'   },
  GME:   { price:  24.83, change: 15.20, sentiment: 88, conf: 71, dir: 'UP'   },
  AMZN:  { price: 193.77, change:  1.02, sentiment: 60, conf: 59, dir: 'UP'   },
};

const DEFAULT_STATS: { price: number; change: number; sentiment: number; conf: number; dir: 'UP' | 'DOWN' } =
  { price: 192.53, change: 1.23, sentiment: 72, conf: 63, dir: 'UP' };

export function Dashboard() {
  const [ticker, setTicker] = useState('AAPL');
  const [refreshKey, setRefreshKey] = useState(0);
  const [showExplainability, setShowExplainability] = useState(false);
  const [stats, setStats] = useState(DEFAULT_STATS);
  // Drives stat-flash animation — incremented each time ticker changes
  const [statKey, setStatKey] = useState(0);
  const { toast } = useToast();
  const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  // Update stats when ticker changes
  useEffect(() => {
    const d = TICKER_DATA[ticker];
    if (d) { setStats(d); setStatKey(k => k + 1); }
  }, [ticker]);

  const handleSelect = (t: string) => {
    setTicker(t);
    setRefreshKey(k => k + 1);
    toast(`Switched active ticker to ${t}`, 'success');
  };

  const handleRefresh = () => {
    setRefreshKey(k => k + 1);
    toast('Dashboard data refreshed', 'success');
  };

  const toggleExplainability = () => {
    setShowExplainability(prev => !prev);
  };

  // Navigate using hash-based router
  const navigateTo = (hash: string) => { window.location.hash = hash; };

  const isUp = stats.change >= 0;

  return (
    <RealtimeProvider ticker={ticker}>
      <DashboardLayout selectedTicker={ticker} onTickerSelect={handleSelect}>

        {/* Page header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="flex items-center gap-2 mb-0.5">
              <div className="flex items-center gap-1.5 text-[11px] text-emerald-400 font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse inline-block" />
                LIVE
              </div>
              <h1 className="text-xl font-bold text-white">
                <span className="font-data">{ticker}</span>
                <span className="text-slate-400 font-normal"> — AI Intelligence Dashboard</span>
              </h1>
            </div>
            <p className="text-xs text-slate-500 flex items-center gap-1.5">
              <Cpu size={11} />
              Informer Transformer · FinBERT Ensemble · 7-Method Anomaly · 5-Agent Desk — Updated {now}
            </p>
          </div>
          <Button
            id="refresh-all-btn"
            variant="ghost" size="sm"
            onClick={handleRefresh}
            className="gap-1.5"
          >
            <RefreshCw size={13} /> Refresh All
          </Button>
        </div>

        {/* Quick stats banner — animated on ticker change */}
        <div key={statKey} className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
          {/* Price */}
          <div className="glass rounded-xl p-3 flex flex-col gap-0.5 hover:border-slate-600/80 transition-all duration-200 group">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Price</span>
            <span className="font-data font-bold text-lg text-white group-hover:text-cyan-100 transition-colors">
              ${stats.price.toFixed(2)}
            </span>
            <span className="text-[10px] text-slate-600">Last close · {ticker}</span>
          </div>

          {/* Change */}
          <div className={`glass rounded-xl p-3 flex flex-col gap-0.5 border transition-all duration-300 ${
            isUp ? 'border-emerald-500/20 hover:border-emerald-500/40' : 'border-rose-500/20 hover:border-rose-500/40'
          }`}>
            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Change</span>
            <span className={`font-data font-bold text-lg flex items-center gap-1 ${isUp ? 'text-emerald-400' : 'text-rose-400'}`}>
              {isUp ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
              {isUp ? '+' : ''}{stats.change.toFixed(2)}%
            </span>
            <span className="text-[10px] text-slate-600">Today · 1d</span>
          </div>

          {/* Sentiment */}
          <div className="glass rounded-xl p-3 flex flex-col gap-0.5 hover:border-cyan-500/30 transition-all duration-200 group">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold flex items-center gap-1">
              <Brain size={9} /> Sentiment
            </span>
            <span className={`font-data font-bold text-lg ${stats.sentiment >= 60 ? 'text-emerald-400' : stats.sentiment >= 40 ? 'text-amber-400' : 'text-rose-400'}`}>
              {stats.sentiment} <span className="text-sm font-normal text-slate-500">/ 100</span>
            </span>
            <span className="text-[10px] text-slate-600">FinBERT ensemble score</span>
          </div>

          {/* Forecast */}
          <div className="glass rounded-xl p-3 flex flex-col gap-0.5 hover:border-purple-500/30 transition-all duration-200 group">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold flex items-center gap-1">
              <BarChart2 size={9} /> Forecast
            </span>
            <span className={`font-data font-bold text-lg flex items-center gap-1 ${stats.dir === 'UP' ? 'text-emerald-400' : 'text-rose-400'}`}>
              {stats.dir === 'UP' ? <Zap size={14} /> : <TrendingDown size={14} />}
              {stats.dir} ↑
            </span>
            <span className="text-[10px] text-slate-600">4h horizon · {stats.conf}% conf.</span>
          </div>
        </div>

        {/* Main card grid */}
        <div key={refreshKey} className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <SentimentCard
            ticker={ticker}
            isExpanded={showExplainability}
            onExpandToggle={toggleExplainability}
          />
          <ForecastCard ticker={ticker} />
          <SignalCard ticker={ticker} onViewDetails={() => setShowExplainability(true)} />
          <AnomalyCard
            ticker={ticker}
            onViewAnalysis={() => setShowExplainability(true)}
          />
          <div className="md:col-span-2">
            <HypeStormCard ticker={ticker} />
          </div>
        </div>

        {/* Live AI Event Feed */}
        <div className="mt-4">
          <div className="flex items-center gap-2 mb-2">
            <Zap size={13} className="text-purple-400" />
            <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">AI Market Intelligence Stream</span>
            <span className="text-[10px] text-slate-600">— real-time analysis from 5-agent ensemble</span>
          </div>
          <LiveEventFeed />
        </div>

        {/* Model Explainability Dashboard (expandable) */}
        {showExplainability && (
          <div className="mt-4 transition-all duration-500 ease-in-out">
            <ExplainabilityDashboard ticker={ticker} />
          </div>
        )}

        {/* Footer */}
        <div className="mt-6 flex items-center gap-2 text-[11px] text-slate-600 border-t border-slate-800/40 pt-4">
          <TrendingUp size={11} />
          MoodMarket — Informer Transformer + FinBERT + 7-Method Ensemble Anomaly Detection + 5-Agent Async Desk.
          <div className="ml-auto flex items-center gap-3">
            <button
              id="nav-to-compare"
              onClick={() => navigateTo('compare')}
              className="flex items-center gap-1 text-slate-600 hover:text-cyan-400 transition-colors text-[11px] cursor-pointer"
            >
              <GitCompare size={11} /> Compare
            </button>
            <button
              id="nav-to-portfolio"
              onClick={() => navigateTo('portfolio')}
              className="flex items-center gap-1 text-slate-600 hover:text-emerald-400 transition-colors text-[11px] cursor-pointer"
            >
              <Portfolio size={11} /> Portfolio
            </button>
            <span>Not financial advice.</span>
          </div>
        </div>
      </DashboardLayout>
      <AIChatButton ticker={ticker} />
    </RealtimeProvider>
  );
}


/* clean architecture alignment */
