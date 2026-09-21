/**
 * Background Task Matrix & Progress Tracker for ZEZO OS.
 */

export class TaskManagerUI {
    constructor(taskListContainerId, taskMatrixDrawerId) {
        this.listContainer = document.getElementById(taskListContainerId);
        this.drawer = document.getElementById(taskMatrixDrawerId);
        this.tasks = new Map();
        this.inspectedTaskId = null;
    }

    updateTasks(taskList = []) {
        taskList.forEach(task => {
            if (task && task.id) {
                this.tasks.set(task.id, task);
            }
        });
        this.render();
    }

    render() {
        if (!this.listContainer) return;
        const taskArray = Array.from(this.tasks.values()).reverse();

        if (taskArray.length === 0) {
            this.listContainer.innerHTML = `
                <div style="padding: 24px; text-align: center; color: var(--text-muted); font-family: var(--font-mono); font-size: 10px;">
                    ◈ NO BACKGROUND TASKS ACTIVE
                </div>
            `;
            return;
        }

        this.listContainer.innerHTML = taskArray.map(task => {
            const status = (task.status || 'RUNNING').toUpperCase();
            const isRunning = status === 'RUNNING';
            const progress = status === 'DONE' || status === 'COMPLETED' ? 100 : (task.progress || 0);
            const tool = (task.tool || 'AGENT').toUpperCase();
            const elapsed = task.elapsed_sec ? `${task.elapsed_sec.toFixed(1)}s` : '0.0s';

            let statusColor = 'var(--accent)';
            if (status === 'DONE' || status === 'COMPLETED') statusColor = 'var(--green)';
            if (status === 'FAILED' || status === 'CANCELLED') statusColor = 'var(--red)';

            return `
                <div class="task-card" style="background: var(--bg-surface); border: 1px solid var(--border-subtle); padding: 8px 10px; margin-bottom: 6px; display: flex; flex-direction: column; gap: 4px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; font-family: var(--font-mono); font-size: 9px;">
                        <div style="display: flex; align-items: center; gap: 6px;">
                            <span style="color: var(--accent); background: var(--accent-dim); padding: 1px 4px; font-weight: 700;">⚡ ${tool}</span>
                            <span style="color: var(--text-secondary);">#${task.id.slice(0, 8)}</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 6px;">
                            <span style="color: ${statusColor}; font-weight: 700;">${status}</span>
                            <span style="color: var(--text-muted);">${elapsed}</span>
                            ${isRunning ? `<button onclick="window.zezoApp.cancelTask('${task.id}')" style="background: var(--red-dim); color: var(--red); border: 1px solid rgba(239,68,68,0.3); font-size: 8px; font-family: var(--font-mono); cursor: pointer; padding: 0 4px;">✕</button>` : ''}
                        </div>
                    </div>
                    <div style="font-family: var(--font-sans); font-size: 10px; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                        ${task.message || 'Task processing in background...'}
                    </div>
                    <div style="height: 3px; background: rgba(255,255,255,0.06); width: 100%; overflow: hidden;">
                        <div style="height: 100%; width: ${progress}%; background: ${statusColor}; transition: width 0.3s ease;"></div>
                    </div>
                </div>
            `;
        }).join('');
    }
}
