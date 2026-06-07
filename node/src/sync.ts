import { access, cp, mkdir, rm, symlink } from "node:fs/promises";
import path from "node:path";
import { utcNowIso } from "./config.js";
import { dirHash } from "./hash.js";
import type { GitHubClient } from "./github.js";
import type { SyncProgressReporter } from "./progress.js";
import { downloadSkillFiles, repoCacheDir, type RemoteSkill, type RepoConfig } from "./repos.js";
import { installKey, nestedInstallPath } from "./scanner.js";

export interface SyncResult {
  installed: string[];
  removed: string[];
  updated: string[];
}

export async function applySync(
  client: GitHubClient,
  repo: RepoConfig,
  agentId: string,
  manifest: any,
  remoteInventory: Record<string, RemoteSkill>,
  commitSha: string,
  selected: Set<string>,
  toUpdate: Set<string>,
  flatSymlinks: boolean,
  skillsDir: string,
  progress?: SyncProgressReporter,
): Promise<SyncResult> {
  const result: SyncResult = { installed: [], removed: [], updated: [] };
  await mkdir(skillsDir, { recursive: true });

  const existing: string[] = [];
  for (const name of Object.keys(remoteInventory)) {
    try {
      await access(path.join(nestedInstallPath(skillsDir, repo.slug, name), "SKILL.md"));
      existing.push(name);
    } catch {
      // not installed
    }
  }

  const toRemove = existing.filter((n) => !selected.has(n)).sort();
  const toApply: Array<[string, RemoteSkill]> = [];

  for (const name of [...selected].sort()) {
    const remote = remoteInventory[name];
    const installPath = nestedInstallPath(skillsDir, repo.slug, name);
    let wasInstalled = false;
    try {
      await access(path.join(installPath, "SKILL.md"));
      wasInstalled = true;
    } catch {
      wasInstalled = false;
    }
    const key = installKey(repo.slug, name);
    const entry = manifest.agents?.[agentId]?.[key];
    const needsCopy =
      !wasInstalled || toUpdate.has(name) || !entry || entry.remote_fingerprint !== remote.fingerprint;
    if (needsCopy) {
      toApply.push([name, remote]);
    } else if (flatSymlinks) {
      await ensureFlatSymlink(skillsDir, repo.slug, name);
    }
  }

  progress?.begin(toRemove.length + toApply.length);

  for (let index = 0; index < toRemove.length; index += 1) {
    const name = toRemove[index];
    progress?.removing(name, index + 1, toRemove.length);
    await removeSkill(skillsDir, repo.slug, name, agentId, manifest);
    result.removed.push(name);
  }

  for (const [name, remote] of toApply) {
    const installPath = nestedInstallPath(skillsDir, repo.slug, name);
    let wasInstalled = false;
    try {
      await access(path.join(installPath, "SKILL.md"));
      wasInstalled = true;
    } catch {
      wasInstalled = false;
    }

    const cacheSkillDir = path.join(repoCacheDir(repo), repo.skillsPath, name);
    await downloadSkillFiles(client, repo, remote, cacheSkillDir, progress);
    progress?.installing(name);
    await rm(installPath, { recursive: true, force: true });
    await cp(cacheSkillDir, installPath, { recursive: true });

    if (!wasInstalled) result.installed.push(name);
    else result.updated.push(name);

    manifest.agents ??= {};
    manifest.agents[agentId] ??= {};
    manifest.agents[agentId][installKey(repo.slug, name)] = {
      repo_slug: repo.slug,
      remote_path: remote.remotePath,
      commit_sha: commitSha,
      remote_fingerprint: remote.fingerprint,
      installed_hash: await dirHash(installPath),
      installed_at: utcNowIso(),
    };
    if (flatSymlinks) {
      progress?.linking(name);
      await ensureFlatSymlink(skillsDir, repo.slug, name);
    }
  }

  return result;
}

async function removeSkill(
  skillsDir: string,
  repoSlug: string,
  skillName: string,
  agentId: string,
  manifest: any,
): Promise<void> {
  const installPath = nestedInstallPath(skillsDir, repoSlug, skillName);
  await rm(installPath, { recursive: true, force: true });
  const link = path.join(skillsDir, skillName);
  await rm(link, { force: true });
  const key = installKey(repoSlug, skillName);
  delete manifest.agents?.[agentId]?.[key];
}

async function ensureFlatSymlink(
  skillsDir: string,
  repoSlug: string,
  skillName: string,
): Promise<void> {
  const link = path.join(skillsDir, skillName);
  const target = path.join(repoSlug, skillName);
  try {
    const { lstat } = await import("node:fs/promises");
    const info = await lstat(link);
    if (info.isSymbolicLink()) return;
    if (info.isDirectory() || info.isFile()) return;
  } catch {
    // create symlink
  }
  await rm(link, { force: true });
  await symlink(target, link);
}
