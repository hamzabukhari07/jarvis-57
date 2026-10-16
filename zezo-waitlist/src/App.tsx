import React, { useState, useEffect, useMemo } from 'react';
import { Check, Loader2 } from 'lucide-react';
import { CONFIG } from './config';

export function App() {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState('');

  // Check if user already joined
  useEffect(() => {
    const alreadyJoined = localStorage.getItem('zezo_joined_email');
    if (alreadyJoined) {
      setStatus('success');
      setEmail(alreadyJoined);
    }
  }, []);

  // Generate subtle scattered pinprick stars matching the cosmic inspiration
  const stars = useMemo(() => {
    const starList = [];
    const count = 48;
    for (let i = 0; i < count; i++) {
      // Deterministic spread
      const top = ((i * 37) % 75) + 5; // keep in upper 80% of screen
      const left = ((i * 53) % 94) + 3;
      const opacity = 0.25 + ((i % 5) * 0.15); // 0.25 - 0.85
      const size = i % 7 === 0 ? 2 : 1.5;
      starList.push({ id: i, top: `${top}%`, left: `${left}%`, opacity, size });
    }
    return starList;
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !email.includes('@') || !email.includes('.')) {
      setErrorMessage('Please enter a valid email address.');
      setStatus('error');
      return;
    }

    setStatus('loading');
    setErrorMessage('');

    try {
      if (CONFIG.GOOGLE_SCRIPT_URL && CONFIG.GOOGLE_SCRIPT_URL.trim() !== '') {
        await fetch(CONFIG.GOOGLE_SCRIPT_URL, {
          method: 'POST',
          mode: 'no-cors',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            email: email.trim(),
            timestamp: new Date().toISOString(),
            referrer: document.referrer || 'direct',
          }),
        });
      } else {
        // Fast local mock latency for immediate preview
        await new Promise((res) => setTimeout(res, 600));
      }

      localStorage.setItem('zezo_joined_email', email);
      setStatus('success');
    } catch (err) {
      console.error(err);
      setErrorMessage('Unable to register. Please retry.');
      setStatus('error');
    }
  };

  return (
    <div className="relative min-h-screen w-full bg-black text-white flex flex-col justify-between items-center overflow-hidden selection:bg-white/20 selection:text-white">
      {/* 1. Atmospheric Horizon Sky Glow */}
      <div className="absolute inset-0 horizon-atmosphere pointer-events-none" />

      {/* 2. Scattered Star Particles */}
      <div className="absolute inset-0 pointer-events-none">
        {stars.map((star) => (
          <div
            key={star.id}
            style={{
              top: star.top,
              left: star.left,
              opacity: star.opacity,
              width: `${star.size}px`,
              height: `${star.size}px`,
            }}
            className="absolute rounded-full bg-white"
          />
        ))}
      </div>

      {/* Header (Minimal branding) */}
      <header className="relative z-20 w-full max-w-5xl px-6 pt-8 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-sm tracking-wider uppercase text-zinc-300">
            ZEZO
          </span>
        </div>

        <div className="text-xs text-zinc-500 font-mono tracking-widest uppercase">
          Autonomous OS
        </div>
      </header>

      {/* Hero Section — Exact Composition of Inspiration */}
      <main className="relative z-20 w-full max-w-3xl px-6 py-12 flex flex-col items-center text-center my-auto">
        {/* Top Capsule Badge */}
        <div className="inline-flex items-center justify-center px-4 py-1.5 rounded-full bg-white/[0.06] border border-white/[0.12] text-xs sm:text-[13px] text-zinc-300 font-normal tracking-wide backdrop-blur-md mb-8 shadow-sm">
          <span>ZEZO • Launching Soon</span>
        </div>

        {/* Headline with Italic Serif */}
        <h1 className="text-4xl sm:text-6xl md:text-[68px] font-normal tracking-tight text-white max-w-2xl leading-[1.12] mb-5">
          The wait is part<br />
          of the <span className="font-serif-italic text-zinc-100">journey.</span>
        </h1>

        {/* Subtitle */}
        <p className="text-sm sm:text-base text-zinc-400 max-w-md font-normal leading-relaxed mb-9">
          Be the first to experience ZEZO ahead of our private launch. Autonomous multi-agent OS running natively on your machine.
        </p>

        {/* Single Capsule Waitlist Form */}
        <div className="w-full max-w-[440px]">
          {status === 'success' ? (
            /* Minimal Inline Checkmark State */
            <div className="p-3.5 rounded-2xl bg-white/[0.08] border border-emerald-500/40 backdrop-blur-xl flex items-center justify-center gap-2.5 text-emerald-400 text-sm font-medium shadow-2xl transition-all duration-300">
              <div className="h-5 w-5 rounded-full bg-emerald-500/20 flex items-center justify-center text-emerald-400">
                <Check className="w-3.5 h-3.5 stroke-[2.5]" />
              </div>
              <span>You're on the list. We'll notify you soon.</span>
            </div>
          ) : (
            /* Unified Capsule Input + Button */
            <form onSubmit={handleSubmit} className="flex flex-col gap-2">
              <div className="p-1.5 rounded-2xl bg-white/[0.08] border border-white/[0.14] backdrop-blur-xl flex items-center shadow-2xl transition-all duration-150 focus-within:border-white/[0.28]">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Your email address"
                  disabled={status === 'loading'}
                  required
                  className="bg-transparent px-4 py-2 text-sm sm:text-[15px] text-white placeholder-zinc-400 focus:outline-none flex-1 min-w-0"
                />
                <button
                  type="submit"
                  disabled={status === 'loading'}
                  className="bg-white hover:bg-zinc-100 text-black font-medium text-sm sm:text-[14px] px-5 py-2.5 rounded-xl transition-all duration-150 active:scale-95 shrink-0 cursor-pointer shadow-sm disabled:opacity-50 flex items-center gap-1.5"
                >
                  {status === 'loading' ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-black" />
                      <span>Saving...</span>
                    </>
                  ) : (
                    <span>Get Notified</span>
                  )}
                </button>
              </div>

              {status === 'error' && (
                <p className="text-xs text-rose-400 mt-1 font-mono text-center">
                  {errorMessage}
                </p>
              )}
            </form>
          )}
        </div>
      </main>

      {/* 3. Celestial Glowing Planet Horizon Arc */}
      <div 
        className="planet-horizon"
        style={{
          bottom: '-72vh',
        }}
      />

      {/* Footer (Minimal attribution) */}
      <footer className="relative z-20 w-full max-w-5xl px-6 pb-6 pt-2 flex items-center justify-between text-xs text-zinc-500 font-mono">
        <span>Architected by {CONFIG.CREATOR_NAME}</span>
        <span>Private Launch</span>
      </footer>
    </div>
  );
}

export default App;
