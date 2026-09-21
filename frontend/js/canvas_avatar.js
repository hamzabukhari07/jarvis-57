/**
 * 60 FPS HTML5 Canvas Visualizer for ZEZO OS.
 * Renders the holographic reactor core avatar and the dual-harmonic sinusoidal waveform.
 */

export class AvatarVisualizer {
    constructor(avatarCanvasId, waveformCanvasId) {
        this.avatarCanvas = document.getElementById(avatarCanvasId);
        this.waveformCanvas = document.getElementById(waveformCanvasId);
        this.avatarCtx = this.avatarCanvas ? this.avatarCanvas.getContext('2d') : null;
        this.waveformCtx = this.waveformCanvas ? this.waveformCanvas.getContext('2d') : null;

        this.state = 'IDLE'; // IDLE, LISTENING, SPEAKING, THINKING, MUTED
        this.accentColor = '#f24e1e';
        this.volume = 0.0;
        this.time = 0;
        this.particles = [];
        this.animationId = null;

        this._initParticles();
        this._handleResize();
        window.addEventListener('resize', () => this._handleResize());
    }

    _handleResize() {
        if (this.avatarCanvas) {
            const rect = this.avatarCanvas.getBoundingClientRect();
            this.avatarCanvas.width = (rect.width || 360) * window.devicePixelRatio;
            this.avatarCanvas.height = (rect.height || 360) * window.devicePixelRatio;
        }
        if (this.waveformCanvas) {
            const rect = this.waveformCanvas.getBoundingClientRect();
            this.waveformCanvas.width = (rect.width || 120) * window.devicePixelRatio;
            this.waveformCanvas.height = (rect.height || 24) * window.devicePixelRatio;
        }
    }

    _initParticles() {
        this.particles = [];
        const count = 36;
        for (let i = 0; i < count; i++) {
            this.particles.push({
                angle: (i / count) * Math.PI * 2,
                distance: 60 + Math.random() * 80,
                speed: 0.005 + Math.random() * 0.01,
                size: 1 + Math.random() * 2,
                alpha: 0.2 + Math.random() * 0.6,
            });
        }
    }

    setState(newState) {
        this.state = newState ? newState.toUpperCase() : 'IDLE';
    }

    setAccent(hexColor) {
        if (hexColor) this.accentColor = hexColor;
    }

    setVolume(vol) {
        this.volume = Math.min(1.0, Math.max(0.0, vol || 0.0));
    }

    start() {
        if (this.animationId) return;
        const render = () => {
            this.time += 0.016;
            this._renderAvatar();
            this._renderWaveform();
            this.animationId = requestAnimationFrame(render);
        };
        this.animationId = requestAnimationFrame(render);
    }

    stop() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
    }

    _renderAvatar() {
        if (!this.avatarCtx || !this.avatarCanvas) return;
        const ctx = this.avatarCtx;
        const w = this.avatarCanvas.width;
        const h = this.avatarCanvas.height;
        const cx = w / 2;
        const cy = h / 2;

        ctx.clearRect(0, 0, w, h);

        // State-based dynamic parameters
        let speedMult = 1.0;
        let ringGlow = 0.4;
        let coreRadius = 26;
        let color = this.accentColor;

        if (this.state === 'LISTENING') {
            color = '#22c55e'; // Green
            speedMult = 1.2;
            ringGlow = 0.6;
        } else if (this.state === 'SPEAKING') {
            color = this.accentColor;
            speedMult = 1.8;
            coreRadius = 28 + Math.sin(this.time * 8) * 4;
            ringGlow = 0.8;
        } else if (this.state === 'THINKING') {
            color = '#06b6d4'; // Cyan
            speedMult = 2.4;
            ringGlow = 0.7;
        } else if (this.state === 'MUTED') {
            color = '#ef4444'; // Red
            speedMult = 0.2;
            ringGlow = 0.2;
        }

        // ── 1. Outer Orbiting Ring ──
        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(this.time * 0.3 * speedMult);
        ctx.strokeStyle = color;
        ctx.globalAlpha = 0.25;
        ctx.lineWidth = 1 * window.devicePixelRatio;
        ctx.beginPath();
        ctx.arc(0, 0, 110 * (w / 360), 0, Math.PI * 2);
        ctx.stroke();

        // 4 Geometric Notch ticks on outer ring
        for (let i = 0; i < 4; i++) {
            const a = (i * Math.PI) / 2;
            const r1 = 104 * (w / 360);
            const r2 = 116 * (w / 360);
            ctx.beginPath();
            ctx.moveTo(Math.cos(a) * r1, Math.sin(a) * r1);
            ctx.lineTo(Math.cos(a) * r2, Math.sin(a) * r2);
            ctx.stroke();
        }
        ctx.restore();

        // ── 2. Segmented Counter-Rotating Arc Ring ──
        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(-this.time * 0.5 * speedMult);
        ctx.strokeStyle = color;
        ctx.globalAlpha = 0.5;
        ctx.lineWidth = 1.5 * window.devicePixelRatio;

        const segs = 3;
        const segLen = (Math.PI * 2) / segs - 0.4;
        for (let i = 0; i < segs; i++) {
            const startA = i * ((Math.PI * 2) / segs);
            ctx.beginPath();
            ctx.arc(0, 0, 75 * (w / 360), startA, startA + segLen);
            ctx.stroke();
        }
        ctx.restore();

        // ── 3. Floating Energy Nodes ──
        ctx.save();
        ctx.translate(cx, cy);
        this.particles.forEach(p => {
            p.angle += p.speed * speedMult;
            const px = Math.cos(p.angle) * p.distance * (w / 360);
            const py = Math.sin(p.angle) * p.distance * (h / 360);
            ctx.fillStyle = color;
            ctx.globalAlpha = p.alpha * ringGlow;
            ctx.fillRect(px, py, p.size * window.devicePixelRatio, p.size * window.devicePixelRatio);
        });
        ctx.restore();

        // ── 4. Glowing Central Core Reactor ──
        ctx.save();
        ctx.translate(cx, cy);

        // Core ambient bloom gradient
        const radGrd = ctx.createRadialGradient(0, 0, 4, 0, 0, 60 * (w / 360));
        radGrd.addColorStop(0, color);
        radGrd.addColorStop(0.3, color);
        radGrd.addColorStop(1, 'rgba(0, 0, 0, 0)');
        ctx.globalAlpha = ringGlow * 0.4;
        ctx.fillStyle = radGrd;
        ctx.beginPath();
        ctx.arc(0, 0, 60 * (w / 360), 0, Math.PI * 2);
        ctx.fill();

        // Central diamond / circle node
        ctx.globalAlpha = 0.9;
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(0, 0, coreRadius * (w / 360), 0, Math.PI * 2);
        ctx.fill();

        // Inner white nucleus
        ctx.globalAlpha = 1.0;
        ctx.fillStyle = '#ffffff';
        ctx.beginPath();
        ctx.arc(0, 0, 6 * (w / 360), 0, Math.PI * 2);
        ctx.fill();

        ctx.restore();
    }

    _renderWaveform() {
        if (!this.waveformCtx || !this.waveformCanvas) return;
        const ctx = this.waveformCtx;
        const w = this.waveformCanvas.width;
        const h = this.waveformCanvas.height;
        const cy = h / 2;

        ctx.clearRect(0, 0, w, h);

        let color = this.accentColor;
        let amp = 2.0;
        let freq = 0.04;

        if (this.state === 'LISTENING') {
            color = '#22c55e';
            amp = 4.0;
            freq = 0.06;
        } else if (this.state === 'SPEAKING') {
            color = this.accentColor;
            amp = 8.0;
            freq = 0.08;
        } else if (this.state === 'THINKING') {
            color = '#06b6d4';
            amp = 5.0;
            freq = 0.12;
        } else if (this.state === 'MUTED') {
            color = '#ef4444';
            amp = 0.5;
        }

        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5 * window.devicePixelRatio;
        ctx.beginPath();

        const points = 40;
        for (let i = 0; i <= points; i++) {
            const x = (i / points) * w;
            // Dual-harmonic sinusoidal waveform with edge-tapering envelope
            const envelope = Math.sin((i / points) * Math.PI); // 0 at edges, 1 in center
            const wave1 = Math.sin(this.time * 6 + i * freq * 10);
            const wave2 = Math.sin(this.time * 3 + i * freq * 5) * 0.5;
            const y = cy + (wave1 + wave2) * amp * envelope * window.devicePixelRatio;

            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.stroke();
    }
}
