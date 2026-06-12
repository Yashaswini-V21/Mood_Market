import { useRealtime } from '../context/RealtimeContext';

export function useRealtimeData() {
  const { priceData, sentimentData, anomalies } = useRealtime();

  return {
    priceData,
    sentimentData,
    anomalies,
  };
}
