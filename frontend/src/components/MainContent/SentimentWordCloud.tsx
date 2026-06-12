import { SentimentWord } from '../../types/sentiment';
import { formatSHAPValue } from '../../utils/explainability-formatting';

interface SentimentWordCloudProps {
  words: SentimentWord[];
}

export function SentimentWordCloud({ words }: SentimentWordCloudProps) {
  // Sort words by frequency to render nicely
  const sortedWords = [...words].sort((a, b) => b.frequency - a.frequency);

  return (
    <div className="glass p-4 rounded-xl border border-slate-800/80 bg-slate-950/40">
      <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3.5">
        Sentiment Word Cloud
      </h4>
      
      {/* Cloud flexbox grid */}
      <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-3 p-3 bg-slate-900/20 rounded-lg min-h-36">
        {sortedWords.map((w, idx) => {
          // Compute size based on frequency
          const baseSize = 10;
          const scale = 0.15;
          const fontSize = baseSize + w.frequency * scale;
          
          // Color based on sentiment
          let color = 'text-slate-400';
          let borderStyle = 'border-slate-800/40';
          if (w.sentiment === 'positive') {
            color = 'text-emerald-400 hover:text-emerald-300';
            borderStyle = 'border-emerald-900/30';
          } else if (w.sentiment === 'negative') {
            color = 'text-rose-400 hover:text-rose-300';
            borderStyle = 'border-rose-900/30';
          }

          const isPositive = w.shap > 0;

          return (
            <div
              key={idx}
              className={`group relative px-2.5 py-1 rounded-md border bg-slate-900/40 cursor-help transition-all duration-200 hover:scale-110 hover:bg-slate-900/80 ${borderStyle} ${color}`}
              style={{ fontSize: `${fontSize}px` }}
            >
              {w.text}

              {/* Word tooltip showing SHAP */}
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-32 hidden group-hover:block z-50 pointer-events-none">
                <div className="bg-slate-900 border border-slate-800 text-[10px] text-white p-2 rounded-lg shadow-xl text-center space-y-0.5 backdrop-blur-md">
                  <div className="font-bold text-slate-400 uppercase tracking-wide">{w.sentiment}</div>
                  <div className="font-data text-xs font-bold" style={{ color: isPositive ? '#10B981' : '#F43F5E' }}>
                    SHAP: {formatSHAPValue(w.shap)}
                  </div>
                </div>
                <div className="w-2 h-2 bg-slate-900 border-r border-b border-slate-800 rotate-45 mx-auto -mt-1.5" />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
