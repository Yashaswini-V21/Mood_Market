import { useState, useEffect, useRef } from 'react';
import { X, Send, Bot, User, Zap, Brain, Loader, MessageSquare } from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────
interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  loading?: boolean;
}

interface AIChatPanelProps {
  ticker: string;
  onClose: () => void;
}

// ─── AI response templates ────────────────────────────────────────────────────
const AI_RESPONSES: Record<string, (ticker: string) => string> = {
  sentiment: (t) => `Based on the latest FinBERT + DistilBERT ensemble analysis for **${t}**, the weighted sentiment score is **72/100 (BULLISH)**.\n\n• **FinBERT**: 0.62 positive confidence\n• **DistilBERT**: 0.58 positive confidence\n• **RoBERTa**: 0.60 positive confidence\n\nTop SHAP tokens driving sentiment: *beats* (+0.35), *surge* (+0.52), *earnings* (+0.28). Key risk token: *cautious* (-0.58).`,
  forecast: (t) => `The Informer ProbSparse Transformer forecasts **${t}** will move **UP** in the next 4 hours with **63% directional confidence** (99% CI: ±2.1%).\n\n• Current price: $192.53\n• Predicted price: $196.98\n• Delta: +$4.45 (+2.3%)\n• Model uncertainty: ±0.8% (Monte Carlo dropout)\n• Historical accuracy: 65.2% vs 50.1% LSTM baseline`,
  anomaly: (t) => `7-Method anomaly ensemble status for **${t}**:\n\n✅ Z-Score: 4.2σ — **TRIGGERED** (threshold: 3.0σ)\n✅ Isolation Forest: 0.82 — **TRIGGERED**\n✅ EWMA: Regime shift — **TRIGGERED**\n⚠️ Autoencoder: 1.1 — Clear\n⚠️ MAD: 0.8 — Clear\n\n**Ensemble Vote: 3/5 → ANOMALY_DETECTED (HIGH)**\nRecommend: Reduce position size by 40%. Stop-loss tightened.`,
  signal: (t) => `Multi-agent trading desk consensus for **${t}**:\n\n🧠 **Sentiment Agent**: BULLISH (72/100 score, 89% conf)\n📊 **Technical Agent**: RSI=72 (overbought), MACD=Bullish\n🔮 **Forecaster Agent**: UP with 63% confidence\n🛡️ **Risk Manager**: 2.4% Kelly position size, SL: 189.40\n✍️ **Synthesizer**: **STRONG BUY** — 4/5 agents aligned\n\nPosition sizing: $2,400 per $100K portfolio. Risk/reward: 1:2.8`,
  default: (t) => `I can analyze **${t}** across all intelligence modules. Try asking me:\n\n• *"What's the current sentiment score?"*\n• *"What does the Informer model predict?"*\n• *"Are there any anomalies detected?"*\n• *"What's the overall trading signal?"*\n• *"Explain the SHAP values"*`,
};

const matchResponse = (input: string, ticker: string): string => {
  const lower = input.toLowerCase();
  if (lower.includes('sentiment') || lower.includes('finbert') || lower.includes('emotion')) return AI_RESPONSES.sentiment(ticker);
  if (lower.includes('forecast') || lower.includes('predict') || lower.includes('price') || lower.includes('inform')) return AI_RESPONSES.forecast(ticker);
  if (lower.includes('anomal') || lower.includes('hype') || lower.includes('detect') || lower.includes('z-score')) return AI_RESPONSES.anomaly(ticker);
  if (lower.includes('signal') || lower.includes('buy') || lower.includes('sell') || lower.includes('trade') || lower.includes('agent')) return AI_RESPONSES.signal(ticker);
  return AI_RESPONSES.default(ticker);
};

// ─── Markdown-lite renderer ───────────────────────────────────────────────────
function MdText({ content }: { content: string }) {
  const parts = content.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);
  return (
    <span>
      {parts.map((p, i) => {
        if (p.startsWith('**') && p.endsWith('**'))
          return <strong key={i} className="text-white font-bold">{p.slice(2, -2)}</strong>;
        if (p.startsWith('*') && p.endsWith('*'))
          return <em key={i} className="text-cyan-300 not-italic">{p.slice(1, -1)}</em>;
        return <span key={i}>{p}</span>;
      })}
    </span>
  );
}

function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === 'user';
  return (
    <div className={`flex gap-2.5 ${isUser ? 'flex-row-reverse' : 'flex-row'} mb-3`}>
      {/* Avatar */}
      <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${
        isUser
          ? 'bg-cyan-600'
          : 'bg-gradient-to-br from-purple-600 to-cyan-600'
      }`}>
        {isUser ? <User size={13} className="text-white" /> : <Bot size={13} className="text-white" />}
      </div>

      {/* Bubble */}
      <div className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-xs leading-relaxed ${
        isUser
          ? 'bg-cyan-600/20 border border-cyan-500/30 text-slate-200 rounded-tr-sm'
          : 'bg-slate-800/80 border border-slate-700/60 text-slate-300 rounded-tl-sm'
      }`}>
        {msg.loading ? (
          <div className="flex items-center gap-1.5">
            <Loader size={11} className="text-purple-400 animate-spin" />
            <span className="text-slate-500 text-[10px] animate-pulse">Analyzing {msg.content}…</span>
          </div>
        ) : (
          <div className="whitespace-pre-line">
            {msg.content.split('\n').map((line, i) => (
              <div key={i}>
                <MdText content={line} />
              </div>
            ))}
          </div>
        )}
        <div className="text-[9px] text-slate-600 mt-1.5 text-right">
          {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
        </div>
      </div>
    </div>
  );
}

// ─── Quick prompts ────────────────────────────────────────────────────────────
const QUICK_PROMPTS = [
  { label: 'Sentiment', prompt: 'What is the current sentiment score?', icon: Brain },
  { label: 'Forecast', prompt: 'What does the Informer model predict?', icon: Zap },
  { label: 'Anomaly', prompt: 'Are there any anomalies detected?', icon: MessageSquare },
  { label: 'Signal', prompt: 'What is the overall trading signal?', icon: Bot },
];

// ─── Main Panel ────────────────────────────────────────────────────────────────
export function AIChatPanel({ ticker, onClose }: AIChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '0',
      role: 'assistant',
      content: `Hello! I'm the MoodMarket AI assistant. Ask me anything about **${ticker}** — sentiment scores, price forecasts, anomaly detection, or trading signals.`,
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const sendMessage = async (text: string) => {
    if (!text.trim() || isTyping) return;
    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text.trim(),
      timestamp: new Date(),
    };
    const loadingMsg: Message = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: ticker,
      timestamp: new Date(),
      loading: true,
    };

    setMessages(prev => [...prev, userMsg, loadingMsg]);
    setInput('');
    setIsTyping(true);

    // Simulate streaming delay
    const delay = 1000;
    await new Promise(r => setTimeout(r, delay));

    const response = matchResponse(text, ticker);
    setMessages(prev => [
      ...prev.slice(0, -1),
      { id: crypto.randomUUID(), role: 'assistant', content: response, timestamp: new Date() },
    ]);
    setIsTyping(false);
  };

  return (
    <div className="fixed bottom-24 right-6 z-50 w-96 max-h-[600px] flex flex-col
                    glass-strong rounded-2xl border border-slate-700/60 shadow-2xl shadow-black/60
                    animate-slide-in-right overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800/60
                      bg-gradient-to-r from-purple-900/30 to-cyan-900/20">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-purple-500 to-cyan-500
                          flex items-center justify-center shadow-lg">
            <Brain size={14} className="text-white" />
          </div>
          <div>
            <div className="text-sm font-bold text-white">MoodMarket AI</div>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-[10px] text-emerald-400 font-semibold">Online · {ticker}</span>
            </div>
          </div>
        </div>
        <button
          id="close-chat-btn"
          onClick={onClose}
          className="w-7 h-7 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700
                     flex items-center justify-center text-slate-400 hover:text-slate-200 transition-all"
        >
          <X size={13} />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-3" style={{ maxHeight: 380 }}>
        {messages.map(msg => <MessageBubble key={msg.id} msg={msg} />)}
        <div ref={bottomRef} />
      </div>

      {/* Quick prompts */}
      <div className="px-3 py-2 border-t border-slate-800/40 flex gap-1.5 flex-wrap">
        {QUICK_PROMPTS.map(q => {
          const Icon = q.icon;
          return (
            <button
              key={q.label}
              onClick={() => sendMessage(q.prompt)}
              disabled={isTyping}
              className="flex items-center gap-1 px-2 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700/80
                         border border-slate-700/60 text-[10px] font-semibold text-slate-400
                         hover:text-slate-200 transition-all disabled:opacity-40"
            >
              <Icon size={10} />
              {q.label}
            </button>
          );
        })}
      </div>

      {/* Input */}
      <div className="px-3 py-3 border-t border-slate-800/60 flex gap-2">
        <input
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && sendMessage(input)}
          placeholder={`Ask about ${ticker}…`}
          disabled={isTyping}
          className="flex-1 h-9 px-3 rounded-xl bg-slate-800 border border-slate-700 text-slate-100
                     placeholder-slate-500 text-xs focus:outline-none focus:border-purple-500
                     focus:ring-1 focus:ring-purple-500/30 transition-all disabled:opacity-50"
        />
        <button
          id="chat-send-btn"
          onClick={() => sendMessage(input)}
          disabled={!input.trim() || isTyping}
          className="w-9 h-9 rounded-xl bg-gradient-to-r from-purple-600 to-cyan-600
                     hover:from-purple-500 hover:to-cyan-500
                     flex items-center justify-center text-white
                     transition-all duration-200 active:scale-95 disabled:opacity-40"
        >
          {isTyping ? <Loader size={13} className="animate-spin" /> : <Send size={13} />}
        </button>
      </div>
    </div>
  );
}

// ─── Floating trigger button ───────────────────────────────────────────────────
interface AIChatButtonProps { ticker: string; }

export function AIChatButton({ ticker }: AIChatButtonProps) {
  const [open, setOpen] = useState(false);
  const [pulse, setPulse] = useState(false);

  // Pulse every 30s to draw attention
  useEffect(() => {
    const iv = setInterval(() => {
      setPulse(true);
      setTimeout(() => setPulse(false), 1500);
    }, 30000);
    return () => clearInterval(iv);
  }, []);

  return (
    <>
      {open && <AIChatPanel ticker={ticker} onClose={() => setOpen(false)} />}
      <button
        id="ai-chat-fab"
        onClick={() => setOpen(o => !o)}
        className={`fixed bottom-6 right-6 z-50 w-14 h-14 rounded-2xl
                   bg-gradient-to-br from-purple-600 to-cyan-600
                   hover:from-purple-500 hover:to-cyan-500
                   flex flex-col items-center justify-center
                   shadow-[0_0_30px_rgba(168,85,247,0.5)]
                   hover:shadow-[0_0_50px_rgba(168,85,247,0.7)]
                   transition-all duration-300 active:scale-95
                   ${open ? 'rotate-[360deg]' : 'rotate-0'}
                   ${pulse ? 'scale-110' : 'scale-100'}`}
        title="Ask the MoodMarket AI"
      >
        {open ? <X size={20} className="text-white" /> : <Brain size={22} className="text-white" />}
        {!open && (
          <span className="text-[8px] text-white/80 font-bold mt-0.5 leading-none">AI</span>
        )}
        {pulse && !open && (
          <span className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-emerald-400 animate-ping" />
        )}
      </button>
    </>
  );
}

/* clean architecture alignment */
