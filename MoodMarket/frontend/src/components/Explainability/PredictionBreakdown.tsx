import { ExplainabilityData } from '../../types/explainability';
import { ArrowUpRight, ArrowDownRight, RefreshCw, AlertTriangle } from 'lucide-react';

interface PredictionBreakdownProps {
  data: ExplainabilityData;
}

export function PredictionBreakdown({ data }: PredictionBreakdownProps) {
  const isUp = data.predictedDirection === 'UP';
  const isDown = data.predictedDirection === 'DOWN';
  const directionColor = isUp 
    ? 'text-emerald-400 border-emerald-500/30 bg-emerald-950/20' 
    : isDown 
      ? 'text-rose-400 border-rose-500/30 bg-rose-950/20' 
      : 'text-slate-400 border-slate-700 bg-slate-900/30';

  const riskColors = {
    LOW: 'text-emerald-400 border-emerald-500/20 bg-emerald-950/10',
    MODERATE: 'text-amber-400 border-amber-500/20 bg-amber-950/10',
    HIGH: 'text-orange-400 border-orange-500/20 bg-orange-950/10',
    EXTREME: 'text-rose-400 border-rose-500/20 bg-rose-950/10',
  };

  return (
    <div className="space-y-6 animate-fade-in text-slate-300">
      {/* 3-Step Process Flow */}
      <div className="relative border-l border-slate-800/80 ml-3.5 space-y-8 pl-6">
        
        {/* Step 1: Input Features */}
        <div className="relative">
          <div className="absolute -left-9.5 top-0.5 bg-slate-900 border border-slate-700 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-cyan-400 shadow-md">
            1
          </div>
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-200 mb-3">
              Ingested Input Features
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {data.predictionSteps[0]?.items.map((item, idx) => {
                const sColor = item.sentiment === 'positive' 
                  ? 'text-emerald-400 bg-emerald-950/30 border border-emerald-800/30' 
                  : item.sentiment === 'negative' 
                    ? 'text-rose-400 bg-rose-950/30 border border-rose-800/30' 
                    : 'text-slate-400 bg-slate-900/40 border border-slate-850';
                
                return (
                  <div key={idx} className="flex items-center justify-between p-2.5 rounded-xl border border-slate-850 bg-slate-900/10 hover:bg-slate-900/30 transition-all duration-200">
                    <span className="text-[11px] text-slate-400">{item.label}</span>
                    <span className={`text-[10px] font-bold font-data px-2 py-0.5 rounded ${sColor}`}>
                      {item.value}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Step 2: Model Processing */}
        <div className="relative">
          <div className="absolute -left-9.5 top-0.5 bg-slate-900 border border-slate-700 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-cyan-400 shadow-md">
            2
          </div>
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-200 mb-3">
              Model Processing Phase
            </h4>
            <div className="space-y-2">
              {data.predictionSteps[1]?.items.map((item, idx) => (
                <div key={idx} className="flex items-center gap-2.5 text-xs">
                  <RefreshCw size={12} className="text-cyan-400 animate-spin-slow shrink-0" />
                  <span className="text-slate-400 font-medium">{item.label}:</span>
                  <span className="text-slate-200 font-medium">{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Step 3: Final Output Prediction */}
        <div className="relative">
          <div className="absolute -left-9.5 top-0.5 bg-slate-900 border border-slate-750 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-cyan-400 shadow-md">
            3
          </div>
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-200 mb-3">
              Final Output Prediction
            </h4>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              {/* Direction Indicator */}
              <div className={`p-4 rounded-2xl border flex items-center gap-3.5 transition-all duration-300 ${directionColor}`}>
                <div className="w-10 h-10 rounded-xl bg-slate-900/60 border border-slate-800/40 flex items-center justify-center shrink-0 shadow-inner">
                  {isUp ? <ArrowUpRight size={22} /> : isDown ? <ArrowDownRight size={22} /> : <span className="font-bold text-slate-400">→</span>}
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 uppercase tracking-wider block">Forecasted Move</span>
                  <span className="text-sm font-extrabold uppercase font-data">
                    {data.predictedDirection} {isUp ? 'UP ↑' : isDown ? 'DOWN ↓' : 'NEUTRAL'}
                  </span>
                </div>
              </div>

              {/* Price Forecast */}
              <div className="p-4 rounded-2xl border border-slate-800/80 bg-slate-900/20 flex items-center gap-3.5">
                <div className="w-10 h-10 rounded-xl bg-slate-900/60 border border-slate-800/40 flex items-center justify-center shrink-0 shadow-inner text-cyan-400">
                  <span className="font-extrabold text-sm font-data">$</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 uppercase tracking-wider block">Predicted Price (4h)</span>
                  <span className="text-sm font-extrabold font-data text-white">
                    ${data.predictedPrice.toFixed(2)}
                  </span>
                </div>
              </div>

              {/* Confidence Level */}
              <div className="p-4 rounded-2xl border border-slate-800/80 bg-slate-900/20">
                <div className="flex justify-between items-center mb-1.5">
                  <span className="text-[10px] text-slate-500 uppercase tracking-wider">Confidence Level</span>
                  <span className="text-xs font-extrabold font-data text-cyan-400">{data.confidence}%</span>
                </div>
                <div className="h-1.5 bg-slate-950 rounded-full overflow-hidden border border-slate-850">
                  <div
                    className="h-full bg-cyan-400 rounded-full transition-all duration-1000"
                    style={{ width: `${data.confidence}%` }}
                  />
                </div>
              </div>

              {/* Risk Level */}
              <div className={`p-4 rounded-2xl border flex items-center justify-between transition-all duration-300 ${riskColors[data.riskLevel]}`}>
                <div className="flex items-center gap-2">
                  <AlertTriangle size={15} />
                  <span className="text-[10px] uppercase tracking-wider font-semibold">Forecast Risk Level</span>
                </div>
                <span className="text-xs font-extrabold font-data">{data.riskLevel}</span>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

/* clean architecture alignment */
