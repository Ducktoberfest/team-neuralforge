# Evaluate the tutor before claiming it teaches well

Passing software tests establishes that the app handles its inputs, evidence and protocol. It does not establish that Gemma is a useful teacher or equivalent to CS50 Duck.

## Live conversation review

```bash
python evaluate_tutor.py --list
python evaluate_tutor.py --case aliases --model gemma-4-26b-a4b-it
```

The default aliases scenario has three learner turns and at most six model requests, including repairs. `--list` uses no API key or model calls. The runner asks for the key privately when it is absent from the environment. Validated model replies are printed for review; rejected raw replies and connection credentials are not saved.

To review all six scenarios explicitly:

```bash
python evaluate_tutor.py --all --model gemma-4-26b-a4b-it --output eval_results/26b-review.json
```

There are 16 learner/prediction events, with a maximum of 32 model requests. Request failures can reduce actual calls. The correct-prediction case executes only the bundled reviewed basket starter through the trusted local runner. Own-code scenarios do not run their submitted code.

## Human rubric

The saved report contains a scenario-specific rubric, transcript, validated actions, request counts and an unscored review section. The exit code describes whether the final replies were usable live responses; it is not a teaching score.

For each rubric item, review the conversation and assign:

- **0:** incorrect, misleading, repetitive or unhelpful.
- **1:** partly helpful, but missing an explanation, appropriate progression or useful next step.
- **2:** accurate, relevant and useful for the learner's current understanding.

Keep notes with concrete quotations or turn references. A model-inferred learning note is a tentative interpretation; check that the learner actually expressed the insight.

## Critical failures

Do not call a scenario ready if it:

- Marks a correct prediction as wrong because the code violates the specification.
- Invents execution or test results for own code, or treats old output as current evidence.
- Repeats the same question after the learner expresses confusion without adding an explanation or clue.
- Ignores an insight the learner already stated and restarts the lesson.
- Supplies a full rewritten submission or an exact patch when the learner asks for the answer.
- Gives an inaccurate concept explanation or encourages a wrong correction.

The validator catches some patterns and exact/near-exact repetition. It cannot guarantee these semantic properties; the human review matters.

## Before a demo

Review all scenarios with the actual model and account. Then try at least two unscripted conversations with your own code and variations of learner replies. Ask a concept question without code, express confusion, explain a valid insight, edit the submission and request the complete solution.

If comparing 26B and 31B, use the same scenarios, generation settings and rubric, save separate reports, and record provider failures/latency separately from teaching scores. One successful request or a larger parameter count is not a teaching-quality comparison.

Reports may contain code and conversation. Keep `eval_results/` out of Git. No live evaluation results are included in this package; no API key was available in the build workspace.
