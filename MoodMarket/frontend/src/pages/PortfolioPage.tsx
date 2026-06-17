import { useState } from 'react';
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip,
  AreaChart, Area, XAxis, YAxis, Legend,
} from 'recharts';
import { DashboardLayout } from '../layouts/DashboardLayout';
import { RealtimeProvider } from '../context/RealtimeContext';
import {
  TrendingUp, TrendingDown, DollarSign, BarChart2, Activity,
  ShieldAlert, Zap, Target, Award
} from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────
interface Position {
  ticker: string; shares: number; avgCost: number; currentPrice: number;
  sector: string; color: string;
}

// ─── Mock data ─────────────────────────────────────────────────────────────────
const POSITIONS: Position[] = [
  { ticker: 'AAPL',  shares: 50,  avgCost: 178.20, currentPrice: 192.53, sector: 'Technology',   color: '#06b6d4' },
  { ticker: 'NVDA',  shares: 10,  avgCost: 720.00, currentPrice: 875.39, sector: 'Semiconductors', color: '#10b981' },
  { ticker: 'MSFT',  shares: 25,  avgCost: 390.00, currentPrice: 415.20, sector: 'Technology',   color: '#a855f7' },
  { ticker: 'TSLA',  shares: 30,  avgCost: 270.00, currentPrice: 248.42, sector: 'EV / Auto',    color: '#ef4444' },
  { ticker: 'META',  shares: 20,  avgCost: 490.00, currentPrice: 526.68, sector: 'Social Media', color: '#6366f1' },
  { ticker: 'AMZN',  shares: 40,  avgCost: 185.00, currentPrice: 193.77, sector: 'E-Commerce',   color: '#ec4899' },
];

// ─── P&L over time — deterministic seed so chart is stable on HMR ──────────
function seededRandom(seed: number): () => number {
  // Simple mulberry32 PRNG — deterministic given the same seed
  let s = seed;
  return () => {
    s |= 0; s = s + 0x6D2B79F5 | 0;
    let t = Math.imul(s ^ s >>> 15, 1 | s);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

const genPLHistory = () => {
  const rand = seededRandom(42); // fixed seed → same chart every time
  let val = 95000;
  return Array.from({ length: 30 }, (_, i) => {
    val += (rand() - 0.45) * 1200;
    return {
      day: `D${i + 1}`,
      portfolio: +val.toFixed(2),
      benchmark: +(95000 + i * 80 + (rand() - 0.5) * 600).toFixed(2),
    };
  });
};

const PL_HISTORY = genPLHistory();

// ─── Helpers ────────────────────────────────────────────────────────────────────
const fmtUSD = (n: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(n);

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass px-3 py-2 rounded-lg text-xs border border-slate-700/60 space-y-1">
      <div className="text-slate-400 font-mono text-[10px]">{label}</div>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full" style={{ background: p.color }} />
          <span className="text-slate-300">{p.dataKey}:</span>
          <span className="font-data font-bold text-white">{fmtUSD(p.value)}</span>
        </div>
      ))}
    </div>
  );
};

const PieTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass px-3 py-2 rounded-lg text-xs border border-slate-700/60">
      <span className="font-data font-bold text-white">{payload[0].name}: </span>
      <span style={{ color: payload[0].payload.color }}>{fmtUSD(payload[0].value)}</span>
    </div>
  );
};

// ─── Portfolio Page ────────────────────────────────────────────────────────────
export function PortfolioPage() {
  const [positions] = useState(POSITIONS);
  const [plHistory] = useState(PL_HISTORY);

  // Derived
  const totalValue    = positions.reduce((s, p) => s + p.shares * p.currentPrice, 0);
  const totalCost     = positions.reduce((s, p) => s + p.shares * p.avgCost, 0);
  const totalPnL      = totalValue - totalCost;
  const totalPnLPct   = (totalPnL / totalCost) * 100;
  const dayChange     = totalValue * 0.0082; // mock 0.82% day change
  const winners       = positions.filter(p => p.currentPrice > p.avgCost).length;

  // Sector allocation
  const sectorMap: Record<string, number> = {};
  positions.forEach(p => {
    const val = p.shares * p.currentPrice;
    sectorMap[p.sector] = (sectorMap[p.sector] ?? 0) + val;
  });
  const SECTOR_COLORS = ['#06b6d4', '#10b981', '#a855f7', '#ef4444', '#6366f1', '#ec4899', '#f59e0b'];
  void SECTOR_COLORS; // used for future extension

  // Pie data by ticker
  const pieData = positions.map(p => ({
    name: p.ticker, value: +(p.shares * p.currentPrice).toFixed(2), color: p.color,
  }));

  const isUp = totalPnL >= 0;

  return (
    <RealtimeProvider ticker="AAPL">
      <DashboardLayout selectedTicker="AAPL" onTickerSelect={() => {}}>
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div>
            <div className="flex items-center gap-2 mb-0.5">
              <Target size={16} className="text-emerald-400" />
              <h1 className="text-xl font-bold text-white">Portfolio Analytics</h1>
            </div>
            <p className="text-xs text-slate-500">AI-enhanced portfolio performance and risk overview</p>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[11px] text-emerald-400 font-semibold">Live positions</span>
          </div>
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
          {[
            { label: 'Portfolio Value',    val: fmtUSD(totalValue),  sub: `Cost: ${fmtUSD(totalCost)}`,  color: 'text-white',          icon: DollarSign },
            { label: 'Total P&L',          val: `${isUp ? '+' : ''}${fmtUSD(totalPnL)}`, sub: `${totalPnLPct >= 0 ? '+' : ''}${totalPnLPct.toFixed(2)}% return`, color: isUp ? 'text-emerald-400' : 'text-rose-400', icon: isUp ? TrendingUp : TrendingDown },
            { label: "Today's Change",     val: `+${fmtUSD(dayChange)}`, sub: '+0.82% vs yesterday',    color: 'text-emerald-400',    icon: Activity },
            { label: 'Win Rate',           val: `${winners}/${positions.length}`, sub: 'Positions in profit',       color: 'text-amber-400',      icon: Award },
          ].map(c => {
            const Icon = c.icon;
            return (
              <div key={c.label} className="glass rounded-xl p-4 border border-slate-800/60 hover:border-slate-600/60 transition-all group">
                <div className="flex items-center gap-1.5 mb-2">
                  <Icon size={13} className={c.color} />
                  <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">{c.label}</span>
                </div>
                <div className={`font-data font-bold text-lg ${c.color}`}>{c.val}</div>
                <div className="text-[10px] text-slate-600 mt-0.5">{c.sub}</div>
              </div>
            );
          })}
        </div>

        {/* Charts row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
          {/* P&L chart */}
          <div className="lg:col-span-2 glass rounded-2xl border border-slate-800/60 p-5">
            <div className="flex items-center gap-2 mb-4">
              <BarChart2 size={14} className="text-cyan-400" />
              <span className="text-sm font-bold text-slate-200">P&L vs Benchmark (30 days)</span>
            </div>
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={plHistory}>
                  <defs>
                    <linearGradient id="pgPortfolio" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="pgBenchmark" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#475569" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#475569" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="day" hide />
                  <YAxis domain={['auto', 'auto']} hide />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend formatter={(v) => <span className="text-[10px] text-slate-400 font-semibold">{v}</span>} />
                  <Area type="monotone" dataKey="portfolio" stroke="#06b6d4" fill="url(#pgPortfolio)" strokeWidth={1.5} animationDuration={800} />
                  <Area type="monotone" dataKey="benchmark" stroke="#475569" fill="url(#pgBenchmark)" strokeWidth={1} animationDuration={800} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Allocation pie */}
          <div className="glass rounded-2xl border border-slate-800/60 p-5">
            <div className="flex items-center gap-2 mb-4">
              <Zap size={14} className="text-purple-400" />
              <span className="text-sm font-bold text-slate-200">Allocation</span>
            </div>
            <div className="h-40">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" innerRadius={38} outerRadius={60}
                       paddingAngle={3} dataKey="value">
                    {pieData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip content={<PieTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="space-y-1 mt-2">
              {pieData.slice(0, 4).map(p => (
                <div key={p.name} className="flex items-center justify-between text-[10px]">
                  <div className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full" style={{ background: p.color }} />
                    <span className="text-slate-400 font-data font-semibold">{p.name}</span>
                  </div>
                  <span className="text-slate-500">{((p.value / totalValue) * 100).toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Positions table */}
        <div className="glass rounded-2xl border border-slate-800/60 p-5 mb-4">
          <div className="flex items-center gap-2 mb-4">
            <Activity size={14} className="text-amber-400" />
            <span className="text-sm font-bold text-slate-200">Open Positions</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-800/60">
                  {['Ticker', 'Sector', 'Shares', 'Avg Cost', 'Current', 'Value', 'P&L', '%'].map(h => (
                    <th key={h} className="text-left py-2 pr-4 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/40">
                {positions.map(p => {
                  const pnl = (p.currentPrice - p.avgCost) * p.shares;
                  const pnlPct = ((p.currentPrice - p.avgCost) / p.avgCost) * 100;
                  const isWin = pnl >= 0;
                  const marketVal = p.shares * p.currentPrice;
                  return (
                    <tr key={p.ticker} className="hover:bg-slate-800/20 transition-colors">
                      <td className="py-2 pr-4">
                        <span className="font-data font-bold text-sm" style={{ color: p.color }}>{p.ticker}</span>
                      </td>
                      <td className="py-2 pr-4 text-slate-500">{p.sector}</td>
                      <td className="py-2 pr-4 font-data text-slate-300">{p.shares}</td>
                      <td className="py-2 pr-4 font-data text-slate-400">${p.avgCost.toFixed(2)}</td>
                      <td className="py-2 pr-4 font-data text-slate-300">${p.currentPrice.toFixed(2)}</td>
                      <td className="py-2 pr-4 font-data font-bold text-white">{fmtUSD(marketVal)}</td>
                      <td className={`py-2 pr-4 font-data font-bold ${isWin ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {isWin ? '+' : ''}{fmtUSD(pnl)}
                      </td>
                      <td className={`py-2 font-data font-bold ${isWin ? 'text-emerald-400' : 'text-rose-400'}`}>
                        <span className={`px-1.5 py-0.5 rounded-md text-[10px] ${isWin ? 'bg-emerald-500/15' : 'bg-rose-500/15'}`}>
                          {isWin ? '+' : ''}{pnlPct.toFixed(2)}%
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Risk section */}
        <div className="glass rounded-2xl border border-slate-800/60 p-5">
          <div className="flex items-center gap-2 mb-4">
            <ShieldAlert size={14} className="text-rose-400" />
            <span className="text-sm font-bold text-slate-200">AI Risk Summary</span>
            <span className="ml-auto text-[10px] font-bold text-amber-400 bg-amber-500/15 border border-amber-500/25 px-2 py-0.5 rounded-md uppercase tracking-wide">Moderate Risk</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              { label: 'Portfolio Beta', value: '1.28', note: 'vs S&P 500', icon: Activity, color: 'text-amber-400' },
              { label: 'Max Drawdown', value: '-8.4%', note: 'Rolling 30d', icon: TrendingDown, color: 'text-rose-400' },
              { label: 'Sharpe Ratio', value: '1.87', note: 'Risk-adjusted return', icon: Award, color: 'text-emerald-400' },
            ].map(r => {
              const Icon = r.icon;
              return (
                <div key={r.label} className="bg-slate-800/30 rounded-xl p-4 text-center">
                  <Icon size={16} className={`${r.color} mx-auto mb-2`} />
                  <div className={`font-data text-2xl font-black ${r.color}`}>{r.value}</div>
                  <div className="text-xs text-slate-300 font-bold mt-1">{r.label}</div>
                  <div className="text-[10px] text-slate-600 mt-0.5">{r.note}</div>
                </div>
              );
            })}
          </div>
          <p className="text-[11px] text-slate-500 mt-4 leading-relaxed">
            ⚠️ <strong className="text-slate-400">TSLA</strong> is currently in a bearish trend (RSI=28, MACD negative).
            Consider reducing exposure or tightening stop-loss to $235. GME anomaly score is critical (95/100) — monitor closely.
          </p>
        </div>
      </DashboardLayout>
    </RealtimeProvider>
  );
}

/* clean architecture alignment */
