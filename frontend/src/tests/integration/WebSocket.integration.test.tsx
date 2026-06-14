import { renderHook, act } from '@testing-library/react';
import { useWebSocket } from '../../hooks/useWebSocket';

describe('useWebSocket React Hook', () => {
  let mockWebSocket: any;

  beforeEach(() => {
    mockWebSocket = {
      send: jest.fn(),
      close: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
    };
    // Mock global WebSocket
    global.WebSocket = jest.fn().mockImplementation(() => mockWebSocket) as any;
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('manages connection status and dispatches updates', () => {
    const { result } = renderHook(() => 
      useWebSocket('ws://localhost:8000/ws/price/AAPL')
    );

    // Initial state check
    expect(result.current.status).toBe('connecting');

    // Simulate connection open event
    const openCallback = mockWebSocket.addEventListener.mock.calls.find(
      (call: any) => call[0] === 'open'
    )[1];

    act(() => {
      openCallback();
    });

    expect(result.current.status).toBe('connected');
  });
});
