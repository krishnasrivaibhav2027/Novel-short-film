import React from 'react';
import { Download, Film, CheckCircle, AlertCircle, Clock, HardDrive, RefreshCw } from 'lucide-react';
import type { ExportRecord, Project, SceneResponse } from '../types';

interface PremiereStepProps {
  project: Project;
  latestExport: ExportRecord | null;
  scenes: SceneResponse[];
  onBackToStudio: () => void;
}

export const PremiereStep: React.FC<PremiereStepProps> = ({
  project,
  latestExport,
  scenes,
  onBackToStudio,
}) => {
  if (!latestExport) {
    return (
      <div className="glass-panel hero-card" style={{ textAlign: 'center', padding: '3rem' }}>
        <Film size={48} color="var(--accent-gold)" style={{ margin: '0 auto 1rem' }} />
        <h2 className="card-title">Movie Assembly Pending</h2>
        <p className="card-desc" style={{ margin: '0 auto 1.5rem' }}>
          Please complete and assemble your scene clips in the Production Studio before premiering.
        </p>
        <button type="button" className="btn btn-primary" onClick={onBackToStudio}>
          Return to Production Studio
        </button>
      </div>
    );
  }

  const fileSizeMb = (latestExport.file_size_bytes / (1024 * 1024)).toFixed(2);
  const downloadUrl = `${latestExport.media_url}?download=true`;

  return (
    <div className="glass-panel hero-card" id="step-premiere">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.5rem' }}>
        <div>
          <span className="chip chip-approved" style={{ marginBottom: '0.4rem' }}>
            <CheckCircle size={12} /> THEATRICAL CUT READY
          </span>
          <h2 className="card-title">{project.title}</h2>
          <p className="card-desc" style={{ marginBottom: 0 }}>
            Official animated film adaptation assembled via FFmpeg with normalized 24fps video and mixed narration audio.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <a
            href={downloadUrl}
            className="btn btn-primary"
            id="btn-download-mp4"
            download
          >
            <Download size={16} />
            <span>Download Film (.MP4)</span>
          </a>

          <button
            type="button"
            className="btn btn-secondary"
            onClick={onBackToStudio}
            id="btn-edit-scenes-cut"
          >
            <RefreshCw size={15} />
            <span>Tweak & Re-Assemble</span>
          </button>
        </div>
      </div>

      {/* Theater View */}
      <div className="screening-theater">
        <div className="video-player-wrapper">
          <video
            src={latestExport.media_url}
            controls
            autoPlay
            playsInline
            className="video-element"
            id="main-movie-player"
          />
        </div>

        {/* Film Specs Pill Bar */}
        <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', justifyContent: 'center', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Clock size={15} color="var(--accent-gold)" /> Runtime: {latestExport.duration_seconds.toFixed(1)}s
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Film size={15} color="#06b6d4" /> Total Shots: {latestExport.clip_count}
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <HardDrive size={15} color="#8b5cf6" /> File Size: {fileSizeMb} MB
          </span>
          {latestExport.missing_scene_count > 0 && (
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--accent-rose)' }}>
              <AlertCircle size={15} /> Missing Cards: {latestExport.missing_scene_count}
            </span>
          )}
        </div>
      </div>

      {/* Shots Timeline Breakdown */}
      <div style={{ marginTop: '2.5rem', borderTop: '1px solid var(--border-subtle)', paddingTop: '1.5rem' }}>
        <h3 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Film size={18} color="var(--accent-gold)" />
          <span>Timeline Shot Breakdown</span>
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
          {scenes.map((sc) => {
            const hasVideo = Boolean(sc.selected_video_url);

            return (
              <div
                key={sc.id}
                style={{
                  background: 'var(--bg-surface)',
                  padding: '0.85rem 1rem',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  gap: '0.75rem',
                  alignItems: 'center',
                }}
              >
                <span className="scene-order-badge" style={{ minWidth: '40px', textAlign: 'center' }}>
                  #{sc.order_index}
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 600, fontSize: '0.9rem', color: '#fff', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {sc.title}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                    {hasVideo ? 'Rendered shot included' : 'Placeholder card inserted'}
                  </div>
                </div>
                <span className={`chip ${hasVideo ? 'chip-approved' : 'chip-failed'}`} style={{ fontSize: '0.68rem' }}>
                  {hasVideo ? 'READY' : 'PLACEHOLDER'}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
