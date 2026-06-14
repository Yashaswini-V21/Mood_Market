import { generateTradingSignal } from '../../utils/signal-generator';

describe('generateTradingSignal utility', () => {
  it('should generate a STRONG BUY signal for bullish inputs', () => {
    const signal = generateTradingSignal(
      'AAPL',
      85, // sentimentScore
      90, // sentimentConfidence
      200.00, // predictedPrice
      180.00, // currentPrice
      50, // rsiValue
      'Bullish' // macdTrend
    );

    expect(signal.ticker).toBe('AAPL');
    expect(signal.recommendation).toBe('STRONG BUY');
    expect(signal.riskLevel).toBe('LOW');
    expect(signal.positionSize.recommendedSize).toBe(3);
    expect(signal.positionSize.stopLoss).toBe(180.00 * 0.95); // 171
    expect(signal.positionSize.takeProfit).toBe(180.00 * 1.10); // 198
  });

  it('should generate a NEUTRAL signal for conflicting indicators', () => {
    const signal = generateTradingSignal(
      'AAPL',
      50, // sentimentScore
      50, // sentimentConfidence
      180.10, // predictedPrice
      180.00, // currentPrice
      50, // rsiValue
      'Neutral' // macdTrend
    );

    expect(signal.recommendation).toBe('NEUTRAL');
    expect(signal.positionSize.recommendedSize).toBe(0);
  });
});
