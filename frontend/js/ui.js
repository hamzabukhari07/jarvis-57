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
    if (id === 'skills-modal' && typeof window.loadSkillsHub === 'function') {
      window.loadSkillsHub();
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

  // ── Declarative Skill Hub Client Controller ──
  let _cachedSkills = [];
  let _cachedDomains = ['ALL'];

  window.loadSkillsHub = async function() {
    const listEl = document.getElementById('skills-catalog-list');
    const badgeEl = document.getElementById('skills-count-badge');
    const domainFilter = document.getElementById('skill-domain-filter');
    if (!listEl) return;

    try {
      listEl.innerHTML = '<div style="color:var(--text-muted);text-align:center;padding:16px;font-size:11px;">Scanning declarative skills...</div>';
      const res = await fetch('/api/skills');
      const data = await res.json();
      if (data.status === 'success') {
        _cachedSkills = data.skills || [];
        _cachedDomains = ['ALL', ...(data.domains || [])];

        if (badgeEl) {
          badgeEl.textContent = `⚡ SKILL HUB · ${_cachedSkills.length} PACKAGES`;
        }

        if (domainFilter) {
          const currentVal = domainFilter.value || 'ALL';
          domainFilter.innerHTML = _cachedDomains.map(d => `<option value="${d}">${d === 'ALL' ? 'All Domains' : d.toUpperCase()}</option>`).join('');
          if (_cachedDomains.includes(currentVal)) {
            domainFilter.value = currentVal;
          }
        }

        window.renderSkillsCatalog(_cachedSkills);
      } else {
        listEl.innerHTML = `<div style="color:#ef4444;text-align:center;padding:16px;font-size:11px;">Failed to load skills: ${data.message || 'Error'}</div>`;
      }
    } catch (e) {
      console.error('Load skills error:', e);
      if (listEl) {
        listEl.innerHTML = '<div style="color:#ef4444;text-align:center;padding:16px;font-size:11px;">Failed to connect to backend skill registry</div>';
      }
    }
  };

  window.renderSkillsCatalog = function(skills) {
    const listEl = document.getElementById('skills-catalog-list');
    if (!listEl) return;

    if (!skills || skills.length === 0) {
      listEl.innerHTML = '<div style="color:var(--text-muted);text-align:center;padding:24px;font-size:11px;">No declarative skills matched.</div>';
      return;
    }

    listEl.innerHTML = skills.map(s => {
      const isPinned = s.pinned === true;
      const isDisabled = s.disabled === true;
      const isAuto = s.auto_activate !== false;
      const domain = (s.domain || 'GENERAL').toUpperCase();
      const tags = (s.tags || []).slice(0, 4);

      return `
        <div class="card" style="display: flex; flex-direction: column; gap: 6px; padding: 10px 12px; background: var(--bg-deep); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm);">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px;">
            <div>
              <div style="display: flex; align-items: center; gap: 6px;">
                <b style="font-size: 11.5px; color: ${isDisabled ? 'var(--text-muted)' : '#fff'};">${s.name}</b>
                <span class="badge ${domain === 'UI' ? 'badge-accent' : (domain === 'CODING' ? 'badge-primary' : 'badge-secondary')}" style="font-size: 8px;">${domain}</span>
                <span style="font-size: 8.5px; color: var(--text-muted); font-family: var(--font-mono);">v${s.version || '1.0'}</span>
              </div>
              <div class="type-body" style="font-size: 10px; color: var(--text-secondary); margin-top: 3px; line-height: 1.4;">${s.description || ''}</div>
            </div>
            
            <div style="display: flex; align-items: center; gap: 4px; flex-shrink: 0;">
              <!-- Pin Toggle -->
              <button class="btn btn-xs ${isPinned ? 'btn-primary' : 'btn-ghost'}" onclick="window.toggleSkillSetting('${s.name}', ${!isPinned}, ${isDisabled}, ${isAuto})" title="${isPinned ? 'Unpin Skill' : 'Pin Skill (Always Injected)'}" style="padding: 3px 6px; font-size: 8.5px;">
                <iconify-icon icon="solar:pin-bold" style="font-size: 11px;"></iconify-icon>
                <span>${isPinned ? 'PINNED' : 'PIN'}</span>
              </button>

              <!-- Enable/Disable Toggle -->
              <button class="btn btn-xs ${isDisabled ? 'btn-ghost' : 'btn-outline'}" onclick="window.toggleSkillSetting('${s.name}', ${isPinned}, ${!isDisabled}, ${isAuto})" title="${isDisabled ? 'Enable Skill' : 'Disable Skill'}" style="padding: 3px 6px; font-size: 8.5px; color: ${isDisabled ? 'var(--text-muted)' : '#22c55e'};">
                <iconify-icon icon="${isDisabled ? 'solar:close-circle-linear' : 'solar:check-circle-bold'}" style="font-size: 11px;"></iconify-icon>
                <span>${isDisabled ? 'OFF' : 'ACTIVE'}</span>
              </button>
            </div>
          </div>

          ${tags.length > 0 ? `
            <div style="display: flex; gap: 4px; flex-wrap: wrap; margin-top: 2px;">
              ${tags.map(t => `<span style="font-size: 8px; font-family: var(--font-mono); background: rgba(255,255,255,0.04); border: 1px solid var(--border-subtle); padding: 1px 5px; border-radius: 3px; color: var(--text-muted);">#${t}</span>`).join('')}
            </div>
          ` : ''}
        </div>
      `;
    }).join('');
  };

  window.filterSkillsList = function() {
    const searchVal = (document.getElementById('skill-search-input')?.value || '').toLowerCase().trim();
    const domainVal = (document.getElementById('skill-domain-filter')?.value || 'ALL').toUpperCase();

    const filtered = _cachedSkills.filter(s => {
      const matchDomain = (domainVal === 'ALL' || (s.domain || '').toUpperCase() === domainVal);
      if (!matchDomain) return false;
      if (!searchVal) return true;

      const combined = `${s.name} ${s.description} ${(s.tags || []).join(' ')} ${(s.triggers || []).join(' ')}`.toLowerCase();
      return combined.includes(searchVal);
    });

    window.renderSkillsCatalog(filtered);
  };

  window.toggleSkillSetting = async function(name, pinned, disabled, autoActivate) {
    try {
      const res = await fetch('/api/skills/mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name,
          pinned: pinned,
          disabled: disabled,
          auto_activate: autoActivate,
        }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        const item = _cachedSkills.find(s => s.name === name);
        if (item) {
          item.pinned = pinned;
          item.disabled = disabled;
          item.auto_activate = autoActivate;
        }
        window.filterSkillsList();
        window.showToast(`✅ Skill '${name}' updated`, 'success', 1800);
      } else {
        window.showToast(`❌ Error: ${data.message || 'Update failed'}`, 'error', 3000);
      }
    } catch (e) {
      console.error('Skill toggle error:', e);
      window.showToast('❌ Failed to update skill state', 'error', 2500);
    }
  };

  window.handleSkillFileUpload = async function(files) {
    if (!files || files.length === 0) return;
    const file = files[0];
    if (!file.name.endsWith('.zip')) {
      window.showToast('❌ Please upload a valid .zip skill package', 'error', 3000);
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      window.showToast(`📦 Uploading and scanning skill package '${file.name}'...`, 'info', 2500);
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });
      const uploadData = await res.json();
      if (uploadData.status === 'success' && uploadData.files && uploadData.files.length > 0) {
        const uploadedPath = uploadData.files[0].path;
        
        // Invoke install
        const installRes = await fetch('/api/skills/install', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ source: uploadedPath }),
        });
        const installData = await installRes.json();
        if (installData.status === 'success') {
          window.showToast(`✅ ${installData.message}`, 'success', 3000);
          window.loadSkillsHub();
        } else {
          window.showToast(`❌ Security Scan / Install Error: ${installData.message}`, 'error', 4500);
        }
      } else {
        window.showToast(`❌ Upload failed: ${uploadData.message || 'Unknown error'}`, 'error', 3000);
      }
    } catch (e) {
      console.error('Skill upload error:', e);
      window.showToast('❌ Error uploading skill package', 'error', 3000);
    }
  };
})();
