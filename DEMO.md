# Four-minute demo — 0.3.0

Launch the updated app, open Connection settings, choose hosted Gemma 26B, enter the key and test the connection. Use a notebook without private material. Complete a live rehearsal first; responses are generated and their wording is not scripted.

## 0:00–0:30 — Bring your own problem

Show the default **Your code** workspace. Choose Python and paste:

```python
labels = ['draft']
snapshot = labels
labels.append('sent')
print(snapshot)
```

Goal: “Keep a snapshot of the labels before later changes.” Reported output: `['draft', 'sent']`. State that this is learner-reported output; this workspace does not execute submissions.

Ask: “I expected snapshot to stay ['draft']. Why did it change too?”

## 0:30–1:30 — Teach, then progress

Follow up naturally. If the explanation uses an unfamiliar term, ask: “I don't understand two names referring to one object. Can you explain with a small unrelated example?”

The duck should explain the concept directly, perhaps with an unrelated example, instead of rephrasing the same question. Then explain your understanding in your own words. Check that the next reply acknowledges it and moves forward.

Open **What I understand so far**. Distinguish learner-written notes from the duck's tentative interpretations; neither is a mastery certificate.

## 1:30–2:10 — Current code and honest evidence

Edit the code to investigate your idea. Show that pasted output remains associated with its previous revision. Update it after running the code yourself, or explicitly confirm it was reproduced with the current version. Ask about the changed code.

Explain that the duck reasons about code here; it does not claim execution or invent a pass verdict.

## 2:10–3:10 — Optional real checks

Switch to **Practice exercises**, choose the basket example and enable the trusted-local runner only for this reviewed code and your own trusted edits. Make a prediction, observe actual child-process output, and discuss it.

If time permits, check a correction against the five reviewed cases. Gemma can choose a case; Python determines the result. State “These checked cases passed for this revision,” not general correctness. Editing invalidates that status.

Switch back to Your code and show the original draft/conversation preserved.

## 3:10–3:45 — Save and resume

Open **My notebook**, show the own-code goal, language and saved source, then start another session and resume the previous record. Code, output attribution, learning notes and conversation restore.

## 3:45–4:00 — Evidence and limits

“Our software checks the workflow, but a useful tutor also needs conversation review. We include six realistic multi-turn evaluation scenarios and a human rubric.”

Show `python evaluate_tutor.py --list` or a previously reviewed transcript, clearly labeled with its actual model and date. No prerecorded response should be presented as live AI.

The immediate demo is local with hosted inference. Public notebook authorization and isolated public exercise execution are future deployment work.
