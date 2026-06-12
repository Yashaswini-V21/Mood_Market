import { TrendingUp, TrendingDown, Activity, Bell } from 'lucide-react';
import { clsx } from 'clsx';
import { Badge } from '../base/Badge';

const GAINERS = [
  { ticker: 'TSLA', change: 15.20 }, { ticker: 'NVDA', change: 12.80 },
  { ticker: 'MSTR', change:  9.30 }, { ticker: 'GME',  change:  8.70 },
];
const LOSERS = [
  { ticker: 'ARKK', change: -8.20 }, { ticker: 'IVV',  change: -5.10 },
  { ticker: 'SPY',  change: -3.40 }, { ticker: 'QQQ',  change: -2.80 },
];
const ALERTS = [
  { ticker: 'GME',  type: 'HYPE_STORM', time: '2m ago',  level: 'HIGH'   as const },
  { ticker: 'TSLA', type: 'VOLUME_SPIKE',time: '8m ago',  level: 'MEDIUM' as const },
  { ticker: 'NVDA', type: 'BREAKOUT',   time: '15m ago', level: 'LOW'    as const },
];

export function RightSidebar() {
  const marketScore = 64;
  const marketSentiment = marketScore >= 60 ? 'BULLISH' : marketScore >= 40 ? 'NEUTRAL' : 'BEARISH';
  const gaugeColor = marketScore >= 60 ? '#10B981' : marketScore >= 40 ? '#F59E0B' : '#EF4444';

  return (
    <aside className="flex flex-col h-full overflow-y-auto gap-0 divide-y divide-slate-800/60">

      {/* Market Sentiment Gauge */}
      <div className="px-4 py-4">
        <div className="flex items-center gap-2 mb-3">
          <Activity size={13} className="text-cyan-400" />
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Market Mood</span>
        </div>
        <div className="flex flex-col items-center gap-2">
          {/* Circular gauge */}
          <div className="relative w-24 h-24">
            <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
              <circle cx="50" cy="50" r="40" fill="none" stroke="#1e293b" strokeWidth="10" />
              <circle
                cx="50" cy="50" r="40" fill="none"
                stroke={gaugeColor}
                strokeWidth="10"
                strokeDasharray={`${(marketScore / 100) * 251.2} 251.2`}
                strokeLinecap="round"
                style={{ transition: 'stroke-dasharray 1s ease, stroke 0.5s ease' }}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="font-data text-xl font-bold text-white">{marketScore}</span>
              <span className="text-[10px] text-slate-500">/ 100</span>
            </div>
          </div>
          <Badge variant={marketSentiment.toLowerCase() as any}>{marketSentiment}</Badge>
        </div>
      </div>

      {/* Top Gainers */}
      <div className="px-4 py-4">
        <div className="flex items-center gap-2 mb-2.5">
          <TrendingUp size={13} className="text-emerald-400" />
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Top Gainers</span>
        </div>
        <div className="space-y-1.5">
          {GAINERS.map(g => (
            <div key={g.ticker} className="flex items-center justify-between">
              <span className="font-data text-sm font-medium text-slate-300">{g.ticker}</span>
              <div className="flex items-center gap-1 text-emerald-400">
                <TrendingUp size={11} />
                <span className="font-data text-xs font-semibold">+{g.change.toFixed(1)}%</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Bottom Losers */}
      <div className="px-4 py-4">
        <div className="flex items-center gap-2 mb-2.5">
          <TrendingDown size={13} className="text-rose-400" />
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Biggest Drops</span>
        </div>
        <div className="space-y-1.5">
          {LOSERS.map(l => (
            <div key={l.ticker} className="flex items-center justify-between">
              <span className="font-data text-sm font-medium text-slate-300">{l.ticker}</span>
              <div className="flex items-center gap-1 text-rose-400">
                <TrendingDown size={11} />
                <span className="font-data text-xs font-semibold">{l.change.toFixed(1)}%</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Latest Alerts */}
      <div className="px-4 py-4">
        <div className="flex items-center gap-2 mb-2.5">
          <Bell size={13} className="text-amber-400" />
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Live Alerts</span>
          <span className="ml-auto w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
        </div>
        <div className="space-y-2">
          {ALERTS.map((a, i) => (
            <div key={i} className="flex items-start gap-2.5 p-2 rounded-lg bg-slate-800/40">
              <div className={clsx(
                'w-1.5 h-1.5 rounded-full mt-1.5 shrink-0',
                a.level === 'HIGH' ? 'bg-amber-400' : a.level === 'MEDIUM' ? 'bg-yellow-400' : 'bg-slate-500'
              )} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5 justify-between">
                  <span className="font-data text-xs font-semibold text-slate-200">{a.ticker}</span>
                  <span className="text-[10px] text-slate-600">{a.time}</span>
                </div>
                <span className="text-[11px] text-slate-500">{a.type.replace(/_/g, ' ')}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}
