# Four-minute demo

Use a successful live Gemma preflight first. Enter the key in the sidebar, enable your
chosen runner, and start a new basket session. Keep the notebook empty of private content.

## 0:00–0:25 — Problem

“When a coding assistant gives us the patch immediately, it can hide the assumption that
caused the bug. Our duck helps a learner expose that assumption through actual execution.”

## 0:25–1:10 — Predict and observe

Read the specification, including the supplied-empty-basket requirement. Predict `["banana"]`
with confidence 5 and the explanation “I expect a new default basket on each call.” Run it.
Show the actual `["apple", "banana"]` output and Gemma's question. Respond to the question
naturally; do not describe the model text as scripted or promise its exact wording.

## 1:10–2:15 — A plausible incomplete correction

Enter this candidate:

```python
def add_item(item, items=None):
    if not items:
        items = []
    items.append(item)
    return items
```

Check the correction. Independent calls pass. Gemma chooses a challenge from the reviewed
bank. If it selects another passing case, the required suite still includes the empty
provided list. Show the returned value, unchanged caller list, and failed identity check.

Explain the agent's role: it reads current code and learner context, selects a relevant case
and then receives real execution results. It cannot create arbitrary shell commands or mark
a case as passed. The bank is reviewed; the live teaching conversation is adaptive.

## 2:15–3:00 — Correct and check

Change the condition to `if items is None:` and check again. All five listed cases should
pass. Say “These five checked cases passed for this revision.” Do not claim proof of
general correctness or that the learner has mastered the concept.

If the learner uses the solution button instead, acknowledge that assistance; the notebook
records it and does not call the result independent discovery.

## 3:00–3:35 — Remember

Open My notebook. Show prediction, confidence, attempts, assistance and outcome recorded
automatically. The optional follow-up question checks a related reference-sharing example.
Skip it if time is short.

## 3:35–4:00 — Contribution and boundaries

“We built an open-source learning workflow around Gemma: predict, investigate with execution,
challenge incomplete corrections, and retain evidence of the session.”

Show the public repository only after you have actually published it. Describe the deployed
model route accurately: hosted Gemma is not offline. The local demo runner is for trusted
code; Docker isolation is an optional route needing its own successful preflight.

## Before presenting

- Complete a whole session with the exact model, machine and network you will use.
- Check several learner replies, including a correct initial prediction and uncertainty.
- Check that hints stay useful without giving an unrequested patch.
- Record observed latencies; no benchmark claim is needed.
- Save a short recording of a successful live session as a clearly labeled backup.
- If the model is unavailable, show the explicit degraded status; never imply static hints
  are a live model response.
