# Repository Governance & Supply-Chain Enforcement

This runbook documents the repository-level controls that make the in-repo
supply-chain enforcement (`SECURITY.md` §4.9) **binding**. Code and CI can
declare the gates, but only branch protection and a few repo settings force
them to actually block a merge. These steps require **repository admin** and
cannot be set from code — apply them in the GitHub UI (or via the REST API)
and keep this document in sync.

## 1. Required status checks on `main`

Settings → Branches → Branch protection rule for `main`:

- **Require a pull request before merging** — no direct pushes to `main`.
- **Require approvals**: at least 1.
- **Require review from Code Owners** — pairs with `.github/CODEOWNERS` so a
  change to a dependency manifest, lockfile, workflow, or enforcement script
  needs the owner's review.
- **Require status checks to pass before merging**, and **Require branches to
  be up to date**.
- **Do not allow bypassing the above settings** — the checks must be
  **non-bypassable**, including for admins (§4.9). Without this, the gates are
  advisory.
- **Require signed commits** — preferred (§4.9 verified/signed commits).
- **Require linear history** — optional, recommended.

> ⚠️ **Which checks to mark required — read this first.** The backend, frontend,
> docker, and actions-lint workflows are **path-filtered**: a PR that touches
> only `frontend/**` never starts the backend job, and GitHub leaves a required
> check that *did not run* in the **pending** state forever — which **blocks the
> merge**. Do **not** naively mark all five job names required, or unrelated PRs
> will deadlock. Pick one of:
>
> - **`Review dependency changes`** is the only workflow with no `paths:`
>   filter, so it runs on every PR and is always safe to require as-is.
> - To require the per-area gates too, first make their workflows run on every
>   PR by **removing the `paths:` filters** from `backend.yml`, `frontend.yml`,
>   `docker.yml`, and `actions-lint.yml` (acceptable for this security-critical
>   repo — every gate then runs on every PR). Only then mark these required:
>   `Lint, Type-check & Test`, `Lint, Format-check & Test`, `Build, Scan & SBOM`,
>   `Verify Actions are SHA-pinned`.
> - Or add a single aggregator job (`needs:` all gates, `if: always()`) in one
>   always-triggered workflow and require only that aggregated check.

## 2. Repository prerequisites

- **Dependency graph**: Settings → Code security → enable **Dependency graph**.
  `Review dependency changes` (dependency-review-action) needs it; without it
  the check errors instead of passing.
- **Dependabot**: `.github/dependabot.yml` is committed (pip, npm, docker,
  github-actions, weekly). Enable **Dependabot alerts** and **security
  updates** under Code security so advisories surface even between scheduled
  runs.
- **Secret scanning + push protection**: enable under Code security.

## 3. Currency SLA (§4.9, §4.4)

Vulnerability currency is enforced both at PR time and on a schedule:

| Surface | Gate | Trigger |
|---|---|---|
| Python deps | `pip-audit --require-hashes` | every backend PR + weekly |
| Frontend deps | `npm audit --audit-level=high` | every frontend PR + weekly |
| Whole tree | `osv-scanner` (recursive) | weekly + manual |
| New deps in a PR | `dependency-review` (fail on high+) | every PR |
| Container images | Trivy (fail on CRITICAL, fixable) | every docker PR + push |

**Remediation window:**

- A **CISA KEV-listed** vulnerability, or any **critical** CVE, must be
  remediated **before merge** — the relevant gate fails the build, so an
  affected PR cannot pass once branch protection requires the checks.
- For code already on `main`, the **weekly scheduled scan**
  (`.github/workflows/security-scan.yml`) re-checks dormant branches. A
  KEV/critical finding must be remediated within **7 days** (open a fix PR;
  the same gates verify it). High-severity findings: **30 days**.
- Remediation means upgrading to a fixed version (Dependabot raises the PR) —
  **never** pinning to a known-vulnerable version or suppressing the gate
  (`SECURITY.md` §4.12). For Python, regenerate the hashed lockfile after a
  bump:
  `uv pip compile backend/requirements.txt --generate-hashes -o backend/requirements.lock`.

## 4. Applying via API (optional)

If applying with the REST API instead of the UI, the branch-protection call is
roughly the following. The `checks` list below only includes the
always-running `Review dependency changes`; add the path-filtered job contexts
**only after** removing their `paths:` filters (see the §1 warning), otherwise
they will keep PRs pending.

```
PUT /repos/{owner}/{repo}/branches/main/protection
{
  "required_status_checks": {
    "strict": true,
    "checks": [
      {"context": "Review dependency changes"}
      // After de-path-filtering the workflows, also add:
      // {"context": "Lint, Type-check & Test"},
      // {"context": "Lint, Format-check & Test"},
      // {"context": "Build, Scan & SBOM"},
      // {"context": "Verify Actions are SHA-pinned"}
    ]
  },
  "required_pull_request_reviews": {"require_code_owner_reviews": true, "required_approving_review_count": 1},
  "enforce_admins": true,
  "restrictions": null
}
```

Confirm afterwards that direct pushes are rejected and that a PR cannot merge
with a failing or pending required check.
