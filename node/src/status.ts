import { loadConfig, loadManifest } from "./config.js";
import { GitHubClient } from "./github.js";
import { dirHash } from "./hash.js";
import { listAgents, resolveSkillsDir } from "./agents.js";
import { fetchRemoteInventory, repoFromConfig } from "./repos.js";
import { computeStatus, installKey, nestedInstallPath } from "./scanner.js";

export interface StatusRow {
  agentId: string;
  repoSlug: string;
  skill: string;
  status: string;
  installedAt: string;
}

export async function collectStatusRows(options: {
  configPath?: string;
  token?: string;
  agent?: string;
  repo?: string;
  checkRemote?: boolean;
}): Promise<StatusRow[]> {
  const config = await loadConfig(options.configPath);
  const manifest = await loadManifest();
  const rows: StatusRow[] = [];
  const client = new GitHubClient(options.token ?? (await GitHubClient.detectToken()));
  const remoteByRepo: Record<string, Record<string, any>> = {};

  if (options.checkRemote) {
    for (const [slug, data] of Object.entries(config.repos ?? {})) {
      if (options.repo && slug !== options.repo) continue;
      const repo = repoFromConfig(slug, data);
      const [, inventory] = await fetchRemoteInventory(client, repo);
      remoteByRepo[slug] = inventory;
    }
  }

  for (const [agentId, agent] of listAgents(config)) {
    if (options.agent && agentId !== options.agent) continue;
    const skillsDir = await resolveSkillsDir(agent);
    const agentManifest = manifest.agents?.[agentId] ?? {};
    for (const [key, entry] of Object.entries<any>(agentManifest).sort()) {
      const repoSlug = entry.repo_slug ?? key.split("/")[0];
      const skillName = key.split("/").slice(1).join("/");
      if (options.repo && repoSlug !== options.repo) continue;
      const installPath = nestedInstallPath(skillsDir, repoSlug, skillName);
      let localHash: string | null = null;
      try {
        localHash = await dirHash(installPath);
      } catch {
        localHash = null;
      }
      const remote = remoteByRepo[repoSlug]?.[skillName];
      const status = computeStatus(
        !!localHash,
        localHash,
        entry.installed_hash,
        entry.remote_fingerprint,
        remote?.fingerprint,
      );
      rows.push({
        agentId,
        repoSlug,
        skill: skillName,
        status,
        installedAt: entry.installed_at ?? "",
      });
    }
  }
  return rows;
}

export function statusExitCode(rows: StatusRow[]): number {
  return rows.some((row) => ["outdated", "modified", "diverged"].includes(row.status)) ? 1 : 0;
}

export async function runStatus(args: any): Promise<number> {
  const rows = await collectStatusRows({
    configPath: args.config,
    token: args.token,
    agent: args.agent,
    repo: args.repo,
    checkRemote: args.checkRemote,
  });
  if (args.format === "json") {
    const payload: Record<string, any[]> = {};
    for (const row of rows) {
      payload[row.agentId] ??= [];
      payload[row.agentId].push({
        repo: row.repoSlug,
        skill: row.skill,
        status: row.status,
        installed_at: row.installedAt,
      });
    }
    console.log(JSON.stringify({ agents: payload }, null, 2));
  } else {
    if (!rows.length) console.log("No skills installed.");
    else {
      console.log("Agent\tRepo\tSkill\tStatus\tInstalled");
      for (const row of rows) {
        console.log(
          `${row.agentId}\t${row.repoSlug}\t${row.skill}\t${row.status}\t${row.installedAt.slice(0, 10)}`,
        );
      }
    }
  }
  return statusExitCode(rows);
}
