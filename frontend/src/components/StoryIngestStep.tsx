import React, { useState } from 'react';
import { Upload, FileText, Sparkles, AlertCircle, ShieldCheck } from 'lucide-react';
import type { Project } from '../types';

interface StoryIngestStepProps {
  project: Project;
  onStorySubmitted: (text: string, rights: boolean) => Promise<void>;
  onFileUpload: (file: File, rights: boolean) => Promise<void>;
  loading: boolean;
  error: string | null;
}

const SAMPLE_DEMO_STORY = `The Obsidian Citadel had stood above the mists for ten thousand years.
Kaelen tightened his dark traveling cloak against the biting wind as he climbed the final precipice of the whispering canyon.
Behind him, Mira adjusted her bronze navigation goggles, her nimble fingers tracing the glowing crystal compass.
"The resonance is peaking," she whispered, her voice barely audible over the howling gale. "The beacon is alive."
Suddenly, a low hum vibrated through the stones. The monolithic arch ahead flared with brilliant azure light.
From within the deep shadows, the guardian sentinel awakened. Its mechanical joints whirred with ancient menace as ocular rings flared crimson.
Kaelen drew his blade, his heart pounding in rhythm with the celestial pulse.
"Stay behind the perimeter barrier, Mira," he commanded, stepping into the blinding glow.
They had finally arrived at the Core of Eternity.`;

export const StoryIngestStep: React.FC<StoryIngestStepProps> = ({
  project,
  onStorySubmitted,
  onFileUpload,
  loading,
  error,
}) => {
  const [activeTab, setActiveTab] = useState<'paste' | 'upload'>('paste');
  const [storyText, setStoryText] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [hasRights, setHasRights] = useState(project.has_rights_confirmation || false);
  const [localErr, setLocalErr] = useState<string | null>(null);

  const charCount = storyText.length;
  const isTooShort = charCount > 0 && charCount < 200;
  const isTooLong = charCount > 60000;

  const handlePasteSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalErr(null);
    if (!hasRights) {
      setLocalErr('You must confirm copyright or adaptation permission before continuing.');
      return;
    }
    if (charCount < 200) {
      setLocalErr('Story is too short. Please provide at least 200 characters.');
      return;
    }
    await onStorySubmitted(storyText, hasRights);
  };

  const handleFileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalErr(null);
    if (!hasRights) {
      setLocalErr('You must confirm copyright or adaptation permission before continuing.');
      return;
    }
    if (!selectedFile) {
      setLocalErr('Please select a file to upload.');
      return;
    }
    await onFileUpload(selectedFile, hasRights);
  };

  const loadSample = () => {
    setStoryText(SAMPLE_DEMO_STORY);
    setHasRights(true);
    setLocalErr(null);
  };

  return (
    <div className="glass-panel hero-card" id="step-story-ingest">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 className="card-title">1. Story Manuscript & Ingestion</h2>
          <p className="card-desc">
            Submit your original short novel or narrative manuscript. Gemini will analyze characters, environments,
            themes, and narrative plot beats to architect a production Story Bible.
          </p>
        </div>

        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={loadSample}
          id="btn-load-sample"
        >
          <Sparkles size={15} color="#f59e0b" />
          <span>Load Sample Story (Instant Demo)</span>
        </button>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
        <button
          type="button"
          className={`btn ${activeTab === 'paste' ? 'btn-primary' : 'btn-secondary'} btn-sm`}
          onClick={() => setActiveTab('paste')}
          id="tab-paste-text"
        >
          <FileText size={15} />
          <span>Paste Manuscript</span>
        </button>
        <button
          type="button"
          className={`btn ${activeTab === 'upload' ? 'btn-primary' : 'btn-secondary'} btn-sm`}
          onClick={() => setActiveTab('upload')}
          id="tab-upload-file"
        >
          <Upload size={15} />
          <span>Upload Document (.txt, .md, .pdf, .docx)</span>
        </button>
      </div>

      {(error || localErr) && (
        <div style={{
          background: 'rgba(244, 63, 94, 0.15)',
          border: '1px solid rgba(244, 63, 94, 0.3)',
          color: '#fda4af',
          padding: '0.75rem 1rem',
          borderRadius: 'var(--radius-md)',
          marginBottom: '1.25rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          fontSize: '0.88rem'
        }}>
          <AlertCircle size={18} />
          <span>{error || localErr}</span>
        </div>
      )}

      {activeTab === 'paste' ? (
        <form onSubmit={handlePasteSubmit}>
          <div className="form-group">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.45rem' }}>
              <label className="form-label" htmlFor="story-textarea">Manuscript Text</label>
              <span style={{ fontSize: '0.78rem', color: isTooShort || isTooLong ? 'var(--accent-rose)' : 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                {charCount.toLocaleString()} / 60,000 chars (Min: 200)
              </span>
            </div>
            <textarea
              id="story-textarea"
              className="form-textarea"
              rows={9}
              placeholder="Paste your story prose here (minimum 200 characters)..."
              value={storyText}
              onChange={(e) => setStoryText(e.target.value)}
              required
            />
          </div>

          <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginTop: '1rem' }}>
            <input
              type="checkbox"
              id="rights-checkbox"
              style={{ width: '18px', height: '18px', accentColor: 'var(--accent-gold)' }}
              checked={hasRights}
              onChange={(e) => setHasRights(e.target.checked)}
              required
            />
            <label htmlFor="rights-checkbox" style={{ fontSize: '0.85rem', color: 'var(--text-muted)', cursor: 'pointer' }}>
              <ShieldCheck size={16} style={{ display: 'inline', verticalAlign: '-3px', marginRight: '4px', color: '#10b981' }} />
              I confirm that I own or have permission to adapt this material (PRD & Safety Compliance)
            </label>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading || !storyText.trim() || !hasRights || isTooShort}
            id="btn-submit-story"
          >
            {loading ? 'Analyzing Manuscript...' : 'Lock Manuscript & Configure Film →'}
          </button>
        </form>
      ) : (
        <form onSubmit={handleFileSubmit}>
          <div className="form-group">
            <label className="form-label" htmlFor="file-input">Select Manuscript File</label>
            <input
              type="file"
              id="file-input"
              className="form-input"
              accept=".txt,.md,.pdf,.docx"
              onChange={(e) => setSelectedFile(e.target.files ? e.target.files[0] : null)}
              required
            />
            <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', marginTop: '0.4rem' }}>
              Supported formats: Plain Text (.txt, .md), Adobe PDF (.pdf), Microsoft Word (.docx) — Max 2 MB
            </div>
          </div>

          <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginTop: '1rem' }}>
            <input
              type="checkbox"
              id="rights-checkbox-file"
              style={{ width: '18px', height: '18px', accentColor: 'var(--accent-gold)' }}
              checked={hasRights}
              onChange={(e) => setHasRights(e.target.checked)}
              required
            />
            <label htmlFor="rights-checkbox-file" style={{ fontSize: '0.85rem', color: 'var(--text-muted)', cursor: 'pointer' }}>
              <ShieldCheck size={16} style={{ display: 'inline', verticalAlign: '-3px', marginRight: '4px', color: '#10b981' }} />
              I confirm that I own or have permission to adapt this material (PRD & Safety Compliance)
            </label>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading || !selectedFile || !hasRights}
            id="btn-upload-submit"
          >
            {loading ? 'Extracting & Validating...' : 'Upload & Configure Film →'}
          </button>
        </form>
      )}
    </div>
  );
};
