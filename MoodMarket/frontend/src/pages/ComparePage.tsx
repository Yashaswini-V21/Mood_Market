import { useState, useEffect } from 'react';
import {
  BarChart2, TrendingUp, TrendingDown, GitCompare, Plus, X, Brain,
  Activity, Target,
} from 'lucide-react';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer,
  AreaChart, Area, XAxis, YAxis, Tooltip, Legend,
} from 'recharts';
import { DashboardLayout } from '../layouts/DashboardLayout';
import { RealtimeProvider } from '../context/RealtimeContext';

// ─── Types ────────────────────────────────────────────────────────────────────
interface TickerProfile {
  ticker: string;
  price: number;
  change: number;
  sentiment: number;
  forecast: number;
  anomalyScore: number;
  rsi: number;
  macd: number;
  volume: number;
  confidence: number;
  direction: 'UP' | 'DOWN';
  color: string;
}

// ─── Seed data per ticker ─────────────────────────────────────────────────────
const TICKER_PROFILES: Record<string, TickerProfile> = {
  AAPL:  { ticker: 'AAPL',  price: 192.53, change:  1.23, sentiment: 72, forecast: 65, anomalyScore: 12, rsi: 72, macd: 2.3,  volume: 65, confidence: 63, direction: 'UP',   color: '#06b6d4' },
  MSFT:  { ticker: 'MSFT',  price: 415.20, change:  0.89, sentiment: 68, forecast: 61, anomalyScore: 8,  rsi: 65, macd: 1.8,  volume: 58, confidence: 61, direction: 'UP',   color: '#a855f7' },
  TSLA:  { ticker: 'TSLA',  price: 248.42, change: -2.15, sentiment: 38, forecast: 35, anomalyScore: 76, rsi: 28, macd: -3.1, volume: 88, confidence: 55, direction: 'DOWN', color: '#ef4444' },
  GOOGL: { ticker: 'GOOGL', price: 172.90, change: -0.54, sentiment: 51, forecast: 48, anomalyScore: 15, rsi: 48, macd: -0.5, volume: 44, confidence: 58, direction: 'DOWN', color: '#f59e0b' },
  NVDA:  { ticker: 'NVDA',  price: 875.39, change:  3.47, sentiment: 81, forecast: 79, anomalyScore: 22, rsi: 68, macd: 4.2,  volume: 92, confidence: 74, direction: 'UP',   color: '#10b981' },
  META:  { ticker: 'META',  price: 526.68, change:  2.31, sentiment: 69, forecast: 64, anomalyScore: 10, rsi: 61, macd: 2.9,  volume: 71, confidence: 67, direction: 'UP',   color: '#6366f1' },
  GME:   { ticker: 'GME',   price:  24.83, change: 15.20, sentiment: 88, forecast: 72, anomalyScore: 95, rsi: 89, macd: 5.1,  volume: 100,confidence: 71, direction: 'UP',   color: '#f97316' },
  AMZN:  { ticker: 'AMZN',  price: 193.77, change:  1.02, sentiment: 60, forecast: 58, anomalyScore: 11, rsi: 55, macd: 1.1,  volume: 62, confidence: 59, direction: 'UP',   color: '#ec4899' },
};

const ALL_TICKERS = Object.keys(TICKER_PROFILES);

// ─── Correlation matrix mock ───────────────────────────────────────────────────
function correlate(a: TickerProfile, b: TickerProfile): number {
  if (a.ticker === b.ticker) return 1.0;
  const diff = Math.abs(a.sentiment - b.sentiment) / 100 + Math.abs(a.rsi - b.rsi) / 100;
  return +(1 - diff * 0.8 + (Math.random() - 0.5) * 0.2).toFixed(2);
}

// ─── Radar dimensions ─────────────────────────────────────────────────────────
const RADAR_KEYS = [
  { key: 'sentiment',    label: 'Sentiment', max: 100 },
  { key: 'forecast',     label: 'Forecast',  max: 100 },
  { key: 'confidence',   label: 'Confidence',max: 100 },
  { key: 'rsi',          label: 'RSI',       max: 100 },
  { key: 'volume',       label: 'Volume',    max: 100 },
  { key: 'anomalyScore', label: 'Anomaly',   max: 100 },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────
const corr2color = (v: number) => {
  if (v >= 0.7) return 'bg-emerald-500/20 text-emerald-400';
  if (v >= 0.3) return 'bg-amber-500/20 text-amber-400';
  return 'bg-rose-500/20 text-rose-400';
};

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass px-3 py-2 rounded-lg text-xs shadow-xl border border-slate-700/60 space-y-1">
      <div className="font-mono text-slate-400 text-[10px] mb-1">{label}</div>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full" style={{ background: p.color }} />
          <span className="text-slate-300 font-semibold">{p.dataKey}:</span>
          <span className="font-data text-white">{p.value?.toFixed(2)}</span>
        </div>
      ))}
    </div>
  );
};

// ─── Sparkline data ────────────────────────────────────────────────────────────
const genSparkline = (base: number, dir: 'UP' | 'DOWN') =>
  Array.from({ length: 30 }, (_, i) => {
    const trend = dir === 'UP' ? i * 0.3 : -i * 0.3;
    return { t: `${i}`, price: +(base + trend + (Math.random() - 0.5) * 2).toFixed(2) };
  });

// ─── Compare Page ─────────────────────────────────────────────────────────────
export function ComparePage() {
  const [selected, setSelected] = useState<string[]>(['AAPL', 'NVDA', 'TSLA']);
  const [adding, setAdding] = useState(false);
  const [profiles, setProfiles] = useState<TickerProfile[]>([]);
  const [sparklines, setSparklines] = useState<Record<string, { t: string; price: number }[]>>({});

  useEffect(() => {
    const profs = selected.map(t => TICKER_PROFILES[t]).filter(Boolean);
    setProfiles(profs);
    const sl: Record<string, { t: string; price: number }[]> = {};
    profs.forEach(p => { sl[p.ticker] = genSparkline(p.price, p.direction); });
    setSparklines(sl);
  }, [selected]);

  const radarData = RADAR_KEYS.map(k => {
    const point: Record<string, string | number> = { metric: k.label };
    profiles.forEach(p => {
      point[p.ticker] = Math.round((p[k.key as keyof TickerProfile] as number));
    });
    return point;
  });

  // Merged sparkline data
  const mergedSpark: Record<string, number>[] = Array.from({ length: 30 }, (_, i) => {
    const point: Record<string, number> = { i };
    profiles.forEach(p => {
      const arr = sparklines[p.ticker];
      if (arr) point[p.ticker] = arr[i]?.price ?? p.price;
    });
    return point;
  });

  const removeTicker = (t: string) => setSelected(prev => prev.filter(x => x !== t));
  const addTicker = (t: string) => {
    if (!selected.includes(t) && selected.length < 4) {
      setSelected(prev => [...prev, t]);
    }
    setAdding(false);
  };

  return (
    <RealtimeProvider ticker={selected[0] ?? 'AAPL'}>
      <DashboardLayout selectedTicker={selected[0] ?? 'AAPL'} onTickerSelect={() => {}}>
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div>
            <div className="flex items-center gap-2 mb-0.5">
              <GitCompare size={16} className="text-purple-400" />
              <h1 className="text-xl font-bold text-white">Multi-Ticker Comparison</h1>
            </div>
            <p className="text-xs text-slate-500">
              Side-by-side analysis — Radar · Price Overlay · Correlation Matrix · Metrics Grid
            </p>
          </div>
          {selected.length < 4 && (
            <button
              id="compare-add-ticker"
              onClick={() => setAdding(a => !a)}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700
                         border border-slate-700 text-xs font-semibold text-slate-300 transition-all"
            >
              <Plus size={13} /> Add Ticker
            </button>
          )}
        </div>

        {/* Add ticker dropdown */}
        {adding && (
          <div className="mb-4 glass rounded-xl border border-slate-800/60 p-3 animate-slide-down">
            <p className="text-xs text-slate-500 mb-2 font-semibold uppercase tracking-wider">Select a ticker to add</p>
            <div className="flex flex-wrap gap-2">
              {ALL_TICKERS.filter(t => !selected.includes(t)).map(t => (
                <button
                  key={t}
                  onClick={() => addTicker(t)}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700
                             text-xs font-data font-semibold text-slate-300 hover:text-white transition-all"
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Selected ticker chips */}
        <div className="flex gap-2 mb-5">
          {profiles.map(p => (
            <div
              key={p.ticker}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-data font-bold transition-all"
              style={{ borderColor: p.color + '40', background: p.color + '12', color: p.color }}
            >
              <span>{p.ticker}</span>
              <span className="text-[10px] opacity-70">${p.price.toFixed(2)}</span>
              <button onClick={() => removeTicker(p.ticker)} className="opacity-50 hover:opacity-100 transition-opacity">
                <X size={11} />
              </button>
            </div>
          ))}
        </div>

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">

          {/* Radar Chart */}
          <div className="glass rounded-2xl border border-slate-800/60 p-5">
            <div className="flex items-center gap-2 mb-4">
              <Activity size={14} className="text-purple-400" />
              <span className="text-sm font-bold text-slate-200">Performance Radar</span>
            </div>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData} cx="50%" cy="50%">
                  <PolarGrid stroke="rgba(255,255,255,0.06)" />
                  <PolarAngleAxis dataKey="metric" tick={{ fill: '#64748b', fontSize: 10 }} />
                  {profiles.map(p => (
                    <Radar
                      key={p.ticker}
                      name={p.ticker}
                      dataKey={p.ticker}
                      stroke={p.color}
                      fill={p.color}
                      fillOpacity={0.12}
                      strokeWidth={2}
                    />
                  ))}
                  <Legend
                    formatter={(v) => <span className="text-[11px] text-slate-400 font-data">{v}</span>}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Price overlay sparkline */}
          <div className="glass rounded-2xl border border-slate-800/60 p-5">
            <div className="flex items-center gap-2 mb-4">
              <BarChart2 size={14} className="text-cyan-400" />
              <span className="text-sm font-bold text-slate-200">Price Trajectories (30 steps)</span>
            </div>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={mergedSpark}>
                  <defs>
                    {profiles.map(p => (
                      <linearGradient key={p.ticker} id={`cg-${p.ticker}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"  stopColor={p.color} stopOpacity={0.2} />
                        <stop offset="95%" stopColor={p.color} stopOpacity={0} />
                      </linearGradient>
                    ))}
                  </defs>
                  <XAxis dataKey="i" hide />
                  <YAxis domain={['auto', 'auto']} hide />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend formatter={(v) => <span className="text-[11px] text-slate-400 font-data">{v}</span>} />
                  {profiles.map(p => (
                    <Area
                      key={p.ticker}
                      type="monotone"
                      dataKey={p.ticker}
                      stroke={p.color}
                      strokeWidth={1.5}
                      fill={`url(#cg-${p.ticker})`}
                      animationDuration={600}
                    />
                  ))}
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Metrics comparison grid */}
        <div className="glass rounded-2xl border border-slate-800/60 p-5 mb-4">
          <div className="flex items-center gap-2 mb-4">
            <Target size={14} className="text-emerald-400" />
            <span className="text-sm font-bold text-slate-200">Metrics Comparison</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-800/60">
                  <th className="text-left py-2 pr-4 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">Metric</th>
                  {profiles.map(p => (
                    <th key={p.ticker} className="text-center py-2 px-3 font-data font-bold" style={{ color: p.color }}>
                      {p.ticker}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/40">
                {[
                  { label: 'Price', key: 'price', fmt: (v: number) => `$${v.toFixed(2)}` },
                  { label: 'Daily Change', key: 'change', fmt: (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(2)}%` },
                  { label: 'Sentiment Score', key: 'sentiment', fmt: (v: number) => `${v}/100` },
                  { label: 'Forecast Signal', key: 'forecast', fmt: (v: number) => `${v}% UP` },
                  { label: 'RSI', key: 'rsi', fmt: (v: number) => v.toFixed(0) },
                  { label: 'MACD', key: 'macd', fmt: (v: number) => v.toFixed(1) },
                  { label: 'Anomaly Score', key: 'anomalyScore', fmt: (v: number) => `${v}/100` },
                  { label: 'Confidence', key: 'confidence', fmt: (v: number) => `${v}%` },
                ].map(row => {
                  const vals = profiles.map(p => p[row.key as keyof TickerProfile] as number);
                  const maxVal = Math.max(...vals);
                  return (
                    <tr key={row.label} className="hover:bg-slate-800/20 transition-colors">
                      <td className="py-2 pr-4 text-slate-500 font-semibold text-[10px] uppercase tracking-wider">{row.label}</td>
                      {profiles.map((p) => {
                        const val = p[row.key as keyof TickerProfile] as number;
                        const isBest = val === maxVal;
                        return (
                          <td key={p.ticker} className="py-2 px-3 text-center font-data">
                            <span
                              className={`px-2 py-0.5 rounded-md font-semibold ${isBest ? 'bg-emerald-500/15 text-emerald-400' : 'text-slate-400'}`}
                            >
                              {row.fmt(val)}
                            </span>
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Correlation Matrix */}
        <div className="glass rounded-2xl border border-slate-800/60 p-5">
          <div className="flex items-center gap-2 mb-4">
            <Brain size={14} className="text-amber-400" />
            <span className="text-sm font-bold text-slate-200">Sentiment Correlation Matrix</span>
          </div>
          <div className="overflow-x-auto">
            <table className="text-xs">
              <thead>
                <tr>
                  <th className="w-16 text-left" />
                  {profiles.map(p => (
                    <th key={p.ticker} className="w-20 text-center py-2 font-data text-[11px]" style={{ color: p.color }}>
                      {p.ticker}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {profiles.map(a => (
                  <tr key={a.ticker}>
                    <td className="font-data text-[11px] pr-3 py-1.5 font-bold" style={{ color: a.color }}>{a.ticker}</td>
                    {profiles.map(b => {
                      const val = correlate(a, b);
                      return (
                        <td key={b.ticker} className="py-1.5 px-2 text-center">
                          <span className={`inline-block px-2 py-0.5 rounded-md text-[11px] font-data font-bold ${corr2color(val)}`}>
                            {val.toFixed(2)}
                          </span>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-[10px] text-slate-600 mt-3">
              Correlation computed from ensemble sentiment + RSI momentum proxy.
              <span className="text-emerald-600 ml-2">■ ≥ 0.7 High</span>
              <span className="text-amber-600 ml-2">■ ≥ 0.3 Moderate</span>
              <span className="text-rose-600 ml-2">■ &lt; 0.3 Low</span>
            </p>
          </div>
        </div>

        {/* Direction summary */}
        <div className="mt-4 flex flex-wrap gap-3">
          {profiles.map(p => (
            <div key={p.ticker} className="flex items-center gap-2 glass rounded-xl px-3 py-2 border border-slate-800/60">
              {p.direction === 'UP'
                ? <TrendingUp size={13} className="text-emerald-400" />
                : <TrendingDown size={13} className="text-rose-400" />
              }
              <span className="font-data text-xs font-bold text-slate-300">{p.ticker}</span>
              <span className={`text-[10px] font-bold ${p.direction === 'UP' ? 'text-emerald-400' : 'text-rose-400'}`}>
                {p.direction} · {p.confidence}% conf
              </span>
            </div>
          ))}
        </div>
      </DashboardLayout>
    </RealtimeProvider>
  );
}

/* clean architecture alignment */
