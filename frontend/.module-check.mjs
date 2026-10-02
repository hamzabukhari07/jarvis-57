
  import { socket } from './js/socket.js';

  let _allTasksCache = [];
  let _selectedTaskId = null;

  function getFriendlyToolBadge(toolName) {
    const tn = (toolName || '').toLowerCase().trim();
    if (tn.includes('antigravity') || tn.includes('opencode') || tn.includes('kilo') || tn.includes('code_helper') || tn.includes('coder')) {
      return 'ZEZO CODER';
    }
    if (tn.includes('clon') || tn.includes('website_cloner')) return 'WEBSITE CLONER';
    if (tn.includes('dev_agent')) return 'DEV AGENT';
    if (tn.includes('design') || tn.includes('extract_design')) return 'DESIGN EXTRACTOR';
    if (tn.includes('web_search') || tn.includes('search')) return 'WEB SEARCH';
    if (tn.includes('web_read') || tn.includes('scraper')) return 'WEB SCRAPER';
    if (tn.includes('file')) return 'FILE PROCESSOR';
    if (tn.includes('system')) return 'SYSTEM TELEMETRY';
    if (tn.includes('reach') || tn.includes('social')) return 'SOCIAL RESEARCH';
    if (tn.includes('message')) return 'MESSAGING';
    if (tn.includes('weather')) return 'WEATHER REPORT';
    if (tn.includes('flight')) return 'FLIGHT FINDER';
    if (tn.includes('youtube')) return 'YOUTUBE INTEL';
    return (toolName || 'TASK').replace(/_/g, ' ').toUpperCase();
  }

  let _lastTasksRenderHash = '';

  function renderTasks(taskList) {
    const list = Array.isArray(taskList) ? taskList : (taskList && taskList.tasks ? taskList.tasks : []);
    _allTasksCache = list;

    const currentHash = JSON.stringify(list.map(t => ({
      id: t.id,
      s: t.status,
      p: t.progress,
      m: t.message,
      l: (t.logs || []).length,
      el: t.elapsed_sec
    })));
    if (currentHash === _lastTasksRenderHash) {
      return;
    }
    _lastTasksRenderHash = currentHash;

    const queueEl = document.getElementById('task-queue-list');
    const badgeEl = document.getElementById('task-count-badge');
    const modalListEl = document.getElementById('task-modal-list');
    const runningCountEl = document.getElementById('task-modal-running-count');
    const queuedCountEl = document.getElementById('task-modal-queued-count');
    const doneCountEl = document.getElementById('task-modal-done-count');

    const activeTasks = list.filter(t => t.status === 'running' || t.status === 'queued');
    const runningTasks = list.filter(t => t.status === 'running');
    const queuedTasks = list.filter(t => t.status === 'queued');
    const doneTasks = list.filter(t => t.status === 'done' || t.status === 'completed');

    if (badgeEl) {
      if (activeTasks.length > 0) {
        badgeEl.innerText = `${activeTasks.length} ACTIVE`;
      } else if (doneTasks.length > 0) {
        badgeEl.innerText = `${doneTasks.length} DONE`;
      } else {
        badgeEl.innerText = `0 ACTIVE`;
      }
    }
    if (runningCountEl) runningCountEl.innerText = runningTasks.length;
    if (queuedCountEl) queuedCountEl.innerText = queuedTasks.length;
    if (doneCountEl) doneCountEl.innerText = doneTasks.length;

    // Render 02 Task Queue (Left Sidebar)
    if (queueEl) {
      if (list.length === 0) {
        queueEl.innerHTML = `
          <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; text-align: center; color: var(--text-muted); padding: 24px 10px;">
            <iconify-icon icon="solar:checklist-minimalistic-linear" style="font-size: 28px; margin-bottom: 6px; opacity: 0.35;"></iconify-icon>
            <div style="font-size: 11px; font-weight: 500;">No Active Tasks</div>
            <div style="font-size: 9px; font-family: var(--font-mono); margin-top: 2px; color: var(--text-muted);">Tasks dispatched via voice or prompt will appear here.</div>
          </div>
        `;
      } else {
        const sortedTasks = [...list].sort((a, b) => {
          const aActive = a.status === 'running' || a.status === 'queued';
          const bActive = b.status === 'running' || b.status === 'queued';
          if (aActive && !bActive) return -1;
          if (!aActive && bActive) return 1;
          return (b.started_at || 0) - (a.started_at || 0);
        });

        queueEl.innerHTML = sortedTasks.map(t => {
          const isRunning = t.status === 'running';
          const isDone = t.status === 'done' || t.status === 'completed';
          const isFailed = t.status === 'failed';
          const badgeClass = isRunning ? 'badge-accent' : (isDone ? 'badge-success' : (isFailed ? 'badge-danger' : 'badge'));
          const prog = isDone ? 100 : (t.progress || (isRunning ? 50 : 0));
          const toolLabel = getFriendlyToolBadge(t.tool);
          const target = (t.params && (t.params.repo || t.params.file_path || t.params.path || t.params.project_path || t.params.target || t.params.query || t.params.url || t.params.link)) || '';
          const isSelected = t.id === _selectedTaskId;
          const borderStyle = isSelected ? 'var(--accent)' : (isRunning ? 'var(--accent)' : (isDone ? '#22c55e' : (isFailed ? '#ef4444' : 'var(--border-default)')));
          const bgStyle = isSelected ? 'rgba(242, 78, 30, 0.12)' : 'var(--bg-elevated)';
          const statusIcon = isDone ? '✓ DONE' : (isFailed ? '✗ FAILED' : `#${t.id}`);

          const subtasks = Array.isArray(t.subtasks) && t.subtasks.length > 0 ? t.subtasks :
                           (t.result && Array.isArray(t.result.subtasks) ? t.result.subtasks : []);
          const hasSubtasks = subtasks.length > 0;
          const isExpanded = _expandedSubtasks && _expandedSubtasks[t.id];

          let subtasksHtml = '';
          if (hasSubtasks) {
            const subtaskRows = subtasks.map(st => {
              const stDone = st.status === 'done' || st.status === 'completed';
              const stRunning = st.status === 'running';
              const stIcon = stDone ? '✓' : (stRunning ? '⟳' : '○');
              const stColor = stDone ? '#22c55e' : (stRunning ? 'var(--accent)' : 'var(--text-muted)');
              return `
                <div style="display: flex; align-items: center; justify-content: space-between; font-size: 9px; padding: 2px 0; color: ${stDone ? '#ddd' : 'var(--text-muted)'};">
                  <span style="display: flex; align-items: center; gap: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                    <span style="color: ${stColor}; font-weight: bold; font-family: var(--font-mono); font-size: 10px;">${stIcon}</span>
                    <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${st.title || st.name || 'Sub-Task'}</span>
                  </span>
                  <span style="font-size: 8px; color: ${stColor}; text-transform: uppercase; font-weight: 600; margin-left: 6px;">${st.status}</span>
                </div>
              `;
            }).join('');

            subtasksHtml = `
              <div style="margin-top: 6px; border-top: 1px dashed rgba(255,255,255,0.1); padding-top: 4px;">
                <div onclick="event.stopPropagation(); toggleSubtasks('${t.id}')" style="display: flex; align-items: center; justify-content: space-between; font-size: 9px; color: var(--accent); cursor: pointer; user-select: none;">
                  <span style="display: flex; align-items: center; gap: 3px; font-weight: 600;">
                    <iconify-icon icon="${isExpanded ? 'solar:alt-arrow-down-linear' : 'solar:alt-arrow-right-linear'}" style="font-size: 11px;"></iconify-icon>
                    ${subtasks.length} Sub-Tasks
                  </span>
                  <span style="font-size: 8px; color: var(--text-muted);">${subtasks.filter(x => x.status === 'done' || x.status === 'completed').length}/${subtasks.length} Complete</span>
                </div>
                ${isExpanded ? `<div style="margin-top: 4px; padding-left: 6px; border-left: 1px solid rgba(242, 78, 30, 0.3);">${subtaskRows}</div>` : ''}
              </div>
            `;
          }

          return `
            <div class="card card-interactive" id="task-card-${t.id}" onclick="selectAndShowTask('${t.id}', false)" style="background: ${bgStyle}; border-left: 2px solid ${borderStyle}; ${isSelected ? 'border-color: var(--accent);' : ''} cursor: pointer; transition: all 0.15s ease; margin-bottom: 6px;" title="Click to view output on Live Canvas">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <span class="badge ${badgeClass}">${toolLabel}</span>
                <span class="mono text-muted" style="font-size: 9px; ${isDone ? 'color: #22c55e; font-weight: 600;' : ''}">${statusIcon}</span>
              </div>
              <div style="font-weight: 600; font-size: 11px; color: #fff; margin-bottom: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                ${t.message || t.tool || 'Task Execution'}
              </div>
              ${target ? `<div class="type-code text-muted" style="font-size: 9px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">Target: ${target}</div>` : ''}
              <div class="progress-track" style="margin-top: 6px;">
                <div class="progress-fill" style="width: ${prog}%; background: ${isDone ? '#22c55e' : (isFailed ? '#ef4444' : 'var(--accent)')};"></div>
              </div>
              ${subtasksHtml}
            </div>
          `;
        }).join('');
      }
    }

    // Render Task Matrix Modal
    if (modalListEl) {
      if (list.length === 0) {
        modalListEl.innerHTML = `
          <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 160px; text-align: center; color: var(--text-muted);">
            <iconify-icon icon="solar:checklist-minimalistic-linear" style="font-size: 32px; margin-bottom: 8px; opacity: 0.35;"></iconify-icon>
            <div style="font-size: 12px; font-weight: 500;">No Background Tasks</div>
            <div style="font-size: 10px; font-family: var(--font-mono); margin-top: 4px; color: var(--text-muted);">All asynchronous agent executions will be registered here.</div>
          </div>
        `;
      } else {
        modalListEl.innerHTML = list.map(t => {
          const isRunning = t.status === 'running';
          const isDone = t.status === 'done' || t.status === 'completed';
          const isFailed = t.status === 'failed';
          const statusBadge = isRunning ? 'badge-accent' : (isDone ? 'badge-success' : (isFailed ? 'badge' : 'badge'));
          const prog = isDone ? 100 : (t.progress || 0);
          const toolLabel = getFriendlyToolBadge(t.tool);
          return `
            <div class="card card-interactive" onclick="selectAndShowTask('${t.id}', true)" style="background: var(--bg-elevated); cursor: pointer; transition: all 0.15s ease;" title="Click for detailed inspection">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                  <span class="badge ${isRunning ? 'badge-accent' : ''}">${toolLabel}</span>
                  <span class="mono text-muted">#${t.id}</span>
                </div>
                <div style="display: flex; align-items: center; gap: 6px;">
                  <span class="badge ${statusBadge}">● ${t.status.toUpperCase()} (${prog}%)</span>
                  <span class="badge" style="font-size: 8px; padding: 2px 4px; color: var(--accent);">🔍 DETAILS</span>
                </div>
              </div>
              <div style="font-weight: 600; margin-bottom: 2px;">${t.message || 'Task Execution'}</div>
              ${t.params ? `<div class="type-code text-muted">${JSON.stringify(t.params)}</div>` : ''}
              <div class="progress-track" style="margin-top: 6px;">
                <div class="progress-fill" style="width: ${prog}%;"></div>
              </div>
            </div>
          `;
        }).join('');
      }
    }
    // Live-update open task detail modal if active
    const detailModalEl = document.getElementById('task-detail-modal');
    if (detailModalEl && (detailModalEl.classList.contains('open') || detailModalEl.classList.contains('active')) && _selectedTaskId) {
      const activeTask = list.find(x => x.id === _selectedTaskId);
      if (activeTask) {
        openTaskDetail(_selectedTaskId, false);
      }
    }
  }

  window.selectAndShowTask = function(taskId, openDetailModal = false) {
    if (!taskId) return;
    _selectedTaskId = taskId;
    const t = _allTasksCache.find(x => x.id === taskId);
    if (!t) return;

    // Highlight active card in task queue
    document.querySelectorAll('#task-queue-list .card').forEach(c => {
      c.style.background = 'var(--bg-elevated)';
      c.style.borderColor = 'var(--border-default)';
    });
    const activeEl = document.getElementById(`task-card-${taskId}`);
    if (activeEl) {
      activeEl.style.background = 'rgba(242, 78, 30, 0.12)';
      activeEl.style.borderColor = 'var(--accent)';
    }

    let outText = '';
    if (t.result) {
      if (typeof t.result === 'string') outText = t.result;
      else if (typeof t.result === 'object') {
        outText = t.result.summary || t.result.output || t.result.full_content || t.result.response || JSON.stringify(t.result, null, 2);
      }
    } else if (t.message) {
      outText = `Stage: ${t.message}`;
    }

    if (outText && typeof setCanvasContent === 'function') {
      setCanvasContent(outText, getFriendlyToolBadge(t.tool));
    }

    if (openDetailModal) {
      openTaskDetail(taskId, true);
    }
  };

  const _expandedSubtasks = {};

  window.toggleSubtasks = function(taskId) {
    if (!taskId) return;
    _expandedSubtasks[taskId] = !_expandedSubtasks[taskId];
    _lastTasksRenderHash = ''; // Force re-render
    if (_allTasksCache) {
      renderTasks(_allTasksCache);
    }
  };

  function openTaskDetail(taskId, showModal = true) {
    if (!taskId) return;
    _selectedTaskId = taskId;
    const t = _allTasksCache.find(x => x.id === taskId) || { id: taskId };

    const badgeEl = document.getElementById('task-detail-badge');
    const idEl = document.getElementById('task-detail-id');
    const titleEl = document.getElementById('task-detail-title');
    const targetEl = document.getElementById('task-detail-target');
    const statusBadgeEl = document.getElementById('task-detail-status-badge');
    const progBarEl = document.getElementById('task-detail-progress-bar');
    const engineEl = document.getElementById('task-detail-engine');
    const modelEl = document.getElementById('task-detail-model');
    const pidEl = document.getElementById('task-detail-pid');
    const startedEl = document.getElementById('task-detail-started');
    const elapsedEl = document.getElementById('task-detail-elapsed');
    const logStreamEl = document.getElementById('task-detail-log-stream');
    const cancelBtn = document.getElementById('task-detail-cancel-btn');

    const friendlyBadge = getFriendlyToolBadge(t.tool);
    const target = (t.params && (t.params.repo || t.params.file_path || t.params.path || t.params.project_path)) || (t.params ? JSON.stringify(t.params).slice(0, 50) : 'Local Workspace');
    const isRunning = t.status === 'running';
    const isDone = t.status === 'done' || t.status === 'completed';
    const isFailed = t.status === 'failed';
    const prog = isDone ? 100 : (t.progress || (isRunning ? 50 : 0));

    if (badgeEl) badgeEl.innerText = friendlyBadge;
    if (idEl) idEl.innerText = `#${t.id}`;
    if (titleEl) titleEl.innerText = t.message || (t.params && t.params.task) || `${friendlyBadge} Execution`;
    if (targetEl) targetEl.innerText = `Target: ${target}`;
    
    if (statusBadgeEl) {
      const statusText = (t.status || 'QUEUED').toUpperCase();
      statusBadgeEl.innerText = `● ${statusText} (${prog}%)`;
      statusBadgeEl.className = isRunning ? 'badge badge-accent' : (isDone ? 'badge badge-success' : (isFailed ? 'badge badge-danger' : 'badge'));
    }

    if (progBarEl) {
      progBarEl.style.width = `${prog}%`;
      progBarEl.style.background = isDone ? '#22c55e' : (isFailed ? '#ef4444' : 'var(--accent)');
    }

    if (engineEl) engineEl.innerText = t.engine || (friendlyBadge === 'ZEZO CODER' ? 'Antigravity Autonomous Engine' : friendlyBadge);
    if (modelEl) modelEl.innerText = t.model || (t.params && t.params.model) || 'Gemini 3.1 Flash';
    if (pidEl) pidEl.innerText = t.pid ? `${t.pid} (Assigned Thread)` : 'Active Worker Thread';
    if (startedEl) startedEl.innerText = t.started_time_str || (t.started_at ? new Date(t.started_at * 1000).toTimeString().split(' ')[0] : '--:--:--');
    
    if (elapsedEl) {
      const sec = t.elapsed_sec || 0;
      elapsedEl.innerText = sec < 60 ? `${Math.round(sec)}s` : `${Math.floor(sec / 60)}m ${Math.round(sec % 60)}s`;
    }

    if (cancelBtn) {
      cancelBtn.style.display = (isRunning || t.status === 'queued') ? 'inline-flex' : 'none';
    }

    // Render Recent Logs
    if (logStreamEl) {
      const logs = Array.isArray(t.logs) && t.logs.length ? t.logs : [];
      if (logs.length === 0) {
        logStreamEl.innerHTML = `
          <div style="color:var(--text-muted); font-size:9.5px;">[${t.started_time_str || '--:--:--'}] ${friendlyBadge} initiated. Execution pipeline active.</div>
          ${t.message ? `<div style="color:#f1f5f9; font-size:9.5px; margin-top:2px;">[${t.started_time_str || '--:--:--'}] Stage: ${t.message}</div>` : ''}
        `;
      } else {
        logStreamEl.innerHTML = logs.map(l => {
          const lTime = l.time || '--:--:--';
          const lText = (l.text || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
          return `
            <div style="display:flex; align-items:baseline; gap:6px; color:#e2e8f0; padding:1px 0;">
              <span style="color:rgba(255,255,255,0.35); flex-shrink:0; font-size:9px;">${lTime}</span>
              <span style="color:var(--accent); font-weight:600; flex-shrink:0; font-size:9px;">${friendlyBadge}:</span>
              <span style="flex:1; white-space:pre-wrap;">${lText}</span>
            </div>
          `;
        }).join('');
      }
      logStreamEl.scrollTop = logStreamEl.scrollHeight;
    }

    if (showModal) {
      openModal('task-detail-modal');
    }
  }
  window.openTaskDetail = openTaskDetail;

  window.cancelCurrentTaskFromDetail = function() {
    if (!_selectedTaskId) return;
    socket.send('task_cancel', { task_id: _selectedTaskId });
    const statusBadgeEl = document.getElementById('task-detail-status-badge');
    const cancelBtn = document.getElementById('task-detail-cancel-btn');
    if (statusBadgeEl) {
      statusBadgeEl.innerText = '● CANCELLING...';
      statusBadgeEl.className = 'badge badge-warn';
    }
    if (cancelBtn) cancelBtn.style.display = 'none';
  };

  window.copyTaskParamsFromDetail = function(btn) {
    if (!_selectedTaskId) return;
    const t = _allTasksCache.find(x => x.id === _selectedTaskId);
    if (!t || !t.params) return;
    const jsonStr = JSON.stringify(t.params, null, 2);
    if (typeof writeToSystemClipboard === 'function') {
      writeToSystemClipboard(jsonStr);
    }
    if (btn) {
      const orig = btn.innerHTML;
      btn.innerHTML = '<iconify-icon icon="solar:check-circle-bold" style="color:#22c55e;"></iconify-icon> COPIED';
      setTimeout(() => { btn.innerHTML = orig; }, 1400);
    }
  };

  window.copyTaskLogsFromDetail = function(btn) {
    if (!_selectedTaskId) return;
    const t = _allTasksCache.find(x => x.id === _selectedTaskId);
    if (!t) return;
    let textToCopy = '';
    if (Array.isArray(t.logs) && t.logs.length) {
      textToCopy = t.logs.map(l => `[${l.time || '--:--:--'}] ${l.text || ''}`).join('\n');
    } else if (t.message) {
      textToCopy = `[${t.started_time_str || '--:--:--'}] ${t.message}`;
    } else {
      textToCopy = `Task #${t.id} (${t.type || 'task'}) - ${t.status || 'unknown'}`;
    }
    if (typeof writeToSystemClipboard === 'function') {
      writeToSystemClipboard(textToCopy);
    } else if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(textToCopy);
    }
    if (btn) {
      const orig = btn.innerHTML;
      btn.innerHTML = '<iconify-icon icon="solar:check-circle-bold" style="color:#22c55e;"></iconify-icon> COPIED';
      setTimeout(() => { btn.innerHTML = orig; }, 1400);
    }
    if (typeof showHudToast === 'function') {
      showHudToast('Task logs copied to clipboard');
    }
  };

  // ── Mobile Remote Pairing Modal: real key + live expiry countdown ──
  // TTL mirrors dashboard/server.py DashboardServer.new_key(expiry_secs=600):
  // every get_remote_key call mints a fresh key valid for 10 minutes.
  const REMOTE_KEY_TTL_SECONDS = 600;
  let _remoteKeyInterval = null;
  let _remoteKeyRemaining = 0;

  function _renderRemoteTimer() {
    const el = document.getElementById('remote-timer-value');
    if (!el) return;
    if (_remoteKeyRemaining <= 0) {
      el.textContent = 'EXPIRED';
      el.style.color = '#ef4444';
      return;
    }
    const m = Math.floor(_remoteKeyRemaining / 60);
    const s = _remoteKeyRemaining % 60;
    el.textContent = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    el.style.color = '#fff';
  }

  function _startRemoteKeyCountdown() {
    if (_remoteKeyInterval) clearInterval(_remoteKeyInterval);
    _remoteKeyRemaining = REMOTE_KEY_TTL_SECONDS;
    _renderRemoteTimer();
    _remoteKeyInterval = setInterval(() => {
      _remoteKeyRemaining -= 1;
      _renderRemoteTimer();
      if (_remoteKeyRemaining <= 0) {
        clearInterval(_remoteKeyInterval);
        _remoteKeyInterval = null;
      }
    }, 1000);
  }

  window.requestRemoteKey = function() {
    socket.send('get_remote_key');
  };

  socket.on('remote_key_data', (data) => {
    const url = (data && data.url) ? String(data.url) : '';
    const key = (data && data.key) ? String(data.key) : '';
    const keyEl = document.getElementById('pairing-key-display');
    const urlEl = document.getElementById('remote-url-display');
    const qrImg = document.getElementById('remote-qr-img');

    if (keyEl) keyEl.textContent = key || '——';
    if (urlEl) urlEl.textContent = url || '—';
    if (qrImg && key && url) {
      const loginUrl = `${url.replace(/\/+$/, '')}/auto-login?key=${encodeURIComponent(key)}`;
      qrImg.src = `https://api.qrserver.com/v1/create-qr-code/?size=160x160&data=${encodeURIComponent(loginUrl)}`;
    }
    _startRemoteKeyCountdown();
  });

  socket.on('connect', () => {
    console.log('[ZEZO-UI] Real-time WebSocket connection active');
    socket.send('get_initial_state');
  });

     socket.on('api_keys_updated', (data) => {
     if (data.status === 'success') {
       if (data.has_gemini_key) {
         const geminiStatus = document.getElementById('gemini-key-status');
         if (geminiStatus) {
           geminiStatus.style.display = 'inline-flex';
           geminiStatus.innerText = data.gemini_api_key_masked
             ? 'SAVED (' + data.gemini_api_key_masked + ')'
             : 'SAVED';
         }
       }
       window._groqKeyConfigured = data.has_groq_key === true || Boolean(data.groq_api_key_masked);
       if (window._groqKeyConfigured) {
         const groqStatus = document.getElementById('groq-key-status');
         if (groqStatus) {
           groqStatus.style.display = 'inline-flex';
           groqStatus.innerText = data.groq_api_key_masked
             ? 'SAVED (' + data.groq_api_key_masked + ')'
             : 'SAVED';
         }
       }
       if (window.showToast) window.showToast('API keys saved', 'success');
     }
   });

   socket.on('pipeline_settings_updated', (data) => {
     if (window.showToast) window.showToast('Pipeline settings saved', 'success');
   });

socket.on('disconnect', () => {
    console.log('[ZEZO-UI] WebSocket disconnected');
    if (typeof setAssistantState === 'function') {
      setAssistantState('offline');
    }
  });

  socket.on('init', (data) => {
    if (!data) return;
    if (data.muted !== undefined) {
      window.isMuted = !!data.muted;
    }
    if (data.sleeping !== undefined) {
      window.isSleeping = !!data.sleeping;
    }
    if (data.state && typeof setAssistantState === 'function') {
      setAssistantState(data.state.toLowerCase());
    } else if (window.isMuted && typeof setAssistantState === 'function') {
      setAssistantState('muted');
    }
    if (data.tasks) {
      renderTasks(data.tasks);
    }
    if (data.assistant_name) {
      const nameEl = document.getElementById('customise-asst-name');
      if (nameEl) nameEl.value = data.assistant_name;
    }
    if (data.voice_name) {
      const voiceEl = document.getElementById('customise-voice-select');
      if (voiceEl) voiceEl.value = data.voice_name;
    }
    if (data.fallback_voices) {
      const fbEl = document.getElementById('customise-fallback-voice-select');
      if (fbEl) {
        fbEl.innerHTML = data.fallback_voices.map(v => `<option value="${v}">${v}</option>`).join('');
        if (data.fallback_voice) fbEl.value = data.fallback_voice;
      }
    }
    if (data.response_language) {
      const langEl = document.getElementById('customise-lang-select');
      if (langEl) langEl.value = data.response_language;
    }
    
    // API Key onboarding & masked badge handling
    if (data.has_gemini_key === false) {
      openModal('onboarding-modal');
    } else {
      closeModal('onboarding-modal');
    }

    if (data.gemini_api_key_masked) {
      const geminiStatus = document.getElementById('gemini-key-status');
      const geminiInput = document.getElementById('customise-gemini-key');
      if (geminiStatus) {
        geminiStatus.style.display = 'inline-flex';
        geminiStatus.innerText = `✓ SAVED (${data.gemini_api_key_masked})`;
      }
      if (geminiInput && !geminiInput.value) {
        geminiInput.placeholder = `${data.gemini_api_key_masked} (Paste to replace)`;
      }
    }
    if (data.groq_api_key_masked) {
      const groqStatus = document.getElementById('groq-key-status');
      const groqInput = document.getElementById('customise-groq-key');
      if (groqStatus) {
        groqStatus.style.display = 'inline-flex';
        groqStatus.innerText = `✓ SAVED (${data.groq_api_key_masked})`;
      }
      if (groqInput && !groqInput.value) {
        groqInput.placeholder = `${data.groq_api_key_masked} (Paste to replace)`;
      }
    }

    if (data.autostart_enabled !== undefined) {
      window.autostartActive = !!data.autostart_enabled;
      const sw = document.getElementById('autostart-switch');
      if (sw) sw.classList.toggle('active', window.autostartActive);
      const ab = document.getElementById('autostart-badge');
      if (ab) {
        ab.innerText = window.autostartActive ? 'ON' : 'OFF';
        ab.className = window.autostartActive ? 'badge badge-success' : 'badge';
      }
    }
    if (data.morning_brief_enabled !== undefined) {
      window.briefActive = !!data.morning_brief_enabled;
      const sw = document.getElementById('brief-mode-switch');
      if (sw) sw.classList.toggle('active', window.briefActive);
      const bb = document.getElementById('brief-mode-badge');
      if (bb) {
        bb.innerText = window.briefActive ? 'ON' : 'OFF';
        bb.className = window.briefActive ? 'badge badge-success' : 'badge';
      }
    }
    if (data.wake_word_enabled !== undefined) {
      window.wakeActive = !!data.wake_word_enabled;
      const sw = document.getElementById('wake-word-switch');
      if (sw) sw.classList.toggle('active-accent', window.wakeActive);
      const wb = document.getElementById('wake-word-badge');
      if (wb) {
        wb.innerText = window.wakeActive ? 'ARMED' : 'OFF';
        wb.className = window.wakeActive ? 'badge badge-accent' : 'badge';
      }
    }
    if (data.push_to_talk_enabled !== undefined) {
      window.pttActive = !!data.push_to_talk_enabled;
      const sw = document.getElementById('ptt-switch');
      if (sw) sw.classList.toggle('active', window.pttActive);
      const pb = document.getElementById('ptt-badge');
      if (pb) {
        pb.innerText = window.pttActive ? 'ON' : 'OFF';
        pb.className = window.pttActive ? 'badge badge-success' : 'badge';
      }
    }
  });

  socket.on('autostart_status', (data) => {
    if (!data) return;
    window.autostartActive = !!data.enabled;
    const sw = document.getElementById('autostart-switch');
    if (sw) sw.classList.toggle('active', window.autostartActive);
    const ab = document.getElementById('autostart-badge');
    if (ab) {
      ab.innerText = window.autostartActive ? 'ON' : 'OFF';
      ab.className = window.autostartActive ? 'badge badge-success' : 'badge';
    }
  });

  socket.on('brief_status', (data) => {
    if (!data) return;
    window.briefActive = !!data.enabled;
    const sw = document.getElementById('brief-mode-switch');
    if (sw) sw.classList.toggle('active', window.briefActive);
    const bb = document.getElementById('brief-mode-badge');
    if (bb) {
      bb.innerText = window.briefActive ? 'ON' : 'OFF';
      bb.className = window.briefActive ? 'badge badge-success' : 'badge';
    }
  });

  socket.on('assistant_settings_updated', (data) => {
    if (!data) return;
    if (data.assistant_name) {
      const nameEl = document.getElementById('customise-asst-name');
      if (nameEl) nameEl.value = data.assistant_name;
      const titleEl = document.querySelector('.window-title span');
      if (titleEl) {
        titleEl.innerText = `${data.assistant_name.toUpperCase()} · AUTONOMOUS DESKTOP OS`;
      }
    }
    if (data.voice_name) {
      const voiceEl = document.getElementById('customise-voice-select');
      if (voiceEl) voiceEl.value = data.voice_name;
    }
    if (data.fallback_voices) {
      const fbEl = document.getElementById('customise-fallback-voice-select');
      if (fbEl) {
        fbEl.innerHTML = data.fallback_voices.map(v => `<option value="${v}">${v}</option>`).join('');
        if (data.fallback_voice) fbEl.value = data.fallback_voice;
      }
    }
    if (data.response_language) {
      const langEl = document.getElementById('customise-lang-select');
      if (langEl) langEl.value = data.response_language;
    }
  });

  socket.on('task_list', (data) => {
    renderTasks(data);
  });

  socket.on('state_change', (data) => {
    if (data && data.state) {
      const s = data.state.toLowerCase();
      if (s === 'muted') {
        window.isMuted = true;
      } else if (s === 'listening' || s === 'speaking' || s === 'thinking' || s === 'executing') {
        window.isMuted = false;
        window.isSleeping = false;
      } else if (s === 'sleeping') {
        window.isSleeping = true;
      }
      if (typeof setAssistantState === 'function') {
        setAssistantState(s);
      }
    }
  });

  socket.on('telemetry_update', (m) => {
    if (!m) return;
    const updateBar = (id, val, text) => {
      const fill = document.getElementById(`bar_${id}`);
      const lbl = document.getElementById(`val_${id}`);
      if (fill) fill.style.width = `${Math.min(100, Math.max(0, val))}%`;
      if (lbl) lbl.textContent = text;
    };
    if (m.cpu !== undefined) updateBar('cpu', m.cpu, `${m.cpu.toFixed(0)}%`);
    if (m.mem !== undefined) updateBar('mem', m.mem, `${m.mem.toFixed(0)}%`);
    if (m.gpu !== undefined) updateBar('gpu', m.gpu >= 0 ? m.gpu : 0, m.gpu >= 0 ? `${m.gpu.toFixed(0)}%` : 'N/A');
    if (m.net !== undefined) {
      const netStr = m.net < 1.0 ? `${(m.net * 1024).toFixed(0)}KB/s` : `${m.net.toFixed(1)}MB/s`;
      updateBar('net', Math.min(100, m.net * 10), netStr);
    }
    if (m.tmp !== undefined) updateBar('tmp', m.tmp >= 0 ? m.tmp : 0, m.tmp >= 0 ? `${m.tmp.toFixed(0)}°C` : 'N/A');
  });

  socket.on('log_entry', (entry) => {
    if (!entry || !entry.message) return;
    const tag = (entry.tag || 'SYS').toUpperCase();
    const msg = entry.message;
    const box = document.getElementById('stream-box');
    if (!box) return;

    // Suppress internal state transitions
    if (msg.startsWith('State changed to') || msg.startsWith('SYS: State changed to')) return;

    const now = new Date().toTimeString().split(' ')[0];
    const safeMsg = msg.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const copyMsg = safeMsg.replace(/'/g, "\\'");

    let cardHtml = '';
    if (tag === 'USER') {
      cardHtml = `
        <div class="stream-msg stream-msg-user">
          <div class="stream-msg-header">
            <div class="stream-msg-meta">
              <span class="mono text-muted">${now}</span>
              <span class="stream-msg-tag"><iconify-icon icon="solar:user-linear" style="font-size: 10px;"></iconify-icon> USER</span>
            </div>
            <button class="msg-copy-btn" onclick="copySingleMessage(this, '${copyMsg}')"><iconify-icon icon="solar:copy-linear"></iconify-icon></button>
          </div>
          <div class="stream-msg-body">${safeMsg}</div>
        </div>
      `;
    } else if (tag === 'AI' || tag === 'ZEZO') {
      cardHtml = `
        <div class="stream-msg stream-msg-zezo">
          <div class="stream-msg-header">
            <div class="stream-msg-meta">
              <span class="mono text-muted">${now}</span>
              <span class="stream-msg-tag"><iconify-icon icon="solar:atom-bold" style="font-size: 10px;"></iconify-icon> ZEZO AI</span>
            </div>
            <button class="msg-copy-btn" onclick="copySingleMessage(this, '${copyMsg}')"><iconify-icon icon="solar:copy-linear"></iconify-icon></button>
          </div>
          <div class="stream-msg-body">${safeMsg}</div>
        </div>
      `;
    } else {
      let extraClass = '';
      if (tag === 'ERR') extraClass = 'interrupt';
      if (tag === 'FILE') extraClass = 'ok';
      cardHtml = `
        <div class="stream-msg stream-msg-sys ${extraClass}">
          <div class="stream-msg-header">
            <div class="stream-msg-meta">
              <span class="mono text-muted">${now}</span>
              <span class="stream-msg-tag">[${tag}]</span>
            </div>
            <button class="msg-copy-btn" onclick="copySingleMessage(this, '${copyMsg}')"><iconify-icon icon="solar:copy-linear"></iconify-icon></button>
          </div>
          <div class="stream-msg-body">${safeMsg}</div>
        </div>
      `;
    }
    box.insertAdjacentHTML('beforeend', cardHtml);
    box.scrollTop = box.scrollHeight;

    const logModalBuf = document.getElementById('log-modal-buffer');
    if (logModalBuf) {
      logModalBuf.insertAdjacentHTML('beforeend', `<div style="color:${tag==='ERR'?'#ef4444':(tag==='USER'?'#38bdf8':(tag==='AI'?'var(--accent)':'var(--text-secondary)'))};">[${now}] [${tag}] ${safeMsg}</div>`);
      logModalBuf.scrollTop = logModalBuf.scrollHeight;
    }
  });

  socket.on('content_display', (payload) => {
    if (!payload) return;
    if (typeof setCanvasContent === 'function') {
      setCanvasContent(payload.type || 'output', payload.title || 'Task Inspection', payload.text || '', payload.html || null);
    }
  });

  // Real Command Execution
  window.executeCommand = function() {
    const input = document.getElementById('user-input');
    if (!input) return;
    const val = input.value.trim();
    if (!val) return;

    socket.send('user_message', { text: val });
    input.value = '';
  };

  // Real Emergency Interrupt / Stop
  window.emergencyStop = function() {
    socket.send('interrupt', {});
    setAssistantState('interrupted');
    setTimeout(() => {
      if (currentAssistantState === 'interrupted') {
        setAssistantState(window.isSleeping ? 'sleeping' : 'listening');
      }
    }, 1800);
  };
  window.executeInterrupt = window.emergencyStop;

  // Real Mic Toggle
  window.toggleMic = function() {
    window.isMuted = !window.isMuted;
    setAssistantState(window.isMuted ? 'muted' : (window.isSleeping ? 'sleeping' : 'listening'));
    socket.send('mute_toggle', { muted: !!window.isMuted });
  };

  // Real Power / Sleep / Wake Toggle
  window.togglePowerSleep = function() {
    window.isSleeping = !window.isSleeping;
    if (window.isSleeping) {
      setAssistantState('sleeping');
      socket.send('sleep_toggle', { sleeping: true });
    } else {
      setAssistantState('listening');
      socket.send('sleep_toggle', { sleeping: false });
    }
  };

  // Real Desktop Shortcut
  window.simulateShortcut = function() {
    socket.send('create_shortcut', {});
    alert('⚡ Desktop shortcut creation requested from Python backend.');
  };

  // Real Autostart Toggle
  window.toggleAutostart = function() {
    if (typeof window.autostartActive === 'undefined') window.autostartActive = false;
    window.autostartActive = !window.autostartActive;
    const sw = document.getElementById('autostart-switch');
    if (sw) sw.classList.toggle('active', window.autostartActive);
    const badge = document.getElementById('autostart-badge');
    if (badge) {
      badge.innerText = window.autostartActive ? 'ON' : 'OFF';
      badge.className = window.autostartActive ? 'badge badge-success' : 'badge';
    }
    socket.send('autostart_toggle', { enable: window.autostartActive });
  };

  // Real Morning Brief Toggle
  window.toggleBriefMode = function() {
    if (typeof window.briefActive === 'undefined') window.briefActive = true;
    window.briefActive = !window.briefActive;
    const sw = document.getElementById('brief-mode-switch');
    if (sw) sw.classList.toggle('active', window.briefActive);
    const badge = document.getElementById('brief-mode-badge');
    if (badge) {
      badge.innerText = window.briefActive ? 'ON' : 'OFF';
      badge.className = window.briefActive ? 'badge badge-success' : 'badge';
    }
    socket.send('brief_toggle', { enable: window.briefActive });
  };

  // Real Wake Word Toggle
  window.toggleWakeWord = function() {
    if (typeof window.wakeActive === 'undefined') window.wakeActive = true;
    window.wakeActive = !window.wakeActive;
    const sw = document.getElementById('wake-word-switch');
    if (sw) sw.classList.toggle('active-accent', window.wakeActive);
    const badge = document.getElementById('wake-word-badge');
    if (badge) {
      badge.innerText = window.wakeActive ? 'ARMED' : 'OFF';
      badge.className = window.wakeActive ? 'badge badge-accent' : 'badge';
    }
    socket.send('wake_toggle', { enable: window.wakeActive });
  };

  // Real PTT Toggle
  window.togglePtt = function() {
    if (typeof window.pttActive === 'undefined') window.pttActive = true;
    window.pttActive = !window.pttActive;
    const sw = document.getElementById('ptt-switch');
    if (sw) sw.classList.toggle('active', window.pttActive);
    const badge = document.getElementById('ptt-badge');
    if (badge) {
      badge.innerText = window.pttActive ? 'ON' : 'OFF';
      badge.className = window.pttActive ? 'badge badge-success' : 'badge';
    }
    socket.send('ptt_toggle', { enable: window.pttActive });
  };

  // Real Theme Accent Persistence
  const origSetColor = window.setCustomColor;
  window.setCustomColor = function(hex, name) {
    if (typeof origSetColor === 'function') origSetColor(hex, name);
    socket.send('set_accent', { color: hex });
  };

  // ── Multi-Payload File & Folder Ingestion & Management ──
  window.ingestedPayloads = [];

  window.renderPayloadList = function() {
    const container = document.getElementById('payload-items-container');
    const countLabel = document.getElementById('payload-count-label');
    const listEl = document.getElementById('payload-list-items');
    if (!container || !listEl) return;

    if (!window.ingestedPayloads || window.ingestedPayloads.length === 0) {
      container.style.display = 'none';
      listEl.innerHTML = '';
      return;
    }

    container.style.display = 'flex';
    if (countLabel) {
      countLabel.innerText = `INGESTED PAYLOADS (${window.ingestedPayloads.length})`;
    }

    listEl.innerHTML = window.ingestedPayloads.map((item, idx) => {
      const isFolder = !!item.is_folder;
      const iconName = isFolder ? 'solar:folder-with-files-bold-duotone' : 'solar:document-text-linear';
      const badgeText = isFolder 
        ? `${item.files_count || 0} Files` 
        : `${item.size ? (item.size / 1024).toFixed(1) : '0'} KB`;
      const safeName = (item.name || 'item').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      
      return `
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 4px 7px; background: var(--bg-deep); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); transition: all 0.2s ease;">
          <div style="display: flex; align-items: center; gap: 6px; overflow: hidden; cursor: pointer; flex: 1; min-width: 0;" onclick="selectPayloadItem(${idx})" title="Click to view intel in canvas">
            <iconify-icon icon="${iconName}" style="color:var(--accent); font-size: 13px; flex-shrink: 0;"></iconify-icon>
            <span style="font-size: 9.5px; font-weight: 500; font-family: var(--font-mono); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--text-primary);">${safeName}</span>
          </div>
          <div style="display: flex; align-items: center; gap: 5px; flex-shrink: 0;">
            <span class="badge badge-accent" style="font-size: 7.5px; padding: 1px 4px;">${badgeText}</span>
            <button onclick="removePayloadItem(${idx}, event)" style="background: none; border: none; color: var(--text-muted); cursor: pointer; padding: 1px 3px; font-size: 10px; border-radius: 2px; display: flex; align-items: center; justify-content: center; transition: color 0.15s;" onmouseover="this.style.color='#ef4444'" onmouseout="this.style.color='var(--text-muted)'" title="Remove payload">
              ✕
            </button>
          </div>
        </div>
      `;
    }).join('');
  };

  window.selectPayloadItem = function(idx) {
    const item = window.ingestedPayloads[idx];
    if (!item) return;
    if (item.text && typeof setCanvasContent === 'function') {
      const isFolder = !!item.is_folder;
      const safeText = item.text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      const titlePrefix = isFolder ? 'WORKSPACE INTEL' : 'DOCUMENT INTEL';
      const badgeText = isFolder ? `Folder Workspace · ${item.files_count || 0} Files` : `${item.engine || 'Direct Read'} · ${(item.size / 1024).toFixed(1)} KB`;
      const htmlContent = `
        <div style="padding: 6px; font-family: var(--font-mono); font-size: 11px; line-height: 1.5; color: var(--text-primary); white-space: pre-wrap; word-break: break-word;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 6px;">
            <span style="font-weight: 600; color: var(--accent);">${isFolder ? '📁' : '📄'} ${item.name}</span>
            <span class="badge badge-accent">${badgeText}</span>
          </div>
          <div>${safeText}</div>
        </div>
      `;
      setCanvasContent('file', `${titlePrefix} · ${item.name}`, item.text, htmlContent);
    }
  };

  window.removePayloadItem = function(idx, event) {
    if (event) event.stopPropagation();
    const item = window.ingestedPayloads[idx];
    if (!item) return;
    window.ingestedPayloads.splice(idx, 1);
    socket.send('payload_remove', { path: item.path, is_folder: item.is_folder, name: item.name });
    renderPayloadList();
    if (typeof showHudToast === 'function') {
      showHudToast(`Removed ${item.name}`);
    }
  };

  window.clearAllPayloads = function() {
    window.ingestedPayloads = [];
    socket.send('payload_clear');
    renderPayloadList();
    if (typeof showHudToast === 'function') {
      showHudToast('Cleared all ingested payloads');
    }
  };

  let _lastIngestedSig = '';
  let _lastIngestedTime = 0;

  window.displayIngestedFile = function(fileInfo) {
    if (!fileInfo) return;
    const isFolder = !!fileInfo.is_folder;

    const existingIdx = window.ingestedPayloads.findIndex(x => (x.path && fileInfo.path && x.path === fileInfo.path) || (x.name === fileInfo.name));
    if (existingIdx >= 0) {
      window.ingestedPayloads[existingIdx] = fileInfo;
    } else {
      window.ingestedPayloads.unshift(fileInfo);
    }
    renderPayloadList();

    if (fileInfo.text && typeof setCanvasContent === 'function') {
      const safeText = fileInfo.text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      const titlePrefix = isFolder ? 'WORKSPACE INTEL' : 'DOCUMENT INTEL';
      const badgeText = isFolder ? `Folder Workspace · ${fileInfo.files_count || 0} Files` : `${fileInfo.engine || 'Direct Read'} · ${(fileInfo.size / 1024).toFixed(1)} KB`;
      const htmlContent = `
        <div style="padding: 6px; font-family: var(--font-mono); font-size: 11px; line-height: 1.5; color: var(--text-primary); white-space: pre-wrap; word-break: break-word;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 6px;">
            <span style="font-weight: 600; color: var(--accent);">${isFolder ? '📁' : '📄'} ${fileInfo.name}</span>
            <span class="badge badge-accent">${badgeText}</span>
          </div>
          <div>${safeText}</div>
        </div>
      `;
      setCanvasContent('file', `${titlePrefix} · ${fileInfo.name}`, fileInfo.text, htmlContent);
    }

    // Add activity stream card (deduplicated within 2s)
    const sig = `${fileInfo.name}:${fileInfo.size}:${isFolder}`;
    const nowMs = Date.now();
    const isDuplicate = (_lastIngestedSig === sig && (nowMs - _lastIngestedTime) < 2000);
    _lastIngestedSig = sig;
    _lastIngestedTime = nowMs;

    const box = document.getElementById('stream-box');
    if (box && !isDuplicate) {
      const now = new Date().toTimeString().split(' ')[0];
      const preview = fileInfo.text ? (fileInfo.text.substring(0, 160).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') + '...') : 'Attached — ask ZEZO to read it.';
      const safeName = (fileInfo.name || 'payload').replace(/'/g, "\\'");
      const tagLabel = isFolder ? '[FOLDER ATTACHED]' : '[FILE ATTACHED]';
      const descLabel = isFolder ? `Workspace folder (${fileInfo.files_count || 0} files) attached & registered.` : (fileInfo.text ? `(${((fileInfo.size || 0) / 1024).toFixed(1)} KB) read via ${fileInfo.engine || 'engine'}.` : `(${((fileInfo.size || 0) / 1024).toFixed(1)} KB) attached — not read yet.`);
      box.insertAdjacentHTML('beforeend', `
        <div class="stream-msg stream-msg-sys ok">
          <div class="stream-msg-header">
            <div class="stream-msg-meta">
              <span class="mono text-muted">${now}</span>
              <span class="stream-msg-tag">${tagLabel}</span>
            </div>
            <button class="msg-copy-btn" onclick="copySingleMessage(this, '${safeName}')"><iconify-icon icon="solar:copy-linear"></iconify-icon></button>
          </div>
          <div class="stream-msg-body">
            <strong>${isFolder ? '📁 ' : ''}${fileInfo.name}</strong> ${descLabel}<br>
            <span style="color: var(--text-muted); font-size: 10px;">${preview}</span>
          </div>
        </div>
      `);
      box.scrollTop = box.scrollHeight;
    }
  };

  window.uploadPayloadFiles = async function(fileList) {
    if (!fileList || !fileList.length) return;
    const formData = new FormData();
    for (let i = 0; i < fileList.length; i++) {
      formData.append('file', fileList[i]);
    }

    try {
      await fetch('/api/upload', {
        method: 'POST',
        body: formData
      });
    } catch (err) {
      console.warn('Payload upload error:', err);
    }
  };

  window.uploadPayloadFolder = async function(fileList) {
    if (!fileList || !fileList.length) return;
    const formData = new FormData();

    for (let i = 0; i < fileList.length; i++) {
      const file = fileList[i];
      const relPath = file.webkitRelativePath || file.customRelativePath || file.name;
      formData.append('file', file, relPath);
    }

    try {
      await fetch('/api/upload', {
        method: 'POST',
        body: formData
      });
    } catch (err) {
      console.warn('Folder upload error:', err);
    }
  };

  // Recursive Directory Scanner for Folder Drag-and-Drop
  async function scanFilesFromEntries(items) {
    const fileEntries = [];
    async function readEntry(entry, path = '') {
      if (entry.isFile) {
        return new Promise((resolve) => {
          entry.file((file) => {
            file.customRelativePath = path ? `${path}/${file.name}` : file.name;
            fileEntries.push(file);
            resolve();
          }, () => resolve());
        });
      } else if (entry.isDirectory) {
        const dirReader = entry.createReader();
        const readBatch = () => new Promise((resolve) => {
          dirReader.readEntries((entries) => resolve(entries), () => resolve([]));
        });
        const currentPath = path ? `${path}/${entry.name}` : entry.name;
        let batch = await readBatch();
        while (batch.length > 0) {
          for (const child of batch) {
            await readEntry(child, currentPath);
          }
          batch = await readBatch();
        }
      }
    }

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.webkitGetAsEntry) {
        const entry = item.webkitGetAsEntry();
        if (entry) await readEntry(entry);
      } else if (item.getAsFile) {
        const file = item.getAsFile();
        if (file) fileEntries.push(file);
      }
    }
    return fileEntries;
  }

  socket.on('file_ingested', (fileInfo) => {
    displayIngestedFile(fileInfo);
  });

  // Prevent browser default file navigation on window drag & drop.
  // The animation loops (WebGL globe + dot matrix) are paused while a drag is
  // active so the renderer main thread can answer Chromium's drag-action
  // request in time ("updateDragAction was not called within 3000 ms").
  const _zezoPauseAnim = (dragging) => {
    window._zezoDragging = dragging;
    window._zezoAnimActive = !dragging && !document.hidden;
  };
  window.addEventListener('dragenter', (e) => {
    e.preventDefault();
    _zezoPauseAnim(true);
  });
  window.addEventListener('dragover', (e) => {
    e.preventDefault();
    if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy';
    _zezoPauseAnim(true);
  });
  window.addEventListener('dragend', () => _zezoPauseAnim(false));
  window.addEventListener('dragleave', (e) => {
    if (!e.relatedTarget) _zezoPauseAnim(false);   // left the window without dropping
  });
  window.addEventListener('drop', async (e) => {
    e.preventDefault();
    _zezoPauseAnim(false);
    const dropBox = document.getElementById('dropzone-box');
    if (dropBox) dropBox.classList.remove('dragover');
    if (e.dataTransfer && e.dataTransfer.items && e.dataTransfer.items.length) {
      const files = await scanFilesFromEntries(e.dataTransfer.items);
      if (files && files.length) {
        const hasFolder = files.some(f => f.customRelativePath && f.customRelativePath.includes('/'));
        if (hasFolder) {
          uploadPayloadFolder(files);
        } else {
          uploadPayloadFiles(files);
        }
        return;
      }
    }
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length) {
      uploadPayloadFiles(e.dataTransfer.files);
    }
  });

  // Setup drag and drop on dropzone
  const dropBox = document.getElementById('dropzone-box');
  if (dropBox) {
    dropBox.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropBox.classList.add('dragover');
    });
    dropBox.addEventListener('dragleave', (e) => {
      e.preventDefault();
      dropBox.classList.remove('dragover');
    });
    dropBox.addEventListener('drop', async (e) => {
      e.stopPropagation();
      e.preventDefault();
      _zezoPauseAnim(false);
      dropBox.classList.remove('dragover');
      if (e.dataTransfer && e.dataTransfer.items && e.dataTransfer.items.length) {
        const files = await scanFilesFromEntries(e.dataTransfer.items);
        if (files && files.length) {
          const hasFolder = files.some(f => f.customRelativePath && f.customRelativePath.includes('/'));
          if (hasFolder) {
            uploadPayloadFolder(files);
          } else {
            uploadPayloadFiles(files);
          }
          return;
        }
      }
      if (e.dataTransfer && e.dataTransfer.files) {
        uploadPayloadFiles(e.dataTransfer.files);
      }
    });
  }

  // ── Voice Preview Player ──
  let _voiceAudio = null;
  window.previewCurrentVoice = function() {
    const voiceSelect = document.getElementById('customise-voice-select');
    const btn = document.getElementById('btn-preview-voice');
    const label = document.getElementById('preview-btn-label');
    const icon = document.getElementById('preview-btn-icon');
    const status = document.getElementById('voice-preview-status');
    const voice = (voiceSelect ? voiceSelect.value : 'Puck').toLowerCase();

    if (_voiceAudio) {
      _voiceAudio.pause();
      _voiceAudio = null;
    }

    if (btn) btn.classList.add('btn-primary');
    if (label) label.innerText = 'PLAYING...';
    if (icon) icon.setAttribute('icon', 'solar:soundwave-bold');
    if (status) status.innerHTML = `<iconify-icon icon="solar:soundwave-bold" style="color:var(--accent);"></iconify-icon> Playing ${voiceSelect ? voiceSelect.value : ''} sample audio...`;

    _voiceAudio = new Audio(`/assets/voices/${voice}.mp3`);
    _voiceAudio.onended = function() {
      if (btn) btn.classList.remove('btn-primary');
      if (label) label.innerText = 'PREVIEW VOICE';
      if (icon) icon.setAttribute('icon', 'solar:play-circle-bold-duotone');
      if (status) status.innerHTML = `<iconify-icon icon="solar:volume-loud-linear"></iconify-icon> Click Preview to listen to a live sample of this voice persona`;
      _voiceAudio = null;
    };
    _voiceAudio.onerror = function() {
      if (btn) btn.classList.remove('btn-primary');
      if (label) label.innerText = 'PREVIEW VOICE';
      if (icon) icon.setAttribute('icon', 'solar:play-circle-bold-duotone');
      if (status) status.innerHTML = `<span style="color:#ef4444;">Preview unavailable for this voice</span>`;
      _voiceAudio = null;
    };
    _voiceAudio.play().catch(e => {
      console.warn('Audio play failed:', e);
      if (btn) btn.classList.remove('btn-primary');
      if (label) label.innerText = 'PREVIEW VOICE';
      if (icon) icon.setAttribute('icon', 'solar:play-circle-bold-duotone');
    });
  };

  window.togglePasswordVisibility = function(inputId, btn) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const isPass = input.type === 'password';
    input.type = isPass ? 'text' : 'password';
    if (btn) {
      btn.innerHTML = `<iconify-icon icon="solar:${isPass ? 'eye-closed-linear' : 'eye-linear'}"></iconify-icon> ${isPass ? 'Hide' : 'Show'}`;
    }
  };

  // ── Save Customise Assistant Settings & API Keys ──
  window.saveCustomiseSettings = async function() {
    const nameEl = document.getElementById('customise-asst-name');
    const voiceEl = document.getElementById('customise-voice-select');
    const langEl = document.getElementById('customise-lang-select');
    const fallbackVoiceEl = document.getElementById('customise-fallback-voice-select');
    const geminiKeyEl = document.getElementById('customise-gemini-key');
    const groqKeyEl = document.getElementById('customise-groq-key');

    const name = nameEl ? nameEl.value.trim() : 'ZEZO';
    const voice = voiceEl ? voiceEl.value : 'Charon';
    const lang = langEl ? langEl.value : 'auto';
    const fallbackVoice = fallbackVoiceEl ? fallbackVoiceEl.value : '';
    const geminiKey = geminiKeyEl ? geminiKeyEl.value.trim() : '';
    const groqKey = groqKeyEl ? groqKeyEl.value.trim() : '';

    try {
      const resp = await fetch('/api/settings/assistant', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          assistant_name: name,
          voice_name: voice,
          response_language: lang,
          fallback_voice: fallbackVoice,
          gemini_api_key: geminiKey,
          groq_api_key: groqKey,
        })
      });
      const data = await resp.json();
      if (data.status === 'success') {
        const titleEl = document.querySelector('.window-title span');
        if (titleEl && name) {
          titleEl.innerText = `${name.toUpperCase()} · AUTONOMOUS DESKTOP OS`;
        }
        if (data.data && data.data.gemini_api_key_masked) {
          const geminiStatus = document.getElementById('gemini-key-status');
          if (geminiStatus) {
            geminiStatus.style.display = 'inline-flex';
            geminiStatus.innerText = `✓ SAVED (${data.data.gemini_api_key_masked})`;
          }
        }
        if (data.data && data.data.groq_api_key_masked) {
          window._groqKeyConfigured = true;
          const groqStatus = document.getElementById('groq-key-status');
          if (groqStatus) {
            groqStatus.style.display = 'inline-flex';
            groqStatus.innerText = `✓ SAVED (${data.data.groq_api_key_masked})`;
          }
        }
        closeModal('onboarding-modal');
        closeModal('customise-modal');
      }
    } catch (err) {
      console.warn('Failed to save assistant settings via HTTP:', err);
      socket.send('save_assistant_settings', {
        assistant_name: name,
        voice_name: voice,
        response_language: lang,
        fallback_voice: fallbackVoice,
      });
      if (geminiKey || groqKey) {
        socket.send('save_api_keys', {
          gemini_api_key: geminiKey,
          groq_api_key: groqKey,
        });
      }
    }
  };

  window.saveOnboardingKey = async function() {
    const keyInput = document.getElementById('onboarding-gemini-key');
    const geminiKey = keyInput ? keyInput.value.trim() : '';
    if (!geminiKey) {
      alert('Please paste a valid Google Gemini API Key.');
      return;
    }

    try {
      const resp = await fetch('/api/settings/assistant', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          gemini_api_key: geminiKey
        })
      });
      const data = await resp.json();
      if (data.status === 'success') {
        closeModal('onboarding-modal');
        const geminiStatus = document.getElementById('gemini-key-status');
        if (geminiStatus && data.data && data.data.gemini_api_key_masked) {
          geminiStatus.style.display = 'inline-flex';
          geminiStatus.innerText = `✓ SAVED (${data.data.gemini_api_key_masked})`;
        }
      }
    } catch (e) {
      socket.send('save_api_keys', { gemini_api_key: geminiKey });
      closeModal('onboarding-modal');
    }
  };

  // ═══════════════════════════════════════════════════════════════════
  // ── High-Tech Backend Log Console Real-Time Engine (Log Bus Bridge) ──
  // ═══════════════════════════════════════════════════════════════════
  let _backendLogs = [];
  let _isLogFollow = true;
  let _isLogPaused = false;
  let _knownSources = new Set(['ALL']);

  const LEVEL_PRIORITY = {
    'DEBUG': 0,
    'INFO': 1,
    'WARNING': 2,
    'ERROR': 3,
    'CRITICAL': 4
  };

  function updateLogSourcesDropdown(sourcesList) {
    const select = document.getElementById('log-source-filter');
    if (!select) return;
    const currentVal = select.value || 'ALL';

    if (Array.isArray(sourcesList)) {
      sourcesList.forEach(s => { if (s) _knownSources.add(s); });
    }

    const sortedSources = Array.from(_knownSources).filter(s => s !== 'ALL').sort();
    let opts = '<option value="ALL">ALL SOURCES</option>';
    sortedSources.forEach(s => {
      opts += `<option value="${s}" ${s === currentVal ? 'selected' : ''}>${s}</option>`;
    });
    select.innerHTML = opts;
    if (_knownSources.has(currentVal)) {
      select.value = currentVal;
    }
  }

  function renderBackendLogs() {
    const buffer = document.getElementById('log-modal-buffer');
    const statsBadge = document.getElementById('log-stats-badge');
    const searchInput = document.getElementById('log-search-filter');
    const levelSelect = document.getElementById('log-level-filter');
    const sourceSelect = document.getElementById('log-source-filter');

    if (!buffer) return;

    const query = searchInput ? searchInput.value.trim().toLowerCase() : '';
    const minLevelName = levelSelect ? levelSelect.value : 'ALL';
    const selectedSource = sourceSelect ? sourceSelect.value : 'ALL';
    const minLevel = minLevelName === 'ALL' ? -1 : (LEVEL_PRIORITY[minLevelName] ?? -1);

    const filtered = _backendLogs.filter(item => {
      const lvl = (item.level || 'INFO').toUpperCase();
      const lvlPrio = LEVEL_PRIORITY[lvl] ?? 1;

      if (minLevel !== -1 && lvlPrio < minLevel) return false;
      if (selectedSource !== 'ALL' && item.src !== selectedSource) return false;

      if (query) {
        const textToSearch = `${item.ts || ''} ${item.src || ''} ${item.level || ''} ${item.msg || ''}`.toLowerCase();
        if (!textToSearch.includes(query)) return false;
      }
      return true;
    });

    if (statsBadge) {
      statsBadge.innerText = `${filtered.length} / ${_backendLogs.length} BUFFERED LINES`;
    }

    if (filtered.length === 0) {
      buffer.innerHTML = `
        <div style="color:var(--text-muted); padding:20px; text-align:center; font-family:var(--font-mono); font-size:11px;">
          ${_backendLogs.length === 0 ? '[SYS] Backend Log Ring Buffer empty or connecting...' : '[SYS] No log entries match the active filters.'}
        </div>
      `;
      return;
    }

    const htmlRows = filtered.map(item => {
      const lvl = (item.level || 'INFO').toUpperCase();
      let color = '#a0a0ab';
      let lvlColor = '#94a3b8';

      if (lvl === 'ERROR' || lvl === 'CRITICAL') {
        color = '#f87171';
        lvlColor = '#ef4444';
      } else if (lvl === 'WARNING') {
        color = '#fbbf24';
        lvlColor = '#f59e0b';
      } else if (lvl === 'DEBUG') {
        color = '#64748b';
        lvlColor = '#475569';
      } else if (lvl === 'INFO') {
        color = '#e2e8f0';
        lvlColor = '#38bdf8';
      }

      const safeMsg = (item.msg || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

      return `
        <div style="display:flex; align-items:baseline; gap:8px; padding:1px 0; color:${color}; word-break:break-all;">
          <span style="color:rgba(255,255,255,0.35); flex-shrink:0; font-size:9.5px;">${item.ts || '--:--:--'}</span>
          <span style="color:var(--accent); font-weight:600; flex-shrink:0; font-size:9.5px; min-width:65px;">[${item.src || 'zezo'}]</span>
          <span style="color:${lvlColor}; font-weight:700; flex-shrink:0; font-size:9px; width:45px;">${lvl}</span>
          <span style="flex:1; white-space:pre-wrap;">${safeMsg}</span>
        </div>
      `;
    }).join('');

    buffer.innerHTML = htmlRows;

    if (_isLogFollow && !_isLogPaused) {
      buffer.scrollTop = buffer.scrollHeight;
    }
  }

  window.requestBackendLogs = function() {
    socket.send('get_backend_logs', {});
  };

  window.filterBackendLogs = function() {
    renderBackendLogs();
  };

  window.toggleLogFollow = function() {
    _isLogFollow = !_isLogFollow;
    const btn = document.getElementById('log-follow-btn');
    const label = document.getElementById('log-follow-label');
    if (btn) {
      if (_isLogFollow) {
        btn.classList.add('active');
        if (label) label.innerText = 'FOLLOW';
      } else {
        btn.classList.remove('active');
        if (label) label.innerText = 'FREE SCROLL';
      }
    }
    if (_isLogFollow) {
      const buffer = document.getElementById('log-modal-buffer');
      if (buffer) buffer.scrollTop = buffer.scrollHeight;
    }
  };

  window.toggleLogPause = function() {
    _isLogPaused = !_isLogPaused;
    const btn = document.getElementById('log-pause-btn');
    const label = document.getElementById('log-pause-label');
    if (btn) {
      if (_isLogPaused) {
        btn.classList.add('active');
        btn.style.borderColor = '#ef4444';
        btn.style.color = '#ef4444';
        if (label) label.innerText = 'RESUME';
      } else {
        btn.classList.remove('active');
        btn.style.borderColor = '';
        btn.style.color = '';
        if (label) label.innerText = 'PAUSE';
      }
    }
    if (!_isLogPaused) {
      renderBackendLogs();
    }
  };

  window.clearBackendLogsUI = function() {
    _backendLogs = [];
    socket.send('clear_backend_logs', {});
    renderBackendLogs();
  };

  window.exportBackendLogsUI = function() {
    socket.send('export_backend_logs', {});
  };

  window.copyBackendLogsUI = function(btn) {
    if (!_backendLogs.length) return;
    const searchInput = document.getElementById('log-search-filter');
    const query = searchInput ? searchInput.value.trim().toLowerCase() : '';

    let textToCopy = '=== ZEZO BACKEND LOG BUS EXPORT ===\n';
    textToCopy += `Timestamp: ${new Date().toISOString()}\n`;
    textToCopy += `Total Lines: ${_backendLogs.length}\n\n`;

    _backendLogs.forEach(item => {
      textToCopy += `[${item.ts || '--:--:--'}] [${(item.src || 'zezo').padEnd(12)}] [${(item.level || 'INFO').padEnd(7)}] ${item.msg || ''}\n`;
    });

    if (typeof writeToSystemClipboard === 'function') {
      writeToSystemClipboard(textToCopy);
    }

    if (btn) {
      const origHtml = btn.innerHTML;
      btn.innerHTML = '<iconify-icon icon="solar:check-circle-bold" style="font-size:11px; color:#22c55e;"></iconify-icon> <span style="color:#22c55e;">COPIED!</span>';
      setTimeout(() => {
        btn.innerHTML = origHtml;
      }, 1500);
    }
  };

  // Socket Handlers for Backend Log Bus
  socket.on('backend_logs', (payload) => {
    if (!payload) return;
    const lines = payload.lines || (payload.data && payload.data.lines) || (Array.isArray(payload) ? payload : []);
    if (!lines.length) return;

    const sources = payload.sources || (payload.data && payload.data.sources);
    if (sources) {
      updateLogSourcesDropdown(sources);
    }

    lines.forEach(l => {
      if (l && l.src) _knownSources.add(l.src);
    });

    if (!_isLogPaused) {
      _backendLogs.push(...lines);
      if (_backendLogs.length > 5000) {
        _backendLogs = _backendLogs.slice(_backendLogs.length - 5000);
      }
      renderBackendLogs();
    }
  });

  socket.on('backend_logs_snapshot', (payload) => {
    if (!payload) return;
    const lines = payload.lines || (payload.data && payload.data.lines) || (Array.isArray(payload) ? payload : []);
    _backendLogs = lines;
    const sources = payload.sources || (payload.data && payload.data.sources);
    if (sources) {
      updateLogSourcesDropdown(sources);
    }
    _backendLogs.forEach(l => {
      if (l && l.src) _knownSources.add(l.src);
    });
    renderBackendLogs();
  });

  socket.on('backend_logs_cleared', () => {
    _backendLogs = [];
    renderBackendLogs();
  });

  socket.on('backend_logs_export_data', (payload) => {
    const text = (payload && payload.text) || '';
    if (!text) return;
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `zezo_backend_logs_${new Date().toISOString().replace(/[:.]/g, '-')}.log`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });

  // ── AUDIO I/O PANEL ────────────────────────────────────────────────────────
  // The panel used to be static HTML. It now reflects the real saved endpoints,
  // lists the devices the app can actually open, and warns when a saved device
  // is unavailable (meaning ZEZO silently fell back to the system default).
  function _fillAudioSelect(selectEl, devices, current, defaultName) {
    if (!selectEl) return;
    selectEl.innerHTML = '';
    const add = (label, value) => {
      const opt = document.createElement('option');
      opt.value = value;
      opt.textContent = label;
      selectEl.appendChild(opt);
    };
    add(defaultName ? `System default — ${defaultName}` : 'System default', '');
    (devices || []).forEach(d => { if (d && d !== 'System default') add(d, d); });
    if (current && !(devices || []).includes(current)) {
      add(`${current} (unavailable)`, current);
    }
    selectEl.value = current || '';
  }

  function applyAudioDevices(data) {
    if (!data) return;
    _fillAudioSelect(document.getElementById('audio-input-select'),
                     data.input_devices,  data.input_device,
                     data.default_input_device);
    _fillAudioSelect(document.getElementById('audio-output-select'),
                     data.output_devices, data.output_device,
                     data.default_output_device);

    const inWarn  = document.getElementById('audio-input-warning');
    const outWarn = document.getElementById('audio-output-warning');
    if (inWarn) {
      const bad = data.input_available === false;
      inWarn.style.display = bad ? 'block' : 'none';
      inWarn.textContent = bad
        ? '⚠ Saved mic cannot be opened at 16 kHz — ZEZO is using the system default.'
        : '';
    }
    if (outWarn) {
      const bad = data.output_available === false;
      outWarn.style.display = bad ? 'block' : 'none';
      outWarn.textContent = bad
        ? '⚠ Saved speaker cannot be opened at 24 kHz — ZEZO is using the system default.'
        : '';
    }
  }

  window.requestAudioDevices = function() {
    if (window.socket) window.socket.send('get_audio_devices', {});
  };

  window.saveAudioDevices = function() {
    const inEl  = document.getElementById('audio-input-select');
    const outEl = document.getElementById('audio-output-select');
    const input_device  = inEl  ? inEl.value  : '';
    const output_device = outEl ? outEl.value : '';
    const label = document.getElementById('audio-save-label');
    if (window.socket) {
      window.socket.send('save_audio_devices', { input_device, output_device });
      if (label) {
        label.textContent = 'APPLIED — RECONNECTING';
        setTimeout(() => { label.textContent = 'APPLY & RECONNECT'; }, 2500);
      }
    }
    if (typeof closeModal === 'function') closeModal('audio-modal');
  };

  socket.on('audio_devices_updated', applyAudioDevices);
  socket.on('init', applyAudioDevices);

  // Live microphone meter — shows whether ZEZO's mic is actually hearing
  // anything, independent of the echo filter or any gate.
  let _micLoudAt = 0;
  socket.on('mic_level', (d) => {
    const lvl = Math.max(0, Math.min(1, (d && d.level) || 0));
    const bar = document.getElementById('audio-mic-bar');
    const st  = document.getElementById('audio-mic-status');
    if (bar) bar.style.width = `${Math.min(100, lvl * 140)}%`;
    if (st) {
      if (lvl > 0.03) {
        _micLoudAt = Date.now();
        st.textContent = 'MIC: hearing you';
        st.style.color = '#22c55e';
      } else if (Date.now() - _micLoudAt > 2000) {
        st.textContent = 'MIC: no signal';
        st.style.color = '#f59e0b';
      }
    }
  });

   // Toast Helper
   window.showToast = function(message, type) {
     var container = document.getElementById('zezo-toast-container');
     if (!container) return;
     var icons = { success: '[OK]', error: '[X]', info: '[i]' };
     var toast = document.createElement('div');
     toast.className = 'zezo-toast ' + (type || 'info');
     toast.innerHTML = '<span class="toast-icon">' + (icons[type] || '[i]') + '</span><span>' + message + '</span>';
     container.appendChild(toast);
     setTimeout(function() {
       toast.classList.add('removing');
       setTimeout(function() { toast.remove(); }, 200);
     }, 2500);
   };
   window.showHudToast = window.showToast;

  // ── VOICE PIPELINE MODAL ──────────────────────────────────────────────────────
  window.togglePipelineMode = function(mode) {
    const cascadeSection = document.getElementById('cascade-engines-section');
    if (cascadeSection) {
      cascadeSection.style.display = mode === 'cascade' ? 'flex' : 'none';
    }
    updatePipelineWarnings();
  };

  window.updateTtsVoiceOptions = function() {
    const ttsEngine = document.getElementById('tts-engine-select')?.value || 'kokoro';
    const voiceSelect = document.getElementById('tts-voice-select');
    if (!voiceSelect) return;

    const voices = {};
    voices.kokoro = ['af_heart', 'af_bella', 'af_nicole', 'af_sarah', 'af_sky', 'am_adam', 'am_michael', 'bf_emma', 'bf_isabella', 'bm_george', 'bm_lewis'];
    voices.edge_tts = ['en-US-AriaNeural', 'en-US-GuyNeural', 'en-GB-SoniaNeural', 'en-GB-RyanNeural'];
    voices.elevenlabs = ['default', 'voice_1', 'voice_2', 'voice_3'];

    voiceSelect.innerHTML = '<option value="">Default for Engine</option>';
    (voices[ttsEngine] || []).forEach(v => {
      const opt = document.createElement('option');
      opt.value = v;
      opt.textContent = v;
      voiceSelect.appendChild(opt);
    });
  };

  window.updatePipelineWarnings = function() {
    const warningsDiv = document.getElementById('pipeline-warnings-section');
    if (!warningsDiv) return;
    warningsDiv.innerHTML = '';

    const mode = document.querySelector('input[name="pipeline-mode"]:checked')?.value || 'live';
    if (mode === 'live') return;

    const warnings = [];

    // Check for Groq API key if Groq LLM/STT selected
    const sttEngine = document.getElementById('stt-engine-select')?.value;
    const llmEngine = document.getElementById('llm-engine-select')?.value;
    const useGroq = (sttEngine === 'groq_whisper') || (llmEngine === 'groq');
    if (useGroq && !window._groqKeyConfigured) {
      warnings.push('⚠️ Groq API key not configured');
    }

    // Check TTS engine requirements
    const ttsEngine = document.getElementById('tts-engine-select')?.value || 'kokoro';
    if (ttsEngine === 'elevenlabs' && !window._elevenLabsKeyConfigured) {
      warnings.push('⚠️ ElevenLabs API key not configured');
    }
    if (ttsEngine === 'kokoro') {
      warnings.push('ℹ️ Kokoro requires Python 3.11–3.13');
    }

    // Check LLM availability
    if (llmEngine === 'ollama') {
      warnings.push('ℹ️ Ensure Ollama is running locally');
    }

    // Only show tools limitation as a note, not a warning
    if (warnings.length === 0) {
      warnings.push('ℹ️ Tools & code actions limited in Cascade mode');
    }

    warnings.forEach(w => {
      const badge = document.createElement('div');
      badge.style.display = 'flex';
      badge.style.alignItems = 'center';
      badge.style.gap = '6px';
      badge.style.padding = '8px 10px';
      
      // Determine badge style based on prefix
      let bgColor = 'var(--accent-dim)';
      let borderColor = 'var(--accent)';
      let textColor = 'var(--accent)';
      
      if (w.startsWith('ℹ️')) {
        bgColor = 'rgba(100, 150, 255, 0.15)';
        borderColor = 'rgba(100, 150, 255, 0.5)';
        textColor = 'rgba(100, 150, 255, 1)';
      }
      
      badge.style.backgroundColor = bgColor;
      badge.style.border = `1px solid ${borderColor}`;
      badge.style.borderRadius = 'var(--radius-sm)';
      badge.style.fontSize = '11px';
      badge.style.color = textColor;
      badge.innerHTML = w.replace(/^[⚠️ℹ️]+/, '');
      warningsDiv.appendChild(badge);
    });
  };

  window.applyPreset = function(preset) {
    const modeInput = document.querySelector('input[name="pipeline-mode"]');
    const sttSelect = document.getElementById('stt-engine-select');
    const llmSelect = document.getElementById('llm-engine-select');
    const ttsSelect = document.getElementById('tts-engine-select');

    if (preset === 'live') {
      if (modeInput) modeInput.checked = true;
      if (modeInput) modeInput.value = 'live';
      togglePipelineMode('live');
    } else if (preset === 'cloud-fast') {
      if (modeInput) modeInput.checked = false;
      document.querySelector('input[name="pipeline-mode"][value="cascade"]').checked = true;
      if (sttSelect) sttSelect.value = 'groq_whisper';
      if (llmSelect) llmSelect.value = 'groq';
      if (ttsSelect) ttsSelect.value = 'edge_tts';
      updateTtsVoiceOptions();
      togglePipelineMode('cascade');
    } else if (preset === 'balanced') {
      document.querySelector('input[name="pipeline-mode"][value="cascade"]').checked = true;
      if (sttSelect) sttSelect.value = 'groq_whisper';
      if (llmSelect) llmSelect.value = 'groq';
      if (ttsSelect) ttsSelect.value = 'kokoro';
      updateTtsVoiceOptions();
      togglePipelineMode('cascade');
    } else if (preset === 'offline') {
      document.querySelector('input[name="pipeline-mode"][value="cascade"]').checked = true;
      if (sttSelect) sttSelect.value = 'local_whisper';
      if (llmSelect) llmSelect.value = 'ollama';
      if (ttsSelect) ttsSelect.value = 'kokoro';
      updateTtsVoiceOptions();
      togglePipelineMode('cascade');
    }
  };

  window.savePipelineSettings = function() {
    const mode = document.querySelector('input[name="pipeline-mode"]:checked')?.value || 'live';
    const payload = { pipeline_mode: mode };

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

    // Disable APPLY button during save
    const applyBtn = document.querySelector('#pipeline-modal .btn-primary');
    const origText = applyBtn?.textContent || 'APPLY';
    if (applyBtn) {
      applyBtn.disabled = true;
      applyBtn.textContent = 'SAVING...';
    }

    fetch('/api/settings/pipeline', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    .then(r => r.json())
    .then(d => {
      if (d.status === 'success') {
        closeModal('pipeline-modal');
        if (typeof showHudToast === 'function') {
          showHudToast('✅ Pipeline settings saved');
        }
      } else {
        // Re-enable button on error
        if (applyBtn) {
          applyBtn.disabled = false;
          applyBtn.textContent = origText;
        }
        if (typeof showHudToast === 'function') {
          showHudToast(`❌ Error: ${d.message || 'Failed to save'}`);
        } else {
          console.error('Save failed:', d.message);
        }
      }
    })
    .catch(e => {
      // Re-enable button on error
      if (applyBtn) {
        applyBtn.disabled = false;
        applyBtn.textContent = origText;
      }
      if (typeof showHudToast === 'function') {
        showHudToast('❌ Error: Could not save settings');
      } else {
        console.error('Pipeline save error:', e);
      }
    });
  };

  // Initialize pipeline warnings on modal open
  socket.on('init', (data) => {
    if (data) {
      // Populate pipeline state
      if (data.pipeline_mode) {
        const modeRadio = document.querySelector(`input[name="pipeline-mode"][value="${data.pipeline_mode}"]`);
        if (modeRadio) modeRadio.checked = true;
        togglePipelineMode(data.pipeline_mode);

        if (data.stt_engine && document.getElementById('stt-engine-select')) {
          document.getElementById('stt-engine-select').value = data.stt_engine;
        }
        if (data.llm_engine && document.getElementById('llm-engine-select')) {
          document.getElementById('llm-engine-select').value = data.llm_engine;
        }
        if (data.tts_engine && document.getElementById('tts-engine-select')) {
          document.getElementById('tts-engine-select').value = data.tts_engine;
          updateTtsVoiceOptions();
        }
        if (data.tts_voice && document.getElementById('tts-voice-select')) {
          document.getElementById('tts-voice-select').value = data.tts_voice;
        }
      }
      // Populate warning check flags
      window._groqKeyConfigured = data.has_groq_key === true || Boolean(data.groq_api_key_masked);
      window._elevenLabsKeyConfigured = data.has_elevenlabs_key === true;
      // Note: Ollama health check would require a separate endpoint; defaulting to optimistic
      window._ollamaRunning = true;
    }
  });

  // Connect to WebSocket AFTER all function handlers are defined
  socket.connect();
