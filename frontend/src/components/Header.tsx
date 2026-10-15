import React from 'react';
import { Clapperboard, DollarSign, RefreshCw, Cpu } from 'lucide-react';
import type { Project, SystemHealth } from '../types';

interface HeaderProps {
  currentProject: Project | null;
  health: SystemHealth | null;
  onNewProject: () => void;
  onOpenUsage: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentProject,
  health,
  onNewProject,
  onOpenUsage,
}) => {
  return (
    <header className="app-header" id="main-header">
      <div className="container header-content">
        <div className="logo-group">
          <div className="logo-badge">
            <Clapperboard size={22} />
          </div>
          <div>
            <div className="logo-title">NOVEL-TO-MOVIE AI</div>
            <div className="logo-subtitle">Multimodal Film Studio • LangGraph Orchestration</div>
          </div>
        </div>

        <div className="header-meta">
          {health && (
            <div className="status-pill" title={`Text: ${health.models.text} | Video: ${health.models.video}`}>
              <Cpu size={14} color="#06b6d4" />
              <span>
                {health.provider_mode === 'free_tier'
                  ? 'Gemini Free Tier (Text + TTS) • $0 Budget'
                  : health.use_live_providers
                  ? 'Gemini 3.8 + Veo 3.1'
                  : 'Animatic Mode (Fallback)'}
              </span>
              <span
                className="status-dot"
                style={{
                  background: health.provider_mode === 'free_tier' ? '#06b6d4' : health.use_live_providers ? 'var(--accent-emerald)' : 'var(--accent-gold)',
                  boxShadow: health.provider_mode === 'free_tier' ? '0 0 10px #06b6d4' : health.use_live_providers ? '0 0 10px var(--accent-emerald)' : '0 0 10px var(--accent-gold)',
                }}
              />
            </div>
          )}

          {currentProject && (
            <button
              className="btn btn-secondary btn-sm"
              onClick={onOpenUsage}
              id="btn-usage-hud"
              title="View operational costs & token usage"
            >
              <DollarSign size={14} color="#f59e0b" />
              <span>Usage & Budget</span>
            </button>
          )}

          <button
            className="btn btn-secondary btn-sm"
            onClick={onNewProject}
            id="btn-new-film"
          >
            <RefreshCw size={14} />
            <span>New Film</span>
          </button>
        </div>
      </div>
    </header>
  );
};
