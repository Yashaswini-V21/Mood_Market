import { ReactNode } from 'react';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { MobileLayout } from './MobileLayout';
import { TabletLayout } from './TabletLayout';
import { DesktopLayout } from './DesktopLayout';

interface DashboardLayoutProps {
  children: ReactNode;
  selectedTicker: string;
  onTickerSelect: (ticker: string) => void;
}

export function DashboardLayout({ children, selectedTicker, onTickerSelect }: DashboardLayoutProps) {
  const { isMobile, isTablet } = useMediaQuery();

  if (isMobile) {
    return (
      <MobileLayout selectedTicker={selectedTicker} onTickerSelect={onTickerSelect}>
        {children}
      </MobileLayout>
    );
  }

  if (isTablet) {
    return (
      <TabletLayout selectedTicker={selectedTicker} onTickerSelect={onTickerSelect}>
        {children}
      </TabletLayout>
    );
  }

  return (
    <DesktopLayout selectedTicker={selectedTicker} onTickerSelect={onTickerSelect}>
      {children}
    </DesktopLayout>
  );
}

/* clean architecture alignment */
