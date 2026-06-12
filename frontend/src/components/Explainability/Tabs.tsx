import { ReactNode } from 'react';

interface TabItem {
  id: string;
  label: string;
  icon?: ReactNode;
}

interface TabsProps {
  tabs: TabItem[];
  activeTab: string;
  onChange: (id: string) => void;
}

export function Tabs({ tabs, activeTab, onChange }: TabsProps) {
  return (
    <div className="flex border-b border-slate-800/80 mb-6 overflow-x-auto scrollbar-thin">
      {tabs.map((tab) => {
        const isActive = tab.id === activeTab;
        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={`flex items-center gap-2 px-5 py-3 text-xs font-semibold uppercase tracking-wider whitespace-nowrap transition-all duration-300 border-b-2 -mb-[2px]
              ${isActive 
                ? 'border-cyan-400 text-cyan-400 bg-cyan-950/20 font-bold' 
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
              }`}
          >
            {tab.icon && <span className="shrink-0">{tab.icon}</span>}
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
