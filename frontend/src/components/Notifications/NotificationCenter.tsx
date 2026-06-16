import { useState, useCallback } from 'react';
import { Bell, X, CheckCheck, AlertTriangle, TrendingUp, Brain, Zap, Activity } from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────
export type AlertSeverity = 'critical' | 'high' | 'medium' | 'low';
export type AlertCategory = 'anomaly' | 'hype' | 'signal' | 'sentiment' | 'system';

export interface AppAlert {
  id: string;
  category: AlertCategory;
  severity: AlertSeverity;
  title: string;
  body: string;
  ticker?: string;
  timestamp: Date;
  read: boolean;
}

// ─── Seed alerts ──────────────────────────────────────────────────────────────
const INITIAL_ALERTS: AppAlert[] = [
  { id: '1', category: 'hype', severity: 'critical', title: 'HYPE STORM: GME', body: 'Reddit mentions +340% above 30d baseline. Z-Score 8.7σ. Coordinated pump detected.', ticker: 'GME', timestamp: new Date(Date.now() - 2 * 60000), read: false },
  { id: '2', category: 'anomaly', severity: 'high', title: 'Anomaly: TSLA', body: '3/5 detectors triggered. Z-Score 4.2σ, Isolation Forest: non-linear pattern, EWMA regime shift.', ticker: 'TSLA', timestamp: new Date(Date.now() - 8 * 60000), read: false },
  { id: '3', category: 'signal', severity: 'high', title: 'STRONG BUY: NVDA', body: 'Synthesizer agent: 4/5 agents aligned. Sentiment 81/100, RSI 68, Forecast UP 79%.', ticker: 'NVDA', timestamp: new Date(Date.now() - 15 * 60000), read: false },
  { id: '4', category: 'sentiment', severity: 'medium', title: 'Sentiment Shift: AAPL', body: 'FinBERT ensemble: 72/100 BULLISH. Key tokens: earnings (+0.28), beats (+0.35).', ticker: 'AAPL', timestamp: new Date(Date.now() - 32 * 60000), read: true },
  { id: '5', category: 'system', severity: 'low', title: 'Model Recalibrated', body: 'Informer temperature scaling updated. ECE: 0.023. Accuracy maintained at 65.2%.', timestamp: new Date(Date.now() - 60 * 60000), read: true },
  { id: '6', category: 'hype', severity: 'high', title: 'Volume Spike: MSTR', body: 'Twitter + Reddit correlation 0.91. Mentions/hr: 890. Alert level: ELEVATED.', ticker: 'MSTR', timestamp: new Date(Date.now() - 90 * 60000), read: true },
];

// ─── Config ────────────────────────────────────────────────────────────────────
const CATEGORY_CONFIG: Record<AlertCategory, { icon: React.ElementType; color: string; bg: string; label: string }> = {
  anomaly:   { icon: AlertTriangle, color: 'text-rose-400',   bg: 'bg-rose-500/15 border-rose-500/25',   label: 'Anomaly' },
  hype:      { icon: Zap,           color: 'text-amber-400',  bg: 'bg-amber-500/15 border-amber-500/25', label: 'Hype Storm' },
  signal:    { icon: TrendingUp,    color: 'text-emerald-400',bg: 'bg-emerald-500/15 border-emerald-500/25',label:'Signal' },
  sentiment: { icon: Brain,         color: 'text-cyan-400',   bg: 'bg-cyan-500/15 border-cyan-500/25',   label: 'Sentiment' },
  system:    { icon: Activity,      color: 'text-slate-400',  bg: 'bg-slate-500/15 border-slate-500/25', label: 'System' },
};

const SEVERITY_DOT: Record<AlertSeverity, string> = {
  critical: 'bg-rose-500 animate-pulse',
  high:     'bg-amber-500',
  medium:   'bg-cyan-500',
  low:      'bg-slate-600',
};

const fmt = (d: Date) => {
  const diff = Math.round((Date.now() - d.getTime()) / 60000);
  if (diff < 1) return 'just now';
  if (diff < 60) return `${diff}m ago`;
  return `${Math.round(diff / 60)}h ago`;
};

// ─── Alert Item ────────────────────────────────────────────────────────────────
function AlertItem({ alert, onRead, onDismiss }: {
  alert: AppAlert;
  onRead: (id: string) => void;
  onDismiss: (id: string) => void;
}) {
  const cfg = CATEGORY_CONFIG[alert.category];
  const Icon = cfg.icon;

  return (
    <div
      className={`relative flex gap-3 p-3.5 rounded-xl border transition-all duration-200
                  hover:border-slate-600/60 cursor-pointer group
                  ${alert.read ? 'opacity-60' : 'opacity-100'}
                  ${cfg.bg}`}
      onClick={() => onRead(alert.id)}
    >
      {/* Severity dot */}
      <span className={`absolute top-3.5 right-3.5 w-1.5 h-1.5 rounded-full shrink-0 ${SEVERITY_DOT[alert.severity]}`} />

      {/* Icon */}
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
        alert.category === 'anomaly' ? 'bg-rose-500/20' :
        alert.category === 'hype' ? 'bg-amber-500/20' :
        alert.category === 'signal' ? 'bg-emerald-500/20' :
        alert.category === 'sentiment' ? 'bg-cyan-500/20' : 'bg-slate-500/20'
      }`}>
        <Icon size={14} className={cfg.color} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 pr-4">
        <div className="flex items-center gap-2 mb-0.5">
          <span className={`text-[10px] font-bold uppercase tracking-widest ${cfg.color}`}>{cfg.label}</span>
          {alert.ticker && (
            <span className="text-[10px] font-data font-bold text-slate-400 bg-slate-800/60 px-1.5 py-0.5 rounded-md">
              {alert.ticker}
            </span>
          )}
          {!alert.read && (
            <span className="ml-auto w-2 h-2 rounded-full bg-cyan-400 shrink-0" />
          )}
        </div>
        <div className="text-xs font-bold text-slate-200 mb-0.5">{alert.title}</div>
        <div className="text-[11px] text-slate-500 leading-snug line-clamp-2">{alert.body}</div>
        <div className="text-[10px] text-slate-600 mt-1">{fmt(alert.timestamp)}</div>
      </div>

      {/* Dismiss */}
      <button
        onClick={e => { e.stopPropagation(); onDismiss(alert.id); }}
        className="absolute top-2 right-6 opacity-0 group-hover:opacity-100 transition-opacity
                   w-5 h-5 rounded-md flex items-center justify-center
                   hover:bg-slate-700 text-slate-500 hover:text-slate-300"
      >
        <X size={11} />
      </button>
    </div>
  );
}

// ─── Notification Center ───────────────────────────────────────────────────────
interface NotificationCenterProps {
  open: boolean;
  onClose: () => void;
}

export function NotificationCenter({ open, onClose }: NotificationCenterProps) {
  const [alerts, setAlerts] = useState<AppAlert[]>(INITIAL_ALERTS);
  const [filter, setFilter] = useState<AlertCategory | 'all'>('all');

  const unread = alerts.filter(a => !a.read).length;

  const handleRead = useCallback((id: string) => {
    setAlerts(prev => prev.map(a => a.id === id ? { ...a, read: true } : a));
  }, []);

  const handleDismiss = useCallback((id: string) => {
    setAlerts(prev => prev.filter(a => a.id !== id));
  }, []);

  const markAllRead = () => setAlerts(prev => prev.map(a => ({ ...a, read: true })));

  const filtered = filter === 'all' ? alerts : alerts.filter(a => a.category === filter);

  if (!open) return null;

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-40 bg-black/30" onClick={onClose} />

      {/* Panel */}
      <div
        className="fixed top-[84px] right-4 z-50 w-96 max-h-[calc(100vh-100px)] flex flex-col
                   glass-strong rounded-2xl border border-slate-700/60 shadow-2xl shadow-black/60
                   animate-slide-in-right overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3.5 border-b border-slate-800/60">
          <div className="flex items-center gap-2">
            <Bell size={14} className="text-amber-400" />
            <span className="font-bold text-white text-sm">Notification Center</span>
            {unread > 0 && (
              <span className="flex items-center justify-center w-5 h-5 rounded-full bg-rose-500 text-[10px] font-bold text-white">
                {unread}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {unread > 0 && (
              <button
                id="mark-all-read-btn"
                onClick={markAllRead}
                className="flex items-center gap-1 text-[10px] text-cyan-400 hover:text-cyan-300 font-semibold transition-colors"
              >
                <CheckCheck size={11} /> All read
              </button>
            )}
            <button
              id="close-notifications-btn"
              onClick={onClose}
              className="w-7 h-7 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700
                         flex items-center justify-center text-slate-400 hover:text-slate-200 transition-all"
            >
              <X size={13} />
            </button>
          </div>
        </div>

        {/* Filter tabs */}
        <div className="flex gap-1 px-3 py-2 border-b border-slate-800/40 overflow-x-auto">
          {(['all', 'anomaly', 'hype', 'signal', 'sentiment', 'system'] as const).map(cat => {
            const cfg = cat === 'all' ? null : CATEGORY_CONFIG[cat];
            const count = cat === 'all' ? alerts.length : alerts.filter(a => a.category === cat).length;
            return (
              <button
                key={cat}
                onClick={() => setFilter(cat)}
                className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[10px] font-bold
                            transition-all whitespace-nowrap shrink-0 ${
                  filter === cat
                    ? 'bg-slate-700 text-white border border-slate-600'
                    : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                {cfg && <cfg.icon size={10} className={cfg.color} />}
                {cat === 'all' ? 'All' : cfg?.label} ({count})
              </button>
            );
          })}
        </div>

        {/* Alert list */}
        <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2">
          {filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-slate-600">
              <Bell size={24} className="mb-2 opacity-40" />
              <span className="text-xs font-semibold">No alerts in this category</span>
            </div>
          ) : (
            filtered.map(alert => (
              <AlertItem
                key={alert.id}
                alert={alert}
                onRead={handleRead}
                onDismiss={handleDismiss}
              />
            ))
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2.5 border-t border-slate-800/60 flex items-center justify-between">
          <span className="text-[10px] text-slate-600">{filtered.length} alerts · {unread} unread</span>
          <div className="flex items-center gap-1 text-[10px] text-slate-600">
            <Activity size={9} />
            <span>7-method ensemble</span>
          </div>
        </div>
      </div>
    </>
  );
}

// ─── Bell Button for Header ────────────────────────────────────────────────────
export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [alerts] = useState<AppAlert[]>(INITIAL_ALERTS);
  const unread = alerts.filter(a => !a.read).length;

  return (
    <>
      <NotificationCenter open={open} onClose={() => setOpen(false)} />
      <button
        id="notification-bell-btn"
        onClick={() => setOpen(o => !o)}
        className="relative w-9 h-9 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700
                   flex items-center justify-center text-slate-400 hover:text-slate-200 transition-all"
        title="Notifications"
      >
        <Bell size={15} className={unread > 0 ? 'text-amber-400' : ''} />
        {unread > 0 && (
          <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-rose-500 border border-slate-950
                           text-[9px] font-bold text-white flex items-center justify-center">
            {unread}
          </span>
        )}
      </button>
    </>
  );
}
