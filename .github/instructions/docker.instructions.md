# Docker Instructions

## Do
- Keep Docker assets in `docker/` and `docker-compose.yml`.
- Ensure compose supports `api`, `web`, `db` services.
- Keep optional local Oracle service/profile isolated and documented.
- Use deterministic base image tags.
- Ensure backend and frontend images build in CI.

## Do Not
- Do not embed secrets in Dockerfiles or compose files.
- Do not couple local-only overrides into default production paths.
- Do not skip healthcheck/readiness wiring for service dependencies.

## Validation Commands
- `docker compose build`
- `docker compose up -d`
- `docker compose ps`
- `docker compose logs --tail=200 api`
- `docker compose logs --tail=200 web`
- `docker compose logs --tail=200 db`

## Runtime Expectations
- Backend starts only after DB readiness.
- Migrations are documented and run deterministically.
- Config comes from environment variables compatible with Pydantic Settings.

## Stop Conditions
- If container startup order fails, inspect healthchecks and dependency config before changing app code.
- If migration startup behavior is unclear, inspect migration entrypoint scripts and CI workflow.
