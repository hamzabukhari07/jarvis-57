/**
 * frontend/js/pipeline.js — Voice Pipeline Configuration & Preset Management.
 * 
 * Manages:
 *  - Pipeline Modal (Live vs Cascade toggle)
 *  - 4 One-Click Presets (Gemini Live, Cloud Fast, Balanced, Offline)
 *  - Engine-dependent voice dropdown updates
 *  - Warning & requirement badges
 *  - Async API synchronization (/api/settings/pipeline)
 */

(function() {
  window.voiceFallbackActive = false;
  window._groqKeyConfigured = false;
  window._elevenLabsKeyConfigured = false;
  window._ollamaRunning = true;

  window.setGroqKeyConfigured = function(val) {
    window._groqKeyConfigured = !!val;
    if (typeof window.updatePipelineWarnings === 'function') {
      window.updatePipelineWarnings();
    }
  };

  window.setElevenLabsKeyConfigured = function(val) {
    window._elevenLabsKeyConfigured = !!val;
    if (typeof window.updatePipelineWarnings === 'function') {
      window.updatePipelineWarnings();
    }
  };

  const TTS_VOICE_MAP = {
    kokoro: ['af_heart', 'af_bella', 'af_sarah', 'am_adam', 'am_michael', 'bf_emma', 'bm_george'],
    edge_tts: [
      'en-US-GuyNeural',
      'en-US-JennyNeural',
      'en-GB-SoniaNeural',
      'en-GB-RyanNeural',
      'ur-PK-AsadNeural',
      'ur-PK-UzmaNeural',
      'hi-IN-MadhurNeural',
      'hi-IN-SwaraNeural',
      'ar-SA-HamedNeural',
      'ar-SA-ZariyahNeural',
      'es-ES-AlvaroNeural',
      'fr-FR-HenriNeural',
      'de-DE-ConradNeural'
    ],
    elevenlabs: ['21m00Tcm4TlvDq8ikWAM', 'AZnzlk1XvdvUeBnXmlld', 'EXAVITQu4vr4xnSDxMaL', 'ErXwobaYiN019PkySvjV', 'MF3mGyEYCl7XYWbV9V6O']
  };

  window.togglePipelineModal = function() {
    const modal = document.getElementById('pipeline-modal');
    if (!modal) return;
    const applyBtn = document.querySelector('#pipeline-modal .btn-primary');
    if (applyBtn) {
      applyBtn.disabled = false;
      applyBtn.textContent = 'APPLY';
    }
    const isOpen = modal.classList.contains('open');
    if (isOpen) {
      if (typeof window.closeModal === 'function') window.closeModal('pipeline-modal');
      else modal.classList.remove('open');
    } else {
      if (typeof window.openModal === 'function') window.openModal('pipeline-modal');
      else modal.classList.add('open');
      if (typeof window.updatePipelineWarnings === 'function') window.updatePipelineWarnings();
    }
  };

  window.togglePipelineMode = function(mode) {
    const cascadeConfig = document.getElementById('cascade-config-section');
    const warningText = document.getElementById('live-mode-description');
    
    if (mode === 'cascade') {
      if (cascadeConfig) cascadeConfig.style.display = 'flex';
      if (warningText) warningText.style.display = 'none';
      const cascadeRadio = document.querySelector('input[name="pipeline-mode"][value="cascade"]');
      if (cascadeRadio) cascadeRadio.checked = true;
    } else {
      if (cascadeConfig) cascadeConfig.style.display = 'none';
      if (warningText) warningText.style.display = 'flex';
      const liveRadio = document.querySelector('input[name="pipeline-mode"][value="live"]');
      if (liveRadio) liveRadio.checked = true;
    }
    if (typeof window.updateCustomiseVoiceList === 'function') {
      window.updateCustomiseVoiceList();
    }
    window.updatePipelineWarnings();
  };


  window.updateTtsVoiceOptions = function() {
    const engineSelect = document.getElementById('tts-engine-select');
    const voiceSelect = document.getElementById('tts-voice-select');
    if (!engineSelect || !voiceSelect) return;

    const engine = engineSelect.value || 'kokoro';
    const voices = TTS_VOICE_MAP[engine] || [];
    
    voiceSelect.innerHTML = '';
    voices.forEach(v => {
      const opt = document.createElement('option');
      opt.value = v;
      opt.textContent = v;
      voiceSelect.appendChild(opt);
    });

    if (typeof window.updateCustomiseVoiceList === 'function') {
      window.updateCustomiseVoiceList();
    }
  };

  window.updatePipelineWarnings = function() {
    const warningsDiv = document.getElementById('pipeline-warnings-section');
    if (!warningsDiv) return;
    warningsDiv.innerHTML = '';

    const mode = document.querySelector('input[name="pipeline-mode"]:checked')?.value || 'live';
    if (mode === 'live') return;

    const warnings = [];
    const sttEngine = document.getElementById('stt-engine-select')?.value;
    const llmEngine = document.getElementById('llm-engine-select')?.value;
    const useGroq = (sttEngine === 'groq_whisper') || (llmEngine === 'groq');
    if (useGroq && !window._groqKeyConfigured) {
      warnings.push('⚠️ Groq API key not configured — click Configure Keys above');
    }

    const ttsEngine = document.getElementById('tts-engine-select')?.value || 'kokoro';
    if (ttsEngine === 'elevenlabs' && !window._elevenLabsKeyConfigured) {
      warnings.push('⚠️ ElevenLabs API key not configured — click Configure Keys above');
    }
    if (ttsEngine === 'kokoro') {
      warnings.push('ℹ️ Kokoro requires Python 3.11–3.13');
    }
    if (llmEngine === 'ollama') {
      warnings.push('ℹ️ Ensure Ollama is running locally');
    }
    if (warnings.length === 0) {
      warnings.push('ℹ️ Tools & code actions limited in Cascade mode');
    }

    warnings.forEach((w, idx) => {
      const badge = document.createElement('div');
      badge.style.display = 'flex';
      badge.style.alignItems = 'center';
      badge.style.gap = '6px';
      badge.style.padding = '8px 10px';
      badge.style.borderRadius = 'var(--radius-sm)';
      badge.style.fontSize = '11px';
      badge.style.marginTop = idx === 0 ? '0' : '4px';

      let bgColor, borderColor, textColor, borderLeft;
      if (w.startsWith('ℹ️')) {
        bgColor = 'rgba(56, 189, 248, 0.10)';
        borderColor = 'rgba(56, 189, 248, 0.30)';
        textColor = '#38bdf8';
        borderLeft = '3px solid #38bdf8';
      } else {
        bgColor = 'rgba(239, 68, 68, 0.10)';
        borderColor = 'rgba(239, 68, 68, 0.30)';
        textColor = '#ef4444';
        borderLeft = '3px solid #ef4444';
      }

      badge.style.backgroundColor = bgColor;
      badge.style.border = `1px solid ${borderColor}`;
      badge.style.borderLeft = borderLeft;
      badge.style.color = textColor;
      badge.innerHTML = w.replace(/^[⚠️ℹ️]+\s*/, '');
      warningsDiv.appendChild(badge);
    });
  };

  window.selectPreset = function(preset) {
    const sttSelect = document.getElementById('stt-engine-select');
    const llmSelect = document.getElementById('llm-engine-select');
    const ttsSelect = document.getElementById('tts-engine-select');

    if (preset === 'live') {
      window.togglePipelineMode('live');
    } else if (preset === 'cloud-fast') {
      if (sttSelect) sttSelect.value = 'groq_whisper';
      if (llmSelect) llmSelect.value = 'groq';
      if (ttsSelect) ttsSelect.value = 'edge_tts';
      window.updateTtsVoiceOptions();
      window.togglePipelineMode('cascade');
    } else if (preset === 'balanced') {
      if (sttSelect) sttSelect.value = 'groq_whisper';
      if (llmSelect) llmSelect.value = 'groq';
      if (ttsSelect) ttsSelect.value = 'kokoro';
      window.updateTtsVoiceOptions();
      window.togglePipelineMode('cascade');
    } else if (preset === 'offline') {
      if (sttSelect) sttSelect.value = 'local_whisper';
      if (llmSelect) llmSelect.value = 'ollama';
      if (ttsSelect) ttsSelect.value = 'kokoro';
      window.updateTtsVoiceOptions();
      window.togglePipelineMode('cascade');
    }
  };

  window.applyPreset = window.selectPreset;

  window.savePipelineSettings = function() {
    const mode = document.querySelector('input[name="pipeline-mode"]:checked')?.value || 'live';
    const payload = {
      pipeline_mode: mode,
      voice_fallback: window.voiceFallbackActive ? 'auto' : 'off'
    };

    if (mode === 'cascade') {
      const sttSelect = document.getElementById('stt-engine-select');
      const llmSelect = document.getElementById('llm-engine-select');
      const ttsSelect = document.getElementById('tts-engine-select');
      const voiceSelect = document.getElementById('tts-voice-select');

      if (sttSelect) payload.stt_engine = sttSelect.value;
      if (llmSelect) payload.llm_engine = llmSelect.value;
      if (ttsSelect) payload.tts_engine = ttsSelect.value;
      if (voiceSelect) payload.tts_voice = voiceSelect.value;
    }

    const applyBtn = document.querySelector('#pipeline-modal .btn-primary');
    const origText = 'APPLY';
    if (applyBtn) {
      applyBtn.disabled = true;
      applyBtn.textContent = 'SAVING...';
    }

    const resetBtn = () => {
      if (applyBtn) {
        applyBtn.disabled = false;
        applyBtn.textContent = origText;
      }
    };

    // Close the modal immediately — do not block the UI
    if (typeof window.closeModal === 'function') {
      window.closeModal('pipeline-modal');
    }
    if (typeof window.showToast === 'function') {
      window.showToast('✅ Pipeline settings saved', 'success');
    }
    // Instantly restore button for next open
    resetBtn();

    // Fire the request and handle updates
    fetch('/api/settings/pipeline', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    .then(r => r.json())
    .then(d => {
      resetBtn();
      if (typeof window.updateCustomiseVoiceList === 'function' && d && d.data) {
        window.updateCustomiseVoiceList(d.data);
      }
      if (typeof window.updatePipelineWarnings === 'function') {
        window.updatePipelineWarnings();
      }
    })
    .catch(e => {
      resetBtn();
      console.error('Pipeline save error:', e);
      if (typeof window.showToast === 'function') {
        window.showToast('❌ Save failed: ' + e.message, 'error');
      }
    });
  };
})();
