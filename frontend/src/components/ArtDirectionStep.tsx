import React, { useState, useRef } from 'react';
import { Palette, Check, Sparkles, Eye, Copy, CheckCheck, Upload } from 'lucide-react';
import type { Asset } from '../types';

interface ArtDirectionStepProps {
  references: Asset[];
  onGenerateReferences: () => Promise<void>;
  onApproveReferences: (approvedIds: string[]) => Promise<void>;
  onUploadImage?: (assetId: string, file: File) => Promise<void>;
  loading: boolean;
}

export const ArtDirectionStep: React.FC<ArtDirectionStepProps> = ({
  references,
  onGenerateReferences,
  onApproveReferences,
  onUploadImage,
  loading,
}) => {
  const [selectedIds, setSelectedIds] = useState<string[]>(
    references.map((r) => r.id)
  );
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [uploadingId, setUploadingId] = useState<string | null>(null);
  const fileInputRefs = useRef<{ [key: string]: HTMLInputElement | null }>({});

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const copyPrompt = (assetId: string, promptText: string) => {
    navigator.clipboard.writeText(promptText);
    setCopiedId(assetId);
    setTimeout(() => setCopiedId(null), 2500);
  };

  const handleFileChange = async (assetId: string, e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !onUploadImage) return;
    setUploadingId(assetId);
    try {
      await onUploadImage(assetId, file);
    } finally {
      setUploadingId(null);
    }
  };

  const handleApprove = async () => {
    await onApproveReferences(selectedIds);
  };

  return (
    <div className="glass-panel hero-card" id="step-art-direction">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.5rem' }}>
        <div>
          <h2 className="card-title">5. Visual World & Reference Sheets</h2>
          <p className="card-desc">
            Character sheets and environmental plates generated to anchor visual consistency.
            Veo 3.1 utilizes these reference assets to preserve subject identity and cinematic motifs across scenes.
          </p>
        </div>

        {references.length > 0 ? (
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleApprove}
            disabled={loading}
            id="btn-confirm-references"
          >
            <Check size={16} />
            <span>{loading ? 'Confirming Visual World...' : 'Approve Visual World & Enter Studio →'}</span>
          </button>
        ) : (
          <button
            type="button"
            className="btn btn-primary"
            onClick={onGenerateReferences}
            disabled={loading}
            id="btn-generate-references"
          >
            <Sparkles size={16} />
            <span>{loading ? 'Art Director Agent Painting...' : 'Generate Visual Reference Sheets →'}</span>
          </button>
        )}
      </div>

      {references.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '3.5rem 1.5rem', background: 'rgba(0,0,0,0.2)', borderRadius: 'var(--radius-lg)', border: '1px dashed var(--border-subtle)' }}>
          <Palette size={48} color="var(--accent-gold)" style={{ margin: '0 auto 1rem', opacity: 0.8 }} />
          <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '0.5rem' }}>
            Visual References Not Yet Rendered
          </h3>
          <p style={{ color: 'var(--text-muted)', maxWidth: '480px', margin: '0 auto 1.5rem', fontSize: '0.9rem' }}>
            Click below to generate high-resolution concept art sheets for your characters and key locations using the image model.
          </p>
          <button
            type="button"
            className="btn btn-primary"
            onClick={onGenerateReferences}
            disabled={loading}
            id="btn-generate-references-empty"
          >
            <Sparkles size={16} />
            <span>{loading ? 'Art Director Agent Working...' : 'Generate Visual World Now'}</span>
          </button>
        </div>
      ) : (
        <div className="gallery-grid">
          {references.map((asset) => {
            const isSelected = selectedIds.includes(asset.id);
            const isCharacter = asset.asset_type === 'character_reference';
            const name = asset.metadata?.name || (isCharacter ? 'Character Sheet' : 'Environment Plate');

            return (
              <div
                key={asset.id}
                className="asset-card"
                style={{
                  borderColor: isSelected ? 'var(--accent-gold)' : undefined,
                  boxShadow: isSelected ? '0 0 15px rgba(245, 158, 11, 0.2)' : undefined,
                }}
                id={`asset-card-${asset.id}`}
              >
                <div style={{ position: 'relative' }}>
                  <img
                    src={asset.media_url}
                    alt={name}
                    className="asset-preview"
                    loading="lazy"
                  />
                  <span
                    className="chip chip-approved"
                    style={{ position: 'absolute', top: '10px', right: '10px', background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }}
                  >
                    {isCharacter ? 'CHARACTER' : 'LOCATION'}
                  </span>
                </div>

                <div className="asset-body">
                  <div className="asset-title">{name}</div>
                  <div className="asset-meta">
                    Model: {asset.model_id} {asset.is_mock && '(Animatic Concept)'}
                  </div>
                  <div className="asset-prompt">{asset.prompt}</div>

                  {/* Free-tier zero-budget toolbar */}
                  <div style={{ display: 'flex', gap: '0.4rem', marginTop: '0.5rem', flexWrap: 'wrap' }}>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      style={{ fontSize: '0.72rem', padding: '0.2rem 0.5rem' }}
                      onClick={() => copyPrompt(asset.id, asset.prompt || '')}
                      title="Copy prompt for Google AI Studio Build Mode"
                    >
                      {copiedId === asset.id ? <CheckCheck size={11} color="var(--accent-emerald)" /> : <Copy size={11} />}
                      <span>Copy for AI Studio</span>
                    </button>

                    {onUploadImage && (
                      <>
                        <input
                          type="file"
                          accept="image/png,image/jpeg,image/webp"
                          style={{ display: 'none' }}
                          ref={(el) => { fileInputRefs.current[asset.id] = el; }}
                          onChange={(e) => handleFileChange(asset.id, e)}
                        />
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          style={{ fontSize: '0.72rem', padding: '0.2rem 0.5rem' }}
                          onClick={() => fileInputRefs.current[asset.id]?.click()}
                          disabled={uploadingId === asset.id}
                          title="Upload art generated in AI Studio or Midjourney"
                        >
                          <Upload size={11} />
                          <span>{uploadingId === asset.id ? 'Uploading...' : 'Upload Art'}</span>
                        </button>
                      </>
                    )}
                  </div>

                  <div style={{ marginTop: 'auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '0.5rem' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.85rem', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelect(asset.id)}
                        style={{ accentColor: 'var(--accent-gold)' }}
                      />
                      <span>Approved for Production</span>
                    </label>

                    <a
                      href={asset.media_url}
                      target="_blank"
                      rel="noreferrer"
                      className="btn btn-secondary btn-sm"
                      style={{ padding: '0.2rem 0.5rem' }}
                      title="View full resolution"
                    >
                      <Eye size={12} />
                    </a>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
