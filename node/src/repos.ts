import { mkdir, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { cacheDir } from "./config.js";
import { GitHubClient } from "./github.js";
import { remoteFingerprint } from "./hash.js";
import type { SyncProgressReporter } from "./progress.js";
import { parseGithubRepo } from "./repoParse.js";

export interface RepoConfig {
  slug: string;
  owner: string;
  repo: string;
  branch: string;
  skillsPath: string;
}

export interface RemoteSkill {
  name: string;
  remotePath: string;
  fingerprint: string;
  files: Record<string, string>;
}

export function repoFromConfig(slug: string, data: any): RepoConfig {
  const [owner, repoName] = parseGithubRepo(data.owner, data.repo);
  return {
    slug,
    owner,
    repo: repoName,
    branch: data.branch ?? "main",
    skillsPath: data.skills_path ?? "skills",
  };
}

export function repoCacheDir(repo: RepoConfig): string {
  return path.join(cacheDir(), repo.slug);
}

function parseSkillTrees(tree: any[], skillsPath: string): Record<string, Record<string, string>> {
  const prefix = `${skillsPath.replace(/\/$/, "")}/`;
  const skills: Record<string, Record<string, string>> = {};
  for (const item of tree) {
    if (item.type !== "blob") continue;
    const itemPath = item.path as string;
    if (!itemPath.startsWith(prefix)) continue;
    const remainder = itemPath.slice(prefix.length);
    const slash = remainder.indexOf("/");
    if (slash === -1) continue;
    const skillName = remainder.slice(0, slash);
    const relPath = remainder.slice(slash + 1);
    skills[skillName] ??= {};
    skills[skillName][relPath] = item.sha;
  }
  return skills;
}

export async function fetchRemoteInventory(
  client: GitHubClient,
  repo: RepoConfig,
): Promise<[string, Record<string, RemoteSkill>]> {
  const commitSha = await client.resolveCommitSha(repo.owner, repo.repo, repo.branch);
  const tree = await client.fetchTree(repo.owner, repo.repo, repo.branch);
  const bySkill = parseSkillTrees(tree, repo.skillsPath);
  const inventory: Record<string, RemoteSkill> = {};
  for (const [name, files] of Object.entries(bySkill).sort()) {
    if (!files["SKILL.md"]) continue;
    inventory[name] = {
      name,
      remotePath: `${repo.skillsPath}/${name}`,
      fingerprint: remoteFingerprint(files),
      files,
    };
  }
  return [commitSha, inventory];
}

export async function downloadSkillFiles(
  client: GitHubClient,
  repo: RepoConfig,
  skill: RemoteSkill,
  dest: string,
  progress?: SyncProgressReporter,
): Promise<void> {
  await rm(dest, { recursive: true, force: true });
  await mkdir(dest, { recursive: true });
  const files = Object.entries(skill.files).sort(([a], [b]) => a.localeCompare(b));
  for (let index = 0; index < files.length; index += 1) {
    const [relPath, blobSha] = files[index];
    progress?.downloading(skill.name, relPath, index + 1, files.length);
    const content = await client.downloadBlob(repo.owner, repo.repo, blobSha);
    const target = path.join(dest, relPath);
    await mkdir(path.dirname(target), { recursive: true });
    await writeFile(target, content);
  }
}
