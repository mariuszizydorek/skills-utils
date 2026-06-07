import { lstat, rm, symlink } from "node:fs/promises";
import path from "node:path";

export async function ensureFlatSymlink(
  skillsDir: string,
  repoSlug: string,
  skillName: string,
): Promise<void> {
  const link = path.join(skillsDir, skillName);
  const target = path.join(repoSlug, skillName);
  try {
    const info = await lstat(link);
    if (info.isSymbolicLink()) return;
    return;
  } catch {
    // continue
  }
  await rm(link, { force: true });
  await symlink(target, link);
}
