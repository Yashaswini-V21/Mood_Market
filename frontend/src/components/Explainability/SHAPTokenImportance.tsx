import { SHAPToken } from '../../types/explainability';
import { formatSHAPValue, generateSHAPSummary } from '../../utils/explainability-formatting';
import { Info } from 'lucide-react';

interface SHAPTokenImportanceProps {
  tokens: SHAPToken[];
}

export function SHAPTokenImportance({ tokens }: SHAPTokenImportanceProps) {
  // Sort tokens to show most important ones
  const sortedTokens = [...tokens].sort((a, b) => Math.abs(b.shapValue) - Math.abs(a.shapValue));
  const summary = generateSHAPSummary(tokens);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Explanation Banner */}
      <div className="glass p-4 rounded-xl border border-slate-800/60 flex items-start gap-3 bg-slate-900/20">
        <Info size={16} className="text-cyan-400 mt-0.5 shrink-0" />
        <div className="space-y-1">
          <h4 className="text-xs font-semibold text-slate-200">SHAP Token Explanations</h4>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            SHAP (SHapley Additive exPlanations) attributes a weight to each word.
            <span className="text-emerald-400 font-semibold ml-1">Positive values (+)</span> indicate words driving a bullish forecast, while
            <span className="text-rose-400 font-semibold ml-1">Negative values (-)</span> represent bearish drag.
          </p>
        </div>
      </div>

      {/* Highlighter Text Render */}
      <div className="glass p-5 rounded-xl border border-slate-800/80 bg-slate-950/40">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3.5">
          Analyzed Headline Context
        </h4>
        <div className="flex flex-wrap gap-2 leading-relaxed">
          {tokens.map((t, idx) => {
            const isPositive = t.shapValue > 0;
            const absVal = Math.min(Math.abs(t.shapValue) * 3.5, 0.9); // scale opacity, cap at 0.9
            const bgColor = isPositive 
              ? `rgba(16, 185, 129, ${absVal})` 
              : `rgba(244, 63, 94, ${absVal})`;
            const textColor = absVal > 0.4 ? 'text-slate-950' : 'text-slate-200';
            
            return (
              <div
                key={idx}
                className={`group relative px-2.5 py-1 rounded text-xs font-medium cursor-help transition-all duration-200 hover:scale-105 ${textColor}`}
                style={{ backgroundColor: bgColor }}
              >
                {t.token}
                
                {/* Custom premium tooltip */}
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-36 hidden group-hover:block z-50 pointer-events-none">
                  <div className="bg-slate-900 border border-slate-800 text-[10px] text-white p-2 rounded-lg shadow-xl text-center space-y-0.5 backdrop-blur-md">
                    <div className="font-bold text-slate-300">{t.model}</div>
                    <div className="font-data text-xs" style={{ color: isPositive ? '#10B981' : '#F43F5E' }}>
                      SHAP: {formatSHAPValue(t.shapValue)}
                    </div>
                  </div>
                  <div className="w-2 h-2 bg-slate-900 border-r border-b border-slate-800 rotate-45 mx-auto -mt-1.5" />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Top SHAP Drivers Bar Chart */}
      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-4">
          Top Word Drivers
        </h4>
        <div className="space-y-3">
          {sortedTokens.slice(0, 5).map((t, idx) => {
            const isPositive = t.shapValue > 0;
            const percentage = Math.min(Math.abs(t.shapValue) * 100, 100);
            
            return (
              <div key={idx} className="flex items-center gap-3">
                <span className="w-20 text-xs font-bold text-slate-300 truncate font-data">{t.token}</span>
                <span className="text-[10px] text-slate-500 font-data w-8 shrink-0">{t.model}</span>
                
                {/* Horizontal double-sided bar layout */}
                <div className="flex-1 h-5 bg-slate-900/60 rounded overflow-hidden relative border border-slate-800/40">
                  <div className="absolute inset-0 flex items-center justify-between px-2.5 z-10 pointer-events-none">
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider">
                      {isPositive ? 'Bullish' : 'Bearish'}
                    </span>
                    <span className="font-data font-bold text-[10px]" style={{ color: isPositive ? '#10B981' : '#F43F5E' }}>
                      {formatSHAPValue(t.shapValue)}
                    </span>
                  </div>
                  <div
                    className={`h-full rounded-r transition-all duration-1000 ${
                      isPositive ? 'bg-emerald-500/25 border-r border-emerald-500' : 'bg-rose-500/25 border-r border-rose-500'
                    }`}
                    style={{ width: `${percentage}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Summary insights footer */}
      <div className="text-xs text-slate-400 italic font-medium pt-2 border-t border-slate-800/40">
        Insight: {summary}
      </div>
    </div>
  );
}
