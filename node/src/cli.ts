#!/usr/bin/env node
import { writeFile } from "node:fs/promises";
import ora from "ora";
import YAML from "yaml";
import { listAgents, resolveSkillsDir } from "./agents.js";
import { loadConfig, loadManifest, resolveConfigPath, saveManifest } from "./config.js";
import { runDoctor } from "./doctor.js";
import { GitHubClient } from "./github.js";
import { fetchRemoteInventory, repoFromConfig } from "./repos.js";
import { defaultRepoSlug, parseGithubRepo } from "./repoParse.js";
import { buildSkillStates } from "./scanner.js";
import { runStatus } from "./status.js";
import { applySync } from "./sync.js";
import { OraSyncProgress } from "./progress.js";
import {
  confirmApply,
  printPlan,
  printResult,
  promptNewRepo,
  selectAgent,
  selectRepo,
  selectSkills,
  selectUpdates,
} from "./ui.js";

function parseArgs(argv: string[]) {
  const args: any = { command: undefined, format: "table", checkRemote: false, fix: false, noSymlinks: false };
  const rest = [...argv];
  if (!rest.length || !["status", "doctor", "sync"].includes(rest[0])) {
    args.command = rest.length ? undefined : "sync";
  } else {
    args.command = rest.shift();
  }
  while (rest.length) {
    const token = rest.shift();
    if (token === "--config") args.config = rest.shift();
    else if (token === "--token") args.token = rest.shift();
    else if (token === "--agent") args.agent = rest.shift();
    else if (token === "--repo") args.repo = rest.shift();
    else if (token === "--format") args.format = rest.shift();
    else if (token === "--check-remote") args.checkRemote = true;
    else if (token === "--fix") args.fix = true;
    else if (token === "--no-symlinks") args.noSymlinks = true;
  }
  if (!args.command) args.command = "sync";
  return args;
}

async function saveRepoToConfig(
  configPath: string,
  slug: string,
  repoData: Record<string, string>,
): Promise<string> {
  const [owner, repoName] = parseGithubRepo(repoData.owner, repoData.repo);
  if (!slug || slug.startsWith("http") || slug.includes("/")) {
    slug = defaultRepoSlug(owner, repoName);
  }
  const config = await loadConfig(configPath);
  config.repos ??= {};
  config.repos[slug] = {
    owner,
    repo: repoName,
    branch: repoData.branch,
    skills_path: repoData.skills_path,
  };
  await writeFile(configPath, YAML.stringify(config));
  console.log(`Added repo: ${owner}/${repoName} (slug: ${slug})`);
  return slug;
}

async function runInteractive(args: any): Promise<number> {
  const configPath = await resolveConfigPath(args.config);
  let config = await loadConfig(args.config);
  const manifest = await loadManifest();
  const flatSymlinks = config.defaults?.flat_symlinks !== false && !args.noSymlinks;

  const agentChoices = await Promise.all(
    listAgents(config).map(async ([agentId, agent]) => ({
      value: agentId,
      name: `${agent.label ?? agentId} → ${await resolveSkillsDir(agent)}`,
    })),
  );
  const agentId = await selectAgent(agentChoices);
  const agent = config.agents[agentId];
  const skillsDir = await resolveSkillsDir(agent);
  await import("node:fs/promises").then((fs) => fs.mkdir(skillsDir, { recursive: true }));

  const repoChoices = Object.entries(config.repos ?? {}).map(([slug, data]: [string, any]) => ({
    value: slug,
    name: `${data.owner}/${data.repo}`,
  }));
  let repoSlug = await selectRepo(repoChoices);
  if (repoSlug === "__add__") {
    const newRepo = await promptNewRepo();
    repoSlug = await saveRepoToConfig(configPath, newRepo.slug, newRepo);
    config = await loadConfig(args.config);
  }
  const repo = repoFromConfig(repoSlug, config.repos[repoSlug]);
  const token = args.token ?? (await GitHubClient.detectToken());
  const client = new GitHubClient(token);
  const spinner = ora(`Checking ${repo.owner}/${repo.repo}…`).start();
  const [commitSha, remoteInventory] = await fetchRemoteInventory(client, repo);
  spinner.stop();

  const states = await buildSkillStates(repo.slug, skillsDir, remoteInventory, manifest, agentId);
  const selected = await selectSkills(states);
  const existing = new Set(
    states.filter((s) => !s.readOnly && s.installed && s.repoSlug === repo.slug).map((s) => s.name),
  );
  const install = [...selected].filter((n) => !existing.has(n)).sort();
  const remove = [...existing].filter((n) => !selected.has(n)).sort();
  const updateCandidates = states.filter(
    (s) => selected.has(s.name) && ["outdated", "modified", "diverged"].includes(s.status) && !s.readOnly,
  );
  printPlan(install, remove, updateCandidates.map((s) => s.name));
  if (!install.length && !remove.length && !updateCandidates.length) return 0;
  if (!(await confirmApply())) {
    console.log("Cancelled.");
    return 0;
  }
  const toUpdate = await selectUpdates(updateCandidates);
  const progress = new OraSyncProgress();
  try {
    const result = await applySync(
      client,
      repo,
      agentId,
      manifest,
      remoteInventory,
      commitSha,
      selected,
      toUpdate,
      flatSymlinks,
      skillsDir,
      progress,
    );
    await saveManifest(manifest);
    const parts = [];
    if (result.installed.length) parts.push(`installed ${result.installed.length}`);
    if (result.removed.length) parts.push(`removed ${result.removed.length}`);
    if (result.updated.length) parts.push(`updated ${result.updated.length}`);
    progress.succeed(parts.length ? `Done — ${parts.join(", ")}` : "Done — no changes");
    printResult(result.installed, result.removed, result.updated);
  } catch (error) {
    progress.fail("Sync failed");
    throw error;
  }
  return 0;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.command === "status") process.exit(await runStatus(args));
  if (args.command === "doctor") process.exit(await runDoctor(args));
  if (!process.stdin.isTTY) {
    console.error("Interactive sync requires a TTY. Use 'skills-sync-node status'.");
    process.exit(2);
  }
  process.exit(await runInteractive(args));
}

main().catch((error) => {
  console.error(error);
  process.exit(2);
});
