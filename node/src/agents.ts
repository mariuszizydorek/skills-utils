import os from "node:os";
import path from "node:path";

export function expandPath(value: string, cwd = process.cwd()): string {
  const expanded = value.startsWith("~") ? path.join(os.homedir(), value.slice(1)) : value;
  return path.isAbsolute(expanded) ? expanded : path.resolve(cwd, expanded);
}

export async function projectRoot(cwd = process.cwd()): Promise<string> {
  // Project-scoped installs should target the directory where the user runs the CLI.
  return cwd;
}

export async function resolveSkillsDir(agent: any, cwd = process.cwd()): Promise<string> {
  if (agent.scope === "project") {
    const root = await projectRoot(cwd);
    return expandPath(agent.skills_dir, root);
  }
  return expandPath(agent.skills_dir, cwd);
}

export function listAgents(config: any): Array<[string, any]> {
  return Object.entries(config.agents ?? {});
}
