import { render, screen, fireEvent } from '@testing-library/react';
import { SignalCard } from '../../components/TradingSignal/SignalCard';
import { useRealtimeData } from '../../hooks/useRealtimeData';

// Mock the useRealtimeData hook
jest.mock('../../hooks/useRealtimeData', () => ({
  useRealtimeData: jest.fn(),
}));

describe('TradingSignal / SignalCard component', () => {
  it('renders consensus trading signals and responds to user interaction', () => {
    // Setup mock return value
    (useRealtimeData as jest.Mock).mockReturnValue({
      priceData: { price: 180.00, change: 1.2, ticker: 'AAPL' },
      sentimentData: { sentiment: 0.75, confidence: 92, ticker: 'AAPL' }
    });

    const mockViewDetails = jest.fn();

    render(<SignalCard ticker="AAPL" onViewDetails={mockViewDetails} />);

    // Verify signal headers
    expect(screen.getByText(/Trading Signal/i)).toBeInTheDocument();
    
    // Check if the signal button registers actions
    const saveButton = screen.getByRole('button', { name: /Save Signal/i });
    expect(saveButton).toBeInTheDocument();
    fireEvent.click(saveButton);
    expect(screen.getByText(/Saved!/i)).toBeInTheDocument();
  });
});

/* clean architecture alignment */
