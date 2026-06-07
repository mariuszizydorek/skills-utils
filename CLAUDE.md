# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

`skills-utils` ships two parallel implementations — **Python** (`python/`, published to PyPI as `skills-utils-mi`) and **Node/TypeScript** (`node/`, published to npm as `skills-sync-node-mi`) — of the same interactive CLI. The CLI fetches agent skills from GitHub repos via the API and installs them into Cursor / Claude Code / Copilot skill directories.

**The two implementations must behave identically.** Manifest format and hash algorithms are specified in `docs/manifest-schema.md` and verified by tests in both runtimes. When changing behavior in one, mirror the change in the other.

## Commands

### Python (run from `python/`)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]" --index-url https://pypi.org/simple/   # explicit index — avoid corp mirrors
pytest -v                                                       # all tests
pytest -v -m "not integration"                                  # skip tests that hit GitHub API (CI default)
pytest tests/test_hash.py::test_name -v                         # single test
skills-sync doctor                                              # run CLI from venv
```

### Node (run from `node/`)

```bash
npm install
npm run build                       # tsc + copies bundled_config.yaml into dist/
npm test                            # node --test tests/*.test.js (requires build first)
npm link                            # exposes skills-sync-node globally for dev
node --test tests/hash.test.js      # single test file
```

### Release

The **tag is the source of truth** for version. `python/pyproject.toml` and `node/package.json` are patched in-flight by the publish workflow from the release tag (`vX.Y.Z` → `X.Y.Z`); the values committed in `main` are only the *previous* shipped version.

```bash
./scripts/bump-version.sh 0.2.0     # updates both manifests in lockstep (for local builds)
./scripts/publish.sh                # builds both packages locally; prints upload commands

# Normal release flow — workflow handles versioning, no need to commit a bump:
git tag v0.2.0 && git push origin v0.2.0
gh release create v0.2.0 --generate-notes
```

Publishing is automated via `.github/workflows/publish.yml` on GitHub Release:
- `resolve-version` job derives `X.Y.Z` from the release tag (or `workflow_dispatch` input) and validates semver.
- `publish-python` patches `pyproject.toml`, builds, publishes to PyPI via trusted publishing (OIDC, `environment: pypi`). **Verified working.**
- `publish-node` patches `package.json` via `npm version --no-git-tag-version`, builds, publishes to npm via trusted publishing with `--provenance`. The workflow `unset`s `NPM_TOKEN`/`NODE_AUTH_TOKEN` before publishing — don't reintroduce token auth without reading the README's publishing notes.

**npm trusted-publisher gotcha**: as of last failed run, the npm OIDC handshake returned `ENEEDAUTH`, which means trusted publisher is misconfigured on npmjs.com. Verify under package settings for `skills-sync-node-mi`: provider=`GitHub Actions`, owner=`mariuszizydorek`, repository=`skills-utils`, workflow=`publish.yml` (filename, not display name), environment left blank. PyPI requires `environment: pypi`; npm trusted publishing does **not** use the environment field.

## Architecture

Both implementations share the same module layout (Python `snake_case` ↔ Node `camelCase`):

| Module | Responsibility |
|--------|----------------|
| `cli` | argparse/argv dispatch → `sync` (interactive, default) / `status` / `doctor` |
| `config_loader` / `config` | Resolves `~/.skills-utils/config.yaml` (copies `bundled_config.yaml` on first run), loads/saves `manifest.json` |
| `github` | Thin GitHub REST client; auth from `--token`, `GITHUB_TOKEN`, or `gh auth token` |
| `repos` | Fetches commit SHA + tree, builds `RemoteSkill` inventory, downloads files into `cache/` |
| `repo_parse` / `repoParse` | Parses `owner/repo`, URLs, and derives default slugs |
| `agents` | Resolves per-agent install dirs (user `~/.claude/skills` vs project `.claude/skills`); project-scoped agents resolve relative to CWD/git root |
| `scanner` | Walks installed skills, computes `installed_hash`, compares with manifest + remote fingerprint to assign status (`synced`/`outdated`/`modified`/`diverged`/`missing`) |
| `hash` | Deterministic directory hashing — **algorithm is part of the spec**, see `docs/manifest-schema.md` |
| `sync` | Applies install/remove/update plan; writes nested `<skills_dir>/<repo_slug>/<skill>/` and flat symlinks `<skills_dir>/<skill> → <repo_slug>/<skill>` when `flat_symlinks: true` |
| `ui` | InquirerPy (Python) / `@inquirer/prompts` (Node) interactive selection |
| `doctor` | Health checks; `--fix` repairs symlinks / creates missing dirs |
| `status_cmd` / `status` | Non-interactive listing; `--check-remote` re-fetches and diffs |
| `progress` | Spinner/progress reporter wrapper around `rich` (Python) / `ora` (Node) |

### State on disk

- `~/.skills-utils/config.yaml` — user config (created from `bundled_config.yaml` on first run)
- `~/.skills-utils/manifest.json` — installed-skill tracking, version `MANIFEST_VERSION = 1`
- `~/.skills-utils/cache/` — downloaded skill files

The bundled defaults live in `<package>/bundled_config.yaml` in **both** runtimes (Python `src/skills_utils/`, Node `src/`). The Node build copies it into `dist/`. Keep these in sync with the root `config.yaml` template.

### Manifest / hash contract

Critical: `installed_hash` and `remote_fingerprint` must compute identically across Python and Node. The algorithm (file walk, skip rules, JSON serialization, SHA-256) is documented in `docs/manifest-schema.md` and pinned by `test_hash.py` / `hash.test.js`. Do not change one side without updating the spec and the other implementation.

### Interactive sync flow

`cli.run_interactive` (Python) / `runInteractive` (Node):
1. Select agent → resolve target skills dir
2. Select repo from config (or add new one, persisted back to `config.yaml`)
3. Fetch remote inventory → `buildSkillStates` joins remote + local + manifest
4. User ticks skills → diff against currently-installed yields `install` / `remove` / `update` lists
5. Confirm → `applySync` downloads, writes, and updates manifest

## Conventions

- Both packages use the unscoped `-mi` suffix (`skills-utils-mi`, `skills-sync-node-mi`) to avoid name collisions on the public registries. The Python CLI binary is `skills-sync`; the Node binary is `skills-sync-node` so both can coexist on `PATH`.
- Python targets 3.10+; Node targets >=18 with `"type": "module"` (ESM, `.js` import extensions required in TS source).
- Tests marked `@pytest.mark.integration` hit the live GitHub API and are excluded from CI (`-m "not integration"`).
- The README is the source of truth for user-facing docs and is referenced by `pyproject.toml` (`readme = "../README.md"`) — don't move it without updating the build config.
