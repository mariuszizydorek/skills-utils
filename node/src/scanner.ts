import path from "node:path";
import { dirHash } from "./hash.js";
import type { RemoteSkill } from "./repos.js";

export type SkillStatus = "missing" | "synced" | "outdated" | "modified" | "diverged";

export interface SkillState {
  name: string;
  status: SkillStatus;
  installed: boolean;
  repoSlug?: string;
  installPath?: string;
  remote?: RemoteSkill;
  readOnly?: boolean;
  note?: string;
}

export function installKey(repoSlug: string, skillName: string): string {
  return `${repoSlug}/${skillName}`;
}

export function nestedInstallPath(skillsDir: string, repoSlug: string, skillName: string): string {
  return path.join(skillsDir, repoSlug, skillName);
}

export function computeStatus(
  installed: boolean,
  localHash: string | null,
  manifestHash: string | null | undefined,
  manifestFingerprint: string | null | undefined,
  remoteFingerprint: string | null | undefined,
): SkillStatus {
  if (!installed) return "missing";
  const outdated =
    remoteFingerprint != null &&
    manifestFingerprint != null &&
    remoteFingerprint !== manifestFingerprint;
  const modified =
    localHash != null && manifestHash != null && localHash !== manifestHash;
  if (outdated && modified) return "diverged";
  if (outdated) return "outdated";
  if (modified) return "modified";
  return "synced";
}

const STATUS_NOTE: Record<SkillStatus, string> = {
  missing: "new",
  synced: "in sync",
  outdated: "remote changed",
  modified: "local differs",
  diverged: "local + remote changed",
};

export async function buildSkillStates(
  repoSlug: string,
  skillsDir: string,
  remoteInventory: Record<string, RemoteSkill>,
  manifest: any,
  agentId: string,
): Promise<SkillState[]> {
  const agentManifest = manifest.agents?.[agentId] ?? {};
  const states: SkillState[] = [];

  for (const [name, remote] of Object.entries(remoteInventory).sort()) {
    const key = installKey(repoSlug, name);
    const entry = agentManifest[key];
    const installPath = nestedInstallPath(skillsDir, repoSlug, name);
    let installed = false;
    let localHash: string | null = null;
    try {
      const { access, constants } = await import("node:fs/promises");
      await access(path.join(installPath, "SKILL.md"));
      installed = true;
      localHash = await dirHash(installPath);
    } catch {
      installed = false;
    }
    const status = computeStatus(
      installed,
      localHash,
      entry?.installed_hash,
      entry?.remote_fingerprint,
      remote.fingerprint,
    );
    states.push({
      name,
      status,
      installed,
      repoSlug,
      installPath,
      remote,
      note: STATUS_NOTE[status],
    });
  }

  return states;
}
