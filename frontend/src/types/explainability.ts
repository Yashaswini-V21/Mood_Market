export interface SHAPToken {
  token:       string;
  shapValue:   number;  // negative = bearish, positive = bullish
  model:       'FinBERT' | 'DistilBERT';
  position:    number;  // index in sentence
}

export interface AttentionStep {
  timestamp:  string;
  stepIndex:  number;  // 0 = most recent, 71 = oldest
  attention:  number;  // 0–1
  event?:     string;  // optional annotation
  price?:     number;
  volume?:    number;
}

export interface FeatureImportanceItem {
  feature:      string;
  importance:   number;  // 0–1
  direction:    'positive' | 'negative';
  rawValue:     string;  // human-readable value
  description:  string;
}

export interface PredictionStep {
  step:     number;
  title:    string;
  items:    { label: string; value: string; sentiment: 'positive' | 'negative' | 'neutral' }[];
}

export interface ExplainabilityData {
  ticker:             string;
  shapTokens:         SHAPToken[];
  attentionSteps:     AttentionStep[];
  featureImportance:  FeatureImportanceItem[];
  predictionSteps:    PredictionStep[];
  predictedDirection: 'UP' | 'DOWN' | 'NEUTRAL';
  predictedPrice:     number;
  currentPrice:       number;
  confidence:         number;
  riskLevel:          'LOW' | 'MODERATE' | 'HIGH' | 'EXTREME';
}

export interface SHAPData {
  tokens:     SHAPToken[];
  maxAbsVal:  number;
  modelName:  'FinBERT' | 'DistilBERT' | 'Ensemble';
}

export interface AttentionData {
  steps:     AttentionStep[];
  maxWeight: number;
}
