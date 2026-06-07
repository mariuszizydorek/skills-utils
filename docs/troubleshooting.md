# Troubleshooting

This guide covers common `skills-sync` failures, with extra focus on private GitHub repositories.

Prefer a styled view? Open [`troubleshooting.html`](./troubleshooting.html).
Browse all docs from [`index.html`](./index.html).

## Quick health check

Start here:

```bash
skills-sync doctor
```

If you use the Node package command name, run:

```bash
skills-sync-node doctor
```

## Private repository access failures

If sync fails for a private repo, use this sequence.

### 1) Confirm account access

Check that your user/token can read the repository:

```bash
gh api repos/<owner>/<repo>
```

If this fails with 404/403, request repo access first.

### 2) Confirm GitHub auth on your machine

```bash
gh auth status
```

If not authenticated:

```bash
gh auth login
```

### 3) Use explicit token auth (recommended in CI)

```bash
export GITHUB_TOKEN=ghp_xxx
skills-sync --token "$GITHUB_TOKEN"
```

### 4) Know auth resolution order

`skills-sync` resolves auth in this order:

1. `--token`
2. `GITHUB_TOKEN` or `GH_TOKEN`
3. `gh auth token`

### 5) Token permission notes

- Fine-grained PATs need read access to the target repository.
- Classic PATs should include repo read scope for private repositories.

## Common symptoms and fixes

### "No GitHub auth detected"

Fix one of:

- run `gh auth login`
- export `GITHUB_TOKEN`
- pass `--token` explicitly

### "GitHub API unreachable"

Check network and GitHub status, then retry:

```bash
curl -I https://api.github.com
```

### Repo listed in config but "unreachable"

- Verify `owner/repo` is correct in config.
- Confirm default branch exists and repo is not archived or renamed.
- Re-run `skills-sync doctor` after fixing auth or config.
