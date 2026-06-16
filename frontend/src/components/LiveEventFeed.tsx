import { useState, useEffect, useRef } from 'react';
import { Activity, Zap, TrendingUp, AlertTriangle, Radio, Brain } from 'lucide-react';

interface MarketEvent {
  id: string;
  type: 'sentiment' | 'anomaly' | 'forecast' | 'hype' | 'signal';
  ticker: string;
  message: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  timestamp: Date;
  value?: string;
}

const ICON_MAP = {
  sentiment: Brain,
  anomaly: AlertTriangle,
  forecast: TrendingUp,
  hype: Zap,
  signal: Activity,
};

const SEVERITY_COLORS = {
  low:      { text: 'text-slate-400',   dot: 'bg-slate-500',   badge: 'bg-slate-800/60 border-slate-700/60' },
  medium:   { text: 'text-cyan-400',    dot: 'bg-cyan-500',    badge: 'bg-cyan-500/10 border-cyan-500/20' },
  high:     { text: 'text-amber-400',   dot: 'bg-amber-500',   badge: 'bg-amber-500/10 border-amber-500/20' },
  critical: { text: 'text-rose-400',    dot: 'bg-rose-500',    badge: 'bg-rose-500/10 border-rose-500/20 animate-pulse' },
};

const EVENT_TEMPLATES = [
  { type: 'sentiment' as const, severity: 'medium' as const, msg: (t: string) => `FinBERT ensemble scored ${t} at 74/100 — BULLISH signal confirmed`, val: '+74' },
  { type: 'anomaly'  as const, severity: 'high'   as const, msg: (t: string) => `Z-Score 4.2σ detected on ${t} — EWMA regime shift triggered`, val: '4.2σ' },
  { type: 'forecast' as const, severity: 'medium' as const, msg: (t: string) => `Informer model: ${t} 4h outlook UP with 63% confidence`, val: '63%' },
  { type: 'hype'     as const, severity: 'critical' as const, msg: (t: string) => `HYPE STORM: ${t} Reddit mentions +340% above 30d baseline 🚨`, val: '+340%' },
  { type: 'signal'   as const, severity: 'high'   as const, msg: (t: string) => `Synthesizer: ${t} → STRONG BUY — 4/5 agents aligned`, val: 'BUY' },
  { type: 'sentiment' as const, severity: 'low'   as const, msg: (t: string) => `RoBERTa confidence calibrated for ${t}: ECE 0.023`, val: 'ECE 0.02' },
  { type: 'anomaly'  as const, severity: 'medium' as const, msg: (t: string) => `Isolation Forest flagged ${t}: non-linear pattern detected`, val: '3.8σ' },
  { type: 'forecast' as const, severity: 'low'   as const, msg: (t: string) => `Attention rollout shows ${t} volume nodes driving prediction`, val: '↑ vol' },
  { type: 'signal'   as const, severity: 'medium' as const, msg: (t: string) => `Risk Manager: ${t} position sizing set at 2.4% Kelly criterion`, val: '2.4%' },
  { type: 'hype'     as const, severity: 'high'   as const, msg: (t: string) => `Multi-variate Z-Score: ${t} Twitter + Reddit correlation 0.91`, val: '0.91r' },
];

const TICKERS = ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'META', 'GME', 'GOOGL', 'AMZN'];

function makeEvent(): MarketEvent {
  const template = EVENT_TEMPLATES[Math.floor(Math.random() * EVENT_TEMPLATES.length)];
  const ticker = TICKERS[Math.floor(Math.random() * TICKERS.length)];
  return {
    id: crypto.randomUUID(),
    type: template.type,
    ticker,
    message: template.msg(ticker),
    severity: template.severity,
    timestamp: new Date(),
    value: template.val,
  };
}

export function LiveEventFeed() {
  const [events, setEvents] = useState<MarketEvent[]>(() =>
    Array.from({ length: 5 }, makeEvent)
  );
  const [paused, setPaused] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (paused) return;
    const interval = setInterval(() => {
      setEvents(prev => [makeEvent(), ...prev].slice(0, 25));
    }, 2800);
    return () => clearInterval(interval);
  }, [paused]);

  return (
    <div className="glass rounded-xl border border-slate-800/60 overflow-hidden flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-800/60 bg-slate-900/60">
        <div className="flex items-center gap-2">
          <Radio size={13} className="text-emerald-400 animate-pulse" />
          <span className="text-xs font-bold text-slate-200 uppercase tracking-wider">Live AI Event Feed</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-slate-500 font-mono">{events.length} events</span>
          <button
            onClick={() => setPaused(p => !p)}
            className={`text-[10px] px-2 py-0.5 rounded font-semibold border transition-all ${
              paused
                ? 'text-amber-400 border-amber-500/30 bg-amber-500/10'
                : 'text-slate-500 border-slate-700 hover:text-slate-300'
            }`}
          >
            {paused ? '▶ Resume' : '⏸ Pause'}
          </button>
        </div>
      </div>

      {/* Event list */}
      <div
        ref={listRef}
        className="flex-1 overflow-y-auto py-1"
        style={{ maxHeight: 320 }}
      >
        {events.map((evt, idx) => {
          const Icon = ICON_MAP[evt.type];
          const colors = SEVERITY_COLORS[evt.severity];
          const isNew = idx === 0;
          return (
            <div
              key={evt.id}
              className={`flex items-start gap-2.5 px-3 py-2 border-b border-slate-800/30 transition-all duration-500 ${
                isNew ? 'bg-slate-800/30 animate-slide-in-right' : 'hover:bg-slate-800/20'
              }`}
            >
              {/* Severity dot */}
              <div className="flex flex-col items-center gap-1 mt-0.5">
                <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${colors.dot}`} />
              </div>

              {/* Icon */}
              <Icon size={12} className={`${colors.text} mt-0.5 shrink-0`} />

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5 mb-0.5">
                  <span className={`text-[10px] font-bold font-mono px-1 py-0.5 rounded border ${colors.badge} ${colors.text}`}>
                    {evt.ticker}
                  </span>
                  <span className={`text-[10px] font-semibold uppercase tracking-wide ${colors.text}`}>
                    {evt.type}
                  </span>
                  {evt.value && (
                    <span className={`ml-auto text-[10px] font-data font-bold ${colors.text}`}>
                      {evt.value}
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-slate-400 leading-snug line-clamp-2">
                  {evt.message}
                </p>
              </div>

              {/* Time */}
              <span className="text-[9px] text-slate-600 font-mono mt-0.5 shrink-0">
                {evt.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </span>
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div className="px-3 py-1.5 border-t border-slate-800/60 bg-slate-900/40 flex items-center gap-2">
        <div className="flex items-center gap-1.5">
          {(['critical', 'high', 'medium', 'low'] as const).map(s => (
            <div key={s} className="flex items-center gap-1">
              <span className={`w-1.5 h-1.5 rounded-full ${SEVERITY_COLORS[s].dot}`} />
              <span className="text-[9px] text-slate-600 capitalize">{s}</span>
            </div>
          ))}
        </div>
        <div className="ml-auto flex items-center gap-1 text-[9px] text-slate-600">
          <TrendingUp size={9} />
          Powered by 7-method ensemble
        </div>
      </div>
    </div>
  );
}
