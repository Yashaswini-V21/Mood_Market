import { useRealtime } from '../context/RealtimeContext';

export function useWebSocket() {
  const { connectionStates, reconnect, isFallback } = useRealtime();

  return {
    connectionStates,
    reconnect,
    isFallback,
    // Helper to check if a specific channel is connected
    isConnected: (channel: string) => connectionStates[channel] === 'connected',
    isConnecting: (channel: string) => connectionStates[channel] === 'connecting',
    isReconnecting: (channel: string) => connectionStates[channel] === 'reconnecting',
    isDisconnected: (channel: string) => connectionStates[channel] === 'disconnected',
  };
}
