import React, { useState } from 'react';
import { ChevronDown, Check, X } from 'lucide-react';
import type { ToolCall } from '../types';

interface ToolActionCardProps {
  tool: ToolCall;
}

export const ToolActionCard: React.FC<ToolActionCardProps> = ({ tool }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  const renderStatusPill = () => {
    switch (tool.status) {
      case 'running':
        return (
          <span className="tool-status-pill running">
            <span className="tool-spinner"></span>
            <span>Running</span>
          </span>
        );
      case 'completed':
        return (
          <span className="tool-status-pill completed">
            <Check size={11} strokeWidth={2.5} />
            <span>Executed</span>
          </span>
        );
      case 'failed':
        return (
          <span className="tool-status-pill failed">
            <X size={11} strokeWidth={2.5} />
            <span>Failed</span>
          </span>
        );
      case 'cancelled':
        return (
          <span className="tool-status-pill cancelled">
            <span>Cancelled</span>
          </span>
        );
      default:
        return (
          <span className="tool-status-pill queued">
            <span>Queued</span>
          </span>
        );
    }
  };

  return (
    <div className={`tool-action-card ${isCollapsed ? 'collapsed' : ''}`}>
      <div 
        className="tool-card-header" 
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="tool-header-info">
          {renderStatusPill()}
          <span className="tool-name">{tool.name}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="tool-action-detail">{tool.detail}</span>
          <ChevronDown className="tool-toggle-icon" size={13} strokeWidth={2.2} />
        </div>
      </div>
      <div className="tool-card-body">
        <div className="tool-detail-section">
          <span className="tool-detail-label">Action Input</span>
          <div className="tool-command-preview">
            <span className="prompt-sym">$</span>
            <span>{tool.command}</span>
          </div>
        </div>
        <div className="tool-detail-section">
          <span className="tool-detail-label">Execution Result</span>
          <div className="tool-output-preview">{tool.output}</div>
        </div>
      </div>
    </div>
  );
};
