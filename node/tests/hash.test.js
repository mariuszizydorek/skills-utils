import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { dirHash, hashFromMap, remoteFingerprint } from "../dist/hash.js";

test("hash from map is deterministic", () => {
  const mapping = { "SKILL.md": "abc", "scripts/run.py": "def" };
  assert.equal(hashFromMap(mapping), hashFromMap({ "scripts/run.py": "def", "SKILL.md": "abc" }));
});

test("remote fingerprint matches dir hash", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "skill-"));
  const skill = path.join(root, "pdf");
  await mkdir(skill);
  await writeFile(path.join(skill, "SKILL.md"), "---\nname: pdf\n---\nbody\n");
  await mkdir(path.join(skill, "scripts"));
  await writeFile(path.join(skill, "scripts", "run.py"), "print('hi')\n");
  const { createHash } = await import("node:crypto");
  const { readdir, readFile, stat } = await import("node:fs/promises");
  async function walk(dir, base, out) {
    for (const entry of await readdir(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) await walk(full, base, out);
      else {
        const rel = path.relative(base, full).split(path.sep).join("/");
        out[rel] = createHash("sha256").update(await readFile(full)).digest("hex");
      }
    }
  }
  const mapping = {};
  await walk(skill, skill, mapping);
  assert.equal(remoteFingerprint(mapping), await dirHash(skill));
});
