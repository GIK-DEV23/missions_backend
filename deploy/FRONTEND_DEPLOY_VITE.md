# Frontend Deployment Plan: Vite + React on e2-micro VM

Deploy your **Vite + React + TypeScript** frontend on the same e2-micro VM as the backend. nginx serves the Vite build (`dist/`) + proxies API calls. No extra cost, no domain needed.

**Live now at:** `http://34.74.106.149/`

---

## Architecture

```
User Browser (http://34.74.106.149)
    ↓
nginx
    ├─ /            → serves Vite build (frontend/dist/, SPA fallback to index.html)
    ├─ /assets/*     → Vite build assets (long-cached, content-hashed filenames)
    ├─ /api/*        → proxies to Django backend
    ├─ /admin/*      → proxies to Django admin
    ├─ /static/*     → Django collectstatic output (served directly by nginx)
    └─ /media/*      → Django uploads (served directly by nginx)
```

`nginx.conf` and the `frontend/dist` volume mount are **already committed** in this backend repo's `docker-compose.yaml` and `nginx.conf`, and are kept in sync by the GitOps deploy workflow (`.github/workflows/deploy.yaml`, which runs `git reset --hard origin/main` on every merge). You do **not** need to touch either file on the VM — only the contents of `frontend/dist/`, which is untracked by git and safe from `git reset --hard`.

---

## Critical: Vite Build Environment

Your `src/config/env.ts` reads `VITE_API_BASE_URL` at **build time** (Vite inlines env vars into the bundle). It must be `/api` for production, or the built app will fall back to `http://127.0.0.1:9050/api` and every API call will fail.

This repo's frontend has `.env.production` committed with `VITE_API_BASE_URL=/api`, so a plain `npm run build` picks it up automatically — no need to pass the env var inline. If your frontend project doesn't have that file yet, create it:

```env
VITE_API_BASE_URL=/api
```

---

## Deploying a frontend change (every time)

### 1. Build locally

```bash
cd /path/to/your/react/project
npm run build
# Creates dist/ folder (verify: ls dist/index.html dist/assets/)
```

### 2. Compress and copy to the VM

```bash
tar -czf frontend-build.tar.gz dist/
scp -i ~/.ssh/missions_deploy frontend-build.tar.gz deployer@34.74.106.149:/tmp/
rm frontend-build.tar.gz
```

### 3. Extract on the VM and restart nginx

```bash
ssh -i ~/.ssh/missions_deploy deployer@34.74.106.149 << 'EOF'
cd /opt/missions/app
rm -rf frontend/dist
mkdir -p frontend
tar -xzf /tmp/frontend-build.tar.gz -C frontend/
docker compose up -d nginx   # `up -d`, not `restart` — needed the first time a
                              # volume-mounted path changes; restart is enough
                              # for later updates since the mount already exists
sleep 5
docker compose ps
EOF
```

### 4. Verify

```bash
curl -I http://34.74.106.149/          # 200, Content-Type: text/html
curl -s http://34.74.106.149/api/missions/   # reaches Django (401/200, not 404)
```

Then load `http://34.74.106.149/` in a browser and confirm the app renders and API calls succeed (check Network tab — requests should go to `/api/...`, not an absolute URL).

---

## Automation: GitHub Actions (Optional)

Auto-deploy the frontend on every merge to `main` in your **frontend** repo. Create `.github/workflows/deploy-frontend.yaml` there:

```yaml
name: Deploy Frontend

on:
  push:
    branches: [main]
  workflow_dispatch: {}

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"

      - run: npm ci
      - run: npm run build   # VITE_API_BASE_URL=/api comes from committed .env.production

      - run: tar -czf frontend-build.tar.gz dist/

      - name: Copy to VM
        uses: appleboy/scp-action@v0.1.7
        with:
          host: ${{ secrets.HOST }}
          username: ${{ secrets.USERNAME }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          source: "frontend-build.tar.gz"
          target: "/tmp/"

      - name: Deploy on VM
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.HOST }}
          username: ${{ secrets.USERNAME }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/missions/app
            rm -rf frontend/dist
            mkdir -p frontend
            tar -xzf /tmp/frontend-build.tar.gz -C frontend/
            docker compose restart nginx
            sleep 5
            docker compose ps
```

Add these secrets in the **frontend** repo (Settings → Secrets and variables → Actions) — same values as the backend repo's secrets:
- `HOST`: `34.74.106.149`
- `USERNAME`: `deployer`
- `SSH_PRIVATE_KEY`: contents of `~/.ssh/missions_deploy`

---

## Troubleshooting

**React app loads but shows 404 or blank page**
- Verify the build actually landed: `ssh deployer@34.74.106.149 "ls -la /opt/missions/app/frontend/dist/index.html"`
- Confirm the volume mount is active: `ssh deployer@34.74.106.149 "docker exec missions_nginx ls /app/frontend/dist/"`
- If the mount is missing after a fresh VM/deploy, run `docker compose up -d nginx` (not `restart`) — Compose only re-applies volume changes on recreate.

**API calls fail (404 or CORS/network error)**
- Confirm the frontend built with `VITE_API_BASE_URL=/api` — check the built JS bundle: `grep -o 'baseURL:"[^"]*"' dist/assets/*.js` should show `/api`, not `127.0.0.1` or `9050`.
- Check nginx routing: `docker logs missions_nginx`
- Test the backend directly, bypassing nginx: `curl http://34.74.106.149:9050/api/missions/`

**nginx container won't start / crash-loops**
- Validate config: `ssh deployer@34.74.106.149 "cd /opt/missions/app && docker compose config -q"`
- Check logs: `docker logs missions_nginx`

**Page refresh on a client-side route (e.g. `/missions`) returns 404**
- `nginx.conf`'s `location /` already has `try_files $uri $uri/ /index.html;` for this — if it's missing, the deployed `nginx.conf` is stale. Pull the latest backend repo state onto the VM (the GitOps deploy workflow does this automatically on merge).

**Watchtower container stuck `Restarting`**
- Known issue: the `containrrr/watchtower` image is unmaintained and its bundled Docker client is too old for modern Docker Engine (`client version 1.25 is too old`). Fixed in this repo by switching to `nickfedor/watchtower` (the maintained fork) — already reflected in `docker-compose.yaml`.

---

## Summary

1. `npm run build` (production env baked in via committed `.env.production`)
2. `tar` + `scp` the `dist/` folder to `/tmp/` on the VM
3. Extract into `/opt/missions/app/frontend/dist/` (untracked, survives GitOps deploys)
4. `docker compose up -d nginx` (first time) or `restart nginx` (subsequent updates)
5. Verify with `curl` and a browser check

`nginx.conf` and the volume mount live in this backend repo and are deployed automatically — no manual nginx editing needed going forward.
