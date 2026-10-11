export interface Case {
  id: string;
  title: string;
  purpose: string;
  script: string;
  expected: any;
}

export interface TransferReflection {
  transferSnippet: string;
  transferPrompt: string;
  transferChoices: string[];
  correctChoiceIndex: number;
  explanation: string;
}

export interface Exercise {
  id: string;
  title: string;
  concept: string;
  spec: string;
  starter: string;
  entrypoint: string;
  predictionCode: string;
  choices: string[];
  prediction: Case;
  cases: Case[];
  solution: string;
  explanation: string;
  hints: string[];
  forbidden?: string[];
  reflection?: TransferReflection;
}

export interface RunResult {
  id: string;
  caseId: string;
  title: string;
  codeHash: string;
  expected: any;
  actual: any;
  passed: boolean;
  status: 'completed' | 'timeout' | 'syntax_error' | 'runtime_error' | 'runner_error' | 'output_limit';
  error?: string;
  stdout?: string;
  durationMs?: number;
}

export interface SessionMessage {
  role: 'assistant' | 'user' | 'system';
  text: string;
  source: string;
  timestamp?: string;
}

export interface SessionEvent {
  type: string;
  caseId?: string;
  runId?: string;
  codeHash?: string;
  action?: string;
  error?: string;
  durationMs?: number;
  [key: string]: any;
}

export type SessionStage = 'predict' | 'investigate' | 'guide' | 'reflect';

export interface Session {
  id: string;
  isCustomCode: boolean;
  exerciseId: string;
  concept: string;
  title: string;
  startedAt: string;
  updatedAt: string;
  stage: SessionStage;
  code: string;
  codeHash: string;
  prediction: string | null;
  confidence: number | null;
  explanation: string;
  initialObservation: string | null;
  predictionMatchesExecution: boolean | null;
  messages: SessionMessage[];
  runs: RunResult[];
  events: SessionEvent[];
  attempts: number;
  hintLevel: number;
  solutionViewed: boolean;
  verifiedHash: string | null;
  outcome: 'in_progress' | 'verified' | 'solution_revealed';
  modelCalls: number;
  transferPrediction: number | null;
  transferCorrect: boolean | null;
  language?: string;
}
