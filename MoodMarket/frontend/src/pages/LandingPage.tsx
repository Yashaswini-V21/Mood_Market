import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Brain, Zap, Shield, Activity, TrendingUp, BarChart2,
  ArrowRight, Cpu, Layers, Eye, ChevronDown, Star
} from 'lucide-react';

// ─── Particle System ──────────────────────────────────────────────────────────
interface Particle {
  id: number; x: number; y: number; vx: number; vy: number;
  size: number; opacity: number; color: string;
}

const PARTICLE_COLORS = ['#06b6d4', '#a855f7', '#10b981', '#3b82f6', '#f59e0b'];

function ParticleCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<Particle[]>([]);
  const animFrameRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    // Init particles
    particlesRef.current = Array.from({ length: 60 }, (_, i) => ({
      id: i,
      x: Math.random() * window.innerWidth,
      y: Math.random() * window.innerHeight,
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.4,
      size: Math.random() * 2.5 + 0.5,
      opacity: Math.random() * 0.6 + 0.1,
      color: PARTICLE_COLORS[Math.floor(Math.random() * PARTICLE_COLORS.length)],
    }));

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      particlesRef.current.forEach(p => {
        // Move
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0) p.x = canvas.width;
        if (p.x > canvas.width) p.x = 0;
        if (p.y < 0) p.y = canvas.height;
        if (p.y > canvas.height) p.y = 0;

        // Draw
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = p.color + Math.floor(p.opacity * 255).toString(16).padStart(2, '0');
        ctx.fill();
      });

      // Draw connections
      particlesRef.current.forEach((a, i) => {
        particlesRef.current.slice(i + 1).forEach(b => {
          const dist = Math.hypot(a.x - b.x, a.y - b.y);
          if (dist < 120) {
            ctx.beginPath();
            ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y);
            const alpha = (1 - dist / 120) * 0.15;
            ctx.strokeStyle = `rgba(99,102,241,${alpha})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        });
      });

      animFrameRef.current = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      cancelAnimationFrame(animFrameRef.current);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full pointer-events-none"
      style={{ zIndex: 0 }}
    />
  );
}

// ─── Animated Counter ─────────────────────────────────────────────────────────
function AnimCounter({ target, suffix = '', prefix = '', duration = 2000 }: {
  target: number; suffix?: string; prefix?: string; duration?: number;
}) {
  const [value, setValue] = useState(0);
  const [started, setStarted] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) setStarted(true); },
      { threshold: 0.5 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!started) return;
    const start = Date.now();
    const tick = () => {
      const progress = Math.min((Date.now() - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Math.round(eased * target));
      if (progress < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, [started, target, duration]);

  return (
    <div ref={ref} className="font-mono tabular-nums">
      {prefix}{value.toLocaleString()}{suffix}
    </div>
  );
}

// ─── Feature Card ─────────────────────────────────────────────────────────────
function FeatureCard({ icon: Icon, title, description, color, delay }: {
  icon: React.ElementType; title: string; description: string;
  color: string; delay: number;
}) {
  const [visible, setVisible] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) setVisible(true); },
      { threshold: 0.2 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className="group relative glass rounded-2xl p-6 border border-white/5 hover:border-white/10
                 transition-all duration-500 hover:scale-[1.02] hover:-translate-y-1 cursor-default"
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(24px)',
        transition: `opacity 0.6s ease ${delay}ms, transform 0.6s ease ${delay}ms, border-color 0.3s, box-shadow 0.3s, transform 0.3s`,
      }}
    >
      {/* Glow on hover */}
      <div className={`absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 ${color.replace('text-', 'shadow-').replace('-400', '')}`}
           style={{ boxShadow: `0 0 40px ${color.includes('cyan') ? 'rgba(6,182,212,0.15)' : color.includes('purple') ? 'rgba(168,85,247,0.15)' : color.includes('emerald') ? 'rgba(16,185,129,0.15)' : color.includes('blue') ? 'rgba(59,130,246,0.15)' : 'rgba(245,158,11,0.15)'}` }} />
      
      <div className={`w-11 h-11 rounded-xl flex items-center justify-center mb-4 ${
        color.includes('cyan') ? 'bg-cyan-500/15' :
        color.includes('purple') ? 'bg-purple-500/15' :
        color.includes('emerald') ? 'bg-emerald-500/15' :
        color.includes('blue') ? 'bg-blue-500/15' : 'bg-amber-500/15'
      }`}>
        <Icon size={20} className={color} />
      </div>
      <h3 className="text-sm font-bold text-white mb-2">{title}</h3>
      <p className="text-xs text-slate-400 leading-relaxed">{description}</p>
    </div>
  );
}

// ─── Main Landing Page ────────────────────────────────────────────────────────
interface LandingPageProps { onLaunch: () => void; }

export function LandingPage({ onLaunch }: LandingPageProps) {
  const [scrollY, setScrollY] = useState(0);
  const [moodScore] = useState(72);

  useEffect(() => {
    const handler = () => setScrollY(window.scrollY);
    window.addEventListener('scroll', handler, { passive: true });
    return () => window.removeEventListener('scroll', handler);
  }, []);

  const handleLaunch = useCallback(() => onLaunch(), [onLaunch]);

  const heroOpacity = Math.max(0, 1 - scrollY / 400);
  const heroTranslate = scrollY * 0.3;

  const FEATURES = [
    {
      icon: Brain, color: 'text-cyan-400',
      title: 'Informer ProbSparse Transformer',
      description: 'O(L log L) attention complexity. Single-pass generative decoding for 4-hour price direction forecasts with Monte Carlo uncertainty quantification.',
      delay: 0,
    },
    {
      icon: Shield, color: 'text-rose-400',
      title: '7-Method Anomaly Ensemble',
      description: 'Z-Score · Isolation Forest · Autoencoder · EWMA · Adaptive EWMA · Multi-Variate detection. Weighted voting for Hype Storm alerts before price moves.',
      delay: 80,
    },
    {
      icon: Layers, color: 'text-purple-400',
      title: '5-Agent Async Trading Desk',
      description: 'Sentiment · Technical · Forecaster · Risk Manager · Synthesizer — five async agents collaborate like a real hedge fund trading desk.',
      delay: 160,
    },
    {
      icon: Zap, color: 'text-amber-400',
      title: 'FinBERT Sentiment Fusion',
      description: 'FinBERT + DistilBERT + RoBERTa ensemble with confidence-weighted fusion, drift monitoring, and LRU caching for real-time inference.',
      delay: 240,
    },
    {
      icon: Eye, color: 'text-emerald-400',
      title: 'Full Explainability Suite',
      description: 'SHAP deep feature attribution, multi-head attention heatmaps, attention rollout, global importance rankings, ECE calibration measurement.',
      delay: 320,
    },
    {
      icon: Activity, color: 'text-blue-400',
      title: 'Sub-second WebSocket Feeds',
      description: 'JWT-authenticated live price · sentiment · anomaly · forecast streams. Multi-layer Redis caching with 70%+ hit rate and HTTP polling fallback.',
      delay: 400,
    },
  ];

  const STATS = [
    { label: 'Directional Accuracy', value: 65, suffix: '%', prefix: '', note: 'vs 50% LSTM baseline' },
    { label: 'Automated Tests', value: 200, suffix: '+', prefix: '', note: '22 files, 3 layers' },
    { label: 'API Latency P50', value: 20, suffix: 'ms', prefix: '<', note: 'with Redis cache' },
    { label: 'Stocks Monitored', value: 500, suffix: '+', prefix: '', note: 'concurrent tickers' },
  ];

  return (
    <div className="min-h-screen bg-[#020617] text-white overflow-x-hidden font-sans">
      
      {/* ── Aurora Background ──────────────────────────────── */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none" style={{ zIndex: 0 }}>
        <div
          className="absolute w-[900px] h-[900px] rounded-full opacity-[0.07]"
          style={{
            background: 'radial-gradient(circle, #7c3aed 0%, transparent 70%)',
            top: '-200px', left: '-200px',
            animation: 'auroraFloat1 18s ease-in-out infinite',
          }}
        />
        <div
          className="absolute w-[700px] h-[700px] rounded-full opacity-[0.06]"
          style={{
            background: 'radial-gradient(circle, #0ea5e9 0%, transparent 70%)',
            top: '30%', right: '-150px',
            animation: 'auroraFloat2 22s ease-in-out infinite',
          }}
        />
        <div
          className="absolute w-[600px] h-[600px] rounded-full opacity-[0.05]"
          style={{
            background: `radial-gradient(circle, ${moodScore >= 60 ? '#10b981' : '#ef4444'} 0%, transparent 70%)`,
            bottom: '10%', left: '30%',
            animation: 'auroraFloat3 15s ease-in-out infinite',
            transition: 'background 2s ease',
          }}
        />
      </div>
      <ParticleCanvas />

      {/* ── Navbar ────────────────────────────────────────── */}
      <nav
        className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-8 h-16
                   border-b border-white/5 transition-all duration-300"
        style={{
          background: scrollY > 20 ? 'rgba(2,6,23,0.85)' : 'transparent',
          backdropFilter: scrollY > 20 ? 'blur(20px)' : 'none',
        }}
      >
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-cyan-500 flex items-center justify-center">
            <TrendingUp size={16} className="text-white" />
          </div>
          <span className="font-bold text-white tracking-tight">MoodMarket</span>
          <span className="text-[10px] text-purple-400 font-mono bg-purple-500/10 border border-purple-500/20 px-1.5 py-0.5 rounded-full ml-1">
            v1.0
          </span>
        </div>
        <div className="flex items-center gap-4">
          <a
            href="https://github.com/Yashaswini-V21/Mood_Market"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0 1 12 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/></svg> GitHub
          </a>
          <button
            id="nav-launch-btn"
            onClick={handleLaunch}
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-bold rounded-lg
                       bg-gradient-to-r from-purple-600 to-cyan-600 text-white
                       hover:from-purple-500 hover:to-cyan-500 transition-all duration-200 active:scale-95"
          >
            Launch Dashboard <ArrowRight size={13} />
          </button>
        </div>
      </nav>

      {/* ── Hero Section ──────────────────────────────────── */}
      <section
        className="relative min-h-screen flex flex-col items-center justify-center px-6 text-center"
        style={{ zIndex: 1 }}
      >
        <div style={{ opacity: heroOpacity, transform: `translateY(${heroTranslate}px)`, willChange: 'transform' }}>
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-purple-500/30
                          bg-purple-500/10 text-purple-300 text-[11px] font-semibold mb-8
                          animate-[fadeIn_0.8s_ease_both]">
            <Star size={11} className="fill-purple-400 text-purple-400" />
            Future of Productivity · AI Financial Intelligence · Hackathon 2026
          </div>

          {/* Headline */}
          <h1
            className="text-5xl sm:text-7xl font-black mb-6 leading-[1.05] tracking-tight
                       animate-[fadeInUp_0.9s_ease_both]"
            style={{ animationDelay: '100ms' }}
          >
            <span className="text-white">The Market Moves On</span>
            <br />
            <span
              className="bg-gradient-to-r from-purple-400 via-cyan-400 to-emerald-400
                         bg-clip-text text-transparent"
            >
              Emotion Before Data.
            </span>
            <br />
            <span className="text-white text-4xl sm:text-5xl font-bold">We Decode the Emotion.</span>
          </h1>

          {/* Subheadline */}
          <p
            className="text-slate-400 text-lg max-w-2xl mx-auto mb-10 leading-relaxed
                       animate-[fadeInUp_0.9s_ease_both]"
            style={{ animationDelay: '200ms' }}
          >
            Full-stack AI platform fusing real-time social sentiment with an{' '}
            <span className="text-cyan-400 font-semibold">Informer Transformer</span> to forecast stock
            direction and detect coordinated{' '}
            <span className="text-amber-400 font-semibold">Hype Storms</span> — giving traders an edge
            before the crowd catches on.
          </p>

          {/* CTA buttons */}
          <div
            className="flex flex-wrap items-center justify-center gap-4
                       animate-[fadeInUp_0.9s_ease_both]"
            style={{ animationDelay: '300ms' }}
          >
            <button
              id="hero-launch-btn"
              onClick={handleLaunch}
              className="group flex items-center gap-2 px-8 py-4 rounded-xl font-bold text-sm
                         bg-gradient-to-r from-purple-600 to-cyan-600 text-white
                         hover:from-purple-500 hover:to-cyan-500 shadow-[0_0_40px_rgba(168,85,247,0.4)]
                         hover:shadow-[0_0_60px_rgba(168,85,247,0.6)]
                         transition-all duration-300 active:scale-95"
            >
              <Zap size={16} className="group-hover:animate-spin" />
              Launch Intelligence Dashboard
              <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
            </button>
            <a
              href="https://github.com/Yashaswini-V21/Mood_Market"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 px-8 py-4 rounded-xl font-bold text-sm
                         bg-white/5 border border-white/10 text-slate-300
                         hover:bg-white/10 hover:border-white/20 hover:text-white
                         transition-all duration-200"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0 1 12 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/></svg> View Source
            </a>
          </div>

          {/* Tech badges */}
          <div
            className="flex flex-wrap justify-center gap-2 mt-10
                       animate-[fadeInUp_0.9s_ease_both]"
            style={{ animationDelay: '400ms' }}
          >
            {['Python 3.11', 'FastAPI', 'PyTorch', 'React 19', 'TimescaleDB', 'Redis', 'Docker', 'Informer'].map(t => (
              <span key={t} className="text-[11px] text-slate-500 bg-slate-900/60 border border-slate-800 px-2.5 py-1 rounded-full font-mono">
                {t}
              </span>
            ))}
          </div>
        </div>

        {/* Scroll indicator */}
        <div
          className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1 opacity-40"
          style={{ zIndex: 1 }}
        >
          <span className="text-[10px] text-slate-500 uppercase tracking-widest font-semibold">Scroll</span>
          <ChevronDown size={16} className="text-slate-500 animate-bounce" />
        </div>
      </section>

      {/* ── Stats Section ─────────────────────────────────── */}
      <section className="relative z-10 py-20 px-6">
        <div className="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-6">
          {STATS.map((s, i) => (
            <div
              key={s.label}
              className="glass rounded-2xl p-6 text-center border border-white/5
                         hover:border-purple-500/20 transition-all duration-300 group"
            >
              <div className="font-black text-3xl sm:text-4xl text-white mb-1 group-hover:text-transparent
                              group-hover:bg-gradient-to-r group-hover:from-purple-400 group-hover:to-cyan-400
                              group-hover:bg-clip-text transition-all duration-300">
                <AnimCounter target={s.value} suffix={s.suffix} prefix={s.prefix} duration={1800 + i * 200} />
              </div>
              <div className="text-xs font-bold text-slate-300 mb-1">{s.label}</div>
              <div className="text-[10px] text-slate-600">{s.note}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Intelligence Stack Heading ─────────────────────── */}
      <section className="relative z-10 py-4 px-6">
        <div className="max-w-5xl mx-auto text-center mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-cyan-500/20
                          bg-cyan-500/5 text-cyan-400 text-[11px] font-semibold mb-4">
            <Cpu size={11} /> Intelligence Stack
          </div>
          <h2 className="text-3xl sm:text-4xl font-black text-white mb-4">
            Not Just Another{' '}
            <span className="bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
              Trading Bot
            </span>
          </h2>
          <p className="text-slate-400 max-w-xl mx-auto text-sm leading-relaxed">
            Every component is production-grade, research-backed, and explainable.
            Built to win.
          </p>
        </div>
      </section>

      {/* ── Feature Cards ─────────────────────────────────── */}
      <section className="relative z-10 pb-20 px-6">
        <div className="max-w-5xl mx-auto grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURES.map(f => <FeatureCard key={f.title} {...f} />)}
        </div>
      </section>

      {/* ── Architecture Preview ──────────────────────────── */}
      <section className="relative z-10 py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <div className="glass rounded-2xl border border-white/5 p-8 text-center">
            <div className="flex items-center justify-center gap-2 mb-6">
              <BarChart2 size={18} className="text-emerald-400" />
              <span className="font-bold text-white">Model Performance</span>
            </div>
            <div className="grid grid-cols-3 gap-6">
              {[
                { label: 'vs LSTM Baseline', metric: 'Directional Accuracy', lstm: '50.1%', us: '65.2%', color: 'text-emerald-400' },
                { label: 'vs Vanilla Transformer', metric: 'Mean Absolute Error', lstm: '0.071', us: '0.059', color: 'text-cyan-400' },
                { label: 'vs Transformer P99', metric: 'Inference Latency', lstm: '89ms', us: '45ms (INT8)', color: 'text-purple-400' },
              ].map(m => (
                <div key={m.label} className="text-center">
                  <div className="text-[10px] text-slate-500 uppercase tracking-widest mb-2">{m.label}</div>
                  <div className="text-xs text-slate-400 mb-1">{m.metric}</div>
                  <div className="flex items-center justify-center gap-3">
                    <span className="font-data text-slate-600 text-sm line-through">{m.lstm}</span>
                    <ArrowRight size={12} className="text-slate-600" />
                    <span className={`font-data font-bold text-lg ${m.color}`}>{m.us}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Final CTA ─────────────────────────────────────── */}
      <section className="relative z-10 py-24 px-6 text-center">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-4xl font-black text-white mb-4">
            Ready to Decode the{' '}
            <span className="bg-gradient-to-r from-purple-400 to-cyan-400 bg-clip-text text-transparent">
              Market Mood?
            </span>
          </h2>
          <p className="text-slate-400 mb-8 text-sm">
            Launch the live intelligence dashboard and see sentiment, forecast, anomaly, and trading signals
            in real time.
          </p>
          <button
            id="bottom-launch-btn"
            onClick={handleLaunch}
            className="group inline-flex items-center gap-2 px-10 py-4 rounded-xl font-bold
                       bg-gradient-to-r from-purple-600 to-cyan-600 text-white
                       hover:from-purple-500 hover:to-cyan-500
                       shadow-[0_0_60px_rgba(168,85,247,0.5)]
                       hover:shadow-[0_0_80px_rgba(168,85,247,0.7)]
                       transition-all duration-300 active:scale-95 text-sm"
          >
            <Zap size={16} /> Launch Dashboard
            <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
          </button>
        </div>
      </section>

      {/* ── Footer ────────────────────────────────────────── */}
      <footer className="relative z-10 border-t border-white/5 px-8 py-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-gradient-to-br from-purple-500 to-cyan-500 flex items-center justify-center">
            <TrendingUp size={12} className="text-white" />
          </div>
          <span className="text-xs text-slate-500 font-semibold">MoodMarket © 2026 · Yashaswini V · MIT License</span>
        </div>
        <div className="text-[10px] text-slate-700">Not financial advice.</div>
      </footer>

      {/* Animation keyframes */}
      <style>{`
        @keyframes auroraFloat1 {
          0%, 100% { transform: translate(0, 0) scale(1); }
          33%       { transform: translate(60px, 40px) scale(1.1); }
          66%       { transform: translate(-40px, 80px) scale(0.95); }
        }
        @keyframes auroraFloat2 {
          0%, 100% { transform: translate(0, 0) scale(1); }
          50%       { transform: translate(-80px, -50px) scale(1.05); }
        }
        @keyframes auroraFloat3 {
          0%, 100% { transform: translate(0, 0) scale(1); }
          40%       { transform: translate(50px, -30px) scale(1.1); }
          70%       { transform: translate(-20px, 60px) scale(0.9); }
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(24px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}

/* clean architecture alignment */
