import { copyFile, mkdir, readFile, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import YAML from "yaml";

export const MANIFEST_VERSION = 1;
export const SKILLS_UTILS_HOME = ".skills-utils";

export function homeDir(): string {
  return path.join(os.homedir(), SKILLS_UTILS_HOME);
}

export function cacheDir(): string {
  return path.join(homeDir(), "cache");
}

export function manifestPath(): string {
  return path.join(homeDir(), "manifest.json");
}

function bundledConfigPath(): string {
  return path.join(path.dirname(fileURLToPath(import.meta.url)), "bundled_config.yaml");
}

export async function resolveConfigPath(explicit?: string): Promise<string> {
  if (explicit) return path.resolve(explicit.replace(/^~/, os.homedir()));
  const env = process.env.SKILLS_UTILS_CONFIG;
  if (env) return path.resolve(env.replace(/^~/, os.homedir()));
  const userConfig = path.join(homeDir(), "config.yaml");
  try {
    await readFile(userConfig);
    return userConfig;
  } catch {
    await mkdir(homeDir(), { recursive: true });
    await copyFile(bundledConfigPath(), userConfig);
    return userConfig;
  }
}

async function loadBundledConfig(): Promise<any> {
  const text = await readFile(bundledConfigPath(), "utf8");
  return YAML.parse(text) ?? {};
}

function mergeBundledDefaults(config: any, bundled: any): any {
  for (const [key, value] of Object.entries(bundled.agents ?? {})) {
    config.agents ??= {};
    config.agents[key] ??= value;
  }
  config.repos ??= bundled.repos ?? {};
  config.defaults ??= bundled.defaults ?? {};
  return config;
}

export async function loadConfig(explicit?: string): Promise<any> {
  const configPath = await resolveConfigPath(explicit);
  const text = await readFile(configPath, "utf8");
  const config = YAML.parse(text) ?? {};
  const bundled = await loadBundledConfig();
  return mergeBundledDefaults(config, bundled);
}

export async function loadManifest(): Promise<any> {
  try {
    const text = await readFile(manifestPath(), "utf8");
    const data = JSON.parse(text);
    data.agents ??= {};
    return data;
  } catch {
    return { version: MANIFEST_VERSION, agents: {} };
  }
}

export async function saveManifest(data: any): Promise<void> {
  await mkdir(homeDir(), { recursive: true });
  data.version = MANIFEST_VERSION;
  await writeFile(manifestPath(), `${JSON.stringify(data, null, 2)}\n`);
}

export function utcNowIso(): string {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
}
