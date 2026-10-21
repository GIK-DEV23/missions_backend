# Production Readiness Checklist — GIK Missions Backend

Prepared for the Play Store launch of the Souls App (Kenya, free, personal
data of third-party "souls" stored server-side). This backend is the data
controller for personal data under **Kenya's Data Protection Act 2019 (ODPC)**
and supplies the "encrypted in transit / at rest" answers on the **Google Play
Data Safety** form.

Ordered by priority. Each item lists the **file**, the **current state** (as it
exists in the repo today), and the **required change**. Check items off as they
land.

Legend: 🔴 blocker (must ship before the app collects real PII) · 🟠 strongly
recommended · 🟢 hardening / nice-to-have.

---

## 0. Context — what PII this backend stores

Source: `api/souls/models.py`. The `Soul` record holds personal data about
people who never installed the app and cannot consent through it:

- `first_name`, `last_name`
- `phone_number` (`PhoneNumberField`, **indexed**, part of a `unique_together`)
- `gender`, `age_group`, `location` (FK)
- free-text `description`, and `ProgressUpdate.content` (follow-up notes)
- consent fields already present: `consent_given`, `consent_recorded_at`,
  `do_not_contact`, `do_not_contact_at`

This is the data the encryption controls below are protecting.

---

## 1. 🔴 Encryption in transit (TLS / HTTPS)

**This is the hard blocker.** Play Data Safety requires "Yes" to encrypted in
transit; today PII travels over plain HTTP.

### 1.1 🔴 nginx has no TLS
- **File:** `nginx.conf`
- **Current:** single `server { listen 80; ... }` with a literal
  `# === TODO: Redirect traffic to HTTPS once interconnected with domain ===`.
  No `listen 443 ssl`, no certificate, no HTTP→HTTPS redirect.
- **Required:**
  - [ ] Acquire a domain and a TLS certificate (Let's Encrypt via certbot, or
        Cloudflare origin cert).
  - [ ] Add a `listen 443 ssl;` server block with `ssl_certificate` /
        `ssl_certificate_key`, modern protocols (`TLSv1.2 TLSv1.3`) and ciphers.
  - [ ] Change the `:80` block to a permanent redirect to `https://`.
  - [ ] Mount the certs into the `nginx` container (add a volume in
        `docker-compose.yaml`).

### 1.2 🔴 Django not told it is behind TLS
- **File:** `api/project/settings.py`
- **Current:** `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')`
  is **commented out**. `USE_X_FORWARDED_HOST = True` is set. nginx already
  forwards `X-Forwarded-Proto $scheme`.
- **Required (prod only, keep dev working):**
  - [ ] Uncomment `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')`.
  - [ ] `SECURE_SSL_REDIRECT = True`
  - [ ] `SESSION_COOKIE_SECURE = True`
  - [ ] `CSRF_COOKIE_SECURE = True`
  - [ ] `SECURE_HSTS_SECONDS = 31536000`, `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`,
        `SECURE_HSTS_PRELOAD = True`
  - [ ] Gate all of the above behind `if not DEBUG:` so local dev is unaffected.

### 1.3 🔴 Mobile app must point at HTTPS
- **File (app repo):** `souls_app/assets/.env.production`
- **Current:** `Env.apiBaseUrl` falls back to `http://10.0.2.2:8000/api`.
- **Required:**
  - [ ] Set `API_BASE_URL=https://<your-domain>/api` in `.env.production`.
  - [ ] Confirm no cleartext fallback ships in the release build (Android blocks
        cleartext by default on release; a plain-HTTP prod URL would fail at
        runtime).

---

## 2. 🔴 Django production security posture

- **File:** `api/project/settings.py`
- **Current:**
  - `DEBUG` defaults to `True`.
  - When `DEBUG` is truthy: `CORS_ALLOW_ALL_ORIGINS = True` and
    `ALLOWED_HOSTS = ["*"]`.
  - `SECRET_KEY = config("DJANGO_SECRET_KEY")` — no default (good), but
    `.env.example` ships `your-secret-key-here`.
  - `CSRF_TRUSTED_ORIGINS` default is `https://*.127.0.0.1`.
- **Required:**
  - [ ] `DEBUG=False` in the production `.env`.
  - [ ] `ALLOWED_HOSTS` set to the real domain(s) — never `*` in prod.
  - [ ] `CORS_ALLOWED_ORIGINS` limited to the real frontend origin(s).
  - [ ] `CSRF_TRUSTED_ORIGINS` set to the real `https://` domain.
  - [ ] Generate a fresh strong `DJANGO_SECRET_KEY` for prod (also signs JWTs via
        `NINJA_JWT.SIGNING_KEY` → rotating it invalidates all tokens; do it once
        before launch).
  - [ ] Run `python api/manage.py check --deploy` and clear every warning.

---

## 3. 🟠 Encryption at rest

Not a hard Play submission gate, but expected for third-party PII and aligns
with Kenya DPA "appropriate technical measures".

### 3.1 🟠 Database volume
- **File:** `docker-compose.yaml` (`db` service, `postgres:15`, volume
  `postgres_data`).
- **Current:** plain Postgres container on an unencrypted Docker volume.
- **Required (pick one):**
  - [ ] Enable full-disk / LUKS encryption on the VM host disk backing the
        volume, **or**
  - [ ] Migrate to a managed Postgres with encryption-at-rest (see README
        "Production Considerations #2: Consider managed PostgreSQL").

### 3.2 🟠 Media uploads
- **File:** `api/project/settings.py` (`MEDIA_ROOT`), `docker-compose.yaml`
  (`media_volume`).
- **Current:** testimony/profile photos stored unencrypted on `media_volume`.
- **Required:**
  - [ ] Covered by host-disk encryption (3.1), or move media to encrypted
        object storage.

### 3.3 🟢 Field-level encryption (optional, has tradeoffs)
- **File:** `api/souls/models.py`
- **Note:** encrypting `phone_number` / names breaks the existing
  `models.Index(fields=['phone_number'])` and the
  `unique_together = ('first_name','last_name','phone_number','user','mission')`
  constraint (encrypted values can't be indexed/compared for uniqueness).
- **Required (only if you decide the risk warrants it):**
  - [ ] Design a searchable-hash + encrypted-value scheme before adopting a
        library like `django-cryptography`. Do **not** drop-in without redesign.
  - [ ] Default recommendation: rely on volume-level encryption (3.1) first.

---

## 4. 🟠 Secrets & credentials hygiene

- **Files:** `.env.example`, `docker-compose.yaml`, `README.md`.
- **Current:** template ships weak defaults — `DATABASE_PASSWORD=postgres`,
  `DJANGO_SUPERUSER_PASSWORD=adminpassword`, `admin@gmail.com`. `.env` is loaded
  by both `backend` and `db` services.
- **Required:**
  - [ ] Strong, unique `DATABASE_PASSWORD` in prod `.env`.
  - [ ] Strong `DJANGO_SUPERUSER_PASSWORD` and a real admin email; consider
        disabling auto-superuser creation (`api/superuser_setup.py`) in prod
        after first boot.
  - [ ] Confirm the prod `.env` is **not** committed (verify `.gitignore`).
  - [ ] Rotate any secret that has ever been committed or shared.
  - [ ] Consider moving `ADMIN_URL` off the default `admin/` and/or setting
        `ALLOW_ADMIN_SITE=False` in prod if the mobile app doesn't need it.

---

## 5. 🟠 Data-subject rights (Kenya DPA 2019 / Play User Data policy)

- **Files:** `api/souls/models.py` (consent fields exist), app onboarding/soul
  creation flow.
- **Current:** model has `consent_given` / `consent_recorded_at` /
  `do_not_contact`, but consent capture must be enforced end-to-end.
- **Required:**
  - [ ] Ensure the app captures and records consent **before** a soul's PII is
        stored, and populates `consent_given` / `consent_recorded_at`.
  - [ ] Provide a **data deletion path** (account + associated souls) — Play
        requires this; expose an endpoint or documented process.
  - [ ] Honor `do_not_contact` throughout follow-up features.
  - [ ] Publish a **live HTTPS privacy policy** that covers third-party (souls')
        PII, retention, and deletion; link it in the Play listing.
  - [ ] Register/prepare as a data controller with the ODPC if not already.

---

## 6. 🟢 Operational hardening

- [ ] **Backups:** automated, **encrypted** Postgres + media backups with a
      tested restore. (No backup config present in `docker-compose.yaml`.)
- [ ] **DB port exposure:** `docker-compose.yaml` maps `5435:5432` and
      `6381:6379` to the host — close these on the prod VM (bind to localhost or
      remove the port mappings) so Postgres/Redis aren't publicly reachable.
- [ ] **Redis:** currently no auth (`redis-server --appendonly yes`). Add a
      password / network isolation in prod.
- [ ] **App server:** confirm prod runs Gunicorn/uWSGI, not the dev server
      (README "Production Considerations #5").
- [ ] **Logging/audit:** `audit_logs` app exists — confirm sensitive PII isn't
      written to plaintext logs.
- [ ] **`manage.py check --deploy`** passes clean.
- [ ] **Watchtower/GitOps:** confirm the prod image is the intended one and GHCR
      package access is correct (see `deploy/GITOPS.md`).

---

## Definition of done (Play submission gate)

The app can honestly answer the Play Data Safety form and collect real PII once
**all 🔴 items in sections 1 and 2 are complete** and the privacy policy /
deletion path in section 5 are live. Sections 3, 4, and 6 should follow closely
behind for Kenya DPA compliance and operational safety.
