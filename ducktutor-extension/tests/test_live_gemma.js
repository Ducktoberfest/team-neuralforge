const { TutorService } = require('../out/tutor');
const { createExerciseSession } = require('../out/session');
const { EXERCISES } = require('../out/exercises');

async function test() {
  const apiKey = process.env.GEMMA_API_KEY || '';
  const tutor = new TutorService(apiKey, 'gemma-4-26b-a4b-it', 'google');
  const ex = EXERCISES['basket'];
  const session = createExerciseSession(ex);
  session.prediction = '["banana"]';
  session.confidence = 5;
  session.runs.push({
    id: 'testrun',
    caseId: 'prediction',
    title: 'Second independent call',
    codeHash: session.codeHash,
    expected: ['banana'],
    actual: ['apple', 'banana'],
    passed: false,
    status: 'completed'
  });

  console.log('Calling Gemma decide with live API...');
  const decision = await tutor.decide(session, ex, 'prediction_completed', ['ask_question'], ex.cases);
  console.log('Decision Action:', decision.action);
  console.log('Decision Message:', decision.message);
}

test().catch(console.error);
