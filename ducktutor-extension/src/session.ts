import * as crypto from 'crypto';
import { Exercise, Session, SessionMessage, RunResult } from './types';
import { revision } from './runner';

export function createExerciseSession(exercise: Exercise): Session {
  const code = exercise.starter;
  const now = new Date().toISOString();
  return {
    id: crypto.randomBytes(8).toString('hex'),
    isCustomCode: false,
    exerciseId: exercise.id,
    concept: exercise.concept,
    title: exercise.title,
    startedAt: now,
    updatedAt: now,
    stage: 'predict',
    code,
    codeHash: revision(code),
    prediction: null,
    confidence: null,
    explanation: '',
    initialObservation: null,
    predictionMatchesExecution: null,
    messages: [
      {
        role: 'assistant',
        text: `Quack! Welcome to "${exercise.title}". Before we run the code, examine the snippet above and predict what will happen. Rating your confidence helps us debug together!`,
        source: 'DuckTutor',
        timestamp: now,
      },
    ],
    runs: [],
    events: [],
    attempts: 0,
    hintLevel: 0,
    solutionViewed: false,
    verifiedHash: null,
    outcome: 'in_progress',
    modelCalls: 0,
    transferPrediction: null,
    transferCorrect: null,
  };
}

export function createCustomCodeSession(code: string, fileName = 'untitled.py', language = 'python'): Session {
  const now = new Date().toISOString();
  return {
    id: crypto.randomBytes(8).toString('hex'),
    isCustomCode: true,
    exerciseId: 'custom',
    concept: 'User Workspace Code',
    title: `Duck Debug: ${fileName}`,
    startedAt: now,
    updatedAt: now,
    stage: 'predict',
    code,
    codeHash: revision(code),
    prediction: null,
    confidence: null,
    explanation: '',
    initialObservation: null,
    predictionMatchesExecution: null,
    messages: [
      {
        role: 'assistant',
        text: `Quack! I am your Socratic Rubber Duck powered by Gemma 4. Run your code with "▶️ Run & Ask Duck" or click "🔍 Socratic Review" to analyze "${fileName}". What part of this code would you like to examine?`,
        source: 'DuckTutor',
        timestamp: now,
      },
    ],
    runs: [],
    events: [],
    attempts: 0,
    hintLevel: 0,
    solutionViewed: false,
    verifiedHash: null,
    outcome: 'in_progress',
    modelCalls: 0,
    transferPrediction: null,
    transferCorrect: null,
    language,
  };
}

export function updateSessionCode(session: Session, newCode: string): boolean {
  if (session.code === newCode) {
    return false;
  }
  session.code = newCode;
  session.codeHash = revision(newCode);
  session.verifiedHash = null; // Invalidate any previous pass verdict!
  session.outcome = 'in_progress';
  session.updatedAt = new Date().toISOString();
  return true;
}

export function addSessionMessage(session: Session, role: 'assistant' | 'user' | 'system', text: string, source = 'DuckTutor') {
  session.messages.push({
    role,
    text,
    source,
    timestamp: new Date().toISOString(),
  });
  session.updatedAt = new Date().toISOString();
}

export function recordRunResult(session: Session, result: RunResult) {
  session.runs.push(result);
  session.events.push({
    type: 'execution',
    caseId: result.caseId,
    runId: result.id,
    codeHash: session.codeHash,
    passed: result.passed,
    status: result.status,
  });
  session.updatedAt = new Date().toISOString();
}
