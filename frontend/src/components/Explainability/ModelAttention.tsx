import { AttentionStep } from '../../types/explainability';
import { formatAttentionWeight } from '../../utils/explainability-formatting';
import { Activity, Clock } from 'lucide-react';

interface ModelAttentionProps {
  steps: AttentionStep[];
}

export function ModelAttention({ steps }: ModelAttentionProps) {
  const maxWeight = Math.max(...steps.map(s => s.attention), 0.001);

  // Filter significant events that have annotations or high attention
  const highAttentionEvents = [...steps]
    .filter(s => s.event || s.attention > 0.4)
    .sort((a, b) => b.attention - a.attention);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Heatmap Section */}
      <div className="glass p-5 rounded-xl border border-slate-800/80 bg-slate-950/40">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Informer Time-Series Attention Map
            </h4>
            <p className="text-[10px] text-slate-500 mt-1">
              Relative weights assigned to the 72-hour lookback window (left = oldest, right = most recent).
            </p>
          </div>
          <span className="flex items-center gap-1 text-[10px] text-cyan-400 font-medium">
            <Activity size={12} /> Live Focus
          </span>
        </div>

        {/* Heatmap Grid */}
        <div className="grid grid-cols-12 gap-1.5 p-1 bg-slate-900/40 rounded-lg border border-slate-800/40">
          {steps.map((step) => {
            const normalized = step.attention / maxWeight;
            // Map to colors: slate-800 for near zero, glowing cyan/blue for high attention
            const glowOpacity = normalized * 0.9;
            const bgStyle = normalized > 0.05
              ? { 
                  backgroundColor: `rgba(6, 182, 212, ${normalized})`,
                  boxShadow: normalized > 0.7 ? `0 0 12px rgba(6, 182, 212, ${glowOpacity})` : 'none'
                }
              : {};

            return (
              <div
                key={step.stepIndex}
                className={`group relative aspect-square rounded-md transition-all duration-300 hover:scale-110 cursor-help border border-slate-800/40
                  ${normalized <= 0.05 ? 'bg-slate-800/40 hover:bg-slate-700/60' : ''}`}
                style={bgStyle}
              >
                {/* Cell tooltip */}
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 hidden group-hover:block z-50 pointer-events-none">
                  <div className="bg-slate-900 border border-slate-800 text-[10px] text-white p-2.5 rounded-lg shadow-xl space-y-1 backdrop-blur-md">
                    <div className="flex items-center gap-1 font-bold text-slate-400">
                      <Clock size={10} /> {step.timestamp}
                    </div>
                    <div className="font-data text-xs text-cyan-400 font-bold">
                      Weight: {formatAttentionWeight(step.attention)}
                    </div>
                    {step.price && (
                      <div className="text-slate-300 font-data">
                        Price: ${step.price.toFixed(2)} {step.volume ? `| Vol: ${step.volume}` : ''}
                      </div>
                    )}
                    {step.event && (
                      <div className="text-amber-400 font-medium mt-1 border-t border-slate-800/60 pt-1">
                        ★ {step.event}
                      </div>
                    )}
                  </div>
                  <div className="w-2 h-2 bg-slate-900 border-r border-b border-slate-800 rotate-45 mx-auto -mt-1.5" />
                </div>
              </div>
            );
          })}
        </div>

        {/* Legend */}
        <div className="flex justify-between items-center mt-3 text-[10px] text-slate-500 px-1">
          <span>Oldest (t - 72h)</span>
          <div className="flex items-center gap-1.5">
            <span>Low attention</span>
            <div className="w-16 h-2 rounded bg-gradient-to-r from-slate-800/40 via-cyan-700/50 to-cyan-400" />
            <span>High attention</span>
          </div>
          <span>Recent (t - 1h)</span>
        </div>
      </div>

      {/* Critical Events Timeline */}
      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3.5">
          Timeline of Aligned Key Events
        </h4>
        <div className="space-y-2.5">
          {highAttentionEvents.slice(0, 4).map((step, idx) => {
            const barPct = Math.round((step.attention / maxWeight) * 100);
            
            return (
              <div key={idx} className="flex items-center gap-3 glass p-2.5 rounded-xl border border-slate-800/50 bg-slate-900/10">
                <div className="w-20 shrink-0 text-left">
                  <span className="text-[10px] text-slate-500 block">{step.timestamp}</span>
                  <span className="font-data text-xs font-bold text-slate-300">
                    {step.price ? `$${step.price.toFixed(2)}` : 'N/A'}
                  </span>
                </div>
                
                {/* Spark / bar of attention weight */}
                <div className="w-12 shrink-0">
                  <div className="text-[9px] text-slate-500 mb-0.5">Attention</div>
                  <div className="h-1.5 bg-slate-850 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-cyan-400 rounded-full"
                      style={{ width: `${barPct}%` }}
                    />
                  </div>
                </div>

                {/* Event or annotation */}
                <div className="flex-1 min-w-0">
                  <span className="text-xs font-semibold text-slate-200 block truncate">
                    {step.event || 'Substantial attention spike detected'}
                  </span>
                  <span className="text-[10px] text-slate-400 truncate block">
                    No anomaly flagged but high structural model focus.
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
