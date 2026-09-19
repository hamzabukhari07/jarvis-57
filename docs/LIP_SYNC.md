# JARVIS — Lip-Sync System

## Overview

The lip-sync system produces ~50 mouth shapes per second by fusing two sources: **audio formant analysis** and **transcript parsing**.

**Files**: `main.py:_pcm_visemes()`, `core/viseme.py`

## Dual-Source Fusion

### Source 1: Audio Formants

**File**: `main.py:_pcm_visemes()` (lines 158-215)

Analyzes 20ms slices of audio via FFT:

```
Window: 1024 samples (~43ms at 24kHz)
Hop: 480 samples (~20ms) → 50 frames per second

Formant bands:
  F1_lo (150-450 Hz): Close vowels
  F1_hi (450-1100 Hz): Open vowels
  F2_back (600-1300 Hz): Rounded vowels
  F2_front (1700-3200 Hz): Spread vowels
  Hiss (3800-8000 Hz): Fricatives

openness = f1h / (f1l + f1h)  # Jaw drop
width = (f2f - f2b) / (f2f + f2b)  # Spread vs rounded

# Damping:
# - Wide-open jaw cannot purse → openness dampens width
# - Fricatives are formed with closed mouth → hiss reduces openness
# - Openness *= 1.0 - 0.65 * min(1.0, h * 2.5)
```

### Source 2: Transcript

**File**: `core/viseme.py`

Parses text into phoneme sequences:

```python
VISEMES = {
    "REST": (0.00, 0.00, 0.00),
    "AA": (0.92, -0.05, 0.00),   # open vowels
    "E":  (0.52, 0.42, 0.00),    # spread vowels
    "I":  (0.20, 0.62, 0.00),    # high, spread
    "O":  (0.55, -0.52, 0.00),   # rounded
    "U":  (0.26, -0.74, 0.00),   # rounded
    "MBP": (0.00, 0.00, 1.00),   # closed lips (m, b, p)
    "FV": (0.10, 0.22, 0.55),    # teeth (f, v)
    "S":  (0.16, 0.42, 0.00),    # hissing
    "TD": (0.28, 0.12, 0.00),    # tongue (t, d, n)
    "K":  (0.30, -0.04, 0.00),   # velar (k, g, h)
    "R":  (0.28, -0.16, 0.00),   # rounded
}
```

### Fusion Formula

```python
# Text leads, audio keeps it honest
if text_queue_not_empty:
    o = 0.72 * text_openness + 0.28 * audio_openness
    w = 0.78 * text_width + 0.22 * audio_width
else:
    o, w = audio_openness, audio_width  # audio-only fallback
```

**72% text + 28% audio**: The transcript supplies the shape (critical for closures), the audio supplies timing and force.

## Language Independence

No per-language table exists. Every character is reduced to one of 26 bare Latin letters:

```
1. Unicode decomposition: é→e, ü→u, ş→s, ğ→g
2. Cyrillic transliteration: а→a, б→b, в→v
3. Greek transliteration: α→a, β→v, γ→g
4. Digraphs: "sh"→S, "ch"→S, "th"→TD, "ng"→K
5. Undecomposed: ı→i, ø→o, ß→s

Scripts that CANNOT be read phonetically (CJK, Arabic, Hebrew, Thai):
→ Skip text source, run on audio-only shapes
```

**Coverage check**: If <55% of letters are mappable, text source is skipped entirely.

## Timing

```python
# VisemeStream manages timing:
_MIN_STEP = 0.045   # 45ms minimum per phoneme
_MAX_STEP = 0.105   # 105ms maximum
# Backlog adaptation:
backlog = min(1.0, len(self._q) / 45.0)
step = _MAX_STEP - (_MAX_STEP - _MIN_STEP) * backlog
# Long backlog → shorter steps → mouth catches up
```

## Jaw Animation

```python
# Separate from visemes — driven by audio openness:
# _TAU_OPEN = 0.022s  # jaw dropping toward vowel
# _TAU_SHUT = 0.012s  # lips closing on consonant
# _TAU_REST = 0.055s  # settling back to rest
# _TAU_SHAPE = 0.018s # viseme openness following schedule

# Frame-rate independent:
def _rate(dt, tau):
    return 1.0 - math.exp(-dt / tau)
```

## Historical Fixes

1. **Mouth ran ahead of words**: Each 200ms batch produced 160ms of shapes; new batch overwrote previous
2. **Mouth ran behind words**: Schedule anchored to when audio was handed to device, not when it sounds
3. **Jaw driven by waveform meter**: Held peaks covered consonant closures
4. **Timing in frames not seconds**: Same constant meant 3 different mouths at 60/30/20 fps
5. **Brow barely moved**: Rig weights halved an already small constant → fixed by deriving from anatomy

## The Playback Clock

```python
self._play_cursor = 0.0  # Wall-clock time when next audio begins to sound

# The mouth is scheduled against this cursor, never against "now":
# Batches are handed to the device faster than they play
# "Now" ran the lips ahead of the words and cut every schedule short
# Timing error: 15ms regardless of buffer size (100ms or 500ms)
```

## Summary

```
Rate: ~50 mouth shapes per second
Sources: Audio formants (20ms FFT) + transcript phonemes
Fusion: 72% text + 28% audio
Language: Unicode reduction, one rule set for all scripts
Fallback: Audio-only for scripts that can't be read phonetically
Jaw: Exponential decay with time constants
Clock: Playback cursor, not wall-clock
```