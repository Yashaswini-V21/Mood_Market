import { useState } from 'react';
import { DashboardLayout } from '../layouts/DashboardLayout';
import { SentimentCard } from '../components/MainContent/SentimentCard';
import { ForecastCard } from '../components/MainContent/ForecastCard';
import { HypeStormCard } from '../components/MainContent/HypeStormCard';
import { AnomalyCard } from '../components/MainContent/AnomalyCard';
import { SignalCard } from '../components/TradingSignal/SignalCard';
import { ExplainabilityDashboard } from '../components/Explainability/ExplainabilityDashboard';
import { RealtimeProvider } from '../context/RealtimeContext';
import { TrendingUp, Cpu, RefreshCw } from 'lucide-react';
import { Button } from '../components/base/Button';

export function Dashboard() {
  const [ticker, setTicker] = useState('AAPL');
  const [refreshKey, setRefreshKey] = useState(0);
  const [showExplainability, setShowExplainability] = useState(false);
  const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  const handleSelect = (t: string) => { 
    setTicker(t); 
    setRefreshKey(k => k + 1); 
  };

  const toggleExplainability = () => {
    setShowExplainability(prev => !prev);
  };

  return (
    <RealtimeProvider ticker={ticker}>
      <DashboardLayout selectedTicker={ticker} onTickerSelect={handleSelect}>
        {/* Page header */}
        <div className="flex items-center justify-between mb-5">
          <div>
            <div className="flex items-center gap-2.5 mb-1">
              <div className="flex items-center gap-1.5 text-[11px] text-emerald-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse inline-block" />
                LIVE
              </div>
              <h1 className="text-xl font-bold text-white">
                <span className="font-data">{ticker}</span> Analysis
              </h1>
            </div>
            <p className="text-xs text-slate-500 flex items-center gap-1.5">
              <Cpu size={11} />
              Informer + 7-method ensemble — Updated {now}
            </p>
          </div>
          <Button
            id="refresh-all-btn"
            variant="ghost" size="sm"
            onClick={() => setRefreshKey(k => k + 1)}
            className="gap-1.5"
          >
            <RefreshCw size={13} /> Refresh All
          </Button>
        </div>

        {/* Top banner — ticker quick stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
          {[
            { label: 'Price',      val: '$192.53', color: 'text-white',      sub: 'Last close'     },
            { label: 'Change',     val: '+1.23%',  color: 'text-emerald-400', sub: 'Today'          },
            { label: 'Sentiment',  val: '72 / 100',color: 'text-emerald-400', sub: 'Ensemble score' },
            { label: '4h Forecast',val: 'UP ↑',    color: 'text-emerald-400', sub: '63% confidence' },
          ].map(s => (
            <div key={s.label} className="glass rounded-xl p-3 flex flex-col gap-0.5">
              <span className="text-[11px] text-slate-500 uppercase tracking-wider">{s.label}</span>
              <span className={`font-data font-bold text-base ${s.color}`}>{s.val}</span>
              <span className="text-[10px] text-slate-600">{s.sub}</span>
            </div>
          ))}
        </div>

        {/* Main card grid */}
        <div key={refreshKey} className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Sentiment + Forecast top row */}
          <SentimentCard 
            ticker={ticker} 
            isExpanded={showExplainability} 
            onExpandToggle={toggleExplainability} 
          />
          <ForecastCard  ticker={ticker} />

          {/* Signal + Anomaly middle row */}
          <SignalCard ticker={ticker} onViewDetails={() => setShowExplainability(true)} />
          <AnomalyCard   
            ticker={ticker} 
            onViewAnalysis={() => setShowExplainability(true)} 
          />

          {/* Hype storm bottom row */}
          <div className="md:col-span-2">
            <HypeStormCard ticker={ticker} />
          </div>
        </div>

        {/* Dynamic Model Explainability Dashboard */}
        {showExplainability && (
          <div className="transition-all duration-500 ease-in-out">
            <ExplainabilityDashboard ticker={ticker} />
          </div>
        )}

        {/* Footer note */}
        <div className="mt-6 flex items-center gap-2 text-[11px] text-slate-600">
          <TrendingUp size={11} />
          MoodMarket — Informer + FinBERT + Ensemble Anomaly Detection. Not financial advice.
        </div>
      </DashboardLayout>
    </RealtimeProvider>
  );
}
