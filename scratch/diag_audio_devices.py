"""Enumerate audio devices and test which can open at the app's required rates.

Mirrors core/audio_devices.py + main.py: input 16000 Hz, output 24000 Hz.
Run with the SAME interpreter the app uses.
"""
import sounddevice as sd

IN_RATE = 16000
OUT_RATE = 24000

print("=== host APIs ===")
for i, a in enumerate(sd.query_hostapis()):
    print(f"  {i}: {a['name']!r}  default_in={a.get('default_input_device')} "
          f"default_out={a.get('default_output_device')}")

di, do = sd.default.device
print(f"\n=== sounddevice defaults ===\n  default input idx : {di} "
      f"({sd.query_devices(di)['name'] if di is not None and di >= 0 else 'None'})")
print(f"  default output idx: {do} "
      f"({sd.query_devices(do)['name'] if do is not None and do >= 0 else 'None'})")


def try_open_input(idx):
    try:
        st = sd.InputStream(samplerate=IN_RATE, channels=1, dtype="int16",
                            blocksize=1024, device=idx, callback=lambda *a: None)
        st.start(); st.stop(); st.close()
        return "OPEN-OK"
    except Exception as e:
        return f"FAIL: {str(e)[:70]}"


def try_open_output(idx):
    try:
        st = sd.RawOutputStream(samplerate=OUT_RATE, channels=1, dtype="int16",
                                blocksize=1024, device=idx)
        st.start(); st.stop(); st.close()
        return "OPEN-OK"
    except Exception as e:
        return f"FAIL: {str(e)[:70]}"


print("\n=== devices (input capability) ===")
for i, d in enumerate(sd.query_devices()):
    if d["max_input_channels"] > 0:
        print(f"  [{i:2}] {d['name'][:46]:46} api={d['hostapi']} "
              f"native={d['default_samplerate']:.0f}Hz  {try_open_input(i)}")

print("\n=== devices (output capability) ===")
for i, d in enumerate(sd.query_devices()):
    if d["max_output_channels"] > 0:
        print(f"  [{i:2}] {d['name'][:46]:46} api={d['hostapi']} "
              f"native={d['default_samplerate']:.0f}Hz  {try_open_output(i)}")
