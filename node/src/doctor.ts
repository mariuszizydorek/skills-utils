import { access, constants, lstat, mkdir } from "node:fs/promises";
import path from "node:path";
import { loadConfig, loadManifest, resolveConfigPath } from "./config.js";
import { GitHubClient } from "./github.js";
import { listAgents, resolveSkillsDir } from "./agents.js";
import { repoFromConfig } from "./repos.js";
import { nestedInstallPath } from "./scanner.js";
import { ensureFlatSymlink } from "./doctor-fix.js";

interface CheckResult {
  level: "ok" | "warn" | "error";
  message: string;
}

export async function runDoctor(args: any): Promise<number> {
  const config = await loadConfig(args.config);
  const manifest = await loadManifest();
  const results: CheckResult[] = [];
  const configPath = await resolveConfigPath(args.config);
  results.push({ level: "ok", message: `config.yaml found (${configPath})` });

  const skillCount = Object.values(manifest.agents ?? {}).reduce(
    (sum: number, entries: any) => sum + Object.keys(entries).length,
    0,
  );
  results.push({ level: "ok", message: `manifest.json valid (${skillCount} skills tracked)` });

  const token = args.token ?? (await GitHubClient.detectToken());
  if (token) results.push({ level: "ok", message: "GitHub token available" });
  else
    results.push({
      level: "warn",
      message:
        "No GitHub auth detected - set GITHUB_TOKEN/GH_TOKEN, pass --token, or run gh auth login (public repos OK)",
    });

  const client = new GitHubClient(token);
  if (await client.ping()) results.push({ level: "ok", message: "GitHub API reachable" });
  else results.push({ level: "error", message: "GitHub API unreachable" });

  for (const [slug, data] of Object.entries(config.repos ?? {})) {
    const repo = repoFromConfig(slug, data);
    try {
      const dirs = await client.listSkillDirs(repo.owner, repo.repo, repo.skillsPath);
      results.push({ level: "ok", message: `${repo.owner}/${repo.repo} reachable (${dirs.length} skill folders)` });
    } catch (error: any) {
      results.push({ level: "error", message: `${repo.owner}/${repo.repo} unreachable: ${error.message}` });
    }
  }

  let agents = listAgents(config);
  if (args.agent) agents = agents.filter(([id]) => id === args.agent);

  for (const [agentId, agent] of agents) {
    const skillsDir = await resolveSkillsDir(agent);
    try {
      await access(skillsDir, constants.W_OK);
      results.push({ level: "ok", message: `${skillsDir} writable` });
    } catch {
      try {
        await access(skillsDir);
        results.push({ level: "error", message: `${skillsDir} not writable` });
      } catch {
        results.push({ level: "warn", message: `${skillsDir} missing (creatable)` });
        if (args.fix) {
          await mkdir(skillsDir, { recursive: true });
          results.push({ level: "ok", message: `Created ${skillsDir}` });
        }
      }
    }

    for (const [key, entry] of Object.entries<any>(manifest.agents?.[agentId] ?? {})) {
      const repoSlug = entry.repo_slug ?? key.split("/")[0];
      const skillName = key.split("/").slice(1).join("/");
      const installPath = nestedInstallPath(skillsDir, repoSlug, skillName);
      try {
        await access(path.join(installPath, "SKILL.md"));
      } catch {
        results.push({ level: "warn", message: `Orphan manifest entry: ${agentId}/${key}` });
        continue;
      }
      const link = path.join(skillsDir, skillName);
      try {
        const info = await lstat(link);
        if (info.isSymbolicLink()) {
          try {
            await access(link);
            results.push({ level: "ok", message: `Symlink valid: ${skillName}` });
          } catch {
            results.push({ level: "error", message: `Broken symlink: ${link}` });
            if (args.fix) {
              const { rm, symlink } = await import("node:fs/promises");
              await rm(link, { force: true });
              await symlink(path.join(repoSlug, skillName), link);
              results.push({ level: "ok", message: `Repaired symlink: ${skillName}` });
            }
          }
        }
      } catch {
        if (args.fix && config.defaults?.flat_symlinks !== false) {
          await ensureFlatSymlink(skillsDir, repoSlug, skillName);
          results.push({ level: "ok", message: `Created symlink: ${skillName}` });
        }
      }
    }
  }

  console.log("\nskills-sync doctor\n");
  let errors = 0;
  let warnings = 0;
  for (const item of results) {
    const icon = item.level === "ok" ? "✓" : item.level === "warn" ? "⚠" : "✗";
    console.log(`  ${icon}  ${item.message}`);
    if (item.level === "warn") warnings += 1;
    if (item.level === "error") errors += 1;
  }
  console.log("");
  if (errors) {
    console.log(`${warnings} warnings, ${errors} errors`);
    return 2;
  }
  if (warnings) {
    console.log(`${warnings} warnings`);
    return 1;
  }
  console.log("All checks passed");
  return 0;
}
