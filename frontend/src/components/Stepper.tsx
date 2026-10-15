import React from 'react';
import { BookOpen, Sliders, Compass, Film, Palette, Clapperboard, PlayCircle, Check } from 'lucide-react';

export interface StepDef {
  id: number;
  label: string;
  icon: React.ReactNode;
}

interface StepperProps {
  currentStep: number;
  completedSteps: number[];
  onSelectStep: (stepId: number) => void;
}

export const STEP_DEFINITIONS: StepDef[] = [
  { id: 1, label: 'Story Manuscript', icon: <BookOpen size={16} /> },
  { id: 2, label: 'Film Configuration', icon: <Sliders size={16} /> },
  { id: 3, label: 'Story Bible', icon: <Compass size={16} /> },
  { id: 4, label: 'Screenplay Breakdown', icon: <Film size={16} /> },
  { id: 5, label: 'Visual World & Art', icon: <Palette size={16} /> },
  { id: 6, label: 'Production Studio', icon: <Clapperboard size={16} /> },
  { id: 7, label: 'Cinema Premiere', icon: <PlayCircle size={16} /> },
];

export const Stepper: React.FC<StepperProps> = ({
  currentStep,
  completedSteps,
  onSelectStep,
}) => {
  return (
    <nav className="stepper-nav" aria-label="Production Pipeline Stages">
      <div className="stepper-track">
        {STEP_DEFINITIONS.map((step) => {
          const isActive = currentStep === step.id;
          const isCompleted = completedSteps.includes(step.id);
          const isAccessible = isCompleted || step.id <= currentStep;

          return (
            <button
              key={step.id}
              id={`step-nav-${step.id}`}
              className={`step-item ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}`}
              onClick={() => isAccessible && onSelectStep(step.id)}
              disabled={!isAccessible}
              title={step.label}
            >
              <div className="step-indicator">
                {isCompleted && !isActive ? <Check size={18} /> : step.icon}
              </div>
              <span className="step-title">{step.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};
