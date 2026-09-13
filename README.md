# GIK Missions Backend

GIK missions related backend functionalities and apis.

## Prerequisites

- Docker and Docker Compose
- Git

## Quick Start

1. **Clone the repository**
   ```bash
   git clone git@github.com:godinkenyadev-ops/missions_backend.git
   cd missions_backend
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and configure your settings. The database host must match the
   compose service name (`db`), not the container name:
   ```env
   DJANGO_SECRET_KEY=your-secret-key-here
   DATABASE_NAME=missions_db
   DATABASE_USER=postgres
   DATABASE_PASSWORD=postgres
   DATABASE_HOST=db
   DATABASE_PORT=5432
   REDIS_URL=redis://redis:6379/1
   DJANGO_SUPERUSER_USERNAME=admin
   DJANGO_SUPERUSER_EMAIL=admin@gmail.com
   DJANGO_SUPERUSER_PASSWORD=adminpassword
   ```

3. **Build and run the application**

   The `backend` service defaults to pulling a prebuilt image from GHCR
   (`ghcr.io/paulwritescode/missions_backend:latest`). For local development,
   build the image yourself with `--build` so the local `Dockerfile` is used:
   ```bash
   docker compose up --build
   ```

   > **Note:** Without `--build`, `docker compose up` will try to *pull* the
   > production image instead of building your local code. Always use `--build`
   > (or set `BACKEND_IMAGE=<your-local-tag>`) when running local changes.

   To run only the core services for backend development (skip `nginx`, which
   needs a `./frontend/dist` build and binds ports 80/443, and `watchtower`,
   which is a production auto-updater):
   ```bash
   docker compose up --build db redis backend
   ```

4. **Access the application**
   - API: http://127.0.0.1:9050
   - Documentation: http://127.0.0.1:9050/api/docs
   - Health check: http://127.0.0.1:9050/health/
   - Admin panel: http://127.0.0.1:9050/admin
   - Admin credentials: `api/superuser_setup.py` runs automatically on startup
     and creates a superuser from the `DJANGO_SUPERUSER_*` env vars above.

## Project Structure
This will change over time. Each Django app follows a consistent layout
(`api.py`, `models.py`, `schemas.py`, `selectors.py`, `services.py`,
`filters.py`, `tests.py`, plus `migrations/`). Here is the current structure:
```
missions_backend
├── api
│   ├── audit_logs        # Audit/activity logging
│   ├── authentication    # JWT + Google/Apple OAuth backends, permissions
│   │   └── backends      # apple.py, base.py, google.py, jwt.py, registry.py
│   ├── base              # Shared models, schemas, filters, utils
│   │   └── utils         # exceptions.py, file_parser.py, helpers.py
│   ├── missions          # Missions + analytics.py
│   ├── notifications     # User notifications
│   ├── personal_missions # Personal (individual) missions
│   ├── project           # Django project: settings.py, urls.py, api.py (Ninja root)
│   ├── souls             # Souls / progress updates
│   ├── sync              # Offline sync endpoints
│   ├── testimonies       # Testimonies, miracles, highlights
│   ├── users             # Custom user model, roles, managers
│   ├── manage.py
│   └── superuser_setup.py  # Auto-creates superuser on startup
├── deploy
│   ├── terraform         # GCP VM provisioning (main.tf, variables.tf, ...)
│   ├── FRONTEND_DEPLOY_VITE.md
│   └── GITOPS.md         # Pull-based GitOps deploy notes
├── .github/workflows     # CI: build-and-push.yaml, deploy.yaml
├── API_DOCUMENTATION.org # Full API reference
├── docker-compose.yaml
├── Dockerfile
├── nginx.conf            # Reverse proxy config (production)
├── .env.example
├── poetry.lock
├── pyproject.toml
└── README.md
```

The API is served with **Django Ninja**. Routers are registered in
`api/project/api.py` under these prefixes: `auth/`, `users/`, `missions/`,
`souls/`, `testimonies/`, `sync/`, `personal-missions/`, `notifications/`,
`audit_logs/`.

## Services

### Backend (Django)
- **Container**: `missions_backend`
- **Port**: 9050 (maps to container port 8000)
- **Features**:
  - Automatic database migrations
  - Automatic superuser creation
  - Hot reload for development

### Database (PostgreSQL)
- **Container**: `missions_postgres`
- **Image**: `postgres:15`
- **Port**: 5435 (maps to container port 5432)
- **Data persistence**: Volume `postgres_data`

### Cache / Redis
- **Container**: `missions_redis`
- **Image**: `redis:latest`
- **Port**: 6381 (maps to container port 6379)
- **Used for**: Django cache backend (`django-redis`), configured via `REDIS_URL`
- **Data persistence**: Volume `redis_data`

### Nginx (production reverse proxy)
- **Container**: `missions_nginx`
- **Ports**: 80 / 443
- **Serves**: the Vite frontend build from `./frontend/dist` plus `/media` and
  `/static`. This directory is untracked by git; populate it per
  `deploy/FRONTEND_DEPLOY_VITE.md`.
- **Note**: Not needed for local backend development. Start only
  `db redis backend` to skip it.

### Watchtower (production auto-updater)
- **Container**: `missions_watchtower`
- **Image**: `nickfedor/watchtower:latest` (maintained fork)
- **Purpose**: Pull-based GitOps — polls GHCR and recreates the backend
  container when CI pushes a new image (`--label-enable` limits it to the
  backend only). Not needed locally. See `deploy/GITOPS.md`.

## Development Commands

### Start services
```bash
docker compose up
```

### Build and start (after code changes)
```bash
docker compose up --build
```

### Run in background
```bash
docker compose up -d
```

### View logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f db
```

### Execute commands in containers
```bash
# Django management commands
docker compose exec backend poetry run python api/manage.py <command>

# Shell access
docker compose exec backend bash
docker compose exec db psql -U ${DATABASE_USER} -d ${DATABASE_NAME}
```

### Stop services
```bash
docker compose down
```

### Complete cleanup (removes containers, networks, volumes, and images)
```bash
docker compose down --rmi all --volumes --remove-orphans
```

## Common Django Commands

```bash
# Create migrations
docker compose exec backend poetry run python api/manage.py makemigrations

# Apply migrations(if needed manually)
docker compose exec backend poetry run python api/manage.py migrate

# Create superuser (if needed manually)
docker compose exec backend poetry run python api/manage.py createsuperuser

# Django shell
docker compose exec backend poetry run python api/manage.py shell

# Collect static files (for production)
docker compose exec backend poetry run python api/manage.py collectstatic
```

## Environment Variables
| Variable                    | Description                                  | Default / Example                               |
| --------------------------- | -------------------------------------------- |-------------------------------------------------|
| `DATABASE_NAME`             | PostgreSQL database name                     | `missions_db`                                   |
| `DATABASE_USER`             | PostgreSQL username                          | `postgres`                                      |
| `DATABASE_PASSWORD`         | PostgreSQL password                          | `postgres`                                      |
| `DATABASE_HOST`             | PostgreSQL host                              | `db`                                            |
| `DATABASE_PORT`             | PostgreSQL port                              | `5432`                                          |
| `REDIS_URL`                 | Redis connection URL (Django cache backend)  | `redis://redis:6379/1`                          |
| `DJANGO_SUPERUSER_USERNAME` | Django admin username                        | `admin`                                         |
| `DJANGO_SUPERUSER_EMAIL`    | Django admin email                           | `admin@gmail.com`                               |
| `DJANGO_SUPERUSER_PASSWORD` | Django admin password                        | `adminpassword`                                 |
| `DJANGO_SECRET_KEY`         | Django secret key                            | `your-secret-key-here`                          |
| `ALLOWED_HOSTS`             | Comma-separated list of allowed hosts        | `*`                                             |
| `DEBUG`                     | Enable/disable debug mode                    | `True`                                          |
| `CORS_ALLOWED_ORIGINS`      | Comma-separated list of allowed CORS origins | `http://localhost:3000,http://127.0.0.1:3000`   |
| `GOOGLE_CLIENT_ID`          | Google OAuth client ID                       | -                                               |
| `GOOGLE_CLIENT_SECRET`      | Google OAuth client secret                   | -                                               |
| `GOOGLE_REDIRECT_URI`       | Google OAuth redirect URI                    | `https://developers.google.com/oauthplayground` |                                          |
| `APPLE_CLIENT_ID`           | Apple OAuth client ID                        | -                                               |
| `APPLE_TEAM_ID`             | Apple developer team ID                      | -                                               |
| `APPLE_KEY_ID`              | Apple private key ID                         | -                                               |
| `APPLE_PRIVATE_KEY`         | Apple private key content                    | -                                               |
| `APPLE_REDIRECT_URI`        | Apple OAuth redirect URI                     | -                                               |
| `ALLOW_ADMIN_SITE`          | Enable/disable the Django admin site         | `True`                                          |
| `ADMIN_URL`                 | URL path for the admin site                  | `admin/`                                        |
| `CSRF_TRUSTED_ORIGINS`      | Comma-separated trusted origins for CSRF     | `https://*.127.0.0.1`                           |
| `EMAIL_HOST`                | SMTP host (blank = print emails to console)  | -                                               |
| `EMAIL_PORT`                | SMTP port                                    | `587`                                           |
| `EMAIL_HOST_USER`           | SMTP username                                | -                                               |
| `EMAIL_HOST_PASSWORD`       | SMTP password                                | -                                               |
| `EMAIL_USE_TLS`             | Use TLS for SMTP                             | `True`                                          |
| `DEFAULT_FROM_EMAIL`        | Default "from" address for outgoing email    | `no-reply@gik-missions.org`                     |
| `PASSWORD_RESET_DEEP_LINK_BASE` | Mobile deep link base for password reset | `gikmissions://reset-password`                  |
| `BACKEND_IMAGE`             | Backend image to run (override for local build) | `ghcr.io/paulwritescode/missions_backend:latest` |
| `WATCHTOWER_INTERVAL`       | Watchtower poll interval (seconds)           | `60`                                            |


## Troubleshooting

### Port already in use
If port 9050 is busy, change it in `docker-compose.yaml`:
```yaml
ports:
  - "9051:8000"  # Use different port
```

### Database connection issues
1. Ensure PostgreSQL container is healthy:
   ```bash
   docker compose ps
   ```
2. Check database logs:
   ```bash
   docker compose logs db
   ```

### Container won't start
1. Check logs for errors:
   ```bash
   docker compose logs backend
   ```
2. Rebuild containers:
   ```bash
   docker compose up --build --force-recreate
   ```

### Permission issues
Ensure your user is in the docker group:
```bash
sudo usermod -aG docker $USER
# Log out and log back in
```

### Complete reset
If you need to start fresh:
```bash
docker compose down --rmi all --volumes --remove-orphans
docker compose up --build
```

## Deployment & CI/CD

Deployment uses a **pull-based GitOps** model rather than SSH-push:

- **CI** (`.github/workflows/`):
  - `build-and-push.yaml` builds the backend image and pushes it to GHCR
    (`ghcr.io/paulwritescode/missions_backend`).
  - `deploy.yaml` handles the deploy-side automation.
- **Infrastructure** (`deploy/terraform/`): provisions the GCP VM that runs the
  stack. See `deploy/terraform/README.md`.
- **Runtime updates**: `watchtower` on the VM polls GHCR and recreates the
  backend container when a new image is pushed — no manual deploy needed for
  code changes. See `deploy/GITOPS.md`.
- **Frontend**: the Vite build is served by `nginx` from `./frontend/dist`,
  which is untracked by git. See `deploy/FRONTEND_DEPLOY_VITE.md`.

Full API reference lives in `API_DOCUMENTATION.org`.

## Production Considerations

For production deployment:

1. **Environment variables**: Use secure values and environment-specific settings
2. **Database**: Consider managed PostgreSQL service
3. **Static files**: Configure proper static file serving
4. **Security**: Update `ALLOWED_HOSTS` and `SECRET_KEY`
5. **Server**: Replace development server with Gunicorn/uWSGI
6. **Reverse proxy**: Add Nginx for static files and load balancing
7. **Volumes**: Use named volumes or bind mounts for data persistence

## Contributing

1. Make your changes on a new branch based on `main`
2. Test locally with `docker compose up --build`
3. Ensure all containers start successfully
4. Submit a pull request


## Support
If you encounter issues:
1. Check the logs: `docker compose logs -f`
2. Verify environment variables in `.env`
3. Ensure Docker and Docker Compose are installed correctly
4. Check port availability:
   - **Linux (Ubuntu/Kali/Arch)**: `ss -tlnp | grep 9050` or `netstat -tulnp | grep 9050`
   - **macOS**: `lsof -i :9050` or `netstat -an | grep 9050`
   - **Windows (PowerShell)**: `Get-NetTCPConnection -LocalPort 9050` or `netstat -ano | findstr :9050`
   - **Windows (CMD)**: `netstat -ano | findstr :9050`