import { ShieldAlert, Clock, ExternalLink, CheckCircle } from 'lucide-react';
import { Card, CardHeader, CardTitle } from '../base/Card';
import { AlertBadge } from '../base/Badge';
import { Button } from '../base/Button';
import { clsx } from 'clsx';

interface AnomalyCardProps { 
  ticker: string;
  onViewAnalysis?: () => void;
}

const METHODS = [
  { name: 'Z-Score',         triggered: true,  score: 4.2 },
  { name: 'Isolation Forest',triggered: true,  score: 3.8 },
  { name: 'Autoencoder',     triggered: false, score: 1.1 },
  { name: 'EWMA',            triggered: true,  score: 2.9 },
  { name: 'MAD',             triggered: false, score: 0.8 },
];

export function AnomalyCard({ ticker, onViewAnalysis }: AnomalyCardProps) {
  const triggered = METHODS.filter(m => m.triggered).length;
  const total     = METHODS.length;
  const ensemble  = triggered >= 3 ? 'HIGH' : triggered >= 2 ? 'MEDIUM' : 'LOW';

  return (
    <Card className="animate-fade-in">
      <CardHeader>
        <div className="flex items-center gap-2">
          <ShieldAlert size={15} className="text-rose-400" />
          <CardTitle>Anomaly Details</CardTitle>
        </div>
        <AlertBadge level={ensemble as any} />
      </CardHeader>

      {/* Timestamp */}
      <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-3">
        <Clock size={11} />
        <span>Detected at 01:32:14 UTC — Ensemble vote: {triggered}/{total}</span>
      </div>

      {/* Method list */}
      <div className="space-y-2 mb-4">
        {METHODS.map(m => (
          <div key={m.name} className="flex items-center gap-3">
            <div className={clsx(
              'w-1.5 h-1.5 rounded-full shrink-0',
              m.triggered ? 'bg-rose-400' : 'bg-slate-600'
            )} />
            <span className={clsx(
              'text-xs flex-1',
              m.triggered ? 'text-slate-200' : 'text-slate-600'
            )}>{m.name}</span>

            {/* Score bar */}
            <div className="w-20 h-1.5 bg-slate-800 rounded-full overflow-hidden">
              <div
                className={clsx(
                  'h-full rounded-full transition-all duration-700',
                  m.triggered ? 'bg-rose-500' : 'bg-slate-700'
                )}
                style={{ width: `${Math.min(m.score / 5 * 100, 100)}%` }}
              />
            </div>

            <span className={clsx(
              'font-data text-xs w-8 text-right',
              m.triggered ? 'text-rose-400' : 'text-slate-600'
            )}>{m.score.toFixed(1)}σ</span>

            {m.triggered
              ? <ShieldAlert size={12} className="text-rose-400 shrink-0" />
              : <CheckCircle size={12} className="text-slate-700 shrink-0" />
            }
          </div>
        ))}
      </div>

      {/* Explanation */}
      <div className="text-xs text-slate-500 bg-slate-800/40 rounded-lg p-3 mb-3 leading-relaxed">
        {triggered} of {total} detectors flagged <strong className="text-slate-300">{ticker}</strong> as anomalous.
        Z-Score peaked at 4.2σ (99.99% CI). EWMA detected a volatility regime shift. Recommend reducing position size.
      </div>

      <Button 
        onClick={onViewAnalysis}
        variant="ghost" 
        size="sm" 
        className="w-full gap-1.5 text-cyan-400 border-cyan-500/20 hover:bg-cyan-500/10"
      >
        <ExternalLink size={13} /> View Full Analysis
      </Button>
    </Card>
  );
}

/* clean architecture alignment */
