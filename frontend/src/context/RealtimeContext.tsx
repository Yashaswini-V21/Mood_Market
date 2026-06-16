import { createContext, useContext, useState, useEffect, useRef, ReactNode } from 'react';
import { MoodMarketWSClient, ConnectionState } from '../utils/websocket-client';

interface RealtimeContextType {
  connectionStates: Record<string, ConnectionState>;
  priceData: { price: number; change: number; changePct: number; timestamp: string } | null;
  sentimentData: { sentiment: number; confidence: number; updatedAt: string } | null;
  anomalies: Array<{ ticker: string; anomaly_type: string; confidence: number; explanation: string; timestamp: string }>;
  isFallback: boolean;
  reconnect: () => void;
}

const RealtimeContext = createContext<RealtimeContextType | null>(null);

export function useRealtime() {
  const ctx = useContext(RealtimeContext);
  if (!ctx) throw new Error('useRealtime must be used inside a RealtimeProvider');
  return ctx;
}

interface RealtimeProviderProps {
  children: ReactNode;
  ticker: string;
}

export function RealtimeProvider({ children, ticker }: RealtimeProviderProps) {
  const [connectionStates, setConnectionStates] = useState<Record<string, ConnectionState>>({
    'global': 'disconnected',
    'anomaly': 'disconnected'
  });
  
  const [priceData, setPriceData] = useState<RealtimeContextType['priceData']>(null);
  const [sentimentData, setSentimentData] = useState<RealtimeContextType['sentimentData']>(null);
  const [anomalies, setAnomalies] = useState<RealtimeContextType['anomalies']>([]);
  const [isFallback, setIsFallback] = useState(false);

  const wsClientRef = useRef<MoodMarketWSClient | null>(null);
  const fallbackTimerRef = useRef<number | null>(null);

  // Check if we need fallback polling (if any core ticker channel is disconnected)
  const sentimentChannel = `sentiment:${ticker}`;
  const priceChannel = `price:${ticker}`;
  const isWSDown = 
    connectionStates[sentimentChannel] === 'disconnected' || 
    connectionStates[priceChannel] === 'disconnected';

  // Toggle HTTP polling fallback
  useEffect(() => {
    if (isWSDown) {
      if (!fallbackTimerRef.current) {
        console.log('WS connection lost or down. Starting HTTP polling fallback...');
        setIsFallback(true);
        triggerFallbackFetch();
        fallbackTimerRef.current = window.setInterval(triggerFallbackFetch, 10000); // 10s poll
      }
    } else {
      if (fallbackTimerRef.current) {
        console.log('WS reconnected. Stopping HTTP polling fallback.');
        window.clearInterval(fallbackTimerRef.current);
        fallbackTimerRef.current = null;
        setIsFallback(false);
      }
    }
  }, [isWSDown, ticker]);

  // Fetch from fallback REST routes
  async function triggerFallbackFetch() {
    const cleanTicker = ticker.toUpperCase().trim();
    const headers = {
      'Authorization': 'Bearer moodmarket_secret_api_key_2026',
    };

    // 1. Fetch fallback price
    try {
      const res = await fetch(`http://localhost:8000/api/v1/fallback/price/${cleanTicker}`, { headers });
      if (res.ok) {
        const body = await res.json();
        setPriceData({
          price: body.price,
          change: body.change,
          changePct: body.change_pct,
          timestamp: new Date().toISOString()
        });
      }
    } catch (err) {
      console.warn('Fallback price fetch failed:', err);
    }

    // 2. Fetch fallback sentiment
    try {
      const res = await fetch(`http://localhost:8000/api/v1/fallback/sentiment/${cleanTicker}`, { headers });
      if (res.ok) {
        const body = await res.json();
        setSentimentData({
          sentiment: body.sentiment,
          confidence: body.confidence * 100, // standard 0-100 scale
          updatedAt: new Date().toISOString()
        });
      }
    } catch (err) {
      console.warn('Fallback sentiment fetch failed:', err);
    }

    // 3. Fetch fallback anomaly details
    try {
      const res = await fetch(`http://localhost:8000/api/v1/anomaly/${cleanTicker}`, { headers });
      if (res.ok) {
        const body = await res.json();
        if (body.anomaly_detected) {
          // Push anomaly alert if detected
          setAnomalies(prev => {
            const exists = prev.some(a => a.ticker === cleanTicker && Math.abs(new Date(a.timestamp).getTime() - Date.now()) < 30000);
            if (exists) return prev;
            return [{
              ticker: cleanTicker,
              anomaly_type: body.alert_level,
              confidence: body.confidence * 100,
              explanation: `Volume anomaly detected: ${body.alert_level} severity.`,
              timestamp: new Date().toISOString()
            }, ...prev].slice(0, 20);
          });
        }
      }
    } catch (err) {
      console.warn('Fallback anomaly fetch failed:', err);
    }
  };

  // Setup WS Client
  useEffect(() => {
    const wsUrl = 'ws://localhost:8000';
    const httpUrl = 'http://localhost:8000';

    const client = new MoodMarketWSClient({
      onMessage: (channel, data) => {
        if (channel.startsWith('price:')) {
          setPriceData({
            price: data.price,
            change: data.change,
            changePct: data.change_pct,
            timestamp: data.timestamp
          });
        } else if (channel.startsWith('sentiment:')) {
          setSentimentData({
            sentiment: data.sentiment,
            confidence: data.confidence * 100, // Map from 0-1 to 0-100
            updatedAt: data.updated_at
          });
        } else if (channel === 'anomaly') {
          // Add to anomaly alerts log
          setAnomalies(prev => [data, ...prev].slice(0, 20));
        }
      },
      onStateChange: (channel, state) => {
        setConnectionStates(prev => ({
          ...prev,
          [channel]: state
        }));
      }
    }, wsUrl, httpUrl);

    wsClientRef.current = client;
    client.initialize(ticker);

    return () => {
      client.destroy();
      if (fallbackTimerRef.current) {
        window.clearInterval(fallbackTimerRef.current);
      }
    };
  }, []);

  // Update WS ticker subscriptions when selected ticker changes
  useEffect(() => {
    if (wsClientRef.current) {
      wsClientRef.current.changeTicker(ticker);
      if (isWSDown) {
        triggerFallbackFetch();
      }
    }
  }, [ticker]);

  const reconnect = () => {
    if (wsClientRef.current) {
      console.log('Manually triggering reconnect...');
      wsClientRef.current.initialize(ticker);
    }
  };

  return (
    <RealtimeContext.Provider value={{
      connectionStates,
      priceData,
      sentimentData,
      anomalies,
      isFallback,
      reconnect
    }}>
      {children}
    </RealtimeContext.Provider>
  );
}
