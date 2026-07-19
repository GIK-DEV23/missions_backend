# GitOps on GitHub (no Kubernetes)

This project uses a lightweight, pull-based GitOps flow that fits the free
e2-micro VM. Git (GitHub) is the single source of truth; merges to `main` deploy
automatically; the VM reconciles itself to the registry.

## The flow

```
        commit / PR                merge to main
 you ─────────────────► GitHub ──────────────────► Actions
                                                     │
                          ┌──────────────────────────┤
                          │ 1. Build & Push Image     │  builds image in CI
                          │    → ghcr.io/…:latest     │  (NOT on the 1GB VM)
                          └──────────────┬────────────┘
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 │                                                │
        2a. Deploy workflow (push)              2b. Watchtower on the VM (pull)
        SSHes in, `git pull` (syncs             polls GHCR every 60s, sees the
        compose/nginx config), then             new :latest, pulls it and
        `docker compose pull && up -d`          recreates ONLY the backend
                 │                                                │
                 └───────────────────────┬───────────────────────┘
                                         ▼
                         backend container starts → its CMD runs
                         collectstatic + migrate + server
```

- **Infra as code:** `deploy/terraform/` is the source of truth for the VM.
- **App image built in CI:** `.github/workflows/build-and-push.yaml` → GHCR.
- **Config changes** (compose/nginx/env keys): applied by the **deploy workflow**
  (`.github/workflows/deploy.yaml`) which `git pull`s + `docker compose up -d`.
- **Code-only changes:** picked up automatically by **Watchtower** even without
  the deploy workflow — that's the "self-healing / pull" part.
- **Migrations:** run automatically because the Dockerfile `CMD` runs
  `migrate` + `collectstatic` on container start, and Watchtower/compose restart
  the container with the new image.

## Why both a push deploy AND Watchtower?
They cover different layers:
- Watchtower only updates **images** — it does *not* know about changes to
  `docker-compose.yaml`, `nginx.conf`, or new env vars.
- The deploy workflow `git pull`s so **config** changes land too, and gives you
  an immediate deploy instead of waiting for the poll interval.

If you want pure pull-based (no SSH secrets at all), you can delete
`deploy.yaml` and rely on Watchtower — just remember to `git pull && docker
compose up -d` manually whenever you change compose/nginx.

---

## One-time setup

### 1. GHCR package visibility (pick one)
The image lives at `ghcr.io/<owner>/missions_backend`.

- **Easiest for a demo — make it public:** after the first `Build & Push Image`
  run, open the package on GitHub → **Package settings** → **Change visibility**
  → Public. Then neither the VM nor Watchtower needs registry credentials.

- **Keep it private:** on the VM, log in once and mount the creds into Watchtower:
  ```bash
  # on the VM, as the deploy user
  echo "$GHCR_PAT" | docker login ghcr.io -u <github-username> --password-stdin
  ```
  Then uncomment the `config.json` volume line under the `watchtower` service in
  `docker-compose.yaml`. Use a PAT with `read:packages`.

### 2. Point the backend image at your owner
`docker-compose.yaml` defaults to `ghcr.io/paulwritescode/missions_backend:latest`.
If you deploy from a different owner/org, set it in the VM's `.env`:
```env
BACKEND_IMAGE=ghcr.io/<owner>/missions_backend:latest
WATCHTOWER_INTERVAL=60
```

### 3. GitHub secrets for the deploy workflow
Repo → Settings → Secrets and variables → Actions:
- `HOST` — the VM's static IP (from `terraform output instance_ip`)
- `USERNAME` — `deployer`
- `PROJECT_PATH` — `/opt/missions/app`
- `SSH_PRIVATE_KEY` — private key whose public half is on the VM

### 4. Done
Merge to `main` → CI builds & pushes → deploy workflow syncs config & pulls →
Watchtower keeps the backend reconciled to `:latest` thereafter.

## Verifying it works
On the VM:
```bash
docker compose ps                    # backend, db, redis, nginx, watchtower up
docker logs missions_watchtower -f   # shows poll + "Found new image" events
docker inspect --format='{{.Image}}' missions_backend   # image digest changes after a deploy
```
