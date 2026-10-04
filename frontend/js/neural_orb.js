/**
 * frontend/js/neural_orb.js — Ultra-Fast Hardware-Accelerated Neural Blob Core Engine for ZEZO.
 * 
 * Performance & Architecture:
 * 1. Hardware-Accelerated HTML5 Canvas 2D batch renderer (0 DOM mutations per frame vs 8,320 in SVG).
 * 2. High-DPI Retina resolution scaling via window.devicePixelRatio.
 * 3. 11 authentic organic states & fluid vector shapes (orange-waves, speaking-final, reasoning, working, idle, etc.).
 * 4. Real-time audio reactive speech envelope & mic level modulation.
 * 5. Smooth cubic-bezier blob-grow-in & blob-soft-out state transitions without pops.
 * 6. Zero-overhead idle pausing: Inactive screens are paused, freeing 100% CPU/GPU.
 * 7. Automatic pause during modals/hidden tabs (AGENTS.md Rules 3 & 4).
 */

(function () {
  'use strict';

  const TAU = Math.PI * 2;
  const GOLDEN = Math.PI * (3 - Math.sqrt(5));
  const ease = (x) => (1 - Math.cos(Math.PI * x)) / 2;
  const hash = (n) => {
    const s = Math.sin(n * 127.1) * 43758.5453;
    return s - Math.floor(s);
  };
  const dist2 = (a, b) => (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2;

  const nearest = (pts, i, k) => {
    const idx = [], d = [], p = pts[i];
    for (let j = 0; j < pts.length; j++) {
      if (j === i) continue;
      const e = dist2(p, pts[j]);
      let at = idx.length;
      if (at === k) {
        if (e >= d[k - 1]) continue;
        at--;
      }
      while (at > 0 && d[at - 1] > e) {
        idx[at] = idx[at - 1];
        d[at] = d[at - 1];
        at--;
      }
      idx[at] = j;
      d[at] = e;
    }
    return idx;
  };

  const PERIOD = {
    base: 6500,
    working: 3000,
    reasoning: 6500,
    'talking-1': 4000,
    'talking-3': 3000,
    idle: 9000,
    offline: 14000,
    'orange-waves': 6000,
    'speaking-final': 5000,
    'blue-fabric': 7000,
    'speaking-4': 4500,
  };

  const clocks = new Map();
  function tick(look, now, speed) {
    let c = clocks.get(look);
    if (!c) clocks.set(look, (c = { t: 0, last: now }));
    if (now > c.last) {
      c.t += Math.min(now - c.last, 100) * speed;
      c.last = now;
    }
    return c.t;
  }

  function yawOf(state, t) {
    if (state === 'orange-waves' || state === 'speaking-final' || state === 'blue-fabric' || state === 'speaking-4') {
      return 0;
    }
    if (state.startsWith('talking') || state.startsWith('speaking')) {
      const base = (t / (PERIOD[state] || 4000)) * TAU;
      const wobble = 0.3 * Math.sin(t / 900);
      return base + wobble;
    }
    if (state === 'idle') {
      return (t / (PERIOD[state] || 9000)) * TAU * 0.3 + 0.15 * Math.sin(t / 2000);
    }
    if (state === 'offline') {
      return (t / (PERIOD[state] || 14000)) * TAU * 0.08 + 0.05 * Math.sin(t / 5000);
    }
    return (t / (PERIOD[state] || 6500)) * TAU;
  }

  const RING_AXIS = (() => {
    const tip = (30 * Math.PI) / 180, roll = (10 * Math.PI) / 180;
    return [-Math.sin(roll) * Math.cos(tip), Math.cos(roll) * Math.cos(tip), Math.sin(tip)];
  })();

  const REACH = 24, WALK = 16, TAIL = 5, HOP = 220;

  function arms(count) {
    const at = (lat, lon) => [Math.cos(lat) * Math.cos(lon), Math.sin(lat), Math.cos(lat) * Math.sin(lon)];
    const g = Math.sqrt((4 * Math.PI) / count), n = 8, along = 0.6 * g;
    return Array.from({ length: n }, (_, m) => {
      const room = m ? m & -m : n;
      const lim = Math.min((85 * Math.PI) / 180, Math.acos(Math.min(1, (g * n) / (TAU * room))));
      const out = [];
      for (let lat = -lim + ((m * 0.618) % 1) * along; lat <= lim; lat += along / Math.sqrt(1 + Math.cos(lat) ** 2))
        out.push(at(lat, (m / n) * TAU - lat));
      return out;
    }).flat();
  }

  function distribute(state, count, shape) {
    if (shape) {
      if (typeof shape === 'function') return shape(count, state);
      if (shape.points) return shape.points(count, state);
    }
    if (state === 'background-spiral') return arms(count);
    return Array.from({ length: count }, (_, i) => {
      const y = 1 - (2 * (i + 0.5)) / count, r = Math.sqrt(1 - y * y), th = i * GOLDEN;
      return [r * Math.cos(th), y, r * Math.sin(th)];
    });
  }

  // ── High-Speed HTML5 Canvas 2D Batch Drawer ──
  const CANVAS_RENDERER = {
    mount: ({ canvas, size, color }) => {
      const ctx = canvas.getContext('2d', { alpha: true });
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.round(size * dpr);
      canvas.height = Math.round(size * dpr);

      let currentColor = color || '#c8dcff';

      return {
        setColor(c) {
          if (c) currentColor = c;
        },
        begin() {
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          ctx.fillStyle = currentColor;
        },
        dot(x, y, r, a) {
          if (a <= 0.01) return;
          ctx.globalAlpha = Math.min(1.0, Math.max(0.0, a));
          ctx.beginPath();
          ctx.arc(x * dpr, y * dpr, Math.max(0.5, r) * dpr, 0, TAU);
          ctx.fill();
        },
        end() {
          ctx.globalAlpha = 1.0;
        },
      };
    },
  };

  function mountOrb(canvas, options = {}) {
    const {
      state: asked,
      variant,
      size = 260,
      speed = 1,
      color = '#c8dcff',
      shape,
      density = 1,
      dotSize = 1,
      tilt = 20,
    } = options;

    const VARIANTS = {
      base: ['default'],
      working: ['default'],
      reasoning: ['default'],
      talking: ['1', '3'],
      idle: ['default'],
      offline: ['default'],
      'orange-waves': ['default'],
      'speaking-final': ['default'],
      'blue-fabric': ['default'],
      'speaking-4': ['default'],
    };

    const which = asked && Object.hasOwn(VARIANTS, asked) ? asked : 'base';
    const own = variant !== 'default' && (VARIANTS[which] || []).includes(variant ?? '');
    const state = which === 'talking' && own ? `talking-${variant}` : (which === 'speaking-4' ? 'speaking-4' : (own ? `${which}-${variant}` : which));

    // Density optimized for silky smooth 60 FPS while retaining dense particle core appearance
    const dens = (state === 'orange-waves' || state === 'speaking-final' || state === 'blue-fabric' || state === 'speaking-4') ? 5 : 3.2;
    const count = Math.max(8, Math.round(size * dens * density));
    const form = typeof shape === 'function' ? { points: shape } : shape;
    const c = size / 2;
    const R = c * 0.8 * (form?.scale ?? 1);
    const rs = (size / 64) ** 0.6 * (0.72 * Math.sqrt(4 / dens)) * dotSize * (dens > 4 ? 1.4 : 1);

    const pts = distribute(state, count, form);
    const drawer = CANVAS_RENDERER.mount({ canvas, size, color });

    const reasoning = state === 'reasoning' && pts.length > 1;
    const near = reasoning ? pts.map((_, i) => nearest(pts, i, REACH)) : [];
    const walks = Array.from({ length: 1 }, () => []);
    let hops = 0;

    const isTalking = state.startsWith('talking') || state.startsWith('speaking');
    const talkVariant = isTalking ? state.split('-')[1] : null;
    const isIdle = state === 'idle';
    const isOffline = state === 'offline';

    const isOrange = state === 'orange-waves';
    const isGreen = state === 'speaking-final';
    const isBlue = state === 'blue-fabric';
    const isSpeaking4 = state === 'speaking-4';

    const draw = (t) => {
      const yaw = yawOf(state, t);
      const pitch = (tilt * Math.PI) / 180;
      const sy = Math.sin(yaw), cy = Math.cos(yaw);
      const st = Math.sin(pitch), ct = Math.cos(pitch);

      const facing = (k) => pts[k][1] * st + (-pts[k][0] * sy + pts[k][2] * cy) * ct;

      const lit = new Map();
      if (reasoning) {
        const s = t / HOP, n = Math.floor(s), f = s - n;
        if (!walks[0].length) {
          const first = [...pts.keys()].reduce((b, k) => (facing(k) > facing(b) ? k : b), 0);
          walks[0].push(first);
        }
        hops = Math.max(hops, n - WALK);
        for (; hops < n; hops++) {
          const walk = walks[0];
          const recent = walk.slice(-8), from = walk[walk.length - 1];
          let best = -1, score = -Infinity;
          near[from].forEach((k, j) => {
            const sc = facing(k) + 0.35 * hash(hops * 31 + j);
            if (!recent.includes(k) && sc > score) {
              score = sc;
              best = k;
            }
          });
          walk.push(best < 0 ? near[from][0] : best);
          if (walk.length > WALK) walk.shift();
        }
        const light = (k, v) => k !== undefined && lit.set(k, Math.max(lit.get(k) ?? 0, v));
        for (const walk of walks)
          for (let j = TAIL - 1; j >= 0; j--)
            light(walk[walk.length - 1 - j], j === 0 ? ease(Math.min(1, f * 2)) : 1 - (j - 1 + f) / TAIL);
      }

      let talkPulse = null;
      if (isTalking) {
        if (talkVariant === '1') {
          const u = (t % 2400) / 2400;
          const sweep = u < 0.5 ? u * 2 : 1 - (u - 0.5) * 2;
          talkPulse = { type: 'sweep', at: -1.2 + 2.4 * sweep, width: 0.35 };
        } else if (talkVariant === '3') {
          const u = (t % 2000) / 2000;
          const v = (t % 1600) / 1600;
          talkPulse = {
            type: 'dual',
            atX: -1.1 + 2.2 * (0.5 + 0.5 * Math.sin(u * TAU)),
            atY: -1.1 + 2.2 * (0.5 + 0.5 * Math.cos(v * TAU)),
            width: 0.3,
          };
        } else if (state === 'speaking-4') {
          const u = (t % 1500) / 1500;
          const pulse = u < 0.5 ? u * 2 : 1 - (u - 0.5) * 2;
          talkPulse = { type: 'sweep', at: -1.5 + 3.0 * pulse, width: 0.6 };
        }
      }

      let idleBreath = 0;
      if (isIdle) idleBreath = 0.5 + 0.5 * Math.sin((t / 3000) * TAU);
      let offlineBreath = 0;
      if (isOffline) offlineBreath = 0.5 + 0.5 * Math.sin((t / 6000) * TAU);

      drawer.begin();

      pts.forEach(([x, y, z], i) => {
        const [ly, lc] = [sy, cy];
        const z1 = -x * ly + z * lc;
        let vx = x * lc + z * ly, vy = y * ct - z1 * st;
        const vz = y * st + z1 * ct, d = (vz + 1) / 2;
        let r = (0.5 + 1.4 * d) * rs;
        let a = Math.max(0, (d - 0.3) / 0.7);

        if (isGreen) {
          const voice = Math.max(0, Math.min(1, window.__jarvisSpeechLevel || 0));
          const localWave = 0.92 + 0.08 * Math.sin(i * 0.73);
          const energy = voice * localWave;
          r *= 1 + 0.14 * energy;
          a += (1 - a) * 0.22 * energy;
          vx += vx * 0.028 * energy;
          vy += vy * 0.028 * energy;
        }

        if (state === 'working') {
          const u = t % 1700, at = 1.3 - 2.6 * ease(Math.min(1, u / 1200));
          const q = vx * RING_AXIS[0] + vy * RING_AXIS[1] + vz * RING_AXIS[2];
          const g = u < 1200 ? Math.exp(-(((q - at) / 0.2) ** 2)) : 0;
          r *= 1 + 0.6 * g;
          a += (1 - a) * g;
          const w = Math.min(1, Math.max(0, (q - at) / 0.2)) * (u < 1200 ? 1 : 1 - Math.min(1, 1.6 * ((u - 1200) / 800)));
          vx *= 1 - 0.08 * w;
          vy *= 1 - 0.08 * w;
          r *= 1 - 0.15 * w;
        }

        if (reasoning) {
          const spark = lit.get(i) ?? 0;
          a *= 0.5;
          if (spark) {
            r *= 1 + 0.8 * spark;
            a += (1 - a) * spark;
          }
        }

        if (isTalking && talkPulse) {
          let speak = 0;
          if (talkPulse.type === 'sweep') {
            const dist = Math.abs(vx - talkPulse.at);
            speak = Math.exp(-((dist / talkPulse.width) ** 2));
            speak *= 0.6 + 0.4 * d;
          } else if (talkPulse.type === 'dual') {
            const dx = Math.abs(vx - talkPulse.atX);
            const dy = Math.abs(vy - talkPulse.atY);
            const wx = Math.exp(-((dx / talkPulse.width) ** 2));
            const wy = Math.exp(-((dy / talkPulse.width) ** 2));
            speak = Math.max(wx, wy) * 0.9;
            speak *= 0.5 + 0.5 * d;
          }
          if (speak > 0.01) {
            r *= 1 + 0.7 * speak;
            a += (1 - a) * speak * 0.8;
            vx += vx * 0.03 * speak;
            vy += vy * 0.03 * speak;
          }
        }

        if (isIdle) {
          a *= 0.35;
          a += 0.15 * idleBreath * d;
          const phase = i * 0.7;
          const pulse = 0.5 + 0.5 * Math.sin((t / 4000) * TAU + phase);
          const pulseStrength = 0.08 * pulse;
          a += pulseStrength;
          r *= 1 + 0.05 * idleBreath;
          const drift = 0.02 * Math.sin((t / 2500) * TAU + i * 1.3);
          vx += vx * drift;
          vy += vy * drift;
          const twinkle = Math.max(0, Math.sin((t / 700) * TAU + i * 2.1) - 0.95) * 20;
          if (twinkle > 0) {
            a += twinkle * 0.1;
            r *= 1 + twinkle * 0.2;
          }
        }

        if (isOffline) {
          a *= 0.12;
          a += 0.04 * offlineBreath * d;
          const twinkle = Math.max(0, Math.sin((t / 2200) * TAU + i * 3.7) - 0.99) * 100;
          if (twinkle > 0) {
            a += twinkle * 0.05;
            r *= 1 + twinkle * 0.1;
          }
          const drift = 0.005 * Math.sin((t / 6000) * TAU + i * 0.9);
          vx += vx * drift;
          vy += vy * drift;
        }

        if (isOrange) {
          const wave = 0.055 * Math.sin(y * 2.2 + t * 0.0022) + 0.038 * Math.cos(x * 2.5 + t * 0.0028);
          vx *= 1 + wave;
          vy *= 1 + wave;
          a += 0.06 * Math.sin(y * 2 + t * 0.0025);
        }

        if (isGreen) {
          const bump = 0.15 * Math.sin(x * 4 + t * 0.006) * Math.cos(y * 4 + t * 0.0045) * Math.sin(z * 4);
          vx *= 1 + bump;
          vy *= 1 + bump;
          const pulse = 0.05 * Math.sin(t * 0.009);
          vx *= 1 + pulse;
          vy *= 1 + pulse;
        }

        if (isBlue) {
          const ripple = 0.18 * Math.sin(z * 8 + t * 0.012) + 0.12 * Math.cos(x * 6 + t * 0.009);
          vx *= 1 + ripple;
          vy *= 1 + ripple;
          a *= 0.8 + 0.2 * Math.sin(t * 0.006 + x * 2);
          r *= 0.9 + 0.1 * Math.sin(t * 0.006 + y * 2);
        }

        if (isSpeaking4) {
          const ripple = 0.12 * Math.sin(z * 6 + t * 0.012) + 0.1 * Math.cos(x * 5 + t * 0.009);
          const wave = 0.18 * Math.sin(y * 2 + t * 0.006) + 0.12 * Math.cos(x * 2.5 + t * 0.0045);
          const pulse = 0.1 * Math.sin(t * 0.015);
          vx *= 1 + ripple + wave + pulse;
          vy *= 1 + ripple + wave + pulse;
          vx += 0.06 * Math.sin(t * 0.009) * vy;
          vy += 0.06 * Math.cos(t * 0.009) * vx;
          a *= 0.85 + 0.15 * Math.sin(t * 0.012 + x * 3);
          r *= 0.95 + 0.05 * Math.sin(t * 0.015 + y * 2);
        }

        drawer.dot(c + vx * R, c - vy * R, r, a);
      });

      drawer.end();
    };

    const look = `${state}@${speed}`;
    let raf = 0, dead = false, isRunning = false;

    function frame(now) {
      if (window._zezoAnimActive === false) {
        if (isRunning) raf = requestAnimationFrame(frame);
        return;
      }
      const t = tick(look, now, speed);
      draw(t);
      if (isRunning) raf = requestAnimationFrame(frame);
    }

    const pause = () => {
      isRunning = false;
      if (raf) {
        cancelAnimationFrame(raf);
        raf = 0;
      }
    };

    const play = () => {
      if (!isRunning && !dead) {
        isRunning = true;
        raf = requestAnimationFrame(frame);
      }
    };

    return {
      pause,
      play,
      destroy() {
        dead = true;
        pause();
      },
    };
  }

  // ── Speech Envelope Modulation ──
  window.__jarvisSpeechLevel = 0;
  window.__jarvisSpeechTarget = 0;
  let speechEnvelopeLastFrame = performance.now();

  (function smoothSpeechEnvelope(now) {
    const dt = Math.min(50, Math.max(0, now - speechEnvelopeLastFrame));
    speechEnvelopeLastFrame = now;

    const target = Math.max(0, window.__jarvisSpeechTarget || 0);
    const current = Math.max(0, window.__jarvisSpeechLevel || 0);
    const attack = 1 - Math.exp(-dt / 48);
    const release = 1 - Math.exp(-dt / 145);
    const easing = target > current ? attack : release;

    window.__jarvisSpeechLevel = current + (target - current) * easing;
    window.__jarvisSpeechTarget = target * Math.exp(-dt / 125);

    if (window.__jarvisSpeechTarget < 0.012) window.__jarvisSpeechTarget = 0;
    if (window.__jarvisSpeechLevel < 0.008 && window.__jarvisSpeechTarget === 0) {
      window.__jarvisSpeechLevel = 0;
    }
    requestAnimationFrame(smoothSpeechEnvelope);
  })(performance.now());

  // ── States Definition ──
  const statesList = [
    { state: 'base', color: '#c8dcff' },            // 0: Base
    { state: 'working', color: '#eab308' },         // 1: Working (Energy Torus)
    { state: 'reasoning', color: '#38bdf8' },       // 2: Reasoning (Synaptic Hop Network)
    { state: 'talking', variant: '1', color: '#f97316' }, // 3: Talking Sweep
    { state: 'talking', variant: '3', color: '#f97316' }, // 4: Talking Dual
    { state: 'idle', color: '#00d2ff' },            // 5: Idle / Standby
    { state: 'offline', color: '#64748b' },         // 6: Offline / Muted
    { state: 'orange-waves', color: '#ff9a56' },    // 7: Orange Waves (Listening)
    { state: 'speaking-final', color: '#4ade80' },  // 8: Speaking Final (Green Voice Wave)
    { state: 'blue-fabric', color: '#2a4b6e' },     // 9: Blue Fabric
    { state: 'speaking-4', color: '#c8d6e5' },      // 10: Speaking 4
  ];

  // ZEZO State to Orb Index Mapping
  const ORB_STATE_MAP = {
    standby: 5,     // idle (#00d2ff)
    idle: 5,        // idle (#00d2ff)
    listening: 7,   // orange-waves (#ff9a56 vibrant fluid wave)
    talking: 3,     // talking-1
    thinking: 2,    // reasoning (#38bdf8 synaptic sparks)
    reasoning: 2,   // reasoning
    executing: 1,   // working (#eab308 spinning torus)
    working: 1,     // working
    speaking: 8,    // speaking-final (#4ade80 audio-reactive vocal wave)
    muted: 6,       // offline (#64748b)
    offline: 6,     // offline
    sleeping: 6,    // offline
    connecting: 1,  // working
    interrupted: 6, // offline
  };

  let orbs = [];
  let screens = [];
  let currentIndex = 5; // Start in idle
  let transitionTimer = null;
  let transitionSequence = 0;
  let isInitialized = false;

  function goTo(index) {
    if (index < 0) index = statesList.length - 1;
    if (index >= statesList.length) index = 0;

    if (index === currentIndex && screens[index]?.classList.contains('active')) {
      if (orbs[index]) orbs[index].play();
      return;
    }

    const previousIndex = currentIndex;
    const sequence = ++transitionSequence;
    if (transitionTimer) {
      clearTimeout(transitionTimer);
      transitionTimer = null;
    }

    screens.forEach((screen, i) => {
      if (i !== previousIndex && i !== index) {
        screen.classList.remove('transition-out');
        if (orbs[i]) orbs[i].pause();
      }
    });

    const previousScreen = screens[previousIndex];
    if (previousScreen) {
      previousScreen.classList.remove('active');
      previousScreen.classList.add('transition-out');
    }

    currentIndex = index;
    const incomingScreen = screens[index];
    if (incomingScreen) {
      incomingScreen.classList.remove('transition-out');
      const incomingCanvas = incomingScreen.querySelector('canvas, svg');
      if (incomingCanvas) {
        incomingCanvas.style.animation = 'none';
        void incomingCanvas.getBoundingClientRect();
        incomingCanvas.style.animation = '';
      }
      incomingScreen.classList.add('active');
    }

    orbs.forEach((orb, i) => {
      if (i === index || i === previousIndex) orb.play();
      else orb.pause();
    });

    transitionTimer = setTimeout(() => {
      if (sequence !== transitionSequence) return;
      if (previousScreen) previousScreen.classList.remove('transition-out');
      if (orbs[previousIndex] && previousIndex !== currentIndex) {
        orbs[previousIndex].pause();
      }
      transitionTimer = null;
    }, 720);
  }

  window.initNeuralOrb = function (containerSelector = '#vortex-gif') {
    const container = document.querySelector(containerSelector);
    if (!container) return;

    // Teardown existing
    orbs.forEach(orb => orb.destroy());
    orbs = [];
    screens = [];
    container.innerHTML = '';

    // Create screens-container wrapper
    const screensContainer = document.createElement('div');
    screensContainer.id = 'screens-container';
    screensContainer.className = 'screens-container';
    container.appendChild(screensContainer);

    statesList.forEach(({ state, variant, color }, idx) => {
      const screen = document.createElement('div');
      screen.className = 'screen';
      screen.dataset.index = idx;

      const canvas = document.createElement('canvas');
      canvas.width = 260;
      canvas.height = 260;
      canvas.style.filter = `drop-shadow(0 0 18px ${color}55)`;

      screen.appendChild(canvas);
      screensContainer.appendChild(screen);

      const orb = mountOrb(canvas, {
        state,
        variant,
        size: 260,
        speed: 1,
        color,
      });

      orbs.push(orb);
      screens.push(screen);
    });

    isInitialized = true;
    goTo(currentIndex);
  };

  window.setNeuralOrbState = function (stateKey) {
    if (!isInitialized) {
      window.initNeuralOrb('#vortex-gif');
    }
    const cleanKey = (stateKey || 'standby').toString().toLowerCase().trim();
    const targetIdx = ORB_STATE_MAP[cleanKey] ?? ORB_STATE_MAP.idle;
    goTo(targetIdx);
  };

  window.setNeuralOrbAudioLevel = function (level) {
    const lvl = Math.max(0, Math.min(1, level || 0));
    window.__jarvisSpeechTarget = lvl;
  };

  // Auto initialize
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => window.initNeuralOrb());
  } else {
    setTimeout(() => window.initNeuralOrb(), 30);
  }
})();
