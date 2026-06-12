import { useWebSocket } from '../hooks/useWebSocket';
import { RefreshCw, Radio, RadioOff } from 'lucide-react';

export function RealtimeStatus() {
  const { connectionStates, reconnect, isFallback } = useWebSocket();
  
  // Determine global connection status based on active channels
  const channels = Object.keys(connectionStates).filter(k => k !== 'global');
  const allConnected = channels.length > 0 && channels.every(c => connectionStates[c] === 'connected');
  const anyConnecting = channels.some(c => connectionStates[c] === 'connecting' || connectionStates[c] === 'reconnecting');

  let statusLabel = 'Live';
  let dotColor = 'bg-emerald-400';
  let badgeStyle = 'text-emerald-400 border-emerald-500/25 bg-emerald-950/20';
  let Icon = Radio;
  let pulse = true;

  if (allConnected) {
    statusLabel = 'Live';
    dotColor = 'bg-emerald-400';
    badgeStyle = 'text-emerald-400 border-emerald-500/20 bg-emerald-950/25';
  } else if (anyConnecting) {
    statusLabel = 'Reconnecting...';
    dotColor = 'bg-amber-400';
    badgeStyle = 'text-amber-400 border-amber-500/20 bg-amber-950/25';
  } else if (isFallback) {
    statusLabel = 'Live updates disabled (Polling)';
    dotColor = 'bg-red-400';
    badgeStyle = 'text-red-400 border-red-500/20 bg-red-950/25';
    Icon = RadioOff;
    pulse = false;
  } else {
    statusLabel = 'Offline';
    dotColor = 'bg-slate-500';
    badgeStyle = 'text-slate-500 border-slate-700 bg-slate-900/30';
    Icon = RadioOff;
    pulse = false;
  }

  return (
    <div className={`flex items-center gap-2.5 px-3 py-1.5 rounded-xl border text-[10px] uppercase font-bold tracking-widest transition-all duration-300 ${badgeStyle}`}>
      <span className="flex items-center gap-1.5">
        <Icon size={12} className="shrink-0" />
        <span className="relative flex h-2 w-2">
          {pulse && (
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${dotColor}`} />
          )}
          <span className={`relative inline-flex rounded-full h-2 w-2 ${dotColor}`} />
        </span>
        <span className="font-sans text-[9px] tracking-wide truncate max-w-[120px] sm:max-w-none">
          {statusLabel}
        </span>
      </span>

      {/* Manual reconnect / refresh button */}
      {(anyConnecting || isFallback || !allConnected) && (
        <button
          onClick={reconnect}
          title="Manual Reconnect"
          className="hover:text-white transition-colors p-0.5 rounded hover:bg-slate-800/40"
        >
          <RefreshCw size={10} className={anyConnecting ? 'animate-spin' : ''} />
        </button>
      )}
    </div>
  );
}
