/**
 * frontend/js/ui.js — Core UI Helpers, Toasts, Modals, Clipboard & Ingestion.
 */

(function() {
  // ── Toast Notification System ──
  window.showToast = function(msg, type = 'info', duration = 3200) {
    const container = document.getElementById('zezo-toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `zezo-toast ${type}`;
    
    let iconName = 'solar:info-circle-linear';
    if (type === 'success') iconName = 'solar:check-circle-linear';
    if (type === 'error') iconName = 'solar:danger-triangle-linear';

    toast.innerHTML = `
      <iconify-icon icon="${iconName}" class="toast-icon" style="font-size: 14px; flex-shrink: 0;"></iconify-icon>
      <span style="flex: 1;">${msg}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('removing');
      setTimeout(() => toast.remove(), 220);
    }, duration);
  };

  window.showHudToast = function(msg) {
    window.showToast(msg, msg.includes('❌') ? 'error' : (msg.includes('✅') ? 'success' : 'info'));
  };

  // ── Modal Generic Helpers ──
  window.openModal = function(id) {
    const el = document.getElementById(id);
    if (el) el.classList.add('open');

    // Pause background rAF loops so they do not repaint behind
    // the modal and cause flicker inside it.
    window._zezoAnimActive = false;
    const gif = document.getElementById('vortex-gif');
    if (gif) gif.style.visibility = 'hidden';

    if (id === 'log-modal') {
      if (typeof window.renderBackendLogs === 'function') window.renderBackendLogs();
      if (typeof window.requestBackendLogs === 'function') {
        window.requestBackendLogs();
      }
    }
    if (id === 'qr-modal' && typeof window.requestRemoteKey === 'function') {
      window.requestRemoteKey();
    }
  };

  window.closeModal = function(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove('open');

    // Resume background animations only if no other modal is still open.
    const anyOpen = document.querySelector('.modal-overlay.open');
    if (!anyOpen) {
      window._zezoAnimActive = !document.hidden && !window._zezoDragging;
      const gif = document.getElementById('vortex-gif');
      if (gif) gif.style.visibility = 'visible';
    }
  };

  // ── Clipboard Copy Helper ──
  window.copyToClipboard = function(text, btnEl) {
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
      if (btnEl) {
        btnEl.classList.add('copied');
        const origText = btnEl.innerHTML;
        btnEl.innerHTML = '✓ COPIED';
        setTimeout(() => {
          btnEl.classList.remove('copied');
          btnEl.innerHTML = origText;
        }, 1800);
      }
      window.showToast('Copied to clipboard', 'success', 2000);
    }).catch(err => {
      console.error('Clipboard copy failed:', err);
      window.showToast('Failed to copy', 'error', 2000);
    });
  };

  // ── Agent Preferences Helper ──
  window.saveAgentPreferences = async function() {
    const creationSel = document.getElementById('setting-creation-agent-select');
    const editSel = document.getElementById('setting-edit-agent-select');
    const creationVal = creationSel ? creationSel.value : 'opencode';
    const editVal = editSel ? editSel.value : 'groq_helper';

    try {
      const res = await fetch('/api/settings/agents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          preferred_creation_agent: creationVal,
          preferred_edit_agent: editVal,
        }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        window.showToast('✅ Agent preferences saved', 'success', 2000);
      } else {
        window.showToast(`❌ Save failed: ${data.message || 'Error'}`, 'error', 3000);
      }
    } catch (e) {
      console.error('Agent preference save error:', e);
      window.showToast('❌ Failed to save agent settings', 'error', 2500);
    }
  };
})();
