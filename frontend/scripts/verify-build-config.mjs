import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = resolve(fileURLToPath(new URL("..", import.meta.url)));
const nextBin = resolve(projectRoot, "node_modules", "next", "dist", "bin", "next");
const loadedEnvFiles = [".env", ".env.local", ".env.development", ".env.development.local", ".env.production", ".env.production.local"];
for (const name of loadedEnvFiles) {
  if (existsSync(resolve(projectRoot, name))) {
    process.stderr.write(`Remove frontend/${name} before running test:build-config; Next.js loads it automatically.\n`);
    process.exit(1);
  }
}
const baseEnv = { ...process.env };
delete baseEnv.NEXT_PUBLIC_FILMOPS_MODE;
delete baseEnv.NEXT_PUBLIC_API_URL;

const cases = [
  { name: "missing mode", env: {}, succeeds: false, error: "NEXT_PUBLIC_FILMOPS_MODE" },
  { name: "Live missing API URL", env: { NEXT_PUBLIC_FILMOPS_MODE: "LIVE_GEMINI" }, succeeds: false, error: "NEXT_PUBLIC_API_URL" },
  { name: "Replay", env: { NEXT_PUBLIC_FILMOPS_MODE: "RECORDED_REPLAY" }, succeeds: true },
  { name: "valid Live", env: { NEXT_PUBLIC_FILMOPS_MODE: "LIVE_GEMINI", NEXT_PUBLIC_API_URL: "https://api.example.test" }, succeeds: true },
];

for (const testCase of cases) {
  const result = spawnSync(process.execPath, [nextBin, "build"], {
    cwd: projectRoot,
    env: { ...baseEnv, ...testCase.env },
    encoding: "utf8",
    timeout: 5 * 60_000,
  });
  const output = `${result.stdout ?? ""}\n${result.stderr ?? ""}`;
  if (result.error || result.status === null) {
    process.stderr.write(`Build did not complete: ${testCase.name}\n${result.error?.message ?? "terminated by signal"}\n${output}`);
    process.exit(1);
  }
  const passed = result.status === 0;
  if (passed !== testCase.succeeds || (testCase.error && !output.includes(testCase.error))) {
    process.stderr.write(`Build config case failed: ${testCase.name}\n${output}`);
    process.exit(1);
  }
  process.stdout.write(`verified: ${testCase.name}\n`);
}
