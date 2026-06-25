# QueryGateway Production Deployment Plan

This document is the production deployment recommendation for QueryGateway on AWS EC2. It focuses on the best-practice target architecture and the project-specific gaps that must be fixed before go-live.

The requested document name was `production_deployemnt_md`; this file uses the corrected Markdown filename `production_deployment.md`.

## Executive Recommendation

Use Linux containers for production.

The best target is an Ubuntu Linux EC2 instance running Docker Engine and Docker Compose, or a managed container platform later if the deployment grows. QueryGateway's current Docker assets are already Linux-container based:

- Backend image: `python:3.12-slim`
- Frontend build image: `node:20-slim`
- Frontend runtime image: `nginx:1.27-alpine`
- App database image: `postgres:16-alpine`
- Optional local Oracle XE image: `gvenzl/oracle-xe:21-slim`

Do not convert this project to native Windows containers for production unless there is a hard Windows-only dependency. The current stack does not require one, and Windows containers would create avoidable image, dependency, Nginx, PostgreSQL, and Oracle-driver differences.

If the existing EC2 Windows Server must be used, run the project inside WSL2 Ubuntu with Docker Engine as an interim single-host deployment. That is preferable to Windows containers for this repo, but it is still less clean operationally than a native Linux EC2 host.

## Decision Matrix

| Option | Recommendation | Fit For This Project | Main Reason |
| --- | --- | --- | --- |
| Ubuntu EC2 + Docker Engine | Preferred | Best | Matches repo images, simplest operations, strongest support path for Linux containers. |
| Existing Windows EC2 + WSL2 Ubuntu + Docker Engine | Acceptable interim path | Good, with caveats | Keeps Linux containers, but WSL has lifecycle and networking differences from a normal Linux server. |
| Windows Server native Windows containers | Avoid | Poor | Requires reworking Linux-based images and introduces platform differences. |
| Docker Desktop on Windows Server | Avoid | Poor | Docker does not support Docker Desktop on Windows Server 2019/2022. |
| ECS/Fargate/EKS | Future option | Good at larger scale | More operational maturity, but more setup and migration work than a single EC2 host. |

## Best Practice Target Architecture

### Target Components

```text
Internet
  |
  v
Route 53 DNS
  |
  v
HTTPS endpoint
  |
  +-- Preferred: AWS Application Load Balancer + ACM certificate
  |
  +-- Simpler single-host option: Nginx/Caddy on EC2 with Let's Encrypt
  |
  v
EC2 Ubuntu Linux host
  |
  +-- Docker network: querygateway_internal
      |
      +-- web container: Nginx serves React SPA and proxies /api/*
      |
      +-- api container: FastAPI/Uvicorn, private to Docker network
      |
      +-- optional local db container: PostgreSQL 16 for small deployments only
  |
  +-- Preferred app database: Amazon RDS PostgreSQL 16
  |
  +-- Outbound access:
      |
      +-- external APIs
      +-- Oracle database/listener
      +-- AWS APIs for logs/secrets/backups
```

### Host Operating System

Use Ubuntu Linux on EC2 for the production host.

Recommended baseline:

- Ubuntu Server 24.04 LTS or current AWS-supported Ubuntu LTS AMI.
- Docker Engine, not Docker Desktop.
- Docker Compose plugin.
- EC2 instance profile for AWS permissions.
- EBS volume with enough IOPS for Docker, logs, and any local PostgreSQL volume.
- Security updates enabled and a patching procedure.

Use the current Windows Server only when migration to Linux is not possible yet. In that case, put the deployment inside WSL2 Ubuntu and keep all application files and Docker volumes inside the WSL filesystem, not under `/mnt/c`.

### Public IP And DNS

Use DNS as the stable public entry point.

Recommended:

- Point a domain such as `querygateway.example.com` at an Application Load Balancer, or at an Elastic IP for a simple single-instance deployment.
- Use an Elastic IP only if the instance itself must have a stable public IPv4 address, for example when external systems whitelist the source IP.
- If external APIs or Oracle systems need to whitelist QueryGateway outbound traffic, document the public egress IP and keep it stable.
- Prefer DNS for user-facing access, because instances can be replaced without changing client configuration.

### Network Security

Expose only the minimum required ports.

Inbound security group:

| Port | Source | Purpose | Recommendation |
| --- | --- | --- | --- |
| 443 | Public internet or approved client CIDRs | HTTPS app access | Allow. |
| 80 | Public internet | HTTP redirect or ACME challenge | Allow only if needed. Redirect to HTTPS. |
| 22 | Admin office IP/VPN only | Linux SSH | Restrict. Do not expose globally. |
| 3389 | Admin office IP/VPN only | Windows RDP, if Windows host remains | Restrict. Do not expose globally. |
| 8000 | None publicly | Backend API container | Do not expose publicly. Use Nginx/ALB path routing. |
| 5432 | None publicly | PostgreSQL | Do not expose publicly. Use Docker internal network or RDS private subnet. |
| 1521 | Oracle source only if local Oracle profile is used | Oracle listener | Usually do not expose. |

Outbound security group:

- Allow HTTPS to external APIs required by the solution.
- Allow Oracle listener connectivity to approved Oracle hosts and ports.
- Allow PostgreSQL connectivity to RDS if RDS is used.
- Allow AWS service endpoints needed for logs, secrets, package pulls, and backups.

### TLS Strategy

Production must use HTTPS.

Preferred AWS-native option:

- Application Load Balancer terminates TLS.
- AWS Certificate Manager manages the certificate.
- ALB forwards to the EC2 host on private HTTP.
- EC2 security group accepts app traffic only from the ALB security group.

Simpler single-host option:

- Nginx or Caddy terminates TLS directly on the EC2 host.
- Let's Encrypt manages the certificate.
- Docker `web` container can stay as the app Nginx, or a host-level reverse proxy can sit in front of the compose stack.

Avoid serving the admin UI or data APIs over plain HTTP in production.

### Database Strategy

Preferred production database: Amazon RDS PostgreSQL 16.

Rationale:

- QueryGateway stores all application state in PostgreSQL: connections, encrypted credentials, auth methods, endpoints, schedules, snapshots, job runs, settings, and access logs.
- RDS gives automated backups, easier point-in-time recovery, storage management, monitoring, and patching.
- It removes the highest-risk stateful component from the single EC2 host.

Acceptable small-deployment alternative:

- Run the existing `db` service as a Docker volume on EC2.
- Add daily `pg_dump` backups.
- Snapshot the EBS volume.
- Test restore before go-live.
- Plan a migration path to RDS before business-critical usage.

Do not expose PostgreSQL to the public internet.

### Secrets Strategy

Required production secrets:

- `JWT_SECRET_KEY`
- `ENCRYPTION_KEY`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD_HASH`
- `DATABASE_URL`
- Oracle credentials saved through the app and encrypted with `ENCRYPTION_KEY`

Best practice:

- Store secrets in AWS Secrets Manager or SSM Parameter Store.
- Inject them into the container environment at deploy time.
- Do not commit `.env`.
- Back up `ENCRYPTION_KEY` securely. Losing it makes encrypted Oracle credentials unrecoverable.
- Rotate admin password by generating a new bcrypt hash and redeploying.
- Restrict IAM permissions to only the secrets required by this application.

### Container Runtime Layout

Recommended production runtime:

- `web` listens publicly on `80` inside the host or behind ALB.
- `web` proxies `/api/*` to `api:8000` on the internal Docker network.
- `api` is not published to the public host network.
- `db` is omitted when RDS is used.
- Health checks stay enabled.
- Restart policy is `unless-stopped` or `always`.
- Logs are collected centrally.

For a single-host Compose deployment, keep a production override file such as `compose.production.yml` instead of editing the development compose file directly. Docker's Compose production guidance explicitly recommends production-specific override files for changed ports, environment variables, restart policy, and extra services.

### Observability

Minimum go-live observability:

- API health probes:
  - `/api/v1/admin/health/live`
  - `/api/v1/admin/health/ready`
  - `/api/v1/admin/health/dashboard`
- Structured JSON logs from the API.
- Container logs shipped to CloudWatch Logs or another central log system.
- Alerts for:
  - `live` endpoint non-200
  - `ready` endpoint non-200
  - degraded dashboard status
  - repeated 401/403 spikes
  - repeated 5xx responses
  - scheduler job failures
  - stale snapshots
  - low disk space
  - high CPU/memory
  - RDS storage and connection pressure

Docker can send container logs to CloudWatch Logs with the `awslogs` logging driver. On EC2, prefer an instance profile over static AWS access keys.

### Backup And Restore

For RDS:

- Enable automated backups.
- Set a backup retention window appropriate for the business requirement.
- Create manual snapshots before major upgrades.
- Test point-in-time restore into a temporary instance.

For local Docker PostgreSQL:

- Run daily `pg_dump` backups.
- Store backups outside the instance, for example S3.
- Retain at least 30 days unless policy says otherwise.
- Test restore before go-live.
- Back up `.env` or deployment secrets separately.
- Back up the `ENCRYPTION_KEY` in a secure secrets system.

### Deployment Flow

Recommended release process:

1. Build and test from a clean commit.
2. Build Docker images.
3. Push images to a registry, ideally Amazon ECR.
4. Pull images on the production host.
5. Load production secrets.
6. Run Alembic migrations.
7. Start or recreate services.
8. Verify health endpoints.
9. Verify admin login.
10. Test one Oracle connection.
11. Test one protected `/api/v1/data/*` endpoint.
12. Confirm logs are flowing.
13. Confirm backup job status.

Minimum Compose commands for single-host deployment:

```bash
docker compose -f docker-compose.yml -f compose.production.yml pull
docker compose -f docker-compose.yml -f compose.production.yml build
docker compose -f docker-compose.yml -f compose.production.yml run --rm api alembic upgrade head
docker compose -f docker-compose.yml -f compose.production.yml up -d
docker compose -f docker-compose.yml -f compose.production.yml ps
curl -fsS http://localhost:8000/api/v1/admin/health/live
curl -fsS http://localhost:8000/api/v1/admin/health/ready
```

If `api` is no longer published to the host in production, run health checks through `web`:

```bash
curl -fsS http://localhost/api/v1/admin/health/live
curl -fsS http://localhost/api/v1/admin/health/ready
```

## Windows Server With WSL2 Deployment Notes

Use this only if the existing Windows EC2 server must remain the host.

Recommended WSL pattern:

- Install or use Ubuntu inside WSL2.
- Install Docker Engine inside Ubuntu WSL, not Docker Desktop.
- Clone the repo under the Linux filesystem, for example `/opt/querygateway`, not under `/mnt/c/...`.
- Keep Docker volumes in Linux storage.
- Configure the Windows host firewall to pass only required public ports.
- Configure EC2 security groups as usual.
- Use a Windows scheduled task or service wrapper to start WSL and Docker on boot.
- Document recovery steps after Windows updates or host restarts.
- Monitor that WSL and Docker are actually running after reboot.

WSL-specific risks:

- WSL is designed primarily for development workflows and has behavioral differences from a normal production VM.
- WSL's lightweight VM can start and stop automatically.
- WSL2 uses virtualized networking and can behave like a VM with its own IP.
- Windows path integration can cause unexpected behavior if app files live on mounted Windows drives.

For those reasons, WSL2 is acceptable as a controlled interim path, but not the preferred long-term production target.

## Project-Specific Production Gaps To Fix Before Go-Live

### 1. Create A Production Compose Override

Current state:

- `docker-compose.yml` is development-friendly and publishes `db:5432` and `api:8000`.
- `APP_ENV` is set to `development`.
- Postgres credentials are hardcoded as `db2api/db2api`.
- CORS is localhost-focused.

Required fix:

- Add `compose.production.yml`.
- Remove public `api` and `db` port publishing.
- Set `APP_ENV=production`.
- Set production `CORS_ORIGINS`.
- Use production secrets from environment or a secrets system.
- Add resource limits if the host is shared or small.
- Add logging driver configuration if CloudWatch is used.

Example shape:

```yaml
services:
  api:
    environment:
      APP_ENV: production
      DEBUG: "false"
      LOG_LEVEL: INFO
      CORS_ORIGINS: "https://querygateway.example.com"
      DATABASE_URL: "${DATABASE_URL?DATABASE_URL is required}"
      JWT_SECRET_KEY: "${JWT_SECRET_KEY?JWT_SECRET_KEY is required}"
      ENCRYPTION_KEY: "${ENCRYPTION_KEY?ENCRYPTION_KEY is required}"
      ADMIN_USERNAME: "${ADMIN_USERNAME?ADMIN_USERNAME is required}"
      ADMIN_PASSWORD_HASH: "${ADMIN_PASSWORD_HASH?ADMIN_PASSWORD_HASH is required}"
    ports: []

  web:
    ports:
      - "80:80"

  db:
    profiles:
      - local-db
    ports: []
```

If RDS is used, remove or profile-gate the `db` service so production does not start a local app database by accident.

### 2. Add An Explicit Migration Step

Current state:

- The docs correctly say migrations must be run.
- The Compose startup path does not automatically run `alembic upgrade head`.

Required fix:

- Add a documented deployment command or a dedicated one-shot migration service.
- Run migrations before starting the new API version.
- Never edit already-applied migrations.

Recommended command:

```bash
docker compose -f docker-compose.yml -f compose.production.yml run --rm api alembic upgrade head
```

### 3. Replace Development Database Credentials

Current state:

- `docker-compose.yml` includes:
  - `POSTGRES_DB=db2api`
  - `POSTGRES_USER=db2api`
  - `POSTGRES_PASSWORD=db2api`
  - `DATABASE_URL=postgresql+asyncpg://db2api:db2api@db:5432/db2api`

Required fix:

- Use unique production credentials.
- Prefer RDS PostgreSQL.
- If local Postgres remains, load credentials from `.env` or secrets and do not publish port `5432`.

### 4. Lock Down Public Ports

Current state:

- `web` publishes `80:80`.
- `api` publishes `8000:8000`.
- `db` publishes `5432:5432`.

Required fix:

- Publish only the frontend/reverse proxy port.
- Keep `api` and `db` private to the Docker network.
- Access backend health through `/api/*` on the reverse proxy.

Production target:

```text
Public:
  443 -> ALB or reverse proxy
  80  -> redirect to 443 only

Private:
  web -> api:8000
  api -> RDS or db:5432
```

### 5. Add HTTPS

Current state:

- `docker/nginx.conf` listens on port `80`.
- No TLS config is present in this repo.

Required fix:

- Terminate HTTPS at ALB with ACM, or add a host-level TLS reverse proxy.
- Redirect HTTP to HTTPS.
- Ensure `X-Forwarded-Proto` is passed to the API.
- Update `CORS_ORIGINS` to the final HTTPS domain.

### 6. Verify Authentication Policy For Data Endpoints

Current project rule:

- All data endpoints must require authentication.

Current README behavior:

- The README states that endpoints with no auth method attached are served publicly.

Required fix before go-live:

- Decide whether production must technically prevent public data endpoints.
- If yes, add an enforcement change before production: reject publishing active `/api/v1/data/*` endpoints without an auth method.
- At minimum, add an operational go-live checklist item to audit every endpoint and confirm an auth method is attached.

This is a production security gap because QueryGateway is designed to expose database-backed data routes to external consumers.

### 7. Production Admin Credential Procedure

Current state:

- The app uses a single seeded admin account from:
  - `ADMIN_USERNAME`
  - `ADMIN_PASSWORD_HASH`
- The hash must be bcrypt.

Required fix:

- Generate a strong admin password.
- Generate a bcrypt hash using the backend helper.
- Store only the hash in production secrets.
- Document the admin password rotation procedure.

Example hash generation:

```bash
cd backend
python -c "from app.auth.hashing import hash_password; print(hash_password('replace-with-strong-password'))"
```

### 8. Production Secret Generation And Storage

Required production commands:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Store outputs as:

- `JWT_SECRET_KEY`
- `ENCRYPTION_KEY`

Do not regenerate `ENCRYPTION_KEY` casually. Existing encrypted credentials depend on it.

### 9. Oracle Connectivity Validation

Current state:

- Oracle connectivity uses `python-oracledb`.
- Thin mode is default.
- `ORACLE_CLIENT_LIB_DIR` is only needed for thick mode.

Required fix:

- Confirm whether target Oracle connections work in thin mode.
- If thick mode is required, install Oracle Instant Client in the backend image or host/container path and set `ORACLE_CLIENT_LIB_DIR`.
- Test from the production network path, not only from a developer laptop.
- Validate firewall rules to Oracle listener ports.
- Set query timeouts and pool limits appropriate for Oracle capacity.

### 10. Uvicorn Worker And Scheduler Safety

Current state:

- Backend container command starts one Uvicorn worker:
  - `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- APScheduler is in-process.

Production consideration:

- Scaling API workers can accidentally create multiple in-process schedulers unless scheduler ownership is designed explicitly.
- Keep one API replica/worker until scheduler behavior is reviewed.
- If higher concurrency is required, separate scheduler execution from web serving or add leader-election/job-store controls.

Required go-live decision:

- For first production deployment, keep one `api` replica.
- Do not horizontally scale the `api` service until scheduler duplication risk is resolved.

### 11. CORS Must Match Final Domain

Current state:

- Compose sets:
  - `CORS_ORIGINS=http://localhost:5173,http://localhost:80`

Required fix:

- Set CORS to only production domains.

Example:

```env
CORS_ORIGINS=https://querygateway.example.com
```

Do not use wildcard CORS for production.

### 12. Logging And Retention

Current state:

- Backend logs are structured with `structlog`.
- No production log sink is configured in Compose.

Required fix:

- Ship container logs to CloudWatch Logs, OpenSearch, Datadog, or another central system.
- Define retention.
- Alert on health and error patterns.
- Ensure logs do not include secrets, tokens, or raw credentials.

### 13. Backup And Restore Must Be Proven

Current state:

- `docs/operations.md` includes backup and restore commands.

Required fix:

- Choose RDS automated backups or local `pg_dump` plus off-host storage.
- Run a restore test before go-live.
- Store `ENCRYPTION_KEY` backup securely.
- Document RPO and RTO.

### 14. Add A Production Runbook

Required runbook sections:

- Deploy new version.
- Run migrations.
- Roll back app version.
- Restore database.
- Rotate admin password.
- Rotate JWT signing key.
- Recover from lost `ENCRYPTION_KEY`.
- Check Oracle connectivity.
- Check scheduler failures.
- Check stale snapshots.
- Restart containers.
- Patch host OS and Docker Engine.

### 15. CI/CD And Image Promotion

Current state:

- GitHub Actions build/test workflows exist.
- Docker build workflow exists.

Required fix:

- Decide whether production pulls from source and builds on the server, or pulls signed/versioned images from a registry.
- Best practice is build once in CI and deploy the tested image tag.
- Use ECR or another private registry.
- Tag images with commit SHA and release version.
- Do not deploy mutable `latest` without traceability.

### 16. Host Hardening

Required fix:

- Restrict SSH/RDP to admin IPs or VPN.
- Disable password login for SSH if Linux is used.
- Use least-privilege IAM instance profile.
- Patch OS and Docker Engine.
- Enable EBS encryption.
- Monitor disk usage.
- Keep Docker daemon socket private.
- Do not mount the Docker socket into application containers.
- Use non-root app user where already supported by the backend Dockerfile.

### 17. Frontend Runtime Configuration

Current state:

- The frontend build is static and served by Nginx.
- API calls are proxied through `/api/*`.

Required fix:

- Confirm frontend does not embed localhost URLs in production builds.
- Keep same-origin `/api` calls when possible.
- Validate browser access through final HTTPS domain.

### 18. Health Check Consistency

Current state:

- API container healthcheck uses:
  - `curl -f http://localhost:8000/api/v1/admin/health/live`
- `web` depends on `api` health.

Required fix:

- Keep API healthcheck.
- Add external monitoring through the public route:
  - `https://querygateway.example.com/api/v1/admin/health/live`
  - `https://querygateway.example.com/api/v1/admin/health/ready`
- Ensure health endpoints do not leak sensitive state publicly. Keep detailed dashboard access protected if needed.

## Go-Live Checklist

Before production cutover:

- [ ] Linux EC2 target selected, or WSL2 interim decision documented.
- [ ] Public DNS name selected.
- [ ] Elastic IP or ALB selected.
- [ ] HTTPS configured.
- [ ] EC2 security group exposes only required ports.
- [ ] Windows Firewall configured if Windows host remains.
- [ ] `compose.production.yml` created.
- [ ] `api` port not public.
- [ ] `db` port not public.
- [ ] RDS PostgreSQL selected or local Postgres backup plan approved.
- [ ] Production database credentials created.
- [ ] `JWT_SECRET_KEY` generated and stored securely.
- [ ] `ENCRYPTION_KEY` generated, stored securely, and backed up.
- [ ] `ADMIN_PASSWORD_HASH` generated with bcrypt.
- [ ] `APP_ENV=production`.
- [ ] `DEBUG=false`.
- [ ] `CORS_ORIGINS` set to final HTTPS origin.
- [ ] Alembic migration command included in deployment process.
- [ ] `alembic upgrade head` run successfully.
- [ ] Admin login tested.
- [ ] Oracle connection tested from production host/network.
- [ ] One protected `/api/v1/data/*` endpoint tested.
- [ ] No public data endpoint exists unless explicitly approved.
- [ ] Structured logs are flowing to central logging.
- [ ] Health checks monitored.
- [ ] Backup job configured.
- [ ] Restore tested.
- [ ] Rollback procedure tested.
- [ ] No secrets committed.

## Suggested First Production Path

For the first stable production release, use this sequence:

1. Provision Ubuntu EC2.
2. Attach Elastic IP or put the instance behind an ALB.
3. Install Docker Engine and Compose plugin.
4. Create production secrets in AWS Secrets Manager or SSM Parameter Store.
5. Create RDS PostgreSQL 16.
6. Create `compose.production.yml`.
7. Build and deploy containers.
8. Run Alembic migrations.
9. Bring up the stack.
10. Configure HTTPS.
11. Restrict security groups.
12. Configure CloudWatch logs and metrics.
13. Configure backups.
14. Run the full go-live checklist.

## References

- QueryGateway repo files:
  - `README.md`
  - `docker-compose.yml`
  - `docker/Dockerfile.backend`
  - `docker/Dockerfile.frontend`
  - `docker/nginx.conf`
  - `docs/deployment.md`
  - `docs/operations.md`
  - `backend/app/config.py`
- Docker Desktop Windows support: https://docs.docker.com/desktop/setup/install/windows-install/
- Docker Compose production guidance: https://docs.docker.com/compose/how-tos/production/
- Microsoft WSL production notes: https://learn.microsoft.com/en-us/windows/wsl/faq
- AWS EC2 security groups: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-security-groups.html
- AWS Elastic IP addresses: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/elastic-ip-addresses-eip.html
- Amazon RDS automated backups: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.html
- AWS Secrets Manager: https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html
- Docker CloudWatch logging driver: https://docs.docker.com/engine/logging/drivers/awslogs/
