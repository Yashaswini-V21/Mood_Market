import { ReactNode } from 'react';
import { Header } from '../components/Header/Header';
import { LeftSidebar } from '../components/Sidebar/LeftSidebar';
import { RightSidebar } from '../components/Sidebar/RightSidebar';

interface TabletLayoutProps {
  children: ReactNode;
  selectedTicker: string;
  onTickerSelect: (ticker: string) => void;
}

export function TabletLayout({ children, selectedTicker, onTickerSelect }: TabletLayoutProps) {
  return (
    <div className="min-h-screen bg-slate-950 font-sans text-slate-200">
      {/* Header */}
      <Header onTickerSelect={onTickerSelect} />

      {/* Body container */}
      <div className="pt-[84px] h-screen flex overflow-hidden">
        {/* Left Sidebar Watchlist (narrow width w-48) */}
        <aside className="hidden md:flex flex-col w-52 shrink-0 h-full border-r border-slate-900 bg-slate-950/20">
          <LeftSidebar selected={selectedTicker} onSelect={onTickerSelect} />
        </aside>

        {/* Central main page scroll area */}
        <main className="flex-1 overflow-y-auto px-5 py-5 space-y-6">
          {/* Main cards */}
          <div>
            {children}
          </div>

          {/* Right sidebar content stacked below main cards */}
          <div className="border-t border-slate-900 pt-6 mt-6">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-4">
              Market Summary
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 p-4 rounded-2xl bg-slate-900/10 border border-slate-900">
              <RightSidebar />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
