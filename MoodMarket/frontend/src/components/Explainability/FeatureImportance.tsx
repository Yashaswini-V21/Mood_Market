import { FeatureImportanceItem } from '../../types/explainability';
import { getFeatureDescription } from '../../utils/explainability-formatting';
import { TrendingUp } from 'lucide-react';

interface FeatureImportanceProps {
  features: FeatureImportanceItem[];
}

export function FeatureImportance({ features }: FeatureImportanceProps) {
  // Sort features by importance descending
  const sorted = [...features].sort((a, b) => b.importance - a.importance);

  return (
    <div className="space-y-5 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Ensemble Feature Attribution
          </h4>
          <p className="text-[10px] text-slate-500 mt-0.5">
            Weights assigned by the XGBoost/RandomForest meta-model for feature impact.
          </p>
        </div>
        <span className="flex items-center gap-1 text-[10px] text-emerald-400 font-medium">
          <TrendingUp size={12} /> Model Weights
        </span>
      </div>

      <div className="space-y-4">
        {sorted.map((item, idx) => {
          const isPositive = item.direction === 'positive';
          const pct = Math.round(item.importance * 100);
          const barColor = isPositive ? 'bg-emerald-500' : 'bg-rose-500';
          const borderStyle = isPositive ? 'border-emerald-500/30' : 'border-rose-500/30';
          const textStyle = isPositive ? 'text-emerald-400' : 'text-rose-400';
          
          return (
            <div
              key={idx}
              className={`glass p-3 rounded-xl border ${borderStyle} transition-all duration-300 hover:bg-slate-900/40 relative group`}
            >
              {/* Tooltip / Info */}
              <div className="absolute right-3 top-3 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none">
                <div className="bg-slate-900 border border-slate-800 text-[10px] text-slate-400 px-2.5 py-1 rounded shadow-lg max-w-[200px] text-right">
                  {item.description}
                </div>
              </div>

              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-200">{item.feature}</span>
                  <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold font-data">
                    Value: {item.rawValue}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-bold font-data ${textStyle}`}>
                    {isPositive ? 'Bullish' : 'Bearish'}
                  </span>
                  <span className="font-data text-xs font-bold text-slate-300">
                    {pct}%
                  </span>
                </div>
              </div>

              {/* Progress Bar Container */}
              <div className="h-2 bg-slate-950 rounded-full overflow-hidden border border-slate-850 relative">
                <div
                  className={`h-full rounded-full transition-all duration-1000 ${barColor}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              
              <p className="text-[10px] text-slate-400 mt-2 italic font-medium">
                Insight: {getFeatureDescription(item)}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* clean architecture alignment */
