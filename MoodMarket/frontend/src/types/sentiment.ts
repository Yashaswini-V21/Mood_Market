export interface ModelScore {
  name: 'FinBERT' | 'DistilBERT' | 'RoBERTa';
  score: number;       // 0–1
  weight: number;      // weight in ensemble
  tokenCount: number;
}

export interface SentimentWord {
  text:      string;
  frequency: number;   // 1–100
  sentiment: 'positive' | 'negative' | 'neutral';
  shap:      number;   // SHAP contribution
}

export interface SentimentSource {
  label:      string;
  percentage: number;
  count:      number;
  color:      string;
}

export interface SentimentDataPoint {
  timestamp: string; // ISO string
  value:     number; // 0–100
  volume:    number;
}

export interface SentimentData {
  ticker:      string;
  score:       number;       // 0–100 ensemble score
  confidence:  number;       // 0–100
  label:       'BULLISH' | 'NEUTRAL' | 'BEARISH';
  models:      ModelScore[];
  sources:     SentimentSource[];
  words:       SentimentWord[];
  trend:       SentimentDataPoint[]; // 24h history
  lastUpdated: string; // ISO
}

export type SentimentRange = 'extreme-bearish' | 'bearish' | 'neutral' | 'bullish' | 'extreme-bullish';

export const getSentimentRange = (score: number): SentimentRange => {
  if (score < 20) return 'extreme-bearish';
  if (score < 40) return 'bearish';
  if (score < 60) return 'neutral';
  if (score < 80) return 'bullish';
  return 'extreme-bullish';
};

export const getSentimentColor = (score: number): string => {
  if (score < 30) return '#991B1B';
  if (score < 50) return '#D97706';
  if (score < 70) return '#FBBF24';
  if (score < 85) return '#84CC16';
  return '#10B981';
};

export const getSentimentLabel = (score: number): string => {
  if (score < 30) return 'BEARISH';
  if (score < 45) return 'SLIGHTLY BEARISH';
  if (score < 55) return 'NEUTRAL';
  if (score < 70) return 'SLIGHTLY BULLISH';
  return 'BULLISH';
};

/* clean architecture alignment */
