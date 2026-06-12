import { SHAPToken, FeatureImportanceItem } from '../types/explainability';

/**
 * Format SHAP value to percentage contribution
 */
export function formatSHAPValue(val: number): string {
  const sign = val >= 0 ? '+' : '';
  return `${sign}${(val * 100).toFixed(1)}%`;
}

/**
 * Format attention weight as standard float string
 */
export function formatAttentionWeight(val: number): string {
  return val.toFixed(4);
}

/**
 * Generate a descriptive text summarizing the SHAP contribution and overall sentiment
 */
export function generateSHAPSummary(tokens: SHAPToken[]): string {
  if (tokens.length === 0) return 'No text tokens analyzed.';
  
  const positive = tokens.filter(t => t.shapValue > 0).sort((a, b) => b.shapValue - a.shapValue);
  const negative = tokens.filter(t => t.shapValue < 0).sort((a, b) => a.shapValue - b.shapValue);
  
  let desc = '';
  if (positive.length > 0) {
    desc += `Bullish drive led by "${positive[0].token}" (${formatSHAPValue(positive[0].shapValue)}). `;
  }
  if (negative.length > 0) {
    desc += `Bearish headwind from "${negative[0].token}" (${formatSHAPValue(negative[0].shapValue)}).`;
  }
  
  return desc || 'Sentiment is well-balanced across all tokens.';
}

/**
 * Generate human-readable descriptions of feature importance impact
 */
export function getFeatureDescription(item: FeatureImportanceItem): string {
  const dirText = item.direction === 'positive' ? 'bullish' : 'bearish';
  return `"${item.feature}" had a ${dirText} impact of ${(item.importance * 100).toFixed(0)}% (value: ${item.rawValue}).`;
}
