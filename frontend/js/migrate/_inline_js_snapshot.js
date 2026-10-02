<!-- ═══════════════════════════════════════════════════════════════════ -->
<!-- 4. SCRIPTS: Three.js Particles, Avatar & Interactive Logic -->
<!-- ═══════════════════════════════════════════════════════════════════ -->
<script>
  // ── 1. Live Header Clock & Date ──
  const updateClock = () => {
    const d = new Date();
    const timeStr = d.toTimeString().split(' ')[0];
    const days = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];
    const months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
    const dateStr = `${days[d.getDay()]} ${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}`;
    
    const clockEl = document.getElementById('header-clock-time');
    const dateEl = document.getElementById('header-clock-date');
    if (clockEl) clockEl.innerText = timeStr;
    if (dateEl) dateEl.innerText = dateStr;
  };
  setInterval(updateClock, 1000);
  updateClock();

  // Global animation gate. `false` pauses the WebGL globe and the dot-matrix
  // canvas (during a file drag, or while the window is hidden) so the renderer
  // main thread stays free for Chromium's drag protocol.
  window._zezoAnimActive = true;
  window._zezoDragging = false;
  document.addEventListener('visibilitychange', () => {
    window._zezoAnimActive = !document.hidden && !window._zezoDragging;
  });

  // ── 3. Assistant State Visualizer & Minimalist Dot Matrix Engine ──
  let currentAssistantState = 'standby';

  const STATE_CONFIGS = {
    offline: {
      heading: 'Offline',
      color: '#475569',
      speed: 0.0005
    },
    connecting: {
      heading: 'Connecting...',
      color: '#6366f1',
      speed: 0.0012
    },
    standby: {
      heading: 'Standby...',
      color: '#a855f7',
      speed: 0.0008
    },
    sleeping: {
      heading: 'Standby...',
      color: '#a855f7',
      speed: 0.0008
    },
    listening: {
      heading: 'Listening...',
      color: '#f97316',
      speed: 0.0012
    },
    thinking: {
      heading: 'Thinking...',
      color: '#00d2ff',
      speed: 0.0016
    },
    executing: {
      heading: 'Executing...',
      color: '#eab308',
      speed: 0.0015
    },
    speaking: {
      heading: 'Speaking...',
      color: '#10b981',
      speed: 0.0018
    },
    muted: {
      heading: 'Muted...',
      color: '#64748b',
      speed: 0.0002
    },
    interrupted: {
      heading: 'Halted...',
      color: '#ef4444',
      speed: 0.0010
    }
  };

  function setAssistantState(stateKey) {
    const key = (stateKey || 'offline').toString().toLowerCase().trim();
    const cfg = STATE_CONFIGS[key] || STATE_CONFIGS.offline;
    currentAssistantState = key;

    // Update active pill button
    document.querySelectorAll('.state-pill-btn').forEach(btn => btn.classList.remove('active'));
    const activeBtn = document.getElementById(`state-btn-${key}`);
    if (activeBtn) activeBtn.classList.add('active');

    // Update Minimalist Capsule Text
    const headingEl = document.getElementById('state-heading-text');
    const dockEl = document.getElementById('avatar-command-dock') || document.getElementById('state-telemetry-capsule');
    const powerBtn = document.getElementById('dock-power-btn');
    const powerLabel = document.getElementById('dock-power-label');
    const powerIcon = document.getElementById('dock-power-icon');
    const micBtn = document.getElementById('dock-mic-btn');
    const micIcon = document.getElementById('dock-mic-icon');
    const micLabel = document.getElementById('dock-mic-label');

    if (headingEl) {
      headingEl.innerText = cfg.heading;
      headingEl.style.color = cfg.color || '#f1f5f9';
    }
    if (dockEl) {
      // Keep pure neutral obsidian styling - no colored container border or glowing halo
      dockEl.style.borderColor = 'rgba(255, 255, 255, 0.08)';
      dockEl.style.boxShadow = '0 12px 32px -4px rgba(0, 0, 0, 0.92), inset 0 1px 0 rgba(255, 255, 255, 0.06)';
    }

    // Sync Power / Sleep button visual state
    if (powerBtn) {
      if (key === 'sleeping' || key === 'standby') {
        powerBtn.className = 'dock-btn power-btn sleeping';
        if (powerLabel) powerLabel.innerText = 'WAKE';
        if (powerIcon) powerIcon.setAttribute('icon', 'solar:sun-2-bold');
        powerBtn.title = 'ZEZO in Sleep Mode (Click to Wake Up)';
      } else if (key === 'offline') {
        powerBtn.className = 'dock-btn power-btn offline';
        if (powerLabel) powerLabel.innerText = 'ONLINE';
        if (powerIcon) powerIcon.setAttribute('icon', 'solar:power-bold');
        powerBtn.title = 'ZEZO Offline (Click to Connect)';
      } else {
        powerBtn.className = 'dock-btn power-btn';
        if (powerLabel) powerLabel.innerText = 'SLEEP';
        if (powerIcon) powerIcon.setAttribute('icon', 'solar:power-bold');
        powerBtn.title = 'Put ZEZO to Sleep / Standby Mode';
      }
    }

    // Sync Mic button visual state
    if (micBtn) {
      if (key === 'muted') {
        micBtn.className = 'dock-btn mic-btn muted';
        if (micIcon) micIcon.setAttribute('icon', 'solar:microphone-slash-bold');
        if (micLabel) micLabel.innerText = 'MUTED';
      } else {
        micBtn.className = 'dock-btn mic-btn active';
        if (micIcon) micIcon.setAttribute('icon', 'solar:microphone-3-bold');
        if (micLabel) micLabel.innerText = 'MIC';
      }
    }
  }

  // ── 4. Micro Dot Matrix Canvas Visualizer (2×3 Physical Phosphor Grid) ──
  const initMatrixIcon = () => {
    const canvas = document.getElementById('state-matrix-icon');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const DOT_POSITIONS = [
      { c: 0, r: 0, x: 4.5,  y: 3.5 },
      { c: 1, r: 0, x: 11.5, y: 3.5 },
      { c: 1, r: 1, x: 11.5, y: 9.0 },
      { c: 1, r: 2, x: 11.5, y: 14.5 },
      { c: 0, r: 2, x: 4.5,  y: 14.5 },
      { c: 0, r: 1, x: 4.5,  y: 9.0 }
    ];

    let _lastMatrixFrame = 0;
    const draw = (now) => {
      requestAnimationFrame(draw);
      if (window._zezoAnimActive === false) return;
      if (now - _lastMatrixFrame < 33) return;   // ~30 FPS
      _lastMatrixFrame = now;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const cfg = STATE_CONFIGS[currentAssistantState] || STATE_CONFIGS.standby;
      const t = Date.now() * (cfg.speed || 0.001);

      DOT_POSITIONS.forEach((dot, idx) => {
        let intensity = 0;

        if (currentAssistantState === 'thinking') {
          // Perimeter Circular Traveling Sweep with soft phosphor trail
          const phase = (t * 3.6) % 6;
          const dist = Math.min(Math.abs(idx - phase), 6 - Math.abs(idx - phase));
          intensity = Math.max(0, 1.0 - dist / 1.5);
        } else if (currentAssistantState === 'listening') {
          // Acoustic Waveform / Dynamic Audio Ripple across 2x3 matrix
          const wave = Math.sin(t * 3.4 - (dot.r * 1.2 + dot.c * 0.6));
          intensity = Math.max(0.1, Math.min(1.0, 0.4 + 0.6 * wave));
        } else if (currentAssistantState === 'speaking') {
          // Dual Channel VU Equalizer bounce
          const bar0 = (Math.sin(t * 4.6) * 0.5 + 0.5) * 2.9;
          const bar1 = (Math.cos(t * 4.2) * 0.5 + 0.5) * 2.9;
          const h = (dot.c === 0) ? bar0 : bar1;
          const rowFromBottom = 2 - dot.r;
          intensity = (rowFromBottom <= h) ? Math.min(1.0, h - rowFromBottom + 0.45) : 0.08;
        } else if (currentAssistantState === 'executing') {
          // Alternating Diagonal Dual-Cross Matrix Strobe
          const step = Math.floor(t * 5.0) % 3;
          intensity = ((dot.r + dot.c) % 3 === step) ? 0.95 : 0.12;
        } else if (currentAssistantState === 'connecting') {
          // Top-to-Bottom Matrix Raster Scan
          const scan = (t * 2.8) % 3;
          intensity = Math.max(0.1, 1.0 - Math.abs(dot.r - scan) * 0.85);
        } else if (currentAssistantState === 'interrupted') {
          // High-frequency Alarm Flash
          intensity = (Math.sin(t * 16) > 0) ? 0.95 : 0.05;
        } else if (currentAssistantState === 'muted') {
          // Single dot dim ambient heartbeat
          intensity = (dot.r === 2 && dot.c === 0) ? (0.25 + 0.25 * Math.sin(t * 2.0)) : 0.04;
        } else if (currentAssistantState === 'offline') {
          // Faint static unpowered dots
          intensity = 0.03;
        } else {
          // Standby / Sleeping: Organic Harmonic Breathing Wave
          intensity = 0.15 + 0.55 * (0.5 + 0.5 * Math.sin(t * 1.8 - dot.r * 0.5));
        }

        // Draw Inactive Base Dot
        ctx.beginPath();
        ctx.arc(dot.x, dot.y, 1.4, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(255, 255, 255, 0.10)';
        ctx.fill();

        // Draw Active Phosphor Dot with State Color & Glow
        if (intensity > 0.05) {
          ctx.beginPath();
          ctx.arc(dot.x, dot.y, 1.4 + (intensity > 0.7 ? 0.3 : 0), 0, Math.PI * 2);
          ctx.fillStyle = cfg.color;
          ctx.shadowColor = cfg.color;
          ctx.shadowBlur = (intensity > 0.6) ? 4 : 1;
          ctx.globalAlpha = Math.min(1.0, intensity * 0.95);
          ctx.fill();
          ctx.shadowBlur = 0;
          ctx.globalAlpha = 1.0;
        }
      });

    };
    requestAnimationFrame(draw);
  };
  initMatrixIcon();

  // ── 5. Modal & Drawer Control Functions ──
  function openModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.add('open');
    closeSettingsDrawer();
    if (id === 'log-modal' && typeof window.requestBackendLogs === 'function') {
      window.requestBackendLogs();
    }
    if (id === 'qr-modal' && typeof window.requestRemoteKey === 'function') {
      window.requestRemoteKey();
    }
  }
  function closeModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove('open');
  }

  function toggleSettingsDrawer(e) {
    if (e) e.stopPropagation();
    const drawer = document.getElementById('settings-drawer');
    const btn = document.getElementById('settings-trigger-btn');
    if (drawer.classList.contains('open')) {
      drawer.classList.remove('open');
      btn.classList.remove('active');
    } else {
      drawer.classList.add('open');
      btn.classList.add('active');
    }
  }

  function closeSettingsDrawer() {
    const drawer = document.getElementById('settings-drawer');
    const btn = document.getElementById('settings-trigger-btn');
    if (drawer) drawer.classList.remove('open');
    if (btn) btn.classList.remove('active');
  }

  document.addEventListener('click', (e) => {
    const drawer = document.getElementById('settings-drawer');
    const btn = document.getElementById('settings-trigger-btn');
    if (drawer && drawer.classList.contains('open')) {
      if (!drawer.contains(e.target) && !btn.contains(e.target)) {
        closeSettingsDrawer();
      }
    }
  });

  // Settings Toggles
  function toggleBriefMode() {
    window.briefActive = !window.briefActive;
    const sw = document.getElementById('brief-mode-switch');
    if (sw) sw.classList.toggle('active', !!window.briefActive);
    const badge = document.getElementById('brief-mode-badge');
    if (badge) {
      badge.innerText = window.briefActive ? 'ON' : 'OFF';
      badge.className = window.briefActive ? 'badge badge-success' : 'badge';
    }
    if (window.socket) window.socket.send('brief_toggle', { enable: window.briefActive });
  }

  function toggleWakeWord() {
    window.wakeActive = !window.wakeActive;
    const sw = document.getElementById('wake-word-switch');
    if (sw) sw.classList.toggle('active-accent', !!window.wakeActive);
    const badge = document.getElementById('wake-word-badge');
    if (badge) {
      badge.innerText = window.wakeActive ? 'ARMED' : 'OFF';
      badge.className = window.wakeActive ? 'badge badge-accent' : 'badge';
    }
    if (window.socket) window.socket.send('wake_toggle', { enable: window.wakeActive });
  }

  function toggleAutostart() {
    window.autostartActive = !window.autostartActive;
    const sw = document.getElementById('autostart-switch');
    if (sw) sw.classList.toggle('active', !!window.autostartActive);
    const badge = document.getElementById('autostart-badge');
    if (badge) {
      badge.innerText = window.autostartActive ? 'ON' : 'OFF';
      badge.className = window.autostartActive ? 'badge badge-success' : 'badge';
    }
    if (window.socket) window.socket.send('autostart_toggle', { enable: window.autostartActive });
  }

  function togglePtt() {
    window.pttActive = !window.pttActive;
    const sw = document.getElementById('ptt-switch');
    if (sw) sw.classList.toggle('active', !!window.pttActive);
    const badge = document.getElementById('ptt-badge');
    if (badge) {
      badge.innerText = window.pttActive ? 'ON' : 'OFF';
      badge.className = window.pttActive ? 'badge badge-success' : 'badge';
    }
    if (window.socket) window.socket.send('ptt_toggle', { enable: window.pttActive });
  }

  // Requests a fresh, real one-time key from the backend dashboard.
  // The actual rendering + live expiry countdown lives in the module script
  // below (it owns the WebSocket `socket`), so this only delegates.
  function regenerateKey() {
    if (typeof window.requestRemoteKey === 'function') {
      window.requestRemoteKey();
    }
  }

  // Copies the currently displayed pairing key to the clipboard.
  function copyPairingKey() {
    const keyEl = document.getElementById('pairing-key-display');
    const btn = document.getElementById('copy-pairing-key-btn');
    const raw = keyEl ? keyEl.textContent.trim() : '';
    if (!raw || raw.charAt(0) === '—') return;

    const done = () => {
      if (!btn) return;
      const orig = btn.innerHTML;
      btn.innerHTML = '<iconify-icon icon="solar:check-circle-bold" style="color:#22c55e;"></iconify-icon> COPIED';
      setTimeout(() => { btn.innerHTML = orig; }, 1400);
    };
    if (typeof writeToSystemClipboard === 'function') {
      Promise.resolve(writeToSystemClipboard(raw)).then(done);
    } else if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(raw).then(done).catch(() => {});
    }
  }

  // ── UI Accent Color Switcher Logic (Supports all 8 Cyber Colors) ──
  function setAccentColor(colorHex, colorName) {
    if (!colorHex) return;
    const root = document.documentElement;
    root.style.setProperty('--accent', colorHex);
    root.style.setProperty('--accent-dim', `${colorHex}18`);

    // Update active color picker dot in controls drawer
    document.querySelectorAll('.color-dot-picker').forEach(dot => {
      dot.classList.remove('active');
      if (colorName && dot.id === `color-dot-${colorName}`) {
        dot.classList.add('active');
      } else if (!colorName && dot.getAttribute('onclick') && dot.getAttribute('onclick').toLowerCase().includes(colorHex.toLowerCase())) {
        dot.classList.add('active');
      }
    });

    // Update STATE_CONFIGS listening and speaking to match dynamic accent
    if (STATE_CONFIGS.listening) {
      STATE_CONFIGS.listening.color = colorHex;
      STATE_CONFIGS.listening.haloBg = `radial-gradient(circle, ${colorHex}73 0%, ${colorHex}14 50%, transparent 70%)`;
      STATE_CONFIGS.listening.glowFilter = `drop-shadow(0 0 25px ${colorHex}8c)`;
    }
    if (STATE_CONFIGS.speaking) {
      STATE_CONFIGS.speaking.color = colorHex;
      STATE_CONFIGS.speaking.haloBg = `radial-gradient(circle, ${colorHex}8c 0%, ${colorHex}1f 50%, transparent 70%)`;
      STATE_CONFIGS.speaking.glowFilter = `drop-shadow(0 0 35px ${colorHex}bf)`;
    }

    // Immediately re-apply current state to refresh UI visuals
    setAssistantState(currentAssistantState);
  }

  // ── Additional Native Control Drawer Functions ──
  function toggleFullScreenMode() {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(err => {
        alert(`Error enabling fullscreen: ${err.message}`);
      });
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      }
    }
  }

  function simulateShortcut() {
    alert('✅ Desktop shortcut created: "ZEZO OS.lnk" added to Desktop.');
    const box = document.getElementById('stream-box');
    if (box) {
      const now = new Date().toTimeString().split(' ')[0];
      box.insertAdjacentHTML('beforeend', `
        <div class="stream-msg stream-msg-sys ok">
          <div class="stream-msg-header">
            <div class="stream-msg-meta">
              <span class="mono text-muted">${now}</span>
              <span class="stream-msg-tag" style="background:rgba(34,197,94,0.15); color:#22c55e; border:1px solid rgba(34,197,94,0.35);">SHORTCUT</span>
            </div>
            <button class="msg-copy-btn" onclick="copySingleMessage(this, 'Desktop shortcut registered.')">
              <iconify-icon icon="solar:copy-linear"></iconify-icon>
            </button>
          </div>
          <div class="stream-msg-body" style="color:var(--text-secondary); font-family:var(--font-mono); font-size:10px;">
            Desktop shortcut "ZEZO OS.lnk" registered.
          </div>
        </div>
      `);
      box.scrollTop = box.scrollHeight;
    }
  }



  const HUD_STYLES = ['FLUID VORTEX', 'HOLOGRAPHIC MESH', 'CYBERNETIC CORE'];
  let currentHudIdx = 0;
  function cycleHudStyle() {
    currentHudIdx = (currentHudIdx + 1) % HUD_STYLES.length;
    const label = document.getElementById('hud-style-label');
    if (label) {
      label.innerText = HUD_STYLES[currentHudIdx];
    }
    const box = document.getElementById('stream-box');
    if (box) {
      const now = new Date().toTimeString().split(' ')[0];
      box.insertAdjacentHTML('beforeend', `
        <div class="stream-msg stream-msg-sys hud">
          <div class="stream-msg-header">
            <div class="stream-msg-meta">
              <span class="mono text-muted">${now}</span>
              <span class="stream-msg-tag" style="background:rgba(168,85,247,0.15); color:#c084fc; border:1px solid rgba(168,85,247,0.35);">HUD STYLE</span>
            </div>
            <button class="msg-copy-btn" onclick="copySingleMessage(this, 'Switched avatar renderer to ${HUD_STYLES[currentHudIdx]}')">
              <iconify-icon icon="solar:copy-linear"></iconify-icon>
            </button>
          </div>
          <div class="stream-msg-body" style="color:var(--text-secondary); font-family:var(--font-mono); font-size:10px;">
            Switched avatar renderer to <b>${HUD_STYLES[currentHudIdx]}</b>
          </div>
        </div>
      `);
      box.scrollTop = box.scrollHeight;
    }
  }

  // ── 6. RESIZABLE INSPECTOR LOGIC ──
  const avatarFrame = document.getElementById('avatar-frame');
  const inspectorFrame = document.getElementById('inspector-frame');
  const splitter = document.getElementById('drag-splitter');

  function setInspectorState(mode) {
    if (mode === 'minimize') {
      avatarFrame.style.flex = '5';
      inspectorFrame.style.flex = '0 0 46px';
    } else if (mode === 'maximize') {
      avatarFrame.style.flex = '0 0 130px';
      inspectorFrame.style.flex = '4';
    } else { // default
      avatarFrame.style.flex = '1.1';
      inspectorFrame.style.flex = '1';
    }
    setTimeout(() => {
      if (window._resizeAvatar) window._resizeAvatar();
    }, 280);
  }

  // Draggable Splitter Implementation
  let isDragging = false;
  splitter.addEventListener('mousedown', (e) => {
    isDragging = true;
    document.body.style.cursor = 'row-resize';
    document.body.style.userSelect = 'none';
  });

  window.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    const centerCol = document.getElementById('center-column');
    const rect = centerCol.getBoundingClientRect();
    const offsetY = e.clientY - rect.top;
    const totalHeight = rect.height;

    const topRatio = Math.max(0.15, Math.min(0.85, offsetY / totalHeight));
    const bottomRatio = 1 - topRatio;

    avatarFrame.style.flex = `${topRatio.toFixed(3)}`;
    inspectorFrame.style.flex = `${bottomRatio.toFixed(3)}`;

    if (window._resizeAvatar) window._resizeAvatar();
  });

  window.addEventListener('mouseup', () => {
    if (isDragging) {
      isDragging = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      if (window._resizeAvatar) window._resizeAvatar();
    }
  });

  // Double click splitter to reset
  splitter.addEventListener('dblclick', () => setInspectorState('default'));

  // ── 7. Dynamic Live Output Canvas Controller ──
  window.setCanvasContent = function(type, title, text, html) {
    const emptyState = document.getElementById('canvas-empty-state');
    const activeContent = document.getElementById('canvas-active-content');
    const contentText = document.getElementById('canvas-content-text');
    const badge = document.getElementById('canvas-context-badge');

    if (emptyState) emptyState.style.display = 'none';
    if (activeContent) activeContent.style.display = 'block';

    // Format badge text dynamically
    let badgeText = (type || 'LIVE OUTPUT').toUpperCase();
    const tLower = (title || '').toLowerCase();
    const typeLower = (type || '').toLowerCase();
    if (typeLower === 'web' || tLower.includes('web') || tLower.includes('search') || tLower.includes('news')) {
      badgeText = 'WEB SEARCH';
    } else if (tLower.startsWith('compare') || tLower.includes(' vs ') || tLower.includes('benchmark') || tLower.includes('comparison')) {
      badgeText = 'COMPARISON';
    } else if (typeLower === 'code' || typeLower === 'coding' || tLower.includes('code') || tLower.includes('syntax') || tLower.includes('repo')) {
      badgeText = 'CODE SYNTHESIS';
    } else if (typeLower === 'file' || tLower.includes('file') || tLower.includes('doc') || tLower.includes('pdf')) {
      badgeText = 'DOCUMENT INTEL';
    } else if (typeLower === 'social' || tLower.includes('social') || tLower.includes('github') || tLower.includes('reddit') || tLower.includes('youtube')) {
      badgeText = 'SOCIAL INTEL';
    } else if (typeLower === 'system' || tLower.includes('system') || tLower.includes('telemetry') || tLower.includes('matrix')) {
      badgeText = 'TELEMETRY';
    } else if (typeLower === 'weather' || tLower.includes('weather')) {
      badgeText = 'WEATHER';
    } else if (typeLower === 'flight' || tLower.includes('flight')) {
      badgeText = 'FLIGHTS';
    } else if (title) {
      let clean = title.replace(/\s+/g, ' ').trim().toUpperCase();
      badgeText = clean.length > 20 ? clean.substring(0, 18) + '…' : clean;
    }

    if (badge) {
      badge.innerText = badgeText;
      badge.title = title ? `${title}` : badgeText;
      badge.style.display = 'inline-flex';
    }

    if (contentText) {
      if (html) {
        contentText.innerHTML = html;
      } else {
        contentText.innerText = text || '';
      }
    }
  };

  window.copyCanvasContent = function(btn) {
    const contentText = document.getElementById('canvas-content-text');
    if (!contentText) return;
    const text = contentText.innerText || contentText.textContent || '';
    if (!text) return;

    if (typeof writeToSystemClipboard === 'function') {
      writeToSystemClipboard(text);
    }
    if (btn) {
      const origHtml = btn.innerHTML;
      btn.innerHTML = '<iconify-icon icon="solar:check-circle-bold"></iconify-icon> COPIED!';
      btn.classList.add('btn-primary');
      setTimeout(() => {
        btn.innerHTML = origHtml;
        btn.classList.remove('btn-primary');
      }, 1400);
    }
  };

  window.clearCanvasContent = function() {
    const emptyState = document.getElementById('canvas-empty-state');
    const activeContent = document.getElementById('canvas-active-content');
    const contentText = document.getElementById('canvas-content-text');
    const badge = document.getElementById('canvas-context-badge');

    if (contentText) contentText.innerHTML = '';
    if (activeContent) activeContent.style.display = 'none';
    if (badge) badge.style.display = 'none';
    if (emptyState) emptyState.style.display = 'flex';
  };

  let canvasExpanded = false;
  window.toggleCanvasExpand = function() {
    canvasExpanded = !canvasExpanded;
    const avatarFrame = document.getElementById('avatar-frame');
    const expandBtn = document.getElementById('canvas-expand-btn');
    if (avatarFrame) {
      avatarFrame.style.display = canvasExpanded ? 'none' : 'flex';
    }
    if (expandBtn) {
      expandBtn.innerHTML = `<iconify-icon icon="solar:${canvasExpanded ? 'minimize' : 'maximize'}-square-linear" style="font-size: 12px;"></iconify-icon>`;
      expandBtn.title = canvasExpanded ? 'Restore Split View' : 'Maximize Focus View';
    }
    if (window._resizeAvatar) window._resizeAvatar();
  };

  window.switchHudTab = function(viewId) {
    // Backward compatibility helper
  };

  // ── 9. Interactive Functions & Clipboard / WebSocket Dispatch ──
  function fallbackExecCopy(text) {
    try {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.style.position = 'fixed';
      textarea.style.left = '-9999px';
      textarea.style.top = '-9999px';
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      const ok = document.execCommand('copy');
      document.body.removeChild(textarea);
      return ok;
    } catch (e) {
      console.warn('ExecCommand copy fallback error:', e);
      return false;
    }
  }

  function writeToSystemClipboard(text) {
    if (!text) return Promise.resolve(false);

    // 1. Dispatch over WebSocket so backend sets Qt / OS clipboard directly
    try {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'set_clipboard', text: text }));
      }
    } catch (e) {
      console.warn('WS clipboard dispatch failed:', e);
    }

    // 2. Browser Clipboard API
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text).catch(err => {
        return fallbackExecCopy(text);
      });
    }
    return Promise.resolve(fallbackExecCopy(text));
  }

  function copySingleMessage(btn, text) {
    if (!text) {
      const parentMsg = btn.closest('.stream-msg');
      if (parentMsg) {
        const bodyEl = parentMsg.querySelector('.stream-msg-body');
        if (bodyEl) text = bodyEl.innerText.trim();
      }
    }
    if (!text) return;

    writeToSystemClipboard(text);

    if (btn) {
      const originalHtml = btn.innerHTML;
      btn.classList.add('copied');
      btn.innerHTML = '<iconify-icon icon="solar:check-circle-linear" style="font-size:12px; color:var(--pri, #22c55e);"></iconify-icon> <span style="font-size:8px; color:var(--pri, #22c55e);">COPIED</span>';
      setTimeout(() => {
        btn.classList.remove('copied');
        btn.innerHTML = originalHtml;
      }, 1600);
    }
  }

  function copyEntireStream(btn) {
    const box = document.getElementById('stream-box');
    if (!box) return;
    const messages = box.querySelectorAll('.stream-msg');
    if (!messages.length) return;

    let transcript = '=== ZEZO OS ACTIVITY & CHAT TRANSCRIPT ===\n\n';
    messages.forEach(msg => {
      const time = msg.querySelector('.mono.text-muted')?.innerText || '';
      const tag = msg.querySelector('.stream-msg-tag')?.innerText.trim() || 'LOG';
      const body = msg.querySelector('.stream-msg-body')?.innerText.trim() || '';
      transcript += `[${time}] [${tag}]: ${body}\n`;
    });

    writeToSystemClipboard(transcript);

    const targetBtn = btn || document.getElementById('copy-stream-btn');
    if (targetBtn) {
      const originalHtml = targetBtn.innerHTML;
      targetBtn.innerHTML = '<iconify-icon icon="solar:check-circle-linear" style="font-size:11px; color:var(--pri, #22c55e);"></iconify-icon> COPIED';
      targetBtn.style.borderColor = 'var(--pri, #22c55e)';
      targetBtn.style.color = 'var(--pri, #22c55e)';
      setTimeout(() => {
        targetBtn.innerHTML = originalHtml;
        targetBtn.style.borderColor = '';
        targetBtn.style.color = '';
      }, 1600);
    }
  }

  function copyLogModalBuffer(btn) {
    const buf = document.getElementById('log-modal-buffer');
    if (!buf) return;
    const text = buf.innerText || '';
    if (!text.trim()) return;

    writeToSystemClipboard(text);

    if (btn) {
      const originalHtml = btn.innerHTML;
      btn.innerHTML = '<iconify-icon icon="solar:check-circle-linear" style="font-size:11px; color:var(--pri, #22c55e);"></iconify-icon> COPIED';
      setTimeout(() => {
        btn.innerHTML = originalHtml;
      }, 1600);
    }
  }

  function clearStream() {
    document.getElementById('stream-box').innerHTML = `
      <div class="stream-msg stream-msg-sys">
        <div class="stream-msg-header">
          <div class="stream-msg-meta">
            <span class="mono text-muted">--:--:--</span>
            <span class="stream-msg-tag" style="background:rgba(255,255,255,0.06); color:var(--text-muted);">RESET</span>
          </div>
        </div>
        <div class="stream-msg-body" style="color:var(--text-muted); font-family:var(--font-mono); font-size:10px;">
          Activity stream reset. Ready for speech or prompt command.
        </div>
      </div>
    `;
  }

  // ── Keybinding Listeners ──
  window.addEventListener('keydown', (e) => {
    if (e.ctrlKey && (e.key === 'l' || e.key === 'L')) {
      e.preventDefault();
      openModal('log-modal');
    }
    if (e.key === 'Escape') {
      const openModalEl = document.querySelector('.modal-overlay.open');
      if (openModalEl) {
        closeModal(openModalEl.id);
      } else {
        closeSettingsDrawer();
        if (typeof window.executeInterrupt === 'function') window.executeInterrupt();
      }
    }
  });

  window.addEventListener('load', () => {
    if (typeof initWaveform === 'function') initWaveform();
