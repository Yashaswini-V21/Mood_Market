import { ReactNode, useState } from 'react';
import { MobileHeader } from '../components/responsive/MobileHeader';
import { MobileNav } from '../components/responsive/MobileNav';
import { MobileBottomNav } from '../components/responsive/MobileBottomNav';
import { MobileWatchlist } from '../components/responsive/MobileWatchlist';

interface MobileLayoutProps {
  children: ReactNode;
  selectedTicker: string;
  onTickerSelect: (ticker: string) => void;
}

export function MobileLayout({ children, selectedTicker, onTickerSelect }: MobileLayoutProps) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-950 font-sans text-slate-200 flex flex-col pb-16">
      {/* Mobile Top Header */}
      <MobileHeader 
        isOpen={isMenuOpen} 
        onMenuToggle={() => setIsMenuOpen(prev => !prev)} 
        onTickerSelect={onTickerSelect}
      />

      {/* Slide-out Menu Watchlist Drawer */}
      <MobileNav 
        isOpen={isMenuOpen} 
        onClose={() => setIsMenuOpen(false)} 
        selectedTicker={selectedTicker}
        onTickerSelect={onTickerSelect}
      />

      {/* Main Content Area */}
      <div className="pt-[84px] flex-1 flex flex-col">
        {/* Horizontal scroll Watchlist at top of feed */}
        <MobileWatchlist 
          selectedTicker={selectedTicker} 
          onTickerSelect={onTickerSelect} 
        />

        <main className="flex-1 px-4 py-4 space-y-4">
          {children}
        </main>
      </div>

      {/* Mobile Bottom Navigation Bar */}
      <MobileBottomNav />
    </div>
  );
}
