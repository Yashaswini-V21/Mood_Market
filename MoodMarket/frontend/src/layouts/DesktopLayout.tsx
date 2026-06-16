import { ReactNode } from 'react';
import { Header } from '../components/Header/Header';
import { LeftSidebar } from '../components/Sidebar/LeftSidebar';
import { RightSidebar } from '../components/Sidebar/RightSidebar';

interface DesktopLayoutProps {
  children: ReactNode;
  selectedTicker: string;
  onTickerSelect: (ticker: string) => void;
}

export function DesktopLayout({ children, selectedTicker, onTickerSelect }: DesktopLayoutProps) {
  return (
    <div className="min-h-screen bg-slate-950 font-sans text-slate-200">
      {/* Header */}
      <Header onTickerSelect={onTickerSelect} />

      {/* Grid wrapper */}
      <div className="pt-[84px] h-screen flex overflow-hidden">
        {/* Left Watchlist Sidebar */}
        <aside className="hidden lg:flex flex-col w-60 shrink-0 h-full border-r border-slate-900 bg-slate-950/20">
          <LeftSidebar selected={selectedTicker} onSelect={onTickerSelect} />
        </aside>

        {/* Central main dashboard page */}
        <main className="flex-1 overflow-y-auto px-6 py-5">
          {children}
        </main>

        {/* Right Stats Sidebar */}
        <aside className="hidden xl:flex flex-col w-56 shrink-0 h-full border-l border-slate-900 bg-slate-950/20">
          <RightSidebar />
        </aside>
      </div>
    </div>
  );
}

/* clean architecture alignment */
