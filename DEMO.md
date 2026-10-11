# Four-minute demo

Use a successful live Gemma preflight first (`python preflight.py --trusted-local --model gemma-4-26b-a4b-it`).
In the Streamlit app sidebar, verify the model is set to the default `gemma-4-26b-a4b-it`, enter the API key,
enable your chosen runner (**Trusted local demo** with "I am running only code I trust"), and select
**The basket that remembers** from the 5-exercise catalog (`basket`, `largest`, `total`, `closures`, `countdown`).
Keep the notebook empty of private content.

## 0:00–0:25 — Problem

“When a coding assistant gives us the patch immediately, it can hide the assumption that
caused the bug. Our duck helps a learner expose that assumption through actual execution.”

## 0:25–1:10 — Predict and observe

Read the specification, including the supplied-empty-basket requirement. Select prediction `["banana"]`
with confidence 5 and explanation “I expect a new default basket on each call.” Submit prediction.
Show the actual `["apple", "banana"]` child-process output in the execution panel and Gemma's question.
Respond to the question naturally; do not describe the model text as scripted or promise its exact wording.

## 1:10–2:15 — A plausible incomplete correction

Enter this candidate fix into the code editor:

```python
def add_item(item, items=None):
    if not items:
        items = []
    items.append(item)
    return items
```

Check the correction. Independent calls pass. Gemma chooses a targeted challenge from the reviewed
case bank. If it selects another passing case, the required suite still includes the empty
provided list (`add_item("apple", [])`). Show the returned value, unchanged caller list, and failed identity check.

Explain the agent's role: it reads current code, learner confidence, and execution evidence, selecting a relevant case
and then receiving real execution results. It cannot create arbitrary shell commands or mark
a case as passed. The bank is reviewed; the live teaching conversation is adaptive.

## 2:15–3:00 — Correct and check

Change the condition to `if items is None:` and check again. All five listed cases should
pass. Say “These five checked cases passed for this revision.” Notice that changing the code by even
a single character immediately invalidates the pass verdict (`verified_hash = None`), preventing stale claims.

If the learner uses the solution drawer instead, acknowledge that assistance; the notebook
records that the reference solution was revealed.

## 3:00–3:35 — Remember & Resume

Open **My notebook**. Show prediction, confidence, attempts, assistance, and execution timeline recorded
automatically. Highlight session persistence: close or refresh the tab, then demonstrate
resuming the session via the sidebar expander (**"Resume saved session"**) or the quick-resume buttons in
My Notebook. Full code, evidence, and dialogue restore immediately while preserving revision integrity.

The optional follow-up question checks a related reference-sharing example. Skip it if time is short.

## 3:35–4:00 — Contribution and boundaries

“We built an open-source learning workflow around Gemma: predict with confidence, investigate with execution,
challenge incomplete corrections, retain evidence of the session, and resume anytime.”

Point to the project repository at `https://github.com/Ducktoberfest/team-neuralforge`.
Describe the deployed model route accurately: hosted Gemma (`gemma-4-26b-a4b-it`) is not offline.
The local demo runner is for trusted code; Docker container isolation is an optional route needing its own preflight.

## Before presenting

- Complete a whole session with the exact model, machine and network you will use (`gemma-4-26b-a4b-it`).
- Check several learner replies, including a correct initial prediction and uncertainty.
- Check that hints stay useful without giving an unrequested patch.
- Record observed latencies; no benchmark claim is needed.
- Save a short recording of a successful live session as a clearly labeled backup.
- If the model is unavailable, show the explicit degraded status (**"Exercise hint · live Gemma unavailable"**);
  never imply static hints are a live model response.
