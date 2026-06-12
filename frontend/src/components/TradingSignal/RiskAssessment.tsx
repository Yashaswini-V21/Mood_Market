import { PositionSizingData } from '../../types/trading';
import { AlertTriangle, Percent, ArrowUpRight, ArrowDownRight } from 'lucide-react';

interface RiskAssessmentProps {
  sizing: PositionSizingData;
  riskLevel: 'LOW' | 'MODERATE' | 'HIGH' | 'EXTREME';
}

export function RiskAssessment({ sizing, riskLevel }: RiskAssessmentProps) {
  const isWait = sizing.recommendedSize === 0;

  const riskColors = {
    LOW: 'text-emerald-400 bg-emerald-950/20 border-emerald-500/20',
    MODERATE: 'text-amber-400 bg-amber-950/20 border-amber-500/20',
    HIGH: 'text-orange-400 bg-orange-950/20 border-orange-500/20',
    EXTREME: 'text-rose-400 bg-rose-950/20 border-rose-500/20',
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
          Risk & Sizing Parameters
        </h4>
        <span className={`text-[9px] font-extrabold uppercase px-2 py-0.5 rounded border ${riskColors[riskLevel]}`}>
          {riskLevel} RISK
        </span>
      </div>

      <div className="grid grid-cols-3 gap-3">
        {/* Portfolio Sizing */}
        <div className="glass p-3 rounded-xl border border-slate-800/80 bg-slate-950/40 text-center flex flex-col items-center justify-center">
          <Percent size={14} className="text-cyan-400 mb-1.5" />
          <span className="text-[9px] text-slate-500 uppercase font-bold tracking-wider">Allocation</span>
          <span className="font-data text-sm font-bold text-white mt-0.5">
            {isWait ? '0% (WAIT)' : `${sizing.recommendedSize}%`}
          </span>
        </div>

        {/* Stop Loss */}
        <div className="glass p-3 rounded-xl border border-slate-800/80 bg-slate-950/40 text-center flex flex-col items-center justify-center">
          <ArrowDownRight size={14} className="text-rose-400 mb-1.5" />
          <span className="text-[9px] text-slate-500 uppercase font-bold tracking-wider">Stop Loss</span>
          <span className="font-data text-sm font-bold text-rose-400 mt-0.5">
            ${sizing.stopLoss.toFixed(2)}
          </span>
        </div>

        {/* Take Profit */}
        <div className="glass p-3 rounded-xl border border-slate-800/80 bg-slate-950/40 text-center flex flex-col items-center justify-center">
          <ArrowUpRight size={14} className="text-emerald-400 mb-1.5" />
          <span className="text-[9px] text-slate-500 uppercase font-bold tracking-wider">Take Profit</span>
          <span className="font-data text-sm font-bold text-emerald-400 mt-0.5">
            ${sizing.takeProfit.toFixed(2)}
          </span>
        </div>
      </div>

      {/* Sizing description banner */}
      <div className="glass px-3.5 py-2.5 rounded-xl border border-slate-850 bg-slate-900/10 flex items-start gap-2.5">
        <AlertTriangle size={14} className="text-slate-400 mt-0.5 shrink-0" />
        <p className="text-[10px] text-slate-400 leading-normal">
          <span className="font-bold text-slate-300 uppercase block mb-0.5">Sizing Strategy</span>
          {sizing.rule} Stop-loss and Take-profit markers are dynamically calculated using historical price ranges.
        </p>
      </div>
    </div>
  );
}
