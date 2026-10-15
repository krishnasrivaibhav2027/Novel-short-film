import React, { useEffect, useState, useCallback } from 'react';
import { api } from './api';
import { Header } from './components/Header';
import { Stepper } from './components/Stepper';
import { StoryIngestStep } from './components/StoryIngestStep';
import { ConfigurationStep } from './components/ConfigurationStep';
import { StoryBibleStep } from './components/StoryBibleStep';
import { ScreenplayStep } from './components/ScreenplayStep';
import { ArtDirectionStep } from './components/ArtDirectionStep';
import { ProductionStep } from './components/ProductionStep';
import { PremiereStep } from './components/PremiereStep';
import { UsageDrawer } from './components/UsageDrawer';
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

export const App: React.FC = () => {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);

  // Step Data
  const [storyBible, setStoryBible] = useState<StoryBible | null>(null);
  const [scenes, setScenes] = useState<SceneResponse[]>([]);
  const [references, setReferences] = useState<Asset[]>([]);
  const [jobsSummary, setJobsSummary] = useState<JobsSummary | null>(null);
  const [estimate, setEstimate] = useState<ProductionEstimate | null>(null);
  const [latestExport, setLatestExport] = useState<ExportRecord | null>(null);
  const [usage, setUsage] = useState<UsageSummary | null>(null);

  // UI state
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isUsageOpen, setIsUsageOpen] = useState<boolean>(false);

  // 1. Initial Load & Health
  useEffect(() => {
    api.getHealth()
      .then(setHealth)
      .catch((err) => console.warn('Backend offline or health check failed:', err));
  }, []);

  // 2. Load or Create Initial Project
  const initProject = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const savedProjectId = localStorage.getItem('novel_movie_active_project_id');
      let proj: Project;

      if (savedProjectId) {
        try {
          proj = await api.getProject(savedProjectId);
        } catch {
          proj = await api.createProject('My Animated Film');
          localStorage.setItem('novel_movie_active_project_id', proj.id);
        }
      } else {
        proj = await api.createProject('My Animated Film');
        localStorage.setItem('novel_movie_active_project_id', proj.id);
      }

      setProject(proj);
      await syncProjectState(proj);
    } catch (err: any) {
      setError(err.message || 'Failed to initialize project');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    initProject();
  }, [initProject]);

  // Synchronize pipeline steps based on project state & existing assets
  const syncProjectState = async (proj: Project) => {
    const doneSteps: number[] = [];

    // Step 1 check
    if (proj.story_char_count > 0) {
      doneSteps.push(1);
    }

    // Step 3 (Story Bible) check
    try {
      const bible = await api.getStoryBible(proj.id);
      setStoryBible(bible);
      doneSteps.push(2);
      doneSteps.push(3);
    } catch {
      // not yet analyzed
    }

    // Step 4 (Scenes) check
    try {
      const scList = await api.getScenes(proj.id);
      setScenes(scList);
      if (scList.length > 0) {
        doneSteps.push(4);
      }
    } catch {
      // no scenes yet
    }

    // Step 5 (References) check
    try {
      const refs = await api.getReferences(proj.id);
      setReferences(refs);
      if (refs.length > 0) {
        doneSteps.push(5);
      }
    } catch {
      // no references yet
    }

    // Step 6 (Estimate & Jobs)
    try {
      const est = await api.getEstimate(proj.id);
      setEstimate(est);
    } catch {
      // pass
    }

    try {
      const js = await api.getJobsSummary(proj.id);
      setJobsSummary(js);
    } catch {
      // pass
    }

    // Step 7 (Exports)
    try {
      const exportsList = await api.getExports(proj.id);
      if (exportsList.length > 0) {
        setLatestExport(exportsList[0]);
        doneSteps.push(6);
        doneSteps.push(7);
      }
    } catch {
      // pass
    }

    setCompletedSteps(Array.from(new Set(doneSteps)));

    // Set appropriate active step if fresh navigation
    if (proj.state === 'COMPLETED') {
      setCurrentStep(7);
    } else if (proj.state === 'GENERATING' || proj.state === 'SCENE_REVIEW' || proj.state === 'ASSEMBLING') {
      setCurrentStep(6);
    } else if (proj.state === 'DESIGN_REVIEW' || proj.state === 'DESIGNING') {
      setCurrentStep(5);
    } else if (proj.state === 'PLAN_REVIEW') {
      setCurrentStep(4);
    } else if (proj.story_char_count > 0) {
      setCurrentStep(2);
    } else {
      setCurrentStep(1);
    }
  };

  // 3. Periodic Polling for In-Flight Jobs (Steps 3, 4, 5, 6, 7)
  useEffect(() => {
    if (!project) return;

    const interval = setInterval(async () => {
      try {
        const js = await api.getJobsSummary(project.id);
        setJobsSummary(js);

        // Refresh scenes if in production
        if (currentStep === 6 || js.active_jobs_count > 0) {
          const updatedScenes = await api.getScenes(project.id);
          setScenes(updatedScenes);
        }

        // Check if exports completed
        if (project.state === 'ASSEMBLING' || currentStep === 6) {
          const exList = await api.getExports(project.id);
          if (exList.length > 0) {
            setLatestExport(exList[0]);
            if (currentStep === 6 && (js.active_jobs_count === 0)) {
              setCompletedSteps((prev) => Array.from(new Set([...prev, 6, 7])));
              setCurrentStep(7);
            }
          }
        }
      } catch {
        // quiet poll fail
      }
    }, 2500);

    return () => clearInterval(interval);
  }, [project, currentStep]);

  // 4. Action Handlers
  const handleNewProject = async () => {
    localStorage.removeItem('novel_movie_active_project_id');
    setStoryBible(null);
    setScenes([]);
    setReferences([]);
    setLatestExport(null);
    setCompletedSteps([]);
    setCurrentStep(1);
    await initProject();
  };

  const handleStorySubmitted = async (text: string, rights: boolean) => {
    if (!project) return;
    setLoading(true);
    setError(null);
    try {
      const updated = await api.ingestStoryText(project.id, text, rights);
      setProject(updated);
      setCompletedSteps((prev) => Array.from(new Set([...prev, 1])));
      setCurrentStep(2);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (file: File, rights: boolean) => {
    if (!project) return;
    setLoading(true);
    setError(null);
    try {
      const updated = await api.ingestStoryFile(project.id, file, rights);
      setProject(updated);
      setCompletedSteps((prev) => Array.from(new Set([...prev, 1])));
      setCurrentStep(2);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSettings = async (settings: ProductionSettings) => {
    if (!project) return;
    try {
      const updated = await api.updateSettings(project.id, settings);
      setProject(updated);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleStartAnalysis = async () => {
    if (!project) return;
    setLoading(true);
    setError(null);
    try {
      await api.analyzeStory(project.id);
      // Poll until story bible is ready
      let bible: StoryBible | null = null;
      for (let i = 0; i < 30; i++) {
        await new Promise((r) => setTimeout(r, 1500));
        try {
          bible = await api.getStoryBible(project.id);
          if (bible) break;
        } catch {}
      }
      if (bible) {
        setStoryBible(bible);
        setCompletedSteps((prev) => Array.from(new Set([...prev, 2, 3])));
        setCurrentStep(3);
      } else {
        throw new Error('Analysis timed out. Please retry.');
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleProceedToScreenplay = async () => {
    if (!project) return;
    setLoading(true);
    setError(null);
    try {
      await api.generateScreenplay(project.id);
      let scList: SceneResponse[] = [];
      for (let i = 0; i < 30; i++) {
        await new Promise((r) => setTimeout(r, 1500));
        try {
          scList = await api.getScenes(project.id);
          if (scList.length > 0) break;
        } catch {}
      }
      if (scList.length > 0) {
        setScenes(scList);
        setCompletedSteps((prev) => Array.from(new Set([...prev, 3])));
        setCurrentStep(4);
      } else {
        throw new Error('Screenplay generation timed out. Please retry.');
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateScene = async (
    sceneId: string,
    updates: { title?: string; visual_prompt?: string; dialogue_or_narration?: string }
  ) => {
    if (!project) return;
    try {
      const updatedScene = await api.updateScene(project.id, sceneId, updates);
      setScenes((prev) => prev.map((s) => (s.id === sceneId ? updatedScene : s)));
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleApprovePlan = async () => {
    if (!project) return;
    setLoading(true);
    setError(null);
    try {
      const updated = await api.approvePlan(project.id);
      setProject(updated);
      setCompletedSteps((prev) => Array.from(new Set([...prev, 4])));
      setCurrentStep(5);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateReferences = async () => {
    if (!project) return;
    setLoading(true);
    setError(null);
    try {
      await api.generateReferences(project.id);
      let refs: Asset[] = [];
      for (let i = 0; i < 30; i++) {
        await new Promise((r) => setTimeout(r, 1500));
        try {
          refs = await api.getReferences(project.id);
          if (refs.length > 0) break;
        } catch {}
      }
      if (refs.length > 0) {
        setReferences(refs);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleApproveReferences = async (approvedIds: string[]) => {
    if (!project) return;
    setLoading(true);
    setError(null);
    try {
      const updated = await api.approveReferences(project.id, approvedIds);
      setProject(updated);
      // Fetch estimate
      const est = await api.getEstimate(project.id);
      setEstimate(est);
      setCompletedSteps((prev) => Array.from(new Set([...prev, 5])));
      setCurrentStep(6);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleStartProduction = async (confirmBudget: boolean) => {
    if (!project) return;
    setLoading(true);
    setError(null);
    try {
      await api.startProduction(project.id, confirmBudget);
      const js = await api.getJobsSummary(project.id);
      setJobsSummary(js);
      const scList = await api.getScenes(project.id);
      setScenes(scList);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRetryScene = async (sceneId: string) => {
    if (!project) return;
    try {
      await api.retryScene(project.id, sceneId);
      const js = await api.getJobsSummary(project.id);
      setJobsSummary(js);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleRegenerateScene = async (
    sceneId: string,
    updates: { visual_prompt?: string; dialogue_or_narration?: string }
  ) => {
    if (!project) return;
    try {
      await api.regenerateScene(project.id, sceneId, updates);
      const js = await api.getJobsSummary(project.id);
      setJobsSummary(js);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleAssembleMovie = async () => {
    if (!project) return;
    setLoading(true);
    setError(null);
    try {
      await api.assembleMovie(project.id);
      let exList: ExportRecord[] = [];
      for (let i = 0; i < 30; i++) {
        await new Promise((r) => setTimeout(r, 2000));
        try {
          exList = await api.getExports(project.id);
          if (exList.length > 0) break;
        } catch {}
      }
      if (exList.length > 0) {
        setLatestExport(exList[0]);
        setCompletedSteps((prev) => Array.from(new Set([...prev, 6, 7])));
        setCurrentStep(7);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleUploadSceneClip = async (sceneId: string, file: File) => {
    if (!project) return;
    setLoading(true);
    setError(null);
    try {
      const updatedScene = await api.uploadSceneClip(project.id, sceneId, file);
      setScenes((prev) => prev.map((s) => (s.id === sceneId ? updatedScene : s)));
    } catch (err: any) {
      setError(err.message || 'Failed to upload scene clip');
    } finally {
      setLoading(false);
    }
  };

  const handleUploadAssetImage = async (assetId: string, file: File) => {
    if (!project) return;
    setLoading(true);
    setError(null);
    try {
      const updatedAsset = await api.uploadAssetImage(project.id, assetId, file);
      setReferences((prev) => prev.map((a) => (a.id === assetId ? updatedAsset : a)));
    } catch (err: any) {
      setError(err.message || 'Failed to upload asset image');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenUsage = async () => {
    if (!project) return;
    try {
      const u = await api.getUsage(project.id);
      setUsage(u);
      setIsUsageOpen(true);
    } catch (err: any) {
      console.warn('Could not fetch usage:', err);
    }
  };

  return (
    <div className="app-layout">
      <Header
        currentProject={project}
        health={health}
        onNewProject={handleNewProject}
        onOpenUsage={handleOpenUsage}
      />

      <main className="container" style={{ paddingBottom: '5rem' }}>
        <Stepper
          currentStep={currentStep}
          completedSteps={completedSteps}
          onSelectStep={(s) => setCurrentStep(s)}
        />

        {error && (
          <div
            style={{
              background: 'rgba(244, 63, 94, 0.15)',
              border: '1px solid rgba(244, 63, 94, 0.3)',
              color: '#fda4af',
              padding: '0.85rem 1.25rem',
              borderRadius: 'var(--radius-md)',
              marginBottom: '1.5rem',
              fontSize: '0.9rem',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <span>{error}</span>
            <button
              type="button"
              style={{ background: 'transparent', border: 'none', color: '#fff', cursor: 'pointer' }}
              onClick={() => setError(null)}
            >
              ✕
            </button>
          </div>
        )}

        {/* Step Views */}
        {currentStep === 1 && project && (
          <StoryIngestStep
            project={project}
            onStorySubmitted={handleStorySubmitted}
            onFileUpload={handleFileUpload}
            loading={loading}
            error={error}
          />
        )}

        {currentStep === 2 && project && (
          <ConfigurationStep
            project={project}
            onSaveSettings={handleSaveSettings}
            onStartAnalysis={handleStartAnalysis}
            loading={loading}
          />
        )}

        {currentStep === 3 && storyBible && (
          <StoryBibleStep
            bible={storyBible}
            onProceedToScreenplay={handleProceedToScreenplay}
            loading={loading}
          />
        )}

        {currentStep === 4 && (
          <ScreenplayStep
            scenes={scenes}
            onUpdateScene={handleUpdateScene}
            onApprovePlan={handleApprovePlan}
            loading={loading}
          />
        )}

        {currentStep === 5 && (
          <ArtDirectionStep
            references={references}
            onGenerateReferences={handleGenerateReferences}
            onApproveReferences={handleApproveReferences}
            onUploadImage={handleUploadAssetImage}
            loading={loading}
          />
        )}

        {currentStep === 6 && (
          <ProductionStep
            scenes={scenes}
            jobsSummary={jobsSummary}
            estimate={estimate}
            onStartProduction={handleStartProduction}
            onRetryScene={handleRetryScene}
            onRegenerateScene={handleRegenerateScene}
            onAssembleMovie={handleAssembleMovie}
            onUploadClip={handleUploadSceneClip}
            loading={loading}
          />
        )}

        {currentStep === 7 && project && (
          <PremiereStep
            project={project}
            latestExport={latestExport}
            scenes={scenes}
            onBackToStudio={() => setCurrentStep(6)}
          />
        )}
      </main>

      <UsageDrawer
        isOpen={isUsageOpen}
        onClose={() => setIsUsageOpen(false)}
        usage={usage}
      />
    </div>
  );
};

export default App;
