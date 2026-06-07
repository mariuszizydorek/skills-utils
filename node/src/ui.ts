import { checkbox, confirm, input, select } from "@inquirer/prompts";
import type { SkillState } from "./scanner.js";
import { defaultRepoSlug, parseGithubRepo } from "./repoParse.js";

export async function selectAgent(choices: Array<{ value: string; name: string }>): Promise<string> {
  return select({ message: "Which agent?", choices });
}

export async function selectRepo(choices: Array<{ value: string; name: string }>): Promise<string> {
  return select({
    message: "Remote skills repo:",
    choices: [...choices, { value: "__add__", name: "+ Add new repo..." }],
  });
}

export async function promptNewRepo(): Promise<Record<string, string>> {
  const raw = await input({
    message: "GitHub repo (owner/repo or full URL):",
    validate: (v) => (v.trim().length > 0 ? true : "Required"),
  });
  const [owner, repoName] = parseGithubRepo("", raw);
  const branch = await input({ message: "Branch:", default: "main" });
  const skills_path = await input({ message: "Skills path:", default: "skills" });
  const slug = await input({
    message: "Repo slug (local folder name):",
    default: defaultRepoSlug(owner, repoName),
  });
  console.log(`Will sync from ${owner}/${repoName} → ./${slug}/<skill>`);
  return { slug, owner, repo: repoName, branch, skills_path };
}

export async function selectSkills(states: SkillState[]): Promise<Set<string>> {
  const selectable = states.filter((s) => !s.readOnly);
  const defaults = selectable.filter((s) => s.installed || s.status !== "missing").map((s) => s.name);
  const selected = await checkbox({
    message: "Select skills to install/keep:",
    choices: states.map((s) => ({
      name: s.readOnly ? `${s.name} (${s.note})` : `${s.name} — ${s.note ?? s.status}`,
      value: s.name,
      checked: defaults.includes(s.name),
      disabled: s.readOnly ? true : false,
    })),
  });
  return new Set(selected);
}

export async function selectUpdates(candidates: SkillState[]): Promise<Set<string>> {
  if (!candidates.length) return new Set();
  const selected = await checkbox({
    message: "Update these outdated/modified skills?",
    choices: candidates.map((s) => ({
      name: `${s.name} — ${s.note ?? s.status}`,
      value: s.name,
      checked: true,
    })),
  });
  return new Set(selected);
}

export async function confirmApply(): Promise<boolean> {
  return confirm({ message: "Apply changes?", default: true });
}

export function printPlan(install: string[], remove: string[], updates: string[]): void {
  if (!install.length && !remove.length && !updates.length) {
    console.log("No changes needed.");
    return;
  }
  if (install.length) console.log(`+ install: ${install.join(", ")}`);
  if (remove.length) console.log(`- remove: ${remove.join(", ")}`);
  if (updates.length) console.log(`~ update: ${updates.join(", ")}`);
}

export function printResult(installed: string[], removed: string[], updated: string[]): void {
  console.log("\nDone");
  if (installed.length) console.log(`  Installed: ${installed.join(", ")}`);
  if (removed.length) console.log(`  Removed: ${removed.join(", ")}`);
  if (updated.length) console.log(`  Updated: ${updated.join(", ")}`);
}
