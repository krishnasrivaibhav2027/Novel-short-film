export interface Character {
  character_id: string;
  name: string;
  role: string;
  age_range_or_appearance: string;
  personality_traits: string[];
  wardrobe: string;
  visual_description: string;
  relationships: string[];
}

export interface Location {
  location_id: string;
  name: string;
  description: string;
  time_of_day_options: string[];
  visual_motifs: string[];
}

export interface PlotBeat {
  beat_number: number;
  act: string;
  title: string;
  description: string;
  involved_character_ids: string[];
}

export interface StoryBible {
  title: string;
  logline: string;
  synopsis: string;
  genre: string;
  tone: string;
  themes: string[];
  characters: Character[];
  locations: Location[];
  plot_beats: PlotBeat[];
  continuity_rules: string[];
}

export interface ScenePlan {
  scene_id: string;
  order: number;
  title: string;
  narrative_purpose: string;
  location_id: string;
  character_ids: string[];
  action: string;
  dialogue_or_narration: string;
  visual_prompt: string;
  continuity_notes: string;
  target_seconds: number;
  status: string;
}

export interface ProductionSettings {
  style: string;
  genre: string;
  language: string;
  aspect_ratio: '16:9' | '9:16';
  target_runtime_seconds: number;
  clip_duration_seconds: number;
  preview_mode: boolean;
  max_clips: number;
  budget_limit_usd: number;
  enable_narration: boolean;
  enable_subtitles: boolean;
}

export interface Project {
  id: string;
  title: string;
  owner_session_id: string;
  state: string;
  source_filename?: string | null;
  story_char_count: number;
  has_rights_confirmation: boolean;
  settings: ProductionSettings;
  created_at: string;
  updated_at: string;
}

export interface SceneResponse {
  id: string;
  project_id: string;
  order_index: number;
  title: string;
  state: string;
  plan: ScenePlan;
  current_version: number;
  selected_asset_id?: string | null;
  selected_video_url?: string | null;
  selected_audio_url?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Asset {
  id: string;
  project_id: string;
  scene_id?: string | null;
  asset_type: string;
  ref_identifier?: string | null;
  media_url: string;
  mime_type: string;
  duration_seconds?: number | null;
  model_id: string;
  prompt?: string | null;
  status: string;
  is_approved: boolean;
  is_mock: boolean;
  metadata: Record<string, any>;
  created_at: string;
}

export interface Job {
  id: string;
  project_id: string;
  scene_id?: string | null;
  job_type: string;
  state: string;
  progress_pct: number;
  message?: string | null;
  attempts: number;
  max_attempts: number;
  error_code?: string | null;
  error_details?: string | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface JobsSummary {
  project_id: string;
  project_state: string;
  active_jobs_count: number;
  jobs: Job[];
  scenes_status: Record<string, string>;
}

export interface ProductionEstimate {
  target_runtime_seconds: number;
  clip_duration_seconds: number;
  required_clip_count: number;
  max_clips_cap: number;
  estimated_cost_usd: number;
  budget_limit_usd: number;
  is_within_budget: boolean;
  is_within_clip_cap: boolean;
  warnings: string[];
}

export interface ExportRecord {
  id: string;
  project_id: string;
  media_url: string;
  duration_seconds: number;
  clip_count: number;
  missing_scene_count: number;
  file_size_bytes: number;
  state: string;
  created_at: string;
}

export interface UsageSummary {
  project_id: string;
  total_estimated_cost_usd: number;
  total_tokens: number;
  total_video_seconds: number;
  events_count: number;
  details: Array<{
    operation: string;
    model_id: string;
    cost_usd: number;
    duration: number;
    summary: string;
    is_mock: boolean;
  }>;
}

export interface SystemHealth {
  status: string;
  app_name: string;
  environment: string;
  provider_mode: string;
  use_live_providers: boolean;
  models: {
    text: string;
    image: string;
    video: string;
    tts: string;
  };
  caps: {
    max_scenes: number;
    max_clips: number;
    default_budget_usd: number;
  };
}
