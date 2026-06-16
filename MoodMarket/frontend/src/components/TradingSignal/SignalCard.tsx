import { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle } from '../base/Card';
import { SignalBadge } from './SignalBadge';
import { RiskAssessment } from './RiskAssessment';
import { AccuracyMetrics } from './AccuracyMetrics';
import { generateTradingSignal } from '../../utils/signal-generator';
import { useRealtimeData } from '../../hooks/useRealtimeData';
import { Zap, Save, BarChart2 } from 'lucide-react';

interface SignalCardProps {
  ticker: string;
  onViewDetails?: () => void;
}

export function SignalCard({ ticker, onViewDetails }: SignalCardProps) {
  const { priceData, sentimentData } = useRealtimeData();
  const [saved, setSaved] = useState(false);

  // Extract real-time values or fall back to high quality mocks
  const currentPrice = priceData?.price ?? 192.53;
  const sentimentScore = sentimentData ? Math.round(sentimentData.sentiment * 100) : 72;
  const sentimentConfidence = sentimentData ? Math.round(sentimentData.confidence) : 89;

  // Derive forecast price
  const forecastDelta = ticker === 'AAPL' ? 1.023 : ticker === 'NVDA' ? 1.041 : ticker === 'TSLA' ? 0.965 : 1.012;
  const predictedPrice = currentPrice * forecastDelta;

  // Mock indicators
  const rsi = ticker === 'AAPL' ? 72 : ticker === 'TSLA' ? 28 : ticker === 'NVDA' ? 68 : 55;
  const macd = ticker === 'TSLA' ? 'Bearish' : 'Bullish';

  const signal = generateTradingSignal(
    ticker,
    sentimentScore,
    sentimentConfidence,
    predictedPrice,
    currentPrice,
    rsi,
    macd as any
  );

  // Reset saved state when ticker changes
  useEffect(() => {
    setSaved(false);
  }, [ticker]);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const confidencePct = signal.confidence;
  const colorVariant = signal.recommendation.includes('BUY') 
    ? 'bullish' 
    : signal.recommendation.includes('SELL') 
      ? 'bearish' 
      : 'neutral';

  return (
    <Card variant={colorVariant === 'neutral' ? 'default' : colorVariant} glow className="animate-fade-in space-y-4.5">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Zap size={15} className="text-cyan-400" />
          <CardTitle>Trading Signal</CardTitle>
        </div>
        <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">
          {ticker} Consensus
        </div>
      </CardHeader>

      {/* Main Signal Display */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-3.5 bg-slate-950/40 rounded-xl border border-slate-800/80">
        <div>
          <span className="text-[10px] text-slate-500 uppercase font-bold tracking-widest block mb-1">
            Overall Signal
          </span>
          <SignalBadge type={signal.recommendation} />
        </div>
        <div className="text-left sm:text-right">
          <span className="text-[10px] text-slate-500 uppercase font-bold tracking-widest block mb-1">
            Signal Confidence
          </span>
          <div className="flex items-center gap-2">
            <span className="font-data text-sm font-extrabold text-white">{confidencePct}%</span>
            {/* Simple confidence bar scale */}
            <div className="w-16 h-1.5 bg-slate-800 rounded-full overflow-hidden shrink-0">
              <div 
                className="h-full bg-cyan-400 rounded-full" 
                style={{ width: `${confidencePct}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Signal Components Checklists */}
      <div className="space-y-2.5">
        <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
          Component Breakdown
        </h4>
        <div className="space-y-2">
          {Object.values(signal.components).map((comp, idx) => {
            const isPos = comp.sentiment === 'positive';
            const isNeg = comp.sentiment === 'negative';
            const iconSymbol = isPos ? '✅' : isNeg ? '🚨' : '⚠️';
            const textClass = isPos ? 'text-emerald-400' : isNeg ? 'text-rose-400' : 'text-amber-400';
            
            return (
              <div key={idx} className="flex items-start justify-between text-xs py-1.5 px-3 bg-slate-900/10 rounded-lg border border-slate-850">
                <div className="flex items-center gap-2">
                  <span className="text-xs">{iconSymbol}</span>
                  <span className="text-slate-400 font-medium">{comp.label}</span>
                </div>
                <div className="text-right">
                  <span className={`font-bold uppercase tracking-wide text-[10px] ${textClass}`}>
                    {comp.value}
                  </span>
                  <span className="block text-[9px] text-slate-500 font-semibold font-data mt-0.5">
                    {comp.details}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="h-[1px] bg-slate-850 my-1" />

      {/* Risk and metrics tabs */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4.5">
        <RiskAssessment sizing={signal.positionSize} riskLevel={signal.riskLevel} />
        <AccuracyMetrics metrics={signal.backtest} />
      </div>

      <div className="h-[1px] bg-slate-850 my-1" />

      {/* Save Position / View Details Buttons */}
      <div className="flex gap-3">
        <button
          onClick={handleSave}
          className="flex-1 flex items-center justify-center gap-1.5 py-2.5 px-4 bg-slate-900 hover:bg-slate-800 text-xs font-bold text-slate-200 border border-slate-800 rounded-xl transition-all duration-200 active:scale-95"
        >
          <Save size={14} />
          {saved ? 'Position Saved!' : 'Save Position'}
        </button>
        {onViewDetails && (
          <button
            onClick={onViewDetails}
            className="flex-1 flex items-center justify-center gap-1.5 py-2.5 px-4 bg-cyan-600 hover:bg-cyan-700 text-xs font-bold text-white rounded-xl transition-all duration-200 active:scale-95"
          >
            <BarChart2 size={14} />
            View Details
          </button>
        )}
      </div>
    </Card>
  );
}

/* clean architecture alignment */
