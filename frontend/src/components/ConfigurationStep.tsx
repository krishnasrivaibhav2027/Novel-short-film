import React, { useState } from 'react';
import { Monitor, Smartphone, Clock, Mic, Check } from 'lucide-react';
import type { ProductionSettings, Project } from '../types';

interface ConfigurationStepProps {
  project: Project;
  onSaveSettings: (settings: ProductionSettings) => Promise<void>;
  onStartAnalysis: () => Promise<void>;
  loading: boolean;
}

const STYLE_OPTIONS = [
  { id: 'Cinematic 3D Animation', label: 'Cinematic 3D Animation', desc: 'Pixar/Dreamworks style, volumetric lighting, rich PBR textures' },
  { id: 'Dark Anime', label: 'Dark Cyber Anime', desc: 'Detailed lineart, dramatic cel shading, glowing neon highlights' },
  { id: 'Cyberpunk Noir', label: 'Cyberpunk Noir', desc: 'High-contrast shadows, rain-slicked asphalt, moody blade-runner palette' },
  { id: 'Watercolor Fantasy', label: 'Watercolor Fantasy', desc: 'Soft pastel washes, fluid organic strokes, ethereal Studio Ghibli tone' },
  { id: 'Stop-Motion Claymation', label: 'Claymation / Stop-Motion', desc: 'Tactile sculpted figures, physical miniature depth of field' },
];

const GENRE_OPTIONS = ['Sci-Fi', 'Fantasy', 'Thriller', 'Cyberpunk Noir', 'Adventure', 'Mystery', 'Drama'];

const RUNTIME_PRESETS = [
  { seconds: 30, label: '30s Trailer', desc: 'Fast-paced, 4-shot narrative hook (Demo recommended)', isMvp: true },
  { seconds: 60, label: '60s Teaser', desc: 'Balanced 8-shot cinematic preview', isMvp: true },
  { seconds: 90, label: '90s Short', desc: 'Full narrative arc trailer with complete climax', isMvp: true },
  { seconds: 900, label: '15 Min (Advanced Target)', desc: '113+ clips (Planned post-hackathon feature)', isMvp: false },
];

export const ConfigurationStep: React.FC<ConfigurationStepProps> = ({
  project,
  onSaveSettings,
  onStartAnalysis,
  loading,
}) => {
  const currentSettings = project.settings;
  const [style, setStyle] = useState(currentSettings.style || 'Cinematic 3D Animation');
  const [genre, setGenre] = useState(currentSettings.genre || 'Sci-Fi');
  const [aspectRatio, setAspectRatio] = useState<'16:9' | '9:16'>(currentSettings.aspect_ratio || '16:9');
  const [runtimeSec, setRuntimeSec] = useState<number>(currentSettings.target_runtime_seconds || 60);
  const [enableNarration, setEnableNarration] = useState(currentSettings.enable_narration ?? true);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const updated: ProductionSettings = {
      ...currentSettings,
      style,
      genre,
      aspect_ratio: aspectRatio,
      target_runtime_seconds: runtimeSec,
      enable_narration: enableNarration,
    };
    await onSaveSettings(updated);
    await onStartAnalysis();
  };

  return (
    <div className="glass-panel hero-card" id="step-configuration">
      <h2 className="card-title">2. Adaptation & Film Configuration</h2>
      <p className="card-desc">
        Define the visual direction, aspect ratio, and preview runtime budget.
        Gemini will tailor the camera direction, lighting prompts, and character designs to these parameters.
      </p>

      <form onSubmit={handleSubmit}>
        {/* Genre Selection */}
        <div className="form-group" style={{ marginBottom: '1.5rem' }}>
          <label className="form-label" htmlFor="genre-select">Story Genre & Tone Bias</label>
          <select
            id="genre-select"
            className="form-select"
            value={genre}
            onChange={(e) => setGenre(e.target.value)}
          >
            {GENRE_OPTIONS.map((g) => (
              <option key={g} value={g}>{g}</option>
            ))}
          </select>
        </div>

        {/* Style Selection */}
        <div className="form-group">
          <label className="form-label">Visual Animation Aesthetic</label>
          <div className="grid-cards">
            {STYLE_OPTIONS.map((opt) => (
              <div
                key={opt.id}
                className={`choice-card ${style === opt.id ? 'selected' : ''}`}
                onClick={() => setStyle(opt.id)}
                id={`style-opt-${opt.id.toLowerCase().replace(/\s+/g, '-')}`}
              >
                <div className="choice-header">
                  <span className="choice-title">{opt.label}</span>
                  {style === opt.id && <Check size={16} color="var(--accent-gold)" />}
                </div>
                <p className="choice-desc">{opt.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Aspect Ratio */}
        <div className="form-group" style={{ marginTop: '1.5rem' }}>
          <label className="form-label">Cinematic Aspect Ratio</label>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
            <div
              className={`choice-card ${aspectRatio === '16:9' ? 'selected' : ''}`}
              onClick={() => setAspectRatio('16:9')}
              id="ratio-16-9"
            >
              <div className="choice-header">
                <span className="choice-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Monitor size={18} /> 16:9 Widescreen
                </span>
                {aspectRatio === '16:9' && <Check size={16} color="var(--accent-gold)" />}
              </div>
              <p className="choice-desc">Theatrical film standard for cinematic landscape playback</p>
            </div>

            <div
              className={`choice-card ${aspectRatio === '9:16' ? 'selected' : ''}`}
              onClick={() => setAspectRatio('9:16')}
              id="ratio-9-16"
            >
              <div className="choice-header">
                <span className="choice-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Smartphone size={18} /> 9:16 Vertical
                </span>
                {aspectRatio === '9:16' && <Check size={16} color="var(--accent-gold)" />}
              </div>
              <p className="choice-desc">Mobile-first format for social shorts and trailers</p>
            </div>
          </div>
        </div>

        {/* Runtime Presets */}
        <div className="form-group" style={{ marginTop: '1.5rem' }}>
          <label className="form-label">Target Runtime Preset (PRD Feasibility Strategy)</label>
          <div className="grid-cards">
            {RUNTIME_PRESETS.map((p) => (
              <div
                key={p.seconds}
                className={`choice-card ${runtimeSec === p.seconds ? 'selected' : ''} ${!p.isMvp ? 'disabled' : ''}`}
                onClick={() => p.isMvp && setRuntimeSec(p.seconds)}
                style={{ opacity: p.isMvp ? 1 : 0.5, cursor: p.isMvp ? 'pointer' : 'not-allowed' }}
                id={`runtime-preset-${p.seconds}`}
              >
                <div className="choice-header">
                  <span className="choice-title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <Clock size={16} /> {p.label}
                  </span>
                  {runtimeSec === p.seconds && <Check size={16} color="var(--accent-gold)" />}
                </div>
                <p className="choice-desc">{p.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Narration Toggle */}
        <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginTop: '1.5rem' }}>
          <input
            type="checkbox"
            id="narration-toggle"
            style={{ width: '18px', height: '18px', accentColor: 'var(--accent-gold)' }}
            checked={enableNarration}
            onChange={(e) => setEnableNarration(e.target.checked)}
          />
          <label htmlFor="narration-toggle" style={{ fontSize: '0.9rem', color: 'var(--text-main)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Mic size={16} color="#06b6d4" />
            <span>Generate Expressive Voiceover Narration Track (Gemini 3.8 Flash TTS)</span>
          </label>
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          style={{ marginTop: '1.5rem' }}
          disabled={loading}
          id="btn-save-config"
        >
          {loading ? 'Reasoning with Gemini...' : 'Analyze Story & Generate Story Bible →'}
        </button>
      </form>
    </div>
  );
};
