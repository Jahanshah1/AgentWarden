# Releasing AgentWarden

This repository publishes two separate things:

- The `agentwarden-ai` Python package on PyPI. It includes the proxy, CLI, and
  bundled local dashboard.
- The public `site/` Next.js project on Vercel. It is a marketing and
  documentation site; it does not host anyone's local proxy or traces.

## One-time PyPI setup

1. Confirm that `agentwarden-ai` is available as a PyPI project name.
2. On PyPI, add a Trusted Publisher for GitHub Actions:
   - Owner: `Jahanshah1`
   - Repository: `AgentWarden`
   - Workflow: `publish.yml`
   - Environment: `pypi`
3. In GitHub, create an environment named `pypi`. Add manual approval if you
   want a confirmation step before public releases.

Trusted Publishing is preferred because GitHub exchanges a short-lived OIDC
credential with PyPI. Do not add a long-lived PyPI token to the repository.

## Test a release locally

From the repository root:

```bash
cd dashboard
npm ci
npm run package
cd ..

.venv/bin/pip install --upgrade build twine
.venv/bin/python -m build
.venv/bin/python -m twine check dist/*
```

The build creates a wheel and a source distribution in `dist/`. Verify the
wheel contains `proxy/dashboard_static` before publishing.

## TestPyPI first

Create a TestPyPI API token, then upload only the new version:

```bash
.venv/bin/python -m twine upload --repository testpypi dist/*
```

In a clean virtual environment, install from TestPyPI and confirm the CLI:

```bash
python3.11 -m venv /tmp/agentwarden-release-check
/tmp/agentwarden-release-check/bin/pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ agentwarden-ai
/tmp/agentwarden-release-check/bin/agentwarden --help
```

Each PyPI version is immutable. Bump `version` in `pyproject.toml` before each
new TestPyPI or PyPI upload.

## Publish to PyPI

Preferred: create and publish a GitHub Release after the release tag is pushed.
The `.github/workflows/publish.yml` workflow builds, checks, and publishes via
the Trusted Publisher configuration.

For the first release only, a manual upload with a project-scoped PyPI API token
is acceptable:

```bash
.venv/bin/python -m twine upload dist/*
```

When prompted, use `__token__` as the username and paste the PyPI token as the
password. Never paste the token into source code, a shell history file, or a
GitHub secret once Trusted Publishing is configured.

## Deploy the public site to Vercel

Import this GitHub repository in Vercel and set the Root Directory to `site`.
Vercel detects Next.js automatically. Use `npm run build` as the build command.
The resulting deployment hosts the public homepage only.

The proxy and dashboard must remain local: a hosted Vercel function cannot sit
between a developer's localhost agent and OpenAI, nor should it receive their
API key or local SQLite trace database.
