# skills-utils

Sync agent skills from GitHub repos into Cursor, Claude Code, or Copilot — no git clone required.

## What it is for

Agent skills are folders with a `SKILL.md` file. Repos like [`anthropics/skills`](https://github.com/anthropics/skills) publish official skills, but agents have no built-in install/update flow.

**skills-sync** is an interactive CLI that:

- Lists skills from GitHub via API
- Installs selected skills into the correct agent directory
- Detects local edits vs upstream changes
- Supports multiple repos and agents
- Ships in **Python** and **Node** (shared config + manifest)

## Install (pick one runtime)

### Python (PyPI)

```bash
pip install skills-utils-mi
skills-sync doctor
```

### Node (npm)

```bash
npm install -g skills-sync-node-mi
skills-sync-node doctor
```

> Python registers `skills-sync`; Node registers `skills-sync-node` to avoid PATH collisions when both are installed.

### From source (development)

```bash
# Python
git clone git@github.com:mariuszizydorek/skills-utils.git
cd skills-utils/python
python3 -m venv .venv && source .venv/bin/activate
pip install -e . --index-url https://pypi.org/simple/
skills-sync doctor

# Node
cd skills-utils/node
npm install && npm run build && npm link
skills-sync-node doctor
```

## Usage

After install, run from **any folder**:

```bash
skills-sync                  # interactive: pick agent → repo → tick skills
skills-sync status           # show installed skills
skills-sync doctor           # health check
skills-sync doctor --fix     # repair symlinks / create missing dirs
```

### Common workflows

| Goal | Command |
|------|---------|
| First-time setup | `skills-sync` → pick Cursor → `anthropics/skills` → tick skills |
| Check what's installed | `skills-sync status` |
| Check for upstream updates | `skills-sync status --check-remote` |
| Fix broken setup | `skills-sync doctor --fix` |

## Where data lives

```
~/.skills-utils/
├── config.yaml       # repos + agent paths (created on first run)
├── manifest.json     # installed skills tracking
└── cache/            # downloaded skill files
```

Skills install to agent dirs:

| Agent | Install path |
|-------|----------------|
| Cursor (personal) | `~/.cursor/skills/<repo>/<skill>/` |
| Cursor (project) | `<project>/.cursor/skills/<repo>/<skill>/` |
| Claude Code (personal) | `~/.claude/skills/<repo>/<skill>/` |
| Claude Code (project) | `<project>/.claude/skills/<repo>/<skill>/` |
| Copilot (project) | `<project>/.github/skills/<repo>/<skill>/` |

Run project-scoped agents **from inside the project** (or its git root).

Flat symlinks (`~/.cursor/skills/pdf` → `anthropics/pdf`) are created by default so agents can discover skills.

## Configuration

Edit `~/.skills-utils/config.yaml` or the template [`config.yaml`](config.yaml). Override with `--config` or `SKILLS_UTILS_CONFIG`.

For private repos, use `gh auth login` or set `GITHUB_TOKEN`.

## Development

```bash
# Python tests
cd python && .venv/bin/pytest -v

# Node tests
cd node && npm run build && npm test

# Build release artifacts
./scripts/publish.sh
```

### Publishing (maintainers)

**PyPI** package: `skills-utils-mi`  
**npm** package: `skills-sync-node-mi`

One-time setup:

1. Create a [PyPI API token](https://pypi.org/manage/account/token/) with upload scope for `skills-utils-mi`
2. Create an [npm access token](https://www.npmjs.com/settings/~youruser/tokens) with publish scope
3. For GitHub Actions (recommended): add repo secrets `NPM_TOKEN` and enable [PyPI trusted publishing](https://docs.pypi.org/trusted-publishers/) for this repo

Manual publish:

```bash
./scripts/publish.sh

# PyPI (use __token__ as username, API token as password)
cd python
twine upload dist/skills_utils_mi-*

# npm
cd node
npm login
npm publish --access public
```

Or create a GitHub Release — the publish workflow uploads both packages automatically.

See [`plans/skills-sync-cli/plan.md`](plans/skills-sync-cli/plan.md) for the full design.
