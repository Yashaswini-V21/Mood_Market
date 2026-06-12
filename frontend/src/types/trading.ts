export type SignalType = 'STRONG BUY' | 'BUY' | 'BUY WITH CAUTION' | 'NEUTRAL' | 'SELL' | 'STRONG SELL';

export interface SignalComponent {
  label: string;
  value: string;
  sentiment: 'positive' | 'negative' | 'neutral';
  details?: string;
}

export interface PositionSizingData {
  recommendedSize: number; // percentage (0 to 3)
  rule: string;
  stopLoss: number;
  takeProfit: number;
}

export interface BacktestingData {
  winRate: number; // 0-100
  avgProfit: number; // percentage
  avgLoss: number; // percentage
  maxConsecutiveWins: number;
  maxConsecutiveLosses: number;
  sharpeRatio: number;
}

export interface Signal {
  ticker: string;
  recommendation: SignalType;
  confidence: number; // 0-100
  riskLevel: 'LOW' | 'MODERATE' | 'HIGH' | 'EXTREME';
  components: {
    sentiment: SignalComponent;
    technical: SignalComponent;
    forecast: SignalComponent;
    risk: SignalComponent;
  };
  positionSize: PositionSizingData;
  backtest: BacktestingData;
  timestamp: string;
}
