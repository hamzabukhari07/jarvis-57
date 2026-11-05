import React, { useState, useEffect, useRef } from 'react';
import { 
  Home, Users, Workflow, ChevronDown, ChevronRight, Settings, MoreVertical, 
  Activity, Terminal, QrCode, UserCheck, MessageSquare 
} from 'lucide-react';
import type { Session } from '../types';

interface SidebarProps {
  currentSession?: Session;
  onSelectSession?: (session: Session) => void;
  onNewChat?: () => void;
  onOpenSettings: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  onOpenSettings,
}) => {
  const [activeTab, setActiveTab] = useState<string>('home');
  const [isAgentsOpen, setIsAgentsOpen] = useState(true);
  const [showQuickMenu, setShowQuickMenu] = useState(false);
  const menuContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleOutsideClick = (event: MouseEvent) => {
      if (menuContainerRef.current && !menuContainerRef.current.contains(event.target as Node)) {
        setShowQuickMenu(false);
      }
    };

    if (showQuickMenu) {
      document.addEventListener('mousedown', handleOutsideClick);
    }
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
    };
  }, [showQuickMenu]);

  return (
    <aside className="sidebar">
      <div className="sidebar-panel">
        
        {/* Header & Brand with Online Badge */}
        <div className="sidebar-header">
          <div className="brand-row">
            <a href="#" className="brand">
              <span className="brand-icon">
                <img 
                  src="/zezo-logo.png" 
                  alt="ZEZO Logo" 
                  className="brand-logo-img" 
                />
              </span>
              <div className="brand-info">
                <div className="brand-name">
                  ZEZO
                  <span className="brand-badge">v1.0</span>
                </div>
              </div>
            </a>

            {/* Current System WebSocket Status Indicator */}
            <div className="system-status-indicator" title="WebSocket Live Connected">
              <span className="pulse-dot pulse"></span>
              <span>Online</span>
            </div>
          </div>
        </div>

        {/* Sidebar Body Card (Tree Navigation) */}
        <div className="sidebar-body">
          <div className="nav-tree-container">
            <div className="nav-tree-section-label">NAVIGATION</div>

            {/* 1. HOME (Primary Pill) */}
            <button 
              className={`nav-tree-item ${activeTab === 'home' ? 'active' : ''}`}
              onClick={() => setActiveTab('home')}
            >
              <Home size={16} className="nav-tree-icon" />
              <span className="nav-tree-label">HOME</span>
            </button>

            {/* 2. AGENTS (Collapsible Accordion) */}
            <div className="nav-tree-group">
              <button 
                className={`nav-tree-item ${activeTab.startsWith('agents') ? 'parent-active' : ''}`}
                onClick={() => setIsAgentsOpen(!isAgentsOpen)}
              >
                <Users size={16} className="nav-tree-icon" />
                <span className="nav-tree-label">AGENTS</span>
                {isAgentsOpen ? (
                  <ChevronDown size={14} className="nav-tree-chevron" />
                ) : (
                  <ChevronRight size={14} className="nav-tree-chevron" />
                )}
              </button>

              {/* Sub-Items with Tree Guide Line and Icons */}
              {isAgentsOpen && (
                <div className="nav-sub-tree">
                  <button 
                    className={`nav-sub-item ${activeTab === 'agents-manage' ? 'active' : ''}`}
                    onClick={() => setActiveTab('agents-manage')}
                  >
                    <UserCheck size={14} className="nav-sub-icon" />
                    <span>Manage Agents</span>
                  </button>

                  <button 
                    className={`nav-sub-item ${activeTab === 'agents-chat' ? 'active' : ''}`}
                    onClick={() => setActiveTab('agents-chat')}
                  >
                    <MessageSquare size={14} className="nav-sub-icon" />
                    <span>Chat Space</span>
                  </button>
                </div>
              )}
            </div>

            {/* 3. WORKFLOW */}
            <button 
              className={`nav-tree-item ${activeTab === 'workflow' ? 'active' : ''}`}
              onClick={() => setActiveTab('workflow')}
            >
              <Workflow size={16} className="nav-tree-icon" />
              <span className="nav-tree-label">WORKFLOW</span>
            </button>
          </div>

          {/* Spacer */}
          <div className="nav-tree-spacer" />

        </div>

        {/* Sidebar Footer Controls (Outside the white card, exactly as in Vitrum Studio Reference Design) */}
        <div className="sidebar-footer">
          <button 
            className="footer-link" 
            onClick={onOpenSettings}
            title="Settings"
          >
            <Settings size={14} className="footer-link-icon" />
            <span>Settings</span>
          </button>

          <div className="footer-menu-container" ref={menuContainerRef}>
            <button 
              className={`footer-kbd-btn ${showQuickMenu ? 'active' : ''}`}
              onClick={() => setShowQuickMenu(!showQuickMenu)}
              title="Quick menu"
            >
              <MoreVertical size={14} />
            </button>

            {/* Quick Menu Popup */}
            {showQuickMenu && (
              <div className="quick-menu-popup show" onClick={(e) => e.stopPropagation()}>
                <button className="quick-menu-item" onClick={() => setShowQuickMenu(false)}>
                  <Activity size={14} />
                  <span>Tasks & Process Manager</span>
                </button>
                <button className="quick-menu-item" onClick={() => setShowQuickMenu(false)}>
                  <Terminal size={14} />
                  <span>Live Backend Logs</span>
                </button>
                <div className="quick-menu-divider"></div>
                <button className="quick-menu-item" onClick={() => setShowQuickMenu(false)}>
                  <QrCode size={14} />
                  <span>Mobile Remote QR Pairing</span>
                </button>
              </div>
            )}
          </div>
        </div>

      </div>
    </aside>
  );
};
