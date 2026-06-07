import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

export class GitHubClient {
  token: string | null;

  constructor(token?: string | null) {
    this.token = token ?? null;
  }

  static async detectToken(): Promise<string | null> {
    const env = process.env.GITHUB_TOKEN ?? process.env.GH_TOKEN;
    if (env) return env;
    try {
      const { stdout } = await execFileAsync("gh", ["auth", "token"]);
      return stdout.trim() || null;
    } catch {
      return null;
    }
  }

  private headers(): Record<string, string> {
    const headers: Record<string, string> = {
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
    };
    if (this.token) headers.Authorization = `Bearer ${this.token}`;
    return headers;
  }

  async get(urlPath: string, params?: Record<string, string>): Promise<any> {
    const url = new URL(`https://api.github.com${urlPath}`);
    if (params) {
      for (const [key, value] of Object.entries(params)) url.searchParams.set(key, value);
    }
    const response = await fetch(url, { headers: this.headers() });
    if (!response.ok) throw new Error(`GitHub API ${response.status}: ${urlPath}`);
    return response.json();
  }

  async resolveCommitSha(owner: string, repo: string, branch: string): Promise<string> {
    const data = await this.get(`/repos/${owner}/${repo}/commits/${branch}`);
    return data.sha;
  }

  async listSkillDirs(owner: string, repo: string, skillsPath: string): Promise<string[]> {
    const data = await this.get(`/repos/${owner}/${repo}/contents/${skillsPath}`);
    if (!Array.isArray(data)) throw new Error(`Expected directory at ${skillsPath}`);
    return data.filter((item) => item.type === "dir").map((item) => item.name).sort();
  }

  async fetchTree(owner: string, repo: string, ref: string): Promise<any[]> {
    const commitSha = await this.resolveCommitSha(owner, repo, ref);
    const commit = await this.get(`/repos/${owner}/${repo}/git/commits/${commitSha}`);
    const treeSha = commit.tree.sha;
    const data = await this.get(`/repos/${owner}/${repo}/git/trees/${treeSha}`, { recursive: "1" });
    return data.tree ?? [];
  }

  async downloadBlob(owner: string, repo: string, blobSha: string): Promise<Buffer> {
    const data = await this.get(`/repos/${owner}/${repo}/git/blobs/${blobSha}`);
    return Buffer.from(data.content, data.encoding === "base64" ? "base64" : "utf8");
  }

  async ping(): Promise<boolean> {
    try {
      await this.get("/rate_limit");
      return true;
    } catch {
      return false;
    }
  }
}
