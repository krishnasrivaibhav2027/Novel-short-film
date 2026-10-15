import React, { useState, useRef } from 'react';
import {
  Play,
  RotateCcw,
  AlertTriangle,
  Film,
  DollarSign,
  Edit,
  X,
  Volume2,
  Upload,
  Copy,
  CheckCheck,
  Info,
} from 'lucide-react';
import type { JobsSummary, ProductionEstimate, SceneResponse } from '../types';

interface ProductionStepProps {
  scenes: SceneResponse[];
  jobsSummary: JobsSummary | null;
  estimate: ProductionEstimate | null;
  onStartProduction: (confirmBudget: boolean) => Promise<void>;
  onRetryScene: (sceneId: string) => Promise<void>;
  onRegenerateScene: (sceneId: string, updates: { visual_prompt?: string; dialogue_or_narration?: string }) => Promise<void>;
  onAssembleMovie: () => Promise<void>;
  onUploadClip?: (sceneId: string, file: File) => Promise<void>;
  loading: boolean;
}

export const ProductionStep: React.FC<ProductionStepProps> = ({
  scenes,
  jobsSummary,
  estimate,
  onStartProduction,
  onRetryScene,
  onRegenerateScene,
  onAssembleMovie,
  onUploadClip,
  loading,
}) => {
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [regenModalScene, setRegenModalScene] = useState<SceneResponse | null>(null);
  const [regenPrompt, setRegenPrompt] = useState('');
  const [regenDialogue, setRegenDialogue] = useState('');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [uploadingSceneId, setUploadingSceneId] = useState<string | null>(null);
  const videoInputRefs = useRef<{ [key: string]: HTMLInputElement | null }>({});

  const copyPrompt = (key: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2500);
  };

  const handleVideoUpload = async (sceneId: string, e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !onUploadClip) return;
    setUploadingSceneId(sceneId);
    try {
      await onUploadClip(sceneId, file);
    } finally {
      setUploadingSceneId(null);
    }
  };

  const completedScenesCount = scenes.filter(
    (s) => s.state === 'GENERATED' || s.state === 'APPROVED'
  ).length;
  const failedScenesCount = scenes.filter((s) => s.state === 'FAILED').length;
  const progressPercent = Math.round((completedScenesCount / (scenes.length || 1)) * 100);

  const canAssemble = completedScenesCount > 0 && (jobsSummary?.active_jobs_count || 0) === 0;

  const handleOpenRegen = (s: SceneResponse) => {
    setRegenModalScene(s);
    setRegenPrompt(s.plan.visual_prompt);
    setRegenDialogue(s.plan.dialogue_or_narration);
  };

  const handleConfirmRegen = async () => {
    if (!regenModalScene) return;
    await onRegenerateScene(regenModalScene.id, {
      visual_prompt: regenPrompt,
      dialogue_or_narration: regenDialogue,
    });
    setRegenModalScene(null);
  };

  return (
    <div className="glass-panel hero-card" id="step-production">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.5rem' }}>
        <div>
          <h2 className="card-title">6. Production Studio & Shot Generator</h2>
          <p className="card-desc">
            Orchestrates Veo 3.1 video clip synthesis, Gemini 3.8 TTS voiceover narration, and scene-level retries.
            Failed shots can be retried individually without discarding completed scenes.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          {(jobsSummary?.active_jobs_count || 0) === 0 && completedScenesCount === 0 && (
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setShowConfirmModal(true)}
              disabled={loading}
              id="btn-launch-production"
            >
              <Play size={16} fill="currentColor" />
              <span>Estimate Budget & Launch Production</span>
            </button>
          )}

          {canAssemble && (
            <button
              type="button"
              className="btn btn-accent"
              onClick={onAssembleMovie}
              disabled={loading}
              id="btn-assemble-cut"
            >
              <Film size={16} />
              <span>{loading ? 'FFmpeg Rendering Movie...' : 'Assemble Final Cut (FFmpeg) →'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Zero-Budget / Free Tier Strategy Guide */}
      <div style={{ background: 'rgba(6, 182, 212, 0.08)', border: '1px solid rgba(6, 182, 212, 0.25)', borderRadius: 'var(--radius-md)', padding: '0.85rem 1.15rem', marginBottom: '1.5rem', display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
        <Info size={22} color="#06b6d4" style={{ flexShrink: 0 }} />
        <div style={{ fontSize: '0.83rem', color: 'var(--text-muted)', lineHeight: 1.45 }}>
          <strong style={{ color: '#fff' }}>$0 Zero-Budget AI Workflow:</strong> Using Google's Free Tier? Gemini handles scriptwriting and TTS voiceover for free. For video, you can either let the studio render 24fps animatics automatically, OR 1-click copy the shot prompt into free external video generators (<strong>MiniMax Video-01</strong> or <strong>Luma Dream Machine</strong>) and click <strong>"Upload Rendered Clip (.mp4)"</strong> on each shot below!
        </div>
      </div>

      {/* Progress HUD */}
      <div style={{ background: 'rgba(0,0,0,0.3)', padding: '1.25rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{ fontWeight: 700, fontSize: '1rem', color: '#fff' }}>
              Film Production Progress
            </span>
            <span className="chip chip-planned">
              {completedScenesCount} of {scenes.length} Shots Ready
            </span>
            {(jobsSummary?.active_jobs_count || 0) > 0 && (
              <span className="chip chip-generating">
                {jobsSummary?.active_jobs_count} In Flight
              </span>
            )}
            {failedScenesCount > 0 && (
              <span className="chip chip-failed">
                {failedScenesCount} Failed (Retry Available)
              </span>
            )}
          </div>
          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--accent-gold)' }}>
            {progressPercent}%
          </span>
        </div>

        <div className="progress-bar-container">
          <div className="progress-bar-fill" style={{ width: `${progressPercent}%` }} />
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-dim)' }}>
          <span>Status: {jobsSummary?.project_state || 'READY'}</span>
          <span>Target Clip Duration: 8s per generation (Veo 3.1)</span>
        </div>
      </div>

      {/* Scenes Production Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '1.25rem' }}>
        {scenes.map((scene) => {
          const isDone = scene.state === 'GENERATED' || scene.state === 'APPROVED';
          const isGenerating = scene.state === 'GENERATING';
          const isFailed = scene.state === 'FAILED';

          return (
            <div
              key={scene.id}
              className="scene-card"
              style={{
                display: 'flex',
                flexDirection: 'column',
                borderLeft: isDone ? '4px solid var(--accent-emerald)' : isFailed ? '4px solid var(--accent-rose)' : isGenerating ? '4px solid var(--accent-cyan)' : '4px solid var(--border-subtle)',
              }}
              id={`prod-scene-card-${scene.order_index}`}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '0.5rem' }}>
                <span className="scene-order-badge">SHOT {String(scene.order_index).padStart(2, '0')}</span>
                <span className={`chip chip-${scene.state.toLowerCase()}`}>
                  {scene.state}
                </span>
              </div>

              <div style={{ fontWeight: 700, fontSize: '1rem', color: '#fff', marginBottom: '0.4rem' }}>
                {scene.title}
              </div>

              <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '0.75rem', lineHeight: 1.4, flex: 1 }}>
                {scene.plan.visual_prompt}
              </div>

              {/* Video Preview if generated */}
              {scene.selected_video_url ? (
                <div style={{ marginBottom: '0.75rem', borderRadius: 'var(--radius-sm)', overflow: 'hidden', background: '#000', border: '1px solid var(--border-subtle)' }}>
                  <video
                    src={scene.selected_video_url}
                    controls
                    className="asset-preview"
                    style={{ maxHeight: '180px' }}
                  />
                  {scene.selected_audio_url && (
                    <div style={{ padding: '0.35rem 0.6rem', fontSize: '0.75rem', color: 'var(--accent-gold)', display: 'flex', alignItems: 'center', gap: '0.3rem', background: 'rgba(0,0,0,0.5)' }}>
                      <Volume2 size={12} /> Narration Track Mixed
                    </div>
                  )}
                </div>
              ) : null}

              {/* Zero-Budget Prompt & Clip Upload Toolbar */}
              <div style={{ background: 'rgba(0,0,0,0.25)', padding: '0.5rem', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(255,255,255,0.04)', marginBottom: '0.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: 600 }}>
                    $0 Budget Tools:
                  </span>
                  <div style={{ display: 'flex', gap: '0.3rem' }}>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      style={{ fontSize: '0.68rem', padding: '0.15rem 0.45rem' }}
                      onClick={() => copyPrompt(`minimax_prod_${scene.id}`, `${scene.plan.visual_prompt}, cinematic camera dolly, 4k ultra-high definition`)}
                      title="Copy prompt formatted for MiniMax Video-01 free tier"
                    >
                      {copiedKey === `minimax_prod_${scene.id}` ? <CheckCheck size={10} color="var(--accent-emerald)" /> : <Copy size={10} />}
                      <span>MiniMax</span>
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      style={{ fontSize: '0.68rem', padding: '0.15rem 0.45rem' }}
                      onClick={() => copyPrompt(`luma_prod_${scene.id}`, `${scene.plan.visual_prompt}, dynamic camera move, photorealistic lighting`)}
                      title="Copy prompt formatted for Luma Dream Machine free tier"
                    >
                      {copiedKey === `luma_prod_${scene.id}` ? <CheckCheck size={10} color="var(--accent-emerald)" /> : <Copy size={10} />}
                      <span>Luma</span>
                    </button>
                  </div>
                </div>

                {onUploadClip && (
                  <div>
                    <input
                      type="file"
                      accept="video/mp4,video/webm,video/mov,video/mkv"
                      style={{ display: 'none' }}
                      ref={(el) => { videoInputRefs.current[scene.id] = el; }}
                      onChange={(e) => handleVideoUpload(scene.id, e)}
                    />
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      style={{ width: '100%', fontSize: '0.72rem', padding: '0.25rem 0.5rem', justifyContent: 'center' }}
                      onClick={() => videoInputRefs.current[scene.id]?.click()}
                      disabled={uploadingSceneId === scene.id}
                      title="Upload custom rendered video clip (.mp4) for this scene"
                    >
                      <Upload size={12} />
                      <span>{uploadingSceneId === scene.id ? 'Uploading Clip...' : 'Upload Rendered Clip (.mp4)'}</span>
                    </button>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border-subtle)' }}>
                {isFailed && (
                  <button
                    type="button"
                    className="btn btn-danger btn-sm"
                    style={{ flex: 1 }}
                    onClick={() => onRetryScene(scene.id)}
                    id={`btn-retry-scene-${scene.order_index}`}
                  >
                    <RotateCcw size={13} /> Retry Shot
                  </button>
                )}

                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  style={{ flex: 1 }}
                  onClick={() => handleOpenRegen(scene)}
                  disabled={isGenerating}
                  id={`btn-regen-scene-${scene.order_index}`}
                >
                  <Edit size={13} /> Tweak & Regen (v{scene.current_version})
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Budget Confirmation Modal (FRD §10, AT-07) */}
      {showConfirmModal && estimate && (
        <div className="modal-overlay" id="budget-confirm-modal">
          <div className="modal-card">
            <h3 style={{ fontSize: '1.35rem', fontWeight: 700, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <DollarSign size={20} color="var(--accent-gold)" />
              Confirm Production Budget & Scope
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1.25rem' }}>
              Before launching generative video rendering, review the estimated shot budget and API consumption lower bound.
            </p>

            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '1rem', borderRadius: 'var(--radius-md)', marginBottom: '1.25rem', fontSize: '0.9rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                <span>Target Runtime:</span>
                <strong>{estimate.target_runtime_seconds} seconds</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                <span>Required Shots ceil(T/D):</span>
                <strong>{estimate.required_clip_count} clips (Cap: {estimate.max_clips_cap})</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                <span>Estimated Budget:</span>
                <strong style={{ color: 'var(--accent-gold)' }}>${estimate.estimated_cost_usd.toFixed(2)} USD</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Project Budget Limit:</span>
                <strong>${estimate.budget_limit_usd.toFixed(2)} USD</strong>
              </div>
            </div>

            {estimate.warnings?.length > 0 && (
              <div style={{ background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', color: '#fcd34d', padding: '0.75rem', borderRadius: 'var(--radius-md)', marginBottom: '1.25rem', fontSize: '0.82rem' }}>
                <AlertTriangle size={16} style={{ display: 'inline', verticalAlign: '-3px', marginRight: '4px' }} />
                {estimate.warnings.join(' ')}
              </div>
            )}

            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setShowConfirmModal(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={async () => {
                  setShowConfirmModal(false);
                  await onStartProduction(true);
                }}
                id="btn-confirm-start-prod"
              >
                Confirm & Launch Generation →
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Regeneration Modal (FR-017) */}
      {regenModalScene && (
        <div className="modal-overlay" id="regen-prompt-modal">
          <div className="modal-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 700 }}>
                Regenerate Shot {regenModalScene.order_index} (v{regenModalScene.current_version + 1})
              </h3>
              <button
                type="button"
                style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', cursor: 'pointer' }}
                onClick={() => setRegenModalScene(null)}
              >
                <X size={20} />
              </button>
            </div>

            <div className="form-group">
              <label className="form-label">Visual Cinematic Prompt (Veo 3.1)</label>
              <textarea
                className="form-textarea"
                rows={4}
                value={regenPrompt}
                onChange={(e) => setRegenPrompt(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Dialogue / Narration (Gemini TTS)</label>
              <textarea
                className="form-textarea"
                rows={2}
                value={regenDialogue}
                onChange={(e) => setRegenDialogue(e.target.value)}
              />
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', marginTop: '1.5rem' }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setRegenModalScene(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleConfirmRegen}
                id="btn-confirm-regen-prompt"
              >
                Queue Regeneration
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
