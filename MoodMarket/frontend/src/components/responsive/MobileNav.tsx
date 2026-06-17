import { LeftSidebar } from '../Sidebar/LeftSidebar';
import { X, Star, Settings, LogOut } from 'lucide-react';

interface MobileNavProps {
  isOpen: boolean;
  onClose: () => void;
  selectedTicker: string;
  onTickerSelect: (ticker: string) => void;
}

export function MobileNav({ isOpen, onClose, selectedTicker, onTickerSelect }: MobileNavProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex animate-fade-in">
      {/* Backdrop overlay */}
      <div 
        onClick={onClose} 
        className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm transition-opacity duration-300"
      />

      {/* Drawer panel */}
      <div className="relative flex flex-col w-72 max-w-[85vw] h-full bg-slate-950 border-r border-slate-900 shadow-2xl animate-slide-in-left">
        {/* Header with close button */}
        <div className="flex items-center justify-between p-4 border-b border-slate-900">
          <div className="flex items-center gap-2 text-cyan-400 font-bold uppercase tracking-wider text-xs">
            <Star size={14} className="fill-cyan-400 text-cyan-400" />
            Watchlists
          </div>
          <button 
            onClick={onClose} 
            className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-900"
          >
            <X size={18} />
          </button>
        </div>

        {/* Render Watchlist */}
        <div className="flex-1 overflow-y-auto">
          <LeftSidebar 
            selected={selectedTicker} 
            onSelect={(ticker) => {
              onTickerSelect(ticker);
              onClose();
            }} 
          />
        </div>

        {/* Footer shortcuts */}
        <div className="p-4 border-t border-slate-900 bg-slate-900/10 space-y-3">
          <button className="w-full flex items-center gap-3 px-3 py-2 text-xs font-semibold text-slate-400 hover:text-slate-200 rounded-xl hover:bg-slate-900 transition-colors">
            <Settings size={14} /> Settings
          </button>
          <button className="w-full flex items-center gap-3 px-3 py-2 text-xs font-semibold text-rose-400 hover:text-rose-300 rounded-xl hover:bg-rose-950/20 transition-colors">
            <LogOut size={14} /> Logout
          </button>
        </div>
      </div>
    </div>
  );
}

/* clean architecture alignment */
