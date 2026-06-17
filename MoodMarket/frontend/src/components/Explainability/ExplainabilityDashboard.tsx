import { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle } from '../base/Card';
import { Tabs } from './Tabs';
import { SHAPTokenImportance } from './SHAPTokenImportance';
import { ModelAttention } from './ModelAttention';
import { FeatureImportance } from './FeatureImportance';
import { PredictionBreakdown } from './PredictionBreakdown';
import { ExplainabilityData } from '../../types/explainability';
import { Sparkles, Brain, Eye, HelpCircle } from 'lucide-react';

interface ExplainabilityDashboardProps {
  ticker: string;
}

export function ExplainabilityDashboard({ ticker }: ExplainabilityDashboardProps) {
  const [activeTab, setActiveTab] = useState('shap');
  const [data, setData] = useState<ExplainabilityData | null>(null);
  const [loading, setLoading] = useState(false);

  // Generate realistic data for the ticker
  useEffect(() => {
    setLoading(true);
    const timer = setTimeout(() => {
      const isBullish = ticker === 'AAPL' || ticker === 'NVDA' || Math.random() > 0.4;
      const price = ticker === 'AAPL' ? 192.53 : ticker === 'NVDA' ? 122.50 : ticker === 'TSLA' ? 178.20 : 250.00;
      const predictedPrice = isBullish ? price * (1 + Math.random() * 0.04) : price * (1 - Math.random() * 0.04);
      
      const mockData: ExplainabilityData = {
        ticker,
        shapTokens: [
          { token: 'Earnings', shapValue: isBullish ? 0.28 : -0.15, model: 'FinBERT' as const, position: 0 },
          { token: 'surge', shapValue: isBullish ? 0.35 : 0.05, model: 'FinBERT' as const, position: 1 },
          { token: 'beats', shapValue: isBullish ? 0.42 : 0.12, model: 'DistilBERT' as const, position: 2 },
          { token: 'estimates', shapValue: 0.08, model: 'DistilBERT' as const, position: 3 },
          { token: 'but', shapValue: -0.11, model: 'FinBERT' as const, position: 4 },
          { token: 'guidance', shapValue: isBullish ? -0.05 : -0.32, model: 'FinBERT' as const, position: 5 },
          { token: 'guidance-concern', shapValue: isBullish ? -0.02 : -0.45, model: 'DistilBERT' as const, position: 6 },
          { token: 'cautious', shapValue: isBullish ? -0.18 : -0.58, model: 'DistilBERT' as const, position: 7 }
        ].slice(0, 8),
        attentionSteps: Array.from({ length: 24 }).map((_, i) => {
          const hour = 24 - i;
          let event: string | undefined;
          if (i === 4) event = 'Price spike +250%';
          if (i === 12) event = 'Support level test';
          if (i === 18) event = 'Initial move';
          
          return {
            timestamp: `${hour}h ago`,
            stepIndex: i,
            attention: Math.random() * (i % 5 === 0 ? 0.9 : 0.3),
            event,
            price: price * (1 - (i * 0.002)),
            volume: 10000 + Math.round(Math.random() * 50000)
          };
        }),
        featureImportance: [
          { feature: 'Sentiment Score', importance: 0.42, direction: isBullish ? 'positive' : 'negative', rawValue: '72 / 100', description: 'Overall ensemble sentiment rating' },
          { feature: 'Price Momentum (4h)', importance: 0.26, direction: isBullish ? 'positive' : 'negative', rawValue: '+1.23%', description: 'Exponential moving average trend direction' },
          { feature: 'Hype Volume Volatility', importance: 0.18, direction: 'positive', rawValue: 'High (+340%)', description: 'Reddit/Twitter mention spike intensity' },
          { feature: 'Technical RSI', importance: 0.14, direction: isBullish ? 'positive' : 'negative', rawValue: '72 (Overbought)', description: 'Relative Strength Index' }
        ],
        predictionSteps: [
          {
            step: 1,
            title: 'Input Features Ingestion',
            items: [
              { label: 'Ensemble Sentiment', value: isBullish ? '0.72 (BULLISH)' : '0.28 (BEARISH)', sentiment: isBullish ? 'positive' : 'negative' },
              { label: 'Price Change', value: isBullish ? '+1.23% (POSITIVE)' : '-2.45% (NEGATIVE)', sentiment: isBullish ? 'positive' : 'negative' },
              { label: 'Volume Momentum', value: '+340% (SPIKE)', sentiment: 'positive' },
              { label: 'RSI Indicator', value: '72 (OVERBOUGHT)', sentiment: 'neutral' }
            ]
          },
          {
            step: 2,
            title: 'Attention Processing',
            items: [
              { label: 'Temporal Attention', value: '72h Lookback weights loaded', sentiment: 'neutral' as const },
              { label: 'SHAP Sentiment Attribution', value: '8 active tokens parsed', sentiment: 'neutral' as const },
              { label: 'Ensemble Vote Allocation', value: '3 model consensus reached', sentiment: 'neutral' as const }
            ]
          }
        ],

        predictedDirection: isBullish ? 'UP' : 'DOWN',
        predictedPrice,
        currentPrice: price,
        confidence: Math.round(55 + Math.random() * 25),
        riskLevel: isBullish ? 'MODERATE' : 'HIGH'
      };
      
      setData(mockData);
      setLoading(false);
    }, 450);

    return () => clearTimeout(timer);
  }, [ticker]);

  const tabs = [
    { id: 'shap', label: 'SHAP values', icon: <Sparkles size={13} /> },
    { id: 'attention', label: 'Model Attention', icon: <Brain size={13} /> },
    { id: 'features', label: 'Feature Importance', icon: <Eye size={13} /> },
    { id: 'breakdown', label: 'Prediction Breakdown', icon: <HelpCircle size={13} /> }
  ];

  return (
    <Card className="col-span-1 md:col-span-2 border border-slate-800/80 bg-slate-900/40 mt-5">
      <CardHeader className="flex flex-row items-center justify-between pb-2 border-b border-slate-800/50">
        <div className="flex items-center gap-2.5">
          <Brain size={16} className="text-cyan-400" />
          <CardTitle>Model Explainability & Forecast Diagnostics</CardTitle>
        </div>
        <div className="text-[11px] text-slate-500 font-bold uppercase tracking-widest bg-slate-950/40 px-2.5 py-1 rounded-md border border-slate-850">
          Ensemble Diagnostics: <span className="text-cyan-400 font-data font-bold">{ticker}</span>
        </div>
      </CardHeader>

      <div className="p-4">
        {/* Navigation Tabs */}
        <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

        {/* Tab Panel Content */}
        {loading ? (
          <div className="h-64 flex flex-col items-center justify-center gap-3">
            <div className="w-8 h-8 rounded-full border-2 border-t-cyan-400 border-r-transparent border-b-transparent border-l-transparent animate-spin" />
            <span className="text-xs text-slate-500 uppercase tracking-widest font-bold">Computing Explanations...</span>
          </div>
        ) : data ? (
          <div className="transition-all duration-300">
            {activeTab === 'shap' && <SHAPTokenImportance tokens={data.shapTokens} />}
            {activeTab === 'attention' && <ModelAttention steps={data.attentionSteps} />}
            {activeTab === 'features' && <FeatureImportance features={data.featureImportance} />}
            {activeTab === 'breakdown' && <PredictionBreakdown data={data} />}
          </div>
        ) : (
          <div className="h-64 flex items-center justify-center text-xs text-slate-500 font-bold uppercase tracking-widest">
            Failed to load model diagnostics.
          </div>
        )}
      </div>
    </Card>
  );
}

/* clean architecture alignment */
