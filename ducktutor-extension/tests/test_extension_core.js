const assert = require('assert');
const path = require('path');
const { PythonRunner, revision } = require('../out/runner');
const { EXERCISES } = require('../out/exercises');
const { TutorService } = require('../out/tutor');
const {
  createExerciseSession,
  createCustomCodeSession,
  updateSessionCode,
  recordRunResult,
} = require('../out/session');

async function runTests() {
  console.log('🧪 Starting DuckTutor VS Code Extension Core Tests...\n');

  // Test 1: Revision hash
  console.log('Test 1: Code revision hash computation & invalidation');
  const code1 = 'def foo(): pass';
  const code2 = 'def foo(): pass\n';
  const hash1 = revision(code1);
  const hash2 = revision(code2);
  assert.strictEqual(hash1.length, 12);
  assert.strictEqual(hash2.length, 12);
  assert.notStrictEqual(hash1, hash2, 'Hash must change when whitespace/code changes');
  console.log('  ✓ Revision hashing works');

  // Test 2: Session creation and updates
  console.log('Test 2: Session state machine');
  const basket = EXERCISES['basket'];
  const session = createExerciseSession(basket);
  assert.strictEqual(session.stage, 'predict');
  assert.strictEqual(session.exerciseId, 'basket');
  assert.strictEqual(session.verifiedHash, null);

  const changed = updateSessionCode(session, basket.solution);
  assert.strictEqual(changed, true);
  assert.strictEqual(session.verifiedHash, null);
  console.log('  ✓ Session state & revision invalidation works');

  // Test 3: Python Runner on starter code and solutions
  console.log('Test 3: PythonRunner executing test cases');
  const runner = new PythonRunner('python', 5);

  // Run starter code for basket: should fail fresh_repeat
  const starterRun = await runner.runCase(basket, basket.starter, basket.prediction);
  console.log(`  -> Basket starter prediction run: passed=${starterRun.passed}, actual=${JSON.stringify(starterRun.actual)}`);
  assert.strictEqual(starterRun.status, 'completed');

  // Run reference solution for basket: must pass all cases
  console.log('  -> Testing all 5 exercises reference solutions with PythonRunner:');
  for (const [id, ex] of Object.entries(EXERCISES)) {
    let allPassed = true;
    for (const testCase of ex.cases) {
      const res = await runner.runCase(ex, ex.solution, testCase);
      if (!res.passed) {
        allPassed = false;
        console.error(`    ❌ ${id} failed case ${testCase.id}: expected=${JSON.stringify(testCase.expected)} actual=${JSON.stringify(res.actual)}`);
      }
    }
    assert.strictEqual(allPassed, true, `Exercise ${id} reference solution must pass all cases`);
    console.log(`    ✓ Exercise "${id}" (${ex.title}): all ${ex.cases.length} cases passed`);
  }

  // Test 4: Custom code runner
  console.log('Test 4: Custom Python script execution');
  const customRes = await runner.runCustomCode('x = [1, 2, 3]\nprint("Sum is:", sum(x))');
  assert.strictEqual(customRes.status, 'completed');
  assert.strictEqual(customRes.passed, true);
  assert.strictEqual(customRes.stdout.trim(), 'Sum is: 6');
  console.log('  ✓ Custom code runner captures stdout and exits cleanly');

  // Test 5: TutorService fallback question
  console.log('Test 5: TutorService fallback');
  const tutor = new TutorService('', 'gemma-4-26b-a4b-it', 'google');
  const question = tutor.getFallbackQuestion(session, basket);
  assert(typeof question === 'string' && question.length > 0);
  console.log(`  ✓ Fallback Socratic question generated: "${question}"`);

  console.log('\n🎉 ALL TESTS PASSED SUCCESSFULLY!');
}

runTests().catch((err) => {
  console.error('Test failed with error:', err);
  process.exit(1);
});
