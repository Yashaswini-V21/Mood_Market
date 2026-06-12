import { useState, useEffect } from 'react';
import { Brain, RefreshCw, Clock, ChevronDown, ChevronUp } from 'lucide-react';
import { Card, CardHeader, CardTitle } from '../base/Card';
import { Badge, ConfidenceBadge } from '../base/Badge';
import { SentimentData, getSentimentRange, getSentimentColor, getSentimentLabel } from '../../types/sentiment';
import { SentimentTrendChart } from './SentimentTrendChart';
import { SentimentWordCloud } from './SentimentWordCloud';

interface SentimentCardProps {
  ticker: string;
  isExpanded?: boolean;
  onExpandToggle?: () => void;
}

export function SentimentCard({ ticker, isExpanded: externalExpanded, onExpandToggle }: SentimentCardProps) {
  const [localExpanded, setLocalExpanded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<SentimentData | null>(null);
  const [isHovered, setIsHovered] = useState(false);

  const isExpanded = externalExpanded !== undefined ? externalExpanded : localExpanded;
  const toggleExpanded = () => {
    if (onExpandToggle) {
      onExpandToggle();
    } else {
      setLocalExpanded(prev => !prev);
    }
  };

  // Generate realistic data for the selected ticker
  useEffect(() => {
    setLoading(true);
    const timer = setTimeout(() => {
      const isBullish = ticker === 'AAPL' || ticker === 'NVDA' || Math.random() > 0.45;
      const score = isBullish ? Math.round(65 + Math.random() * 25) : Math.round(15 + Math.random() * 25);
      const confidence = Math.round(75 + Math.random() * 20);

      const generateTrend = () => {
        const list = [];
        const now = new Date();
        for (let i = 24; i >= 0; i--) {
          const t = new Date(now.getTime() - i * 3600 * 1000);
          list.push({
            timestamp: t.toISOString(),
            value: Math.max(0, Math.min(100, score + Math.round((Math.random() - 0.5) * 15))),
            volume: 100 + Math.round(Math.random() * 900),
          });
        }
        return list;
      };

      const mockData: SentimentData = {
        ticker,
        score,
        confidence,
        label: score >= 60 ? 'BULLISH' : score >= 40 ? 'NEUTRAL' : 'BEARISH',
        models: [
          { name: 'FinBERT', score: isBullish ? 0.62 : 0.28, weight: 0.45, tokenCount: 45 },
          { name: 'DistilBERT', score: isBullish ? 0.58 : 0.32, weight: 0.35, tokenCount: 35 },
          { name: 'RoBERTa', score: isBullish ? 0.60 : 0.30, weight: 0.20, tokenCount: 20 },
        ],
        sources: [
          { label: 'News', percentage: 45, count: 120, color: '#06b6d4' },
          { label: 'Reddit', percentage: 35, count: 95, color: '#f97316' },
          { label: 'Twitter', percentage: 20, count: 54, color: '#3b82f6' },
        ],
        words: [
          { text: 'earnings', frequency: 80, sentiment: isBullish ? 'positive' : 'negative', shap: isBullish ? 0.28 : -0.15 },
          { text: 'beats', frequency: 72, sentiment: isBullish ? 'positive' : 'neutral', shap: isBullish ? 0.35 : 0.05 },
          { text: 'guidance', frequency: 65, sentiment: isBullish ? 'neutral' : 'negative', shap: isBullish ? -0.05 : -0.32 },
          { text: 'concern', frequency: 58, sentiment: 'negative', shap: -0.45 },
          { text: 'cautious', frequency: 45, sentiment: 'negative', shap: -0.58 },
          { text: 'bull', frequency: 42, sentiment: 'positive', shap: 0.48 },
          { text: 'tanked', frequency: 38, sentiment: 'negative', shap: -0.62 },
          { text: 'surge', frequency: 30, sentiment: 'positive', shap: 0.52 },
        ],
        trend: generateTrend(),
        lastUpdated: new Date().toISOString(),
      };

      setData(mockData);
      setLoading(false);
    }, 400);

    return () => clearTimeout(timer);
  }, [ticker]);

  if (!data) return null;

  const sentimentColor = getSentimentColor(data.score);
  const range = getSentimentRange(data.score);
  const colorVariant = data.score >= 60 ? 'bullish' : data.score >= 40 ? 'neutral' : 'bearish';

  // Needle calculations: 270 degree arc from -135deg to +135deg
  const needleAngle = -135 + (data.score / 100) * 270;

  // Thicker confidence ring: scaled thickness based on confidence (between 2px and 8px)
  const confidenceRingThickness = 2 + (data.confidence / 100) * 6;

  // Active track gradient selection
  const getGradientId = (score: number) => {
    if (score <= 33) return 'bearishGrad';
    if (score <= 66) return 'neutralGrad';
    return 'bullishGrad';
  };

  return (
    <Card 
      variant={colorVariant === 'neutral' ? 'default' : colorVariant} 
      glow 
      className={`relative col-span-1 md:col-span-2 p-5 border border-slate-800/80 bg-slate-900/40 transition-all duration-500 overflow-hidden ${
        isExpanded ? 'shadow-2xl shadow-cyan-950/20' : ''
      }`}
    >
      <CardHeader>
        <div className="flex items-center gap-2">
          <Brain size={16} className="text-cyan-400" />
          <CardTitle>Interactive Sentiment Dial</CardTitle>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={colorVariant}>{getSentimentLabel(data.score)}</Badge>
          <button 
            id="refresh-sentiment-btn"
            onClick={() => {
              setLoading(true);
              setTimeout(() => {
                setData(prev => prev ? { ...prev, score: Math.round(prev.score * 0.95 + Math.random() * 5), lastUpdated: new Date().toISOString() } : null);
                setLoading(false);
              }, 400);
            }} 
            className="btn-icon h-7 w-7 border border-slate-850 bg-slate-950/20"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </CardHeader>

      {/* Main interactive area */}
      <div className="flex flex-col lg:flex-row items-center justify-center gap-8 py-4 select-none">
        
        {/* Large Circular Dial (200px diameter on desktop) */}
        <div 
          className="relative w-48 h-48 sm:w-[200px] sm:h-[200px] flex items-center justify-center cursor-pointer transition-all duration-300 hover:scale-105"
          onClick={toggleExpanded}
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
          style={{
            filter: isHovered ? `drop-shadow(0 0 16px ${sentimentColor}44)` : `drop-shadow(0 0 8px ${sentimentColor}22)`,
          }}
        >
          <svg viewBox="0 0 200 200" className="w-full h-full">
            {/* Definitions for gradients */}
            <defs>
              <linearGradient id="bearishGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#991B1B" />
                <stop offset="100%" stopColor="#EF4444" />
              </linearGradient>
              <linearGradient id="neutralGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#D97706" />
                <stop offset="100%" stopColor="#FBBF24" />
              </linearGradient>
              <linearGradient id="bullishGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#84CC16" />
                <stop offset="100%" stopColor="#10B981" />
              </linearGradient>
            </defs>

            {/* Confidence Ring (Outer) */}
            <circle 
              cx="100" 
              cy="100" 
              r="90" 
              fill="none" 
              stroke="#1e293b" 
              strokeWidth={confidenceRingThickness} 
              opacity="0.4"
            />
            <circle 
              cx="100" 
              cy="100" 
              r="90" 
              fill="none" 
              stroke="#06b6d4" 
              strokeWidth={confidenceRingThickness} 
              strokeDasharray={`${2 * Math.PI * 90}`}
              strokeDashoffset={`${2 * Math.PI * 90 * (1 - data.confidence / 100)}`}
              strokeLinecap="round"
              transform="rotate(-90, 100, 100)"
              className="transition-all duration-700"
            />

            {/* Semicircular track (270 deg) */}
            <path 
              d="M 43.43 156.57 A 80 80 0 1 1 156.57 156.57" 
              fill="none" 
              stroke="#1e293b" 
              strokeWidth="10" 
              strokeLinecap="round"
            />
            <path 
              d="M 43.43 156.57 A 80 80 0 1 1 156.57 156.57" 
              fill="none" 
              stroke={`url(#${getGradientId(data.score)})`} 
              strokeWidth="10" 
              strokeLinecap="round"
              strokeDasharray={`${2 * Math.PI * 80 * 0.75}`}
              strokeDashoffset={`${2 * Math.PI * 80 * 0.75 * (1 - data.score / 100)}`}
              className="transition-all duration-700"
            />

            {/* Needle pointer */}
            <line 
              x1="100" 
              y1="100" 
              x2="100" 
              y2="30" 
              stroke="#f1f5f9" 
              strokeWidth="4" 
              strokeLinecap="round"
              transform={`rotate(${needleAngle}, 100, 100)`}
              style={{ transition: 'transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)' }}
            />
            <circle cx="100" cy="100" r="8" fill="#f1f5f9" />
          </svg>

          {/* Center text overlay */}
          <div className="absolute inset-0 flex flex-col items-center justify-center mt-6">
            <span className="font-data text-3xl font-extrabold text-white">{data.score}</span>
            <span className="text-[9px] text-slate-400 font-bold tracking-widest uppercase mt-0.5">{range.replace('-', ' ')}</span>
          </div>

          {/* Hover breakdown view card */}
          {isHovered && (
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-4 w-60 z-50 animate-fade-in pointer-events-none">
              <div className="bg-slate-950/95 border border-slate-800/80 p-4 rounded-xl shadow-2xl backdrop-blur-md space-y-2.5 text-left">
                <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest pb-1.5 border-b border-slate-800/80 flex items-center justify-between">
                  <span>Sentiment Analysis</span>
                  <span className="text-cyan-400">Live</span>
                </div>
                <div className="space-y-1.5 text-xs text-slate-300 font-medium">
                  {data.models.map(m => (
                    <div key={m.name} className="flex justify-between font-data">
                      <span>{m.name}:</span>
                      <span className="text-white">{(m.score).toFixed(2)} ({Math.round(m.score * 100)}%)</span>
                    </div>
                  ))}
                  <div className="h-[1px] bg-slate-800/80 my-1" />
                  <div className="flex justify-between font-data text-cyan-400 font-bold">
                    <span>Ensemble:</span>
                    <span>{(data.score / 100).toFixed(2)} ({data.score}%)</span>
                  </div>
                  <div className="flex justify-between font-data">
                    <span>Confidence:</span>
                    <span>{data.confidence}%</span>
                  </div>
                </div>
                <div className="text-[9px] text-slate-500 font-semibold border-t border-slate-800/80 pt-1.5 flex justify-between items-center">
                  <span>Tokens: tanked (-), beats (+)</span>
                  <span>5m ago</span>
                </div>
              </div>
              <div className="w-3.5 h-3.5 bg-slate-950 border-r border-b border-slate-800/80 rotate-45 mx-auto -mt-2 shadow-lg" />
            </div>
          )}
        </div>

        {/* Dynamic score info side-panel */}
        <div className="flex-1 space-y-4 max-w-sm w-full">
          <div>
            <span className="text-[10px] text-slate-500 uppercase font-bold tracking-widest block mb-1">
              Ensemble Model Weight breakdown
            </span>
            <div className="space-y-2.5">
              {data.models.map(m => (
                <div key={m.name}>
                  <div className="flex justify-between text-xs mb-1 font-semibold">
                    <span className="text-slate-400">{m.name}</span>
                    <span className="font-data text-slate-300">{Math.round(m.score * 100)}%</span>
                  </div>
                  <div className="h-1.5 bg-slate-850 rounded-full overflow-hidden border border-slate-850">
                    <div
                      className="h-full rounded-full transition-all duration-700 bg-cyan-500"
                      style={{ width: `${m.score * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
          
          <button 
            onClick={toggleExpanded} 
            className="w-full flex items-center justify-center gap-1.5 py-2 px-4 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-xl text-xs font-semibold text-slate-300 hover:text-slate-100 transition-all duration-200"
          >
            {isExpanded ? (
              <>Collapse Detailed Analysis <ChevronUp size={14} /></>
            ) : (
              <>Expand Detailed Analysis <ChevronDown size={14} /></>
            )}
          </button>
        </div>
      </div>

      {/* Collapsible expanded section showing additional visualizations */}
      {isExpanded && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-5 pt-5 border-t border-slate-800/60 animate-slide-down">
          <SentimentTrendChart trend={data.trend} />
          <SentimentWordCloud words={data.words} />
        </div>
      )}

      {/* Card footer metrics */}
      <div className="flex items-center justify-between pt-3 border-t border-slate-850">
        <div className="flex items-center gap-1.5 text-[10px] text-slate-500 font-bold uppercase">
          <Clock size={11} />
          Last update: {new Date(data.lastUpdated).toLocaleTimeString()}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-slate-500 font-bold uppercase">Target:</span>
          <span className="font-data font-bold text-xs text-white">{ticker}</span>
          <ConfidenceBadge value={data.confidence} />
        </div>
      </div>
    </Card>
  );
}
