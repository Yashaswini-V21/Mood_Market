import { Bell, Settings, User, LogOut, ChevronDown } from 'lucide-react';
import { useState } from 'react';

export function UserMenu() {
  const [open, setOpen] = useState(false);

  return (
    <div className="flex items-center gap-2">
      {/* Notification bell */}
      <button id="notifications-btn" className="btn-icon relative">
        <Bell size={16} />
        <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-amber-400" />
      </button>

      {/* Settings */}
      <button id="settings-btn" className="btn-icon">
        <Settings size={16} />
      </button>

      {/* User menu */}
      <div className="relative">
        <button
          id="user-menu-btn"
          onClick={() => setOpen(o => !o)}
          className="flex items-center gap-2 h-9 pl-2 pr-3 rounded-lg bg-slate-800 border border-slate-700
                     hover:bg-slate-700 transition-colors text-sm text-slate-300"
        >
          <div className="w-6 h-6 rounded-full bg-gradient-to-br from-cyan-500 to-emerald-500 flex items-center justify-center">
            <User size={12} className="text-white" />
          </div>
          <span className="hidden sm:block font-medium">Trader</span>
          <ChevronDown size={13} className="text-slate-500" />
        </button>

        {open && (
          <div className="absolute right-0 top-full mt-1.5 w-44 glass-strong rounded-xl overflow-hidden shadow-glass z-50 animate-slide-up">
            <div className="px-4 py-3 border-b border-slate-700/50">
              <div className="text-sm font-semibold text-slate-200">Yashashwini</div>
              <div className="text-xs text-slate-500">Pro Plan</div>
            </div>
            {[
              { icon: <User size={14} />, label: 'Profile' },
              { icon: <Settings size={14} />, label: 'Settings' },
              { icon: <Bell size={14} />, label: 'Alerts' },
            ].map(item => (
              <button key={item.label}
                className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-300
                           hover:bg-slate-800 transition-colors text-left">
                <span className="text-slate-500">{item.icon}</span>
                {item.label}
              </button>
            ))}
            <div className="border-t border-slate-700/50">
              <button className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-rose-400
                                 hover:bg-rose-500/10 transition-colors text-left">
                <LogOut size={14} />
                Sign out
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
