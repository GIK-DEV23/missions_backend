# Deploying missions-backend to a free GCP e2-micro VM (Terraform)

This provisions an **always-free** Compute Engine `e2-micro` VM and runs the
existing `docker-compose.yaml` stack (Django + Postgres + Redis + nginx) on it,
unchanged. Good for a low-traffic demo at **$0 on GCP**.

> Free-tier rules: one `e2-micro` per month in **us-west1 / us-central1 / us-east1**,
> 30GB standard persistent disk, 1GB North-America egress. Staying inside those
> keeps the bill at $0. A static IP is free while attached to a running VM.

---

## What Terraform creates
- A dedicated VPC + firewall (SSH 22, HTTP 80, HTTPS 443)
- A static external IP
- The `e2-micro` VM (Debian 12) with a startup script that:
  - creates a swap file (the VM only has ~1GB RAM),
  - installs Docker + the compose plugin,
  - optionally clones this repo into `/opt/missions/app`.

## Prerequisites (one time, on your laptop)
1. Install [Terraform](https://developer.hashicorp.com/terraform/install) and the
   [gcloud CLI](https://cloud.google.com/sdk/docs/install).
2. Authenticate Terraform to GCP with your Google account (no key file needed):
   ```bash
   gcloud auth application-default login
   ```
3. Have a GCP **project** with **billing enabled** (still $0 under free tier) and
   the Compute Engine API turned on:
   ```bash
   gcloud services enable compute.googleapis.com --project YOUR_PROJECT_ID
   ```
4. An SSH keypair at `~/.ssh/id_rsa[.pub]` (or set `ssh_public_key_path`).

## Provision the VM
```bash
cd deploy/terraform
cp terraform.tfvars.example terraform.tfvars   # then edit: project_id, region, etc.
terraform init
terraform plan
terraform apply
```
When it finishes, Terraform prints the IP and SSH command:
```
instance_ip = "34.x.x.x"
ssh_command = "ssh deployer@34.x.x.x"
app_url     = "http://34.x.x.x/"
```

## First-time app setup (on the VM)
SSH in, put the code + `.env` in place, and start the stack.

```bash
ssh deployer@<instance_ip>

# If you did NOT set git_repo_url, clone the repo now:
git clone <your-repo-url> /opt/missions/app
cd /opt/missions/app

# Create the production .env (see the values below), then:
docker compose up -d --build
```

Wait for the image to build (a few minutes on e2-micro — swap makes it possible),
then visit `http://<instance_ip>/`.

### Production `.env` values that matter
Start from `.env.example` and set at least:
```env
DEBUG=False
ALLOWED_HOSTS=<instance_ip>            # e.g. 34.x.x.x  (add your domain later)
CSRF_TRUSTED_ORIGINS=http://<instance_ip>
DJANGO_SECRET_KEY=<a long random string>
CORS_ALLOWED_ORIGINS=<your frontend origin>

DATABASE_NAME=missions_db
DATABASE_USER=postgres
DATABASE_PASSWORD=<strong password>
DATABASE_HOST=db
DATABASE_PORT=5432
REDIS_URL=redis://redis:6379/1

DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=you@example.com
DJANGO_SUPERUSER_PASSWORD=<strong password>
```
> With `DEBUG=False`, `ALLOWED_HOSTS` is **required** — the app won't serve
> requests until it contains the IP (and/or domain) you hit it on.

## Continuous deploys (reuse your existing GitHub Action)
`.github/workflows/deploy.yaml` already deploys by SSHing in and running
`git pull && docker compose up -d --build`. Point it at this VM by setting repo
secrets:
- `HOST` = the `instance_ip`
- `USERNAME` = `deployer`
- `PROJECT_PATH` = `/opt/missions/app`
- `SSH_PRIVATE_KEY` = private key whose public half is on the VM

For CI you'll want a dedicated deploy key rather than your personal key:
```bash
ssh-keygen -t ed25519 -f deploy_key -N ""
# add deploy_key.pub to the VM's ~/.ssh/authorized_keys (or set ssh_public_key_path to it)
# put the contents of deploy_key into the SSH_PRIVATE_KEY GitHub secret
```

## Tear down (stop all charges)
```bash
terraform destroy
```

## Notes / gotchas
- **1GB RAM is tight.** Swap covers the build and idle running; heavy concurrent
  traffic will be slow. Fine for a demo, not for production load.
- The stack still uses Django's `runserver` (from the Dockerfile `CMD`). Acceptable
  for a demo; switch to gunicorn later for real traffic.
- Media/static persist on the VM disk via the compose volumes — no data loss on
  container restarts (unlike Cloud Run).
- To restrict SSH, set `allowed_ssh_source_ranges = ["YOUR_IP/32"]` in tfvars.
