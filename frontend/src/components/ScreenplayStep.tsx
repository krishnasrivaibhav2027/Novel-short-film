import React, { useState } from 'react';
import { Edit3, Check, Clock, MessageSquare, Video, Copy, CheckCheck } from 'lucide-react';
import type { SceneResponse } from '../types';

interface ScreenplayStepProps {
  scenes: SceneResponse[];
  onUpdateScene: (sceneId: string, updates: { title?: string; visual_prompt?: string; dialogue_or_narration?: string }) => Promise<void>;
  onApprovePlan: () => Promise<void>;
  loading: boolean;
}

export const ScreenplayStep: React.FC<ScreenplayStepProps> = ({
  scenes,
  onUpdateScene,
  onApprovePlan,
  loading,
}) => {
  const [editingSceneId, setEditingSceneId] = useState<string | null>(null);
  const [editPrompt, setEditPrompt] = useState('');
  const [editDialogue, setEditDialogue] = useState('');
  const [editTitle, setEditTitle] = useState('');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const copyToClipboard = (key: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2500);
  };

  const startEdit = (sc: SceneResponse) => {
    setEditingSceneId(sc.id);
    setEditTitle(sc.title);
    setEditPrompt(sc.plan.visual_prompt);
    setEditDialogue(sc.plan.dialogue_or_narration);
  };

  const saveEdit = async (sceneId: string) => {
    await onUpdateScene(sceneId, {
      title: editTitle,
      visual_prompt: editPrompt,
      dialogue_or_narration: editDialogue,
    });
    setEditingSceneId(null);
  };

  const totalSeconds = scenes.reduce((acc, s) => acc + (s.plan.target_seconds || 8), 0);

  return (
    <div className="glass-panel hero-card" id="step-screenplay">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.5rem' }}>
        <div>
          <h2 className="card-title">4. Screenplay & Shot Breakdown</h2>
          <p className="card-desc">
            Review and fine-tune the cinematic shot sequence. Each scene defines the exact camera angle, subject action,
            lighting, and voiceover text. Human approval is required before generation begins.
          </p>
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            <span className="chip chip-planned" style={{ textTransform: 'none' }}>
              {scenes.length} Ordered Shots
            </span>
            <span className="chip chip-planned" style={{ textTransform: 'none' }}>
              Est. Runtime: ~{totalSeconds}s
            </span>
          </div>
        </div>

        <button
          type="button"
          className="btn btn-primary"
          onClick={onApprovePlan}
          disabled={loading || scenes.length === 0}
          id="btn-approve-screenplay"
        >
          <Check size={16} />
          <span>{loading ? 'Locking Screenplay...' : 'Approve Screenplay & Design World →'}</span>
        </button>
      </div>

      <div className="scene-list">
        {scenes.map((scene) => {
          const isEditing = editingSceneId === scene.id;

          return (
            <div key={scene.id} className="scene-card" id={`scene-card-${scene.order_index}`}>
              <div className="scene-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <span className="scene-order-badge">SHOT {String(scene.order_index).padStart(2, '0')}</span>
                  {isEditing ? (
                    <input
                      type="text"
                      className="form-input"
                      style={{ padding: '0.3rem 0.6rem', fontSize: '1rem', width: '280px' }}
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                    />
                  ) : (
                    <span style={{ fontWeight: 700, fontSize: '1.05rem', color: '#fff' }}>{scene.title}</span>
                  )}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span className="chip chip-planned" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                    <Clock size={12} /> {scene.plan.target_seconds}s
                  </span>
                  {isEditing ? (
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      onClick={() => saveEdit(scene.id)}
                      id={`btn-save-scene-${scene.order_index}`}
                    >
                      <Check size={14} /> Save
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => startEdit(scene)}
                      id={`btn-edit-scene-${scene.order_index}`}
                    >
                      <Edit3 size={14} /> Edit Prompt
                    </button>
                  )}
                </div>
              </div>

              <div style={{ fontSize: '0.82rem', color: 'var(--text-dim)', marginBottom: '0.75rem' }}>
                <strong>Narrative Purpose:</strong> {scene.plan.narrative_purpose}
              </div>

              {/* Visual Prompt */}
              <div style={{ marginBottom: '0.75rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', color: 'var(--accent-cyan)', fontWeight: 600, marginBottom: '0.3rem' }}>
                  <Video size={14} /> CINEMATIC PROMPT (Veo 3.1 Direction):
                </div>
                {isEditing ? (
                  <textarea
                    className="form-textarea"
                    rows={3}
                    value={editPrompt}
                    onChange={(e) => setEditPrompt(e.target.value)}
                  />
                ) : (
                  <>
                    <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.65rem 0.85rem', borderRadius: 'var(--radius-sm)', fontSize: '0.88rem', color: 'var(--text-main)', border: '1px solid rgba(255,255,255,0.04)' }}>
                      {scene.plan.visual_prompt}
                    </div>
                    <div style={{ display: 'flex', gap: '0.4rem', marginTop: '0.4rem', flexWrap: 'wrap', alignItems: 'center' }}>
                      <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginRight: '0.2rem' }}>
                        Free Tier Export:
                      </span>
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        style={{ fontSize: '0.7rem', padding: '0.15rem 0.5rem' }}
                        onClick={() => copyToClipboard(`aistudio_${scene.id}`, scene.plan.visual_prompt)}
                        title="Copy raw prompt for Google AI Studio Build Mode"
                      >
                        {copiedKey === `aistudio_${scene.id}` ? <CheckCheck size={11} color="var(--accent-emerald)" /> : <Copy size={11} />}
                        <span>AI Studio</span>
                      </button>
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        style={{ fontSize: '0.7rem', padding: '0.15rem 0.5rem' }}
                        onClick={() => copyToClipboard(`minimax_${scene.id}`, `${scene.plan.visual_prompt}, cinematic camera dolly, 4k ultra-high definition`)}
                        title="Copy prompt formatted for MiniMax Video-01 free tier"
                      >
                        {copiedKey === `minimax_${scene.id}` ? <CheckCheck size={11} color="var(--accent-emerald)" /> : <Copy size={11} />}
                        <span>MiniMax</span>
                      </button>
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        style={{ fontSize: '0.7rem', padding: '0.15rem 0.5rem' }}
                        onClick={() => copyToClipboard(`luma_${scene.id}`, `${scene.plan.visual_prompt}, dynamic camera move, photorealistic lighting`)}
                        title="Copy prompt formatted for Luma Dream Machine free tier"
                      >
                        {copiedKey === `luma_${scene.id}` ? <CheckCheck size={11} color="var(--accent-emerald)" /> : <Copy size={11} />}
                        <span>Luma</span>
                      </button>
                    </div>
                  </>
                )}
              </div>

              {/* Narration */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', color: 'var(--accent-gold)', fontWeight: 600, marginBottom: '0.3rem' }}>
                  <MessageSquare size={14} /> DIALOGUE / NARRATION TRACK:
                </div>
                {isEditing ? (
                  <textarea
                    className="form-textarea"
                    rows={2}
                    value={editDialogue}
                    onChange={(e) => setEditDialogue(e.target.value)}
                  />
                ) : (
                  <div style={{ background: 'rgba(0,0,0,0.2)', padding: '0.5rem 0.85rem', borderRadius: 'var(--radius-sm)', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                    {scene.plan.dialogue_or_narration || '(No spoken dialogue in this shot)'}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
