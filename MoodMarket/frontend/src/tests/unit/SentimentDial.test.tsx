import { render, screen } from '@testing-library/react';
import SentimentDial from '../../components/MainContent/SentimentCard';

// Mock the canvas/dial drawing or child chart elements if necessary
jest.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div className="mock-recharts-container">{children}</div>,
  PieChart: ({ children }: any) => <div className="mock-pie-chart">{children}</div>,
  Pie: () => <div className="mock-pie" />
}));

describe('SentimentDial component rendering', () => {
  it('renders overall sentiment status and label properly', () => {
    // Render the card component with appropriate props
    render(
      <SentimentDial 
        ticker="AAPL" 
        sentimentScore={0.68} 
        confidence={0.85} 
        sentimentLabel="BULLISH" 
      />
    );
    
    // Check ticker text
    expect(screen.getByText(/AAPL/i)).toBeInTheDocument();
    
    // Check score output
    expect(screen.getByText(/68/)).toBeInTheDocument();
    expect(screen.getByText(/BULLISH/i)).toBeInTheDocument();
  });
});

/* clean architecture alignment */
