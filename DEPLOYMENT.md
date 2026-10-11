# Deploying DuckTutor

For the immediate demo, run Streamlit on the Mac and call hosted Gemma 26B. Google runs the model; you do not need local weights or a GPU server.

## Launch the updated local demo

Extract the archive into your project folder. It excludes notebook data, credentials and virtual environments. Keep your existing `data/`, `.venv/` and local secret files; preserve notebook records before deleting an older project folder.

Open Terminal in the project directory. Stop any old Streamlit process with Ctrl+C so the updated theme loads. If there is no working virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python preflight.py --trusted-local --model gemma-4-26b-a4b-it
python -m streamlit run app.py
```

If the existing `.venv` works, activate it and run the last three commands. Open `http://127.0.0.1:8501`, enter your key in Connection settings, choose 26B, and test the connection. Preflight does not save the key.

For your own trusted exercise edits, select Trusted local demo and check its opt-in box. Leave the default localhost binding in place. For Docker execution, first install/start Docker, pull `python:3.12-slim`, and run `python preflight.py` without `--trusted-local`.

31B remains optional:

```bash
python preflight.py --trusted-local --model gemma-4-31b-it
```

Its default timeout is 60 seconds; 26B's is 20 seconds. Longer timeouts accommodate the slow successes observed on the Mac but cannot fix provider 500/503 errors. The UI offers explicit recovery to 26B.

`diagnose_gemma_request.py` is included for request comparisons. Every selected stage makes a live API call; it does not automatically retry or print generated answers.

## Proposed shared website

Use a Linux server with Streamlit behind an HTTPS reverse proxy, hosted 26B inference, a separate execution worker and persistent notebook storage. No GPU is needed for hosted inference. Select server capacity after measuring concurrent learners; no capacity or cost benchmark has been run.

| Component | Role | Work needed before public access |
| --- | --- | --- |
| Streamlit app | UI, model calls and orchestration | Authentication, per-user authorization, request limits and removal of trusted-local execution from public mode |
| Hosted Gemma | Tutor decisions | Server-managed credentials, quota monitoring and visible error recovery |
| Isolated runner | Execute learner code | Separate service with bounded job environments and no app credentials or notebook access |
| Notebook storage | Persist sessions | Durable storage, ownership checks for list/load/export, backups and retention rules |
| HTTPS proxy | Public entry point | TLS, WebSocket forwarding and access policy |

Deployment sequence:

1. Apply this update and complete the local demonstration.
2. Implement public-mode restrictions, authenticated notebook ownership and a remote-runner adapter. Keep learner-code execution separate from the app's secrets and files.
3. Deploy a staging instance from GitHub to the chosen Linux server. Run the app as an unprivileged service, keep its port private to the proxy, and use persistent notebook storage.
4. Check concurrent sessions, notebook access restrictions, API errors, timeouts and worker cleanup. Verify learner code cannot access app credentials or another learner's records.
5. Open the public URL after those checks pass.

The repository currently has Docker execution, but no separate runner API, authentication or notebook ownership. Docker availability must be established on the chosen host. Mounting the host Docker socket into a web-app container is not the proposed isolation boundary.

## Streamlit Community Cloud

Community Cloud can deploy a UI from a GitHub repository, branch and entry point (`app.py`), with configurable secrets and Python version. Those steps provide hosting, not isolation for arbitrary submitted Python.

Here, trusted-local learner code executes on the **app server**, not in the learner's browser. It can access host resources despite its child environment omitting API keys. The notebook also lists all records in one directory. Publishing the current code unchanged would expose those behaviors to visitors.

After a remote runner and notebook authorization exist, Community Cloud could host the UI while the runner has its own host. Putting the entire current application in one container does not separate learner code from the app's files or credentials.

## Official references

- [Deploy Streamlit from GitHub](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
- [Streamlit HTTPS guidance](https://docs.streamlit.io/develop/concepts/configuration/https-support): terminate TLS at a reverse proxy or load balancer for self-hosted production use.
- [Streamlit Docker deployment](https://docs.streamlit.io/deploy/tutorials/docker): packages the web app, not a learner-code security boundary by itself.

This update includes deployment guidance; no service has been published or production isolation implemented.
