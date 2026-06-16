import { BacktestingData } from '../../types/trading';
import { Award, TrendingUp, TrendingDown, Layers } from 'lucide-react';

interface AccuracyMetricsProps {
  metrics: BacktestingData;
}

export function AccuracyMetrics({ metrics }: AccuracyMetricsProps) {
  return (
    <div className="space-y-4">
      <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
        Historical Backtesting Stats
      </h4>

      <div className="grid grid-cols-2 gap-3.5">
        {/* Win Rate */}
        <div className="glass p-3 rounded-xl border border-slate-800/60 bg-slate-900/10 flex items-center gap-3">
          <Award size={18} className="text-amber-400 shrink-0" />
          <div>
            <span className="text-[9px] text-slate-500 uppercase font-bold tracking-wider block">Win Rate</span>
            <span className="font-data text-sm font-extrabold text-white">
              {metrics.winRate}%
            </span>
          </div>
        </div>

        {/* Sharpe Ratio */}
        <div className="glass p-3 rounded-xl border border-slate-800/60 bg-slate-900/10 flex items-center gap-3">
          <Layers size={18} className="text-cyan-400 shrink-0" />
          <div>
            <span className="text-[9px] text-slate-500 uppercase font-bold tracking-wider block">Sharpe Ratio</span>
            <span className="font-data text-sm font-extrabold text-white">
              {metrics.sharpeRatio.toFixed(2)}
            </span>
          </div>
        </div>
      </div>

      {/* Average profit/loss when right/wrong */}
      <div className="grid grid-cols-2 gap-3.5 text-xs">
        <div className="flex items-center gap-2 text-emerald-400 bg-emerald-950/10 border border-emerald-900/20 px-3 py-2 rounded-xl">
          <TrendingUp size={14} className="shrink-0" />
          <div>
            <span className="text-[8px] text-slate-500 uppercase font-bold tracking-widest block">Avg profit</span>
            <span className="font-data font-bold">+{metrics.avgProfit.toFixed(1)}%</span>
          </div>
        </div>
        <div className="flex items-center gap-2 text-rose-400 bg-rose-950/10 border border-rose-900/20 px-3 py-2 rounded-xl">
          <TrendingDown size={14} className="shrink-0" />
          <div>
            <span className="text-[8px] text-slate-500 uppercase font-bold tracking-widest block">Avg loss</span>
            <span className="font-data font-bold">{metrics.avgLoss.toFixed(1)}%</span>
          </div>
        </div>
      </div>

      {/* Streaks */}
      <div className="flex justify-between items-center text-[10px] text-slate-400 bg-slate-950/40 p-2.5 rounded-xl border border-slate-850">
        <span>Max consecutive wins: <strong className="text-emerald-400 font-data">{metrics.maxConsecutiveWins}</strong></span>
        <span className="w-[1px] h-3 bg-slate-800" />
        <span>Max consecutive losses: <strong className="text-rose-400 font-data">{metrics.maxConsecutiveLosses}</strong></span>
      </div>
    </div>
  );
}

/* clean architecture alignment */
