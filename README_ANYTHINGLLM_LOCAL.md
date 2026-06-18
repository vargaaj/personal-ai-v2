# Local AnythingLLM Runtime

This note documents how the local AnythingLLM container is wired into the
Personal-AI workspace and the `personal-ai-web-app` review console.

The short version:

- AnythingLLM runs from the official Docker image:
  `mintplexlabs/anythingllm:latest`.
- The Docker Compose file lives in a local AnythingLLM source checkout, for
  example `<ANYTHING_LLM_CHECKOUT>\docker\docker-compose.yml`.
- The local `Personal-AI` folder is mounted into AnythingLLM's filesystem tool
  area so scheduled jobs can read and write files in this project.
- Our changed scheduled-job runner is mounted over the image's bundled runner so
  scheduled jobs can use the AnythingLLM model router without rebuilding the
  image.

## Start And Stop

From PowerShell:

```powershell
cd <ANYTHING_LLM_CHECKOUT>\docker
docker compose up -d
```

AnythingLLM is exposed at:

```text
http://localhost:3001
```

Useful operational commands:

```powershell
docker ps
docker logs -f anythingllm
docker compose down
```

The review console is separate from AnythingLLM. Start it from
`personal-ai-web-app` when you want to inspect or edit the loop JSON files:

```powershell
cd <PERSONAL_AI_ROOT>\personal-ai-web-app
conda activate personal-ai
python -m loop_review.main
```

The review console runs at:

```text
http://127.0.0.1:8080
```

## Scheduled Jobs

AnythingLLM scheduled jobs are configured in the AnythingLLM UI and stored in
AnythingLLM's local database as `scheduled_jobs` and `scheduled_job_runs`
records.

When the AnythingLLM server starts, it loads every enabled scheduled job and
registers its cron schedule. Cron interpretation is UTC. When a schedule fires,
AnythingLLM creates a run record and executes the job prompt.

Each scheduled run is executed by:

```text
anything-llm\server\jobs\run-scheduled-job.js
```

In this local setup, that file is bind-mounted into the container at the same
path:

```text
../server/jobs/run-scheduled-job.js:/app/server/jobs/run-scheduled-job.js:ro
```

That mount is important because the running container uses our local changed
scheduled-job runner instead of only the version baked into the image.

The main reason for the local runner change is model routing. The patched
scheduled-job runner lets scheduled jobs use the AnythingLLM model router, so
scheduled loop jobs follow the same local model routing setup as the rest of the
instance.

The rest of the scheduled-job flow is still AnythingLLM's normal flow: the job
uses the configured prompt and tools, records the run result, and can update
local files through the filesystem tool.

For Personal-AI loops, the key result is that scheduled jobs can update JSON
files under:

```text
<PERSONAL_AI_ROOT>\personal-ai-web-app\data\loops
```

The review console then reads those same JSON files directly.

## Docker Setup

The local Docker Compose service is named `anything-llm`, and the container is
named `anythingllm`.

Core settings from `<ANYTHING_LLM_CHECKOUT>\docker\docker-compose.yml`:

```yaml
services:
  anything-llm:
    container_name: anythingllm
    image: mintplexlabs/anythingllm:latest
    cap_add:
      - SYS_ADMIN
    ports:
      - "3001:3001"
    env_file:
      - .env
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

The `.env` file in `anything-llm\docker` provides the local AnythingLLM runtime
configuration. Do not copy secrets from that file into docs or commits.

The `host.docker.internal` mapping lets the container reach model providers or
other services running on the Windows host, such as LM Studio or Ollama.

## Docker Mounts

The important volume mounts are:

These host paths are examples from the local Docker Compose checkout. They do
not mean the AnythingLLM source has to live inside this GitHub repo. If
AnythingLLM is checked out somewhere else, update the left-hand host paths in
your local Compose file while keeping the same intended container paths.

| Host path from `<ANYTHING_LLM_CHECKOUT>\docker` | Container path | Purpose |
| --- | --- | --- |
| `./.env` | `/app/server/.env` | Provides AnythingLLM server environment settings. |
| `../server/storage` | `/app/server/storage` | Persists AnythingLLM storage, including database and uploaded/generated files. |
| Path to the local `Personal-AI` folder | `/app/server/storage/anythingllm-fs/personal-ai` | Exposes this project to the AnythingLLM filesystem tools. |
| `../server/jobs/run-scheduled-job.js` | `/app/server/jobs/run-scheduled-job.js:ro` | Uses the local model-router-capable scheduled-job runner from the AnythingLLM checkout. |
| `../collector/hotdir/` | `/app/collector/hotdir` | Provides the collector hot directory. |
| `../collector/outputs/` | `/app/collector/outputs` | Stores collector outputs. |

Because the local `Personal-AI` folder is mounted into AnythingLLM's default
filesystem-tool root, an agent inside the container can address Personal-AI
files under:

```text
/app/server/storage/anythingllm-fs/personal-ai
```

For example, the Gmail loop state file is available inside the container at:

```text
/app/server/storage/anythingllm-fs/personal-ai/personal-ai-web-app/data/loops/gmail_state.json
```

That is the bridge between scheduled AnythingLLM jobs and the local
`personal-ai-web-app` review console: AnythingLLM writes the JSON files through
the mounted filesystem path, and the review console reads the same files from
the Windows project folder.
