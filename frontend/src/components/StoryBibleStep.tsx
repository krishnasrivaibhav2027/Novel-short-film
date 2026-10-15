import React from 'react';
import { Users, MapPin, ListOrdered, ShieldAlert, Film } from 'lucide-react';
import type { StoryBible } from '../types';

interface StoryBibleStepProps {
  bible: StoryBible;
  onProceedToScreenplay: () => Promise<void>;
  loading: boolean;
}

export const StoryBibleStep: React.FC<StoryBibleStepProps> = ({
  bible,
  onProceedToScreenplay,
  loading,
}) => {
  return (
    <div className="glass-panel hero-card" id="step-story-bible">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.5rem' }}>
        <div>
          <span className="chip chip-approved" style={{ marginBottom: '0.5rem' }}>STORY BIBLE APPROVED</span>
          <h2 className="card-title">{bible.title}</h2>
          <p style={{ fontStyle: 'italic', color: 'var(--accent-gold)', fontSize: '1.05rem', marginTop: '0.25rem' }}>
            "{bible.logline}"
          </p>
        </div>

        <button
          type="button"
          className="btn btn-primary"
          onClick={onProceedToScreenplay}
          disabled={loading}
          id="btn-generate-screenplay"
        >
          <Film size={16} />
          <span>{loading ? 'Screenwriter Agent Working...' : 'Generate Screenplay Breakdown →'}</span>
        </button>
      </div>

      {/* Synopsis */}
      <div className="form-group" style={{ background: 'rgba(0,0,0,0.25)', padding: '1.25rem', borderRadius: 'var(--radius-md)' }}>
        <h4 style={{ fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-dim)', marginBottom: '0.5rem' }}>
          Narrative Synopsis
        </h4>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem', lineHeight: 1.6 }}>{bible.synopsis}</p>
        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem', flexWrap: 'wrap' }}>
          {bible.themes?.map((th, i) => (
            <span key={i} className="chip chip-planned" style={{ textTransform: 'none' }}>
              Theme: {th}
            </span>
          ))}
        </div>
      </div>

      {/* Characters */}
      <div style={{ marginTop: '2rem' }}>
        <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.15rem', fontWeight: 700, marginBottom: '1rem' }}>
          <Users size={18} color="#06b6d4" />
          <span>Cast & Character Bibles</span>
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
          {bible.characters?.map((char) => (
            <div key={char.character_id} className="choice-card" style={{ cursor: 'default' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '0.4rem' }}>
                <span style={{ fontWeight: 700, fontSize: '1.05rem', color: '#fff' }}>{char.name}</span>
                <span className="chip chip-planned">{char.role}</span>
              </div>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                {char.age_range_or_appearance}
              </p>
              <div style={{ fontSize: '0.82rem', color: 'var(--accent-gold)', marginBottom: '0.5rem', background: 'rgba(0,0,0,0.3)', padding: '0.5rem', borderRadius: '4px' }}>
                <strong>Prompt Anchor:</strong> {char.visual_description}
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>
                <strong>Wardrobe:</strong> {char.wardrobe}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Locations */}
      <div style={{ marginTop: '2rem' }}>
        <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.15rem', fontWeight: 700, marginBottom: '1rem' }}>
          <MapPin size={18} color="#8b5cf6" />
          <span>Cinematic Settings & Locations</span>
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
          {bible.locations?.map((loc) => (
            <div key={loc.location_id} className="choice-card" style={{ cursor: 'default' }}>
              <span style={{ fontWeight: 700, fontSize: '1.05rem', color: '#fff' }}>{loc.name}</span>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', margin: '0.4rem 0' }}>{loc.description}</p>
              <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', marginTop: '0.5rem' }}>
                {loc.visual_motifs?.map((motif, i) => (
                  <span key={i} className="chip chip-planned" style={{ textTransform: 'none', fontSize: '0.7rem' }}>
                    {motif}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Plot Beats */}
      <div style={{ marginTop: '2rem' }}>
        <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.15rem', fontWeight: 700, marginBottom: '1rem' }}>
          <ListOrdered size={18} color="#f59e0b" />
          <span>Narrative Plot Beats</span>
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {bible.plot_beats?.map((beat) => (
            <div key={beat.beat_number} style={{ display: 'flex', gap: '1rem', background: 'var(--bg-surface)', padding: '0.85rem 1.1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-gold)', fontWeight: 700, minWidth: '24px' }}>
                #{beat.beat_number}
              </span>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.2rem' }}>
                  <span style={{ fontWeight: 600, color: '#fff' }}>{beat.title}</span>
                  <span className="chip chip-planned">{beat.act}</span>
                </div>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{beat.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Continuity Rules */}
      {bible.continuity_rules?.length > 0 && (
        <div style={{ marginTop: '2rem', background: 'rgba(245, 158, 11, 0.05)', border: '1px solid rgba(245, 158, 11, 0.2)', padding: '1.25rem', borderRadius: 'var(--radius-md)' }}>
          <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--accent-gold)', fontSize: '0.9rem', fontWeight: 700, marginBottom: '0.5rem' }}>
            <ShieldAlert size={16} /> Continuity Invariant Rules
          </h4>
          <ul style={{ paddingLeft: '1.25rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            {bible.continuity_rules.map((rule, idx) => (
              <li key={idx} style={{ marginBottom: '0.25rem' }}>{rule}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
