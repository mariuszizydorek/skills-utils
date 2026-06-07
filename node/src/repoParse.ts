const GITHUB_URL = /(?:https?:\/\/)?(?:www\.)?github\.com\/([^/]+)\/([^/#?]+)/i;

export function parseGithubRepo(owner: string, repo: string): [string, string] {
  const o = (owner ?? "").trim();
  const r = (repo ?? "").trim();
  for (const candidate of [r, o, `${o}/${r}`.replace(/\/+$/, "")]) {
    if (!candidate) continue;
    const match = candidate.match(GITHUB_URL);
    if (match) return [match[1], match[2].replace(/\.git$/, "")];
  }
  if (o.includes("/") && !r) {
    const [a, b] = o.split("/", 2);
    return [a, b.replace(/\.git$/, "")];
  }
  if (r.includes("/") && !o) {
    const [a, b] = r.split("/", 2);
    return [a, b.replace(/\.git$/, "")];
  }
  return [o, r.replace(/\.git$/, "")];
}

export function defaultRepoSlug(owner: string, repo: string): string {
  if (repo === "skills" || repo === "agent-skills") return owner;
  return repo;
}
