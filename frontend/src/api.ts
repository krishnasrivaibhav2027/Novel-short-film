import type {
  Asset,
  ExportRecord,
  JobsSummary,
  ProductionEstimate,
  ProductionSettings,
  Project,
  SceneResponse,
  StoryBible,
  SystemHealth,
  UsageSummary,
} from './types';

const API_BASE = '/api/projects';

function getSessionId(): string {
  let sid = localStorage.getItem('novel_movie_session_id');
  if (!sid) {
    sid = 'user_' + Math.random().toString(36).substring(2, 11);
    localStorage.setItem('novel_movie_session_id', sid);
  }
  return sid;
}

async function fetchJson<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set('X-Session-Id', getSessionId());
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    let errorDetail = 'Network request failed';
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errJson.message || JSON.stringify(errJson);
    } catch {
      errorDetail = response.statusText || `${response.status} Error`;
    }
    throw new Error(errorDetail);
  }
  return response.json();
}

export const api = {
  getHealth: (): Promise<SystemHealth> => fetchJson('/health'),

  createProject: (title: string, language = 'English'): Promise<Project> =>
    fetchJson(API_BASE, {
      method: 'POST',
      body: JSON.stringify({ title, language }),
    }),

  getProject: (id: string): Promise<Project> => fetchJson(`${API_BASE}/${id}`),

  updateSettings: (id: string, settings: ProductionSettings): Promise<Project> =>
    fetchJson(`${API_BASE}/${id}/settings`, {
      method: 'PATCH',
      body: JSON.stringify({ settings }),
    }),

  ingestStoryText: (id: string, text: string, rights: boolean): Promise<Project> =>
    fetchJson(`${API_BASE}/${id}/story`, {
      method: 'POST',
      body: JSON.stringify({ story_text: text, has_rights_confirmation: rights }),
    }),

  ingestStoryFile: (id: string, file: File, rights: boolean): Promise<Project> => {
    const data = new FormData();
    data.append('file', file);
    data.append('has_rights_confirmation', String(rights));
    return fetchJson(`${API_BASE}/${id}/story/upload`, {
      method: 'POST',
      body: data,
    });
  },

  analyzeStory: (id: string): Promise<{ message: string; job_id: string }> =>
    fetchJson(`${API_BASE}/${id}/analyze`, { method: 'POST' }),

  getStoryBible: (id: string): Promise<StoryBible> => fetchJson(`${API_BASE}/${id}/story-bible`),

  generateScreenplay: (id: string): Promise<{ message: string; job_id: string }> =>
    fetchJson(`${API_BASE}/${id}/screenplay`, { method: 'POST' }),

  getScenes: (id: string): Promise<SceneResponse[]> => fetchJson(`${API_BASE}/${id}/scenes`),

  updateScene: (
    id: string,
    sceneId: string,
    updates: {
      title?: string;
      visual_prompt?: string;
      dialogue_or_narration?: string;
      action?: string;
    }
  ): Promise<SceneResponse> =>
    fetchJson(`${API_BASE}/${id}/scenes/${sceneId}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    }),

  approvePlan: (id: string): Promise<Project> =>
    fetchJson(`${API_BASE}/${id}/approve-plan`, { method: 'POST' }),

  generateReferences: (id: string): Promise<{ message: string; job_id: string }> =>
    fetchJson(`${API_BASE}/${id}/references`, { method: 'POST' }),

  getReferences: (id: string): Promise<Asset[]> => fetchJson(`${API_BASE}/${id}/references`),

  approveReferences: (id: string, approvedAssetIds: string[]): Promise<Project> =>
    fetchJson(`${API_BASE}/${id}/approve-references`, {
      method: 'POST',
      body: JSON.stringify({ approved_asset_ids: approvedAssetIds }),
    }),

  getEstimate: (id: string): Promise<ProductionEstimate> =>
    fetchJson(`${API_BASE}/${id}/estimate`),

  startProduction: (id: string, confirmBudget = true): Promise<{ message: string; queued_scenes: number }> =>
    fetchJson(`${API_BASE}/${id}/production`, {
      method: 'POST',
      body: JSON.stringify({ confirm_budget: confirmBudget }),
    }),

  getJobsSummary: (id: string): Promise<JobsSummary> => fetchJson(`${API_BASE}/${id}/jobs`),

  retryScene: (id: string, sceneId: string): Promise<{ message: string; job_id: string }> =>
    fetchJson(`${API_BASE}/${id}/scenes/${sceneId}/retry`, { method: 'POST' }),

  regenerateScene: (
    id: string,
    sceneId: string,
    updates: { visual_prompt?: string; dialogue_or_narration?: string }
  ): Promise<{ message: string; job_id: string; version: number }> =>
    fetchJson(`${API_BASE}/${id}/scenes/${sceneId}/regenerate`, {
      method: 'POST',
      body: JSON.stringify(updates),
    }),

  assembleMovie: (id: string): Promise<{ message: string; job_id: string }> =>
    fetchJson(`${API_BASE}/${id}/assemble`, { method: 'POST' }),

  getExports: (id: string): Promise<ExportRecord[]> => fetchJson(`${API_BASE}/${id}/exports`),

  getUsage: (id: string): Promise<UsageSummary> => fetchJson(`${API_BASE}/${id}/usage`),

  uploadSceneClip: (id: string, sceneId: string, file: File): Promise<SceneResponse> => {
    const data = new FormData();
    data.append('file', file);
    return fetchJson(`${API_BASE}/${id}/scenes/${sceneId}/upload-clip`, {
      method: 'POST',
      body: data,
    });
  },

  uploadAssetImage: (id: string, assetId: string, file: File): Promise<Asset> => {
    const data = new FormData();
    data.append('file', file);
    return fetchJson(`${API_BASE}/${id}/assets/${assetId}/upload-image`, {
      method: 'POST',
      body: data,
    });
  },
};
