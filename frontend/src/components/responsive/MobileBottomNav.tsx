import { Brain, TrendingUp, Zap, ShieldAlert } from 'lucide-react';
import { useState } from 'react';

interface MobileBottomNavProps {
  activeSection?: string;
}

export function MobileBottomNav({}: MobileBottomNavProps) {
  const [activeTab, setActiveTab] = useState('sentiment');

  const navItems = [
    { id: 'sentiment', label: 'Sentiment', icon: Brain, targetId: 'sentiment-card' },
    { id: 'forecast', label: 'Forecast', icon: TrendingUp, targetId: 'forecast-card' },
    { id: 'signals', label: 'Signals', icon: Zap, targetId: 'signal-card' },
    { id: 'anomalies', label: 'Alerts', icon: ShieldAlert, targetId: 'anomaly-card' }
  ];

  const handleNavClick = (tabId: string, targetId: string) => {
    setActiveTab(tabId);
    const element = document.getElementById(targetId);
    if (element) {
      // Smooth scroll to the target element with header offset
      const headerOffset = 90;
      const elementPosition = element.getBoundingClientRect().top;
      const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

      window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth'
      });
    }
  };

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 md:hidden bg-slate-950/95 border-t border-slate-900 px-3 py-2 flex items-center justify-around shadow-2xl backdrop-blur-md">
      {navItems.map((item) => {
        const Icon = item.icon;
        const isActive = activeTab === item.id;
        return (
          <button
            key={item.id}
            onClick={() => handleNavClick(item.id, item.targetId)}
            className={`flex flex-col items-center justify-center gap-1.5 py-1 px-3.5 transition-all duration-200 active:scale-95
              ${isActive ? 'text-cyan-400 font-bold' : 'text-slate-500 hover:text-slate-300'}`}
          >
            <Icon size={18} className={isActive ? 'animate-pulse' : ''} />
            <span className="text-[9px] uppercase font-bold tracking-wider font-sans">
              {item.label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
