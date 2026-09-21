"""
Holographic AI head for the HUD centre — the thing that used to be a ring stack
with the assistant's name in the middle.

Design notes
------------
* **The face is real human geometry.** `core.avatar_mesh` builds the head around
  MediaPipe's canonical face model, so eyelids, nostrils, lips and cheekbones
  are measured anatomy rather than fitted curves. This renderer's whole job is
  to light it, pose it and animate it.
* **Software rendered, on purpose.** Everything is QPainter, so there is no
  OpenGL context, no shader compile, no GPU driver to disagree with us and no
  new pip dependency. It looks the same on a gaming rig, a 2013 laptop, a VM
  and a remote desktop session.
* **Lip-sync comes from the audio pipeline, not from the avatar.** `main.py`
  already computes a real RMS level off the PCM (`_pcm_level`) for both the mic
  and JARVIS's own output. The avatar just consumes that number, so there is no
  second audio path to fall out of sync. The mouth only tracks the level while
  JARVIS is *speaking* — during listening the same level drives the aura, so the
  head never lip-syncs to the user's voice.

The renderer is theme-agnostic: `paint()` takes its colours as arguments, which
is what lets the HueWheel accent picker retint the avatar for free.
"""

from __future__ import annotations

import math
import random

import numpy as np
from PyQt6.QtCore import QLineF, QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen, QPolygonF, QRadialGradient

from core.avatar_mesh import JAW_MAX, JAW_PIVOT, get_head_mesh

# Perspective camera distance in head-half-heights. Large enough that the nose
# does not balloon, small enough to keep a sense of depth.
_CAM_D = 4.6

# Wireframe opacity buckets, so the whole lattice draws in a handful of batched
# drawLines() calls instead of one call per line.
_BUCKETS = 4
_MIN_ALPHA = 0.05

# Resolution of the surface-shading colour ramp. Banding across a filled facet
# is far more visible than banding in line alpha, so this is fine-grained — and
# being a lookup it costs nothing per face.
_LUT_N = 192

# How far the brows travel at full lift, in head-half-heights. Derived, not
# tuned: the brow-to-eye gap is 0.198 and a real raise covers about a third of
# it, then the drawn landmarks only carry half the rig weight.
_BROW_LIFT = 0.14

# Mouth timing, as time constants in seconds rather than per-frame fractions.
# A fixed per-frame lerp silently changes speed with the frame rate: the HUD
# runs at 60 Hz here, throttles its paint to 30, and drops to 20 when idle, so
# the same constant meant three different mouths. These do not.
#
# Shutting is the fastest of the three, and it is measured rather than chosen.
# A short closure occupies a single 20 ms schedule frame, so the mouth has one
# step to reach it: at 20 ms the jaw got a third of the way and the closure
# vanished, at 12 ms it arrives, and going below that changes nothing because
# the analysis window is then the limit, not the smoothing. Halving it doubled
# the closures the mouth visibly makes across a test paragraph, 5 of 21 to 10,
# with no loss of opening on the vowels. Only the return to rest, once talking
# has actually stopped, is leisurely.
_TAU_OPEN = 0.022     # jaw dropping toward a vowel
_TAU_SHUT = 0.012     # lips closing on a consonant, mid-word
_TAU_REST = 0.055     # settling back to rest after speech ends
_TAU_SHAPE = 0.018    # viseme openness following the schedule

# Only the microphone path needs a level floor: it has one coarse RMS and no way
# to tell speech from room tone. JARVIS's own voice arrives as a per-20 ms
# schedule whose silences are already silent, so it needs no floor and must not
# have one — a floor there swallows the gaps between words.
_MIC_FLOOR = 0.14

# How far below this voice's own loud level counts as a closure: -20 dB, which
# is what a stop consonant actually drops to. Expressed as a ratio so it holds
# at any speaker volume.
_CLOSE_FRAC = 0.10


def _rate(dt: float, tau: float) -> float:
    """Per-frame lerp factor for an exponential approach with time constant
    `tau`. Frame-rate independent: the motion takes the same wall-clock time at
    20, 30 or 60 fps, and a long frame catches up instead of stalling."""
    return 1.0 - math.exp(-dt / tau)


def _c(col: QColor, a: float) -> QColor:
    """Copy of `col` at alpha `a` (0-255, clamped)."""
    q = QColor(col)
    q.setAlpha(int(max(0.0, min(255.0, a))))
    return q


def _blend(bg: QColor, col: QColor, a: float) -> QColor:
    """`col` at alpha `a` pre-mixed onto `bg`, returned fully **opaque**.

    Qt's raster engine has a fast path for opaque antialiased lines and a much
    slower blended path for everything else — measured at 1.0 ms versus 2.9 ms
    for the same 780 lines. The HUD paints a flat background behind the avatar,
    so mixing the alpha in by hand is visually equivalent and three times cheaper.
    """
    f = max(0.0, min(1.0, a / 255.0))
    return QColor(int(bg.red() + (col.red() - bg.red()) * f),
                  int(bg.green() + (col.green() - bg.green()) * f),
                  int(bg.blue() + (col.blue() - bg.blue()) * f))


class HoloAvatar:
    """Animated holographic head. One instance per HUD canvas.

    Lifecycle:
        av = HoloAvatar()
        av.step(dt, amp, speaking=..., muted=...)          # once per tick
        av.paint(painter, cx, cy, r, primary, accent, bg)  # once per frame
    """

    # Look: True paints a lit, solid head with a wireframe over it; False is a
    # see-through glass wireframe. Flip here, or per instance.
    shaded = True

    def __init__(self) -> None:
        mesh = get_head_mesh()
        self._v0 = mesh["verts"]
        self._n0 = mesh["normals"]
        self._jaw = mesh["jaw"]
        self._brow_w = mesh["brow"]
        self._lips_w = mesh["lips"]
        self._lip_c = mesh["lip_centre"]
        self._fade = mesh["fade"]
        self._f = mesh["faces"]
        self._fgroup = mesh["face_group"]
        self._fa, self._fb, self._fc = (self._f[:, i] for i in range(3))
        self._e0 = mesh["edges"][:, 0]
        self._e1 = mesh["edges"][:, 1]
        self._lm = mesh["landmarks"]
        # The inner-lip ring runs lower-lip left→right, then upper-lip back.
        # Splitting it lets the upper arc anchor a strip of teeth, which is what
        # keeps an open mouth from reading as a hole punched in the face.
        lips_in = mesh["landmarks"]["lips_in"]
        self._lip_up = np.concatenate([lips_in[10:], lips_in[:1]])

        # Crown (+1.0) down to the bottom of the neck, in head-half-heights.
        # Callers size the head to the room they have with this.
        self.SPAN = mesh["span"][0] - mesh["span"][1]

        self._lut_cache: list = []
        self._lut_key = None

        n = self._v0.shape[0]
        self._v = np.empty((n, 3), dtype=np.float32)

        self._t = 0.0
        self._sway = 0.0           # integrated sway phase — see step()
        self._yaw = 0.0
        self._pitch = 0.0
        self._mouth = 0.0          # 0..1 smoothed jaw opening
        self._glow = 0.0           # 0..1 smoothed overall energy
        self._scan = -1.6          # vertical position of the energy sweep
        self._blink = 0.0          # 0 = open, 1 = shut
        self._blink_at = 3.0

        # ── expression ──────────────────────────────────────────────────────
        # Speech is not just a moving jaw. Brows ride the loudness envelope,
        # eyes widen with the brows, and the gaze flicks between fixation
        # points — those three are what make it read as talking rather than as
        # a puppet chewing.
        self._amp_slow = 0.0
        self._expr = 0.0
        self._expr_tgt = 0.0
        self._expr_at = 0.0
        self._brow = 0.0           # smoothed brow lift, -0.4 .. 1.2
        self._emph = 0.0           # syllable emphasis, drives the head nod
        self._gaze = [0.0, 0.0]
        self._gaze_tgt = [0.0, 0.0]
        self._gaze_at = 0.0

        # ── state expression ────────────────────────────────────────────────
        # The face is the fastest status indicator in the app: you read a gaze
        # before you read a word. Saccades orbit a bias that the assistant's
        # state moves — eyes off to the side while it thinks, back on you while
        # it listens, lids low while it sleeps.
        self._gaze_bias = [0.0, 0.0]
        self._bias_tgt = [0.0, 0.0]
        self._bias_at = 0.0
        self._lids = 1.0           # 1 = wide, 0 = shut; low while asleep
        self._brow_bias = 0.0      # concentration pulls the brows down
        self._glance = None        # (dx, dy, until_t) — a deliberate look

        # ── viseme ──────────────────────────────────────────────────────────
        # Loudness alone only answers "how far open", which is why an RMS-driven
        # mouth flaps rather than speaks. These two carry the *shape*: how open
        # the jaw is for this sound, and whether the lips are spread (/i/) or
        # rounded (/u/). They come from a formant read of the audio actually
        # being played — see `_pcm_visemes` in main.py.
        self._v_open = 1.0
        self._v_wide = 0.0
        self._wide = 0.0           # smoothed lip spread, -1 round .. +1 spread
        self._v_peak = 0.18        # running estimate of this voice's loud level

    # ── animation ───────────────────────────────────────────────────────────

    def _mouth_step(self, dt: float, amp: float, live: bool,
                    v_open: float | None, v_level: float | None) -> None:
        """One increment of the jaw. Called once per viseme frame while JARVIS
        speaks, once per rendered frame otherwise."""
        if v_open is None:
            shape = 1.0
        else:
            self._v_open += (v_open - self._v_open) * _rate(dt, _TAU_SHAPE)
            shape = self._v_open

        if v_level is None:
            gated = max(0.0, (amp - _MIC_FLOOR) / (1.0 - _MIC_FLOOR))
            drive = (gated ** 0.6) * (shape ** 0.75)
        else:
            # Speech RMS spends most of its time well below full scale, so the
            # raw value alone would only ever half-open the jaw. Normalise it
            # against a running estimate of this voice's own loud level rather
            # than a constant: it then reads the same whether the user has the
            # volume low or the model happens to be speaking softly.
            self._v_peak = max(v_level, self._v_peak - dt * 0.55)
            ref = max(0.18, self._v_peak)
            # The floor is a fraction of this voice's own loud level, not a
            # fixed number, so it means the same thing at any volume and in any
            # language. A stop consonant drops 20 dB or more below the vowels
            # around it, which is this ratio — so a real closure lands at
            # exactly zero rather than at some small positive value the curve
            # would otherwise lift back up. That lift is what kept the mouth
            # from ever quite shutting between words.
            q = (v_level - _CLOSE_FRAC * ref) / (ref * (1.0 - _CLOSE_FRAC))
            drive = max(0.0, min(1.0, q)) ** 0.85 * (shape ** 0.75)

        target = min(1.0, drive) if live else 0.0
        if target > self._mouth:
            tau = _TAU_OPEN
        elif live:
            tau = _TAU_SHUT      # mid-word: a consonant, and it must shut now
        else:
            tau = _TAU_REST      # speech is over; settle, don't snap
        self._mouth += (target - self._mouth) * _rate(dt, tau)
        if self._mouth < 0.002:
            self._mouth = 0.0

    def step(self, dt: float, amp: float, speaking: bool = False,
             muted: bool = False, state: str = "",
             v_open: float | None = None, v_wide: float = 0.0,
             v_level: float | None = None,
             v_seq: list | None = None, v_hop: float = 0.02) -> None:
        """Advance the animation.

        `amp` is the 0..1 display audio level. `v_open` / `v_wide` / `v_level`
        are the viseme schedule's shape and true level for this instant; passing
        None falls back to loudness-only articulation, which is what the
        microphone path uses. `v_seq` is every schedule frame the last rendered
        frame spanned, so no closure is lost when the paint rate drops.
        """
        dt = max(0.001, min(0.10, float(dt)))
        self._t += dt
        t = self._t
        amp = max(0.0, min(1.0, float(amp)))
        live = speaking and not muted

        # Idle sway. The phase is *integrated* rather than taken as
        # sin(t * rate * speed): multiplying absolute time by a speed that
        # changes when JARVIS starts or stops talking jumps the phase by
        # t * rate * delta, which after a minute of uptime is several radians
        # and visibly teleports the head the instant a sentence ends.
        speed = (1.0 if not muted else 0.55) * (1.25 if live else 1.0)
        self._sway += dt * speed
        s = self._sway
        self._yaw = 0.26 * math.sin(s * 0.31) + 0.09 * math.sin(s * 0.73 + 1.3)
        self._pitch = (0.060 * math.sin(s * 0.23 + 0.7)
                       + 0.024 * math.sin(s * 0.61))

        # Mouth. Which level is driving it matters more than any rate here.
        #
        # `v_level` is this 20 ms frame's own RMS, taken from the very audio
        # about to be heard, so its silences are real silences. `amp` is the
        # waveform display's level, and that one is a *peak hold*: it keeps the
        # loudest value it has seen and decays gently, on purpose, so the bars
        # do not stutter between audio chunks. Driving a mouth from a peak hold
        # is why the gaps between words never closed — the hold spans exactly
        # the consonant it was supposed to reveal. So the schedule drives the
        # jaw whenever there is one, and `amp` is left to the microphone path,
        # which has nothing better.
        # Advance the mouth once per *schedule* frame rather than once per
        # rendered frame. A bilabial closure lasts around 40 ms — two frames of
        # a 50 Hz schedule — and the HUD throttles its paint to 30 fps and to 20
        # when idle. Point-sampling at 20 fps steps 50 ms at a time, so a whole
        # closure can fall between two samples and simply never be seen; that is
        # information loss no smoothing constant can recover. Sub-stepping costs
        # a few float operations per frame and makes the mouth identical at 20,
        # 30 and 60 fps.
        # An empty list is meaningful and is not the same as None: it says a
        # schedule is playing but this tick landed inside a frame already
        # spoken. The mouth's clock is the schedule's, so the right thing then
        # is to do nothing. Re-stepping the same frame — which is what a
        # truthiness test here would do — advances the jaw twice for one 20 ms
        # of audio, and at 60 fps that alone made the mouth behave differently
        # than at 20.
        if v_seq is not None:
            for lv, op, _wd in v_seq:
                self._mouth_step(v_hop, amp, live, op, lv)
        else:
            self._mouth_step(dt, amp, live, v_open, v_level)

        # Syllable emphasis. Applied unconditionally: `_emph` decays to zero on
        # its own once the mouth closes, whereas gating it on `live` deleted the
        # whole offset in a single frame and snapped the head at sentence end.
        self._emph += (self._mouth - self._emph) * _rate(
            dt, 0.055 if self._mouth > self._emph else 0.32)
        self._pitch -= self._emph * 0.028
        self._yaw += 0.018 * math.sin(t * 1.7) * self._emph

        # Loudness envelope, deliberately lazier than the mouth: brows track the
        # shape of a phrase, not individual syllables.
        env = amp if live else 0.0
        self._amp_slow += (env - self._amp_slow) * _rate(
            dt, 0.16 if env > self._amp_slow else 0.36)

        if live:
            if t >= self._expr_at:
                self._expr_tgt = random.uniform(-0.35, 1.0)
                self._expr_at = t + 1.1 + 2.0 * random.random()
        else:
            self._expr_tgt = 0.0
            self._expr_at = t + 0.8
        self._expr += (self._expr_tgt - self._expr) * 0.075

        brow_t = 0.55 * self._amp_slow + 0.60 * self._expr + self._brow_bias
        self._brow += (max(-0.4, min(1.2, brow_t)) - self._brow) * 0.20

        # ── what the state does to the face ─────────────────────────────────
        st = (state or "").upper()
        thinking = st in ("THINKING", "PROCESSING")
        asleep = st in ("SLEEPING", "STANDBY", "OFFLINE")

        if thinking:
            # People look away to think, and hold it. The direction re-rolls
            # slowly so it reads as thought rather than as scanning.
            if t >= self._bias_at:
                self._bias_tgt = [random.choice((-1.0, 1.0)) * random.uniform(0.45, 0.8),
                                  random.uniform(0.25, 0.55)]
                self._bias_at = t + 1.4 + 1.6 * random.random()
            brow_bias, lid_tgt = -0.28, 0.94
        elif asleep:
            self._bias_tgt = [0.0, -0.25]
            brow_bias, lid_tgt = -0.05, 0.22
        else:
            # LISTENING / idle / speaking: eyes come back to the user.
            self._bias_tgt = [0.0, 0.0]
            self._bias_at = 0.0
            brow_bias = 0.10 if st == "LISTENING" else 0.0
            lid_tgt = 1.0

        for i in (0, 1):
            self._gaze_bias[i] += (self._bias_tgt[i] - self._gaze_bias[i]) * 0.06
        self._lids += (lid_tgt - self._lids) * 0.08
        self._brow_bias += (brow_bias - self._brow_bias) * 0.06

        # Gaze: saccades are near-instant jumps between fixations, and they get
        # more frequent when there is something to say. While thinking they slow
        # right down — a darting eye reads as nervous, not thoughtful.
        if t >= self._gaze_at:
            reach = 0.9 if live else (0.35 if thinking else 0.55)
            self._gaze_tgt = [random.uniform(-1.0, 1.0) * reach,
                              random.uniform(-1.0, 1.0) * reach * 0.55]
            if live:
                self._gaze_at = t + 0.55 + 1.7 * random.random()
            elif thinking:
                self._gaze_at = t + 1.8 + 2.4 * random.random()
            else:
                self._gaze_at = t + 1.3 + 2.8 * random.random()

        # A deliberate glance (something appeared on screen) overrides the
        # wandering for a moment, then hands control back.
        if self._glance is not None:
            gx, gy, until = self._glance
            if t < until:
                self._gaze_tgt = [gx, gy]
            else:
                self._glance = None

        for i, b in enumerate(self._gaze_bias):
            tgt = max(-1.0, min(1.0, self._gaze_tgt[i] + b))
            self._gaze[i] += (tgt - self._gaze[i]) * 0.30

        # Lips lead the jaw slightly in real speech, so they track a touch
        # faster; they also relax to neutral the moment the voice stops.
        wide_t = v_wide if (live and v_open is not None) else 0.0
        self._wide += (max(-1.0, min(1.0, wide_t)) - self._wide) * _rate(dt, 0.030)

        self._glow += ((0.0 if muted else amp) - self._glow) * (
            0.35 if (0.0 if muted else amp) > self._glow else 0.10)

        self._scan += dt * (0.55 + 1.5 * self._glow)
        if self._scan > 1.35:
            self._scan = -1.75

        if self._blink > 0.0:
            self._blink = max(0.0, self._blink - dt * 8.5)
        elif t >= self._blink_at:
            # Concentration suppresses blinking; a sleeping face has no need of
            # it at all, since the lids are already down.
            if asleep:
                self._blink_at = t + 6.0
            else:
                self._blink = 1.0
                gap = 5.5 if thinking else 3.4
                self._blink_at = t + gap + 3.1 * random.random()

    def glance(self, dx: float, dy: float, hold: float = 1.1) -> None:
        """Look deliberately somewhere for `hold` seconds, then wander again.

        Used when something appears on screen: a face that looks at what just
        showed up tells the user it landed, without a word being spoken.
        """
        self._glance = (max(-1.0, min(1.0, float(dx))),
                        max(-1.0, min(1.0, float(dy))),
                        self._t + max(0.1, float(hold)))

    # ── posing ──────────────────────────────────────────────────────────────

    def _pose(self):
        """Jaw drop, brow lift and head rotation, applied to the real geometry."""
        v = self._v
        np.copyto(v, self._v0)

        if self._brow > 0.004 or self._brow < -0.004:
            # The brow-to-eye gap is 0.198 head-half-heights and a real raise
            # moves a third of it. The old 0.045 — halved again by the landmark
            # weights, which average 0.5 — worked out to six pixels on a 250 px
            # head, which is to say invisible.
            v[:, 1] += self._brow_w * (self._brow * _BROW_LIFT)

        if abs(self._wide) > 0.01 and self._mouth > 0.0:
            # Spread pulls the corners out and flattens the lips back; rounding
            # draws them in and pushes them forward into a purse.
            k = self._lips_w * (self._wide * self._mouth)
            v[:, 0] += k * (v[:, 0] - self._lip_c[0]) * 0.55
            v[:, 1] += k * (v[:, 1] - self._lip_c[1]) * 0.30
            v[:, 2] -= k * 0.055

        if self._mouth > 0.004:
            px, py, pz = JAW_PIVOT
            ang = self._jaw * (self._mouth * JAW_MAX)
            ca, sa = np.cos(ang), np.sin(ang)
            dy = v[:, 1] - py
            dz = v[:, 2] - pz
            v[:, 1] = py + dy * ca - dz * sa
            v[:, 2] = pz + dy * sa + dz * ca

        cy, sy = math.cos(self._yaw), math.sin(self._yaw)
        cp, sp = math.cos(self._pitch), math.sin(self._pitch)
        m = np.array([
            [cy, 0.0, sy],
            [sp * sy, cp, -sp * cy],
            [-cp * sy, sp, cp * cy],
        ], dtype=np.float32)

        return v @ m.T, self._n0 @ m.T

    # ── rendering ───────────────────────────────────────────────────────────

    def _lut(self, bg: QColor, primary: QColor):
        """Cached ramp of opaque surface brushes from `bg` to `primary`."""
        key = (bg.rgb(), primary.rgb())
        if self._lut_key != key:
            self._lut_cache = [QBrush(_blend(bg, primary, 255.0 * (i + 0.5) / _LUT_N))
                               for i in range(_LUT_N)]
            self._lut_key = key
        return self._lut_cache

    def paint(self, p: QPainter, cx: float, cy: float, r: float,
              primary: QColor, accent: QColor, bg: QColor | None = None) -> None:
        """Draw the avatar with its head centre at (cx, cy).

        `r` is the head's half-height in pixels — the caller owns the layout, so
        the HUD can fit the head to whatever room the status line leaves it.
        """
        if bg is None:
            bg = QColor(0, 0, 0)
        amp = self._glow
        verts, norms = self._pose()

        # ── aura ────────────────────────────────────────────────────────────
        ar = r * 1.95
        grad = QRadialGradient(cx, cy, ar)
        grad.setColorAt(0.00, _c(primary, 34 + 66 * amp))
        grad.setColorAt(0.38, _c(primary, 20 + 40 * amp))
        grad.setColorAt(1.00, _c(primary, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(QRectF(cx - ar, cy - ar, ar * 2, ar * 2))

        # ── project ─────────────────────────────────────────────────────────
        w = _CAM_D - verts[:, 2]
        np.maximum(w, 0.35, out=w)
        k = (_CAM_D / w) * r
        xs = cx + verts[:, 0] * k
        ys = cy - verts[:, 1] * k

        # Highly polished solid 3D sculpt surface (no wireframe, no dots)
        self._paint_surface(p, xs, ys, norms, verts, primary, accent, bg, amp)
        self._paint_features(p, xs, ys, norms, r, primary, accent, bg, amp)

    def _paint_surface(self, p: QPainter, xs, ys, norms, verts,
                       primary: QColor, accent: QColor, bg: QColor, amp: float) -> None:
        """Render smooth, highly polished studio-lit 3D sculpt surfaces with specular sheen."""
        a, b, c = self._fa, self._fb, self._fc

        # Compute accurate facet normals
        fn = np.cross(verts[b] - verts[a], verts[c] - verts[a])
        fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-9)
        ref = norms[a] + norms[b] + norms[c]
        fn *= np.sign((fn * ref).sum(1))[:, None]

        nz = fn[:, 2]
        area = np.abs((xs[b] - xs[a]) * (ys[c] - ys[a])
                      - (xs[c] - xs[a]) * (ys[b] - ys[a]))
        vis = np.flatnonzero((nz > -0.05) & (area > 1.5))
        if vis.size == 0:
            return
        fn = fn[vis]
        nz = nz[vis]

        ax, ay = xs[a][vis], ys[a][vis]
        bx, by = xs[b][vis], ys[b][vis]
        cxx, cyy = xs[c][vis], ys[c][vis]

        # Multi-point studio lighting for highly polished solid form:
        # 1. Main Key Light (top-left, high angle)
        l_key = np.clip(fn[:, 0] * -0.50 + fn[:, 1] * 0.55 + nz * 0.45, 0.0, 1.0)
        # 2. Fill Light (bottom-right soft bounce)
        l_fill = np.clip(fn[:, 0] * 0.35 + fn[:, 1] * -0.20 + nz * 0.25, 0.0, 1.0) * 0.30
        # 3. Specular Highlight (Blinn-Phong glossy reflection for high polish)
        half_vec = np.array([-0.35, 0.40, 0.84], dtype=np.float32)
        half_vec /= np.linalg.norm(half_vec)
        spec = np.clip((fn * half_vec).sum(1), 0.0, 1.0) ** 14.0 * 0.45
        # 4. Luminous Silhouette Rim Fresnel
        fres = np.clip(1.0 - np.abs(nz), 0.0, 1.0) ** 2.2 * 0.40

        # Composite polished luminance
        lum = 0.16 + 0.55 * (l_key ** 1.1) + l_fill + spec + fres
        lum *= (self._fade[a][vis] + self._fade[b][vis] + self._fade[c][vis]) / 3.0
        lum *= 0.82 + 0.25 * amp

        idx = np.clip((lum * _LUT_N).astype(np.int32), 0, _LUT_N - 1)

        fz = (verts[a, 2][vis] + verts[b, 2][vis] + verts[c, 2][vis]) * (1.0 / 3.0)
        order = np.argsort(self._fgroup[vis] * 1000.0 + fz, kind="stable")
        tris = np.stack([ax, ay, bx, by, cxx, cyy], axis=1)[order].tolist()
        shade = idx[order].tolist()
        lut = self._lut(bg, primary)

        # Draw polished solid facets
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        for q, sh in zip(tris, shade):
            p.setBrush(lut[sh])
            p.drawPolygon(QPolygonF([QPointF(q[0], q[1]), QPointF(q[2], q[3]),
                                     QPointF(q[4], q[5])]))

    # ── face features ───────────────────────────────────────────────────────

    def _ring(self, xs, ys, idx) -> QPolygonF:
        return QPolygonF([QPointF(float(x), float(y))
                          for x, y in zip(xs[idx], ys[idx])])

    def _paint_features(self, p: QPainter, xs, ys, norms, r: float,
                        primary: QColor, accent: QColor, bg: QColor,
                        amp: float) -> None:
        """Render masculine sculpted brows, intelligent living gaze with blinking, and natural lipstick-free lips."""
        face = max(0.0, math.cos(self._yaw) * math.cos(self._pitch)) ** 2
        if face < 0.02:
            return

        lm = self._lm
        vis = max(0.0, min(1.0, 1.0 - self._blink))

        # ── 1. Sculpted Masculine Eyebrows ──────────────────────────────────
        for key in ("brow_l", "brow_r"):
            idx = lm[key]
            bx, by = xs[idx], ys[idx]
            n_pts = len(bx)
            if n_pts >= 2:
                top_pts, bot_pts = [], []
                for i in range(n_pts):
                    # Natural brow taper: thicker medial head, sharp lateral arch
                    taper = math.sin((i / max(1, n_pts - 1)) * math.pi * 0.75 + 0.20)
                    thick = max(1.2, r * 0.020 * taper)
                    top_pts.append(QPointF(float(bx[i]), float(by[i]) - thick))
                    bot_pts.append(QPointF(float(bx[i]), float(by[i]) + thick * 0.35))
                
                brow_poly = QPolygonF(top_pts + bot_pts[::-1])
                # Brow base shadow
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(_blend(bg, primary, 70 * face)))
                p.drawPolygon(brow_poly)
                # Masculine defined brow line
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(_blend(bg, primary, 240 * face), 1.3))
                p.drawPolyline(QPolygonF(top_pts))

        # ── 2. Intelligent Living Eyes (Open Gaze + Natural Blinking) ────────
        for key in ("eye_l", "eye_r"):
            idx = lm[key]
            ex, ey = xs[idx], ys[idx]
            mid_y = float(ey.mean())
            
            # Sclera & Eye Socket Geometry
            poly = QPolygonF([QPointF(float(a), float(b)) for a, b in zip(ex, ey)])
            br = poly.boundingRect()
            
            # Upper eyelid crease line (carved into brow socket)
            n_eye = len(idx)
            half = n_eye // 2
            crease = [QPointF(float(ex[i]), float(ey[i]) - r * 0.018) for i in range(half)]
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(_blend(bg, primary, 110 * face), 1.0))
            p.drawPolyline(QPolygonF(crease))

            if vis > 0.20:
                # ── OPEN LIVING EYE ──
                # Socket shadow & sclera
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(_blend(bg, primary, 40 * face)))
                p.drawPolygon(poly)
                # Sclera surface
                p.setBrush(QBrush(_blend(bg, primary, (95 + 25 * vis) * face)))
                p.drawPolygon(poly)

                # Gaze center
                gx = br.center().x() + self._gaze[0] * br.width() * 0.18
                gy = br.center().y() + self._gaze[1] * br.height() * 0.20
                cpt = QPointF(gx, gy)
                rad = min(br.height() * 0.62, br.width() * 0.21)

                # Iris (Living depth with primary/accent tone)
                p.setBrush(QBrush(_c(primary, int((170 + 70 * amp) * face * vis))))
                p.drawEllipse(cpt, rad, rad * vis)
                # Inner iris ring
                p.setBrush(QBrush(_c(accent, int((130 + 90 * amp) * face * vis))))
                p.drawEllipse(cpt, rad * 0.65, rad * 0.65 * vis)
                # Pupil (Dark, focused, intelligent)
                p.setBrush(QBrush(_c(bg, int(255 * face * vis))))
                p.drawEllipse(cpt, rad * 0.38, rad * 0.38 * vis)
                # Corneal Specular Catchlight (Glint that brings the eye to life!)
                glint = QPointF(gx - rad * 0.24, gy - rad * 0.24 * vis)
                p.setBrush(QBrush(_c(QColor(255, 255, 255), int(240 * face * vis))))
                p.drawEllipse(glint, max(1.0, rad * 0.16), max(1.0, rad * 0.16 * vis))

                # Upper eyelid margin shadow over top of eye
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(_blend(bg, primary, 240 * face), 1.8))
                top_arc = [QPointF(float(ex[i]), float(ey[i])) for i in range(half)]
                p.drawPolyline(QPolygonF(top_arc))

                # Lower eyelid rim
                p.setPen(QPen(_blend(bg, primary, 130 * face), 1.0))
                bot_arc = [QPointF(float(ex[i]), float(ey[i])) for i in range(half, n_eye)]
                if len(bot_arc) > 1:
                    p.drawPolyline(QPolygonF(bot_arc))
            else:
                # ── CLOSED / BLINKING EYE ──
                # Natural closed lid seam
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(_blend(bg, primary, 60 * face)))
                p.drawPolygon(poly)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(_blend(bg, primary, 230 * face), 2.0))
                lid_seam = [QPointF(float(ex[i]), mid_y + (ey[i] - mid_y) * 0.12) for i in range(half)]
                p.drawPolyline(QPolygonF(lid_seam))

        # ── 3. Sculpted Natural Lips (NO LIPSTICK / NO GREEN FILL) ───────────
        inner = self._ring(xs, ys, lm["lips_in"])
        outer = self._ring(xs, ys, lm["lips_out"])

        # Subtle natural lip shading (matching skin material, subtle depth)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(_blend(bg, primary, 85 * face)))
        p.drawPolygon(outer)

        # Mouth cavity when speaking
        if self._mouth > 0.02:
            # Dark oral cavity
            p.setBrush(QBrush(_blend(bg, primary, 20)))
            p.drawPolygon(inner)
            # Upper teeth edge (clean anatomical speech cue)
            ux, uy = xs[self._lip_up], ys[self._lip_up]
            open_h = inner.boundingRect().height()
            th = open_h * 0.28
            pts = [QPointF(float(x), float(y)) for x, y in zip(ux, uy)]
            pts += [QPointF(float(x), float(y) + th) for x, y in zip(ux[::-1], uy[::-1])]
            p.setBrush(QBrush(_blend(bg, primary, 180 + 50 * self._mouth)))
            p.drawPolygon(QPolygonF(pts))

        # Natural lip contours and subtle philtrum seam
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(_blend(bg, primary, (150 + 60 * self._mouth) * face), 1.3))
        p.drawPolygon(inner)
        p.setPen(QPen(_blend(bg, primary, 110 * face), 1.0))
        p.drawPolygon(outer)
