# Wake-word models

Drop trained/imported **openWakeWord** `.onnx` models here. The filename stem is
the model id and it appears automatically in
⚙ → **Assistant Persona** → *Assistant Name* (and drives the wake phrase).

Example:

```
config/wakewords/hey_zezo.onnx     →  "Zezo"  →  say "Hey Zezo"
config/wakewords/hey_nova.onnx     →  "Nova"  →  say "Hey Nova"
```

## Getting models

- **`hey_jarvis`** already ships with the `openwakeword` package — no file needed.
- **Custom names** (e.g. `hey_zezo`, `hey_nova`): train once with the official
  openWakeWord Colab, then rename the output to `hey_<name>.onnx` and place it here.
  Colab: https://colab.research.google.com/drive/1q1oe2zOyZp7UsB3jJiQ1IFn8z5YfjwEb
- **Ready-made community models** (friday, computer, etc.):
  https://github.com/fwartner/home-assistant-wakewords-collection

Only names whose model file exists are selectable. If a name has no model, ZEZO
falls back to a resolvable default model and logs a warning.
