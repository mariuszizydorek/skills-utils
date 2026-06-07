import { createHash } from "node:crypto";
import { readdir, readFile, stat } from "node:fs/promises";
import path from "node:path";

const IGNORE = new Set([".git", "__pycache__", ".DS_Store"]);

async function walkFiles(root: string): Promise<string[]> {
  const entries = await readdir(root, { withFileTypes: true });
  const files: string[] = [];
  for (const entry of entries) {
    if (IGNORE.has(entry.name)) continue;
    const full = path.join(root, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await walkFiles(full)));
    } else if (entry.isFile()) {
      files.push(full);
    }
  }
  return files.sort();
}

export function hashFromMap(mapping: Record<string, string>): string {
  const payload = JSON.stringify(Object.fromEntries(Object.entries(mapping).sort()));
  return `sha256:${createHash("sha256").update(payload).digest("hex")}`;
}

export async function dirHash(root: string): Promise<string> {
  if (!(await stat(root).catch(() => null))) return hashFromMap({});
  const files = await walkFiles(root);
  const mapping: Record<string, string> = {};
  for (const file of files) {
    const rel = path.relative(root, file).split(path.sep).join("/");
    const bytes = await readFile(file);
    mapping[rel] = createHash("sha256").update(bytes).digest("hex");
  }
  return hashFromMap(mapping);
}

export function remoteFingerprint(blobMap: Record<string, string>): string {
  return hashFromMap(blobMap);
}
