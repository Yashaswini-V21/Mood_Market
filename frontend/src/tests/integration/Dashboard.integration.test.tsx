import { render, screen } from '@testing-library/react';
import Dashboard from '../../pages/Dashboard';
import { RealtimeProvider } from '../../context/RealtimeContext';

// Mock recharts canvas rendering
jest.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div className="mock-recharts-container">{children}</div>,
  AreaChart: ({ children }: any) => <div className="mock-area-chart">{children}</div>,
  Area: () => <div className="mock-area" />,
  XAxis: () => <div className="mock-xaxis" />,
  YAxis: () => <div className="mock-yaxis" />,
  Tooltip: () => <div className="mock-tooltip" />,
  PieChart: ({ children }: any) => <div className="mock-pie-chart">{children}</div>,
  Pie: () => <div className="mock-pie" />,
  Cell: () => <div className="mock-cell" />
}));

describe('Dashboard Integration with RealtimeContext', () => {
  it('renders dashboard with sidebar and main content areas', () => {
    render(
      <RealtimeProvider>
        <Dashboard />
      </RealtimeProvider>
    );

    // Verify header status is rendered
    expect(screen.getByText(/MoodMarket/i)).toBeInTheDocument();
    
    // Check if watchlist and main content are rendered
    expect(screen.getByText(/Watchlist/i)).toBeInTheDocument();
  });
});
