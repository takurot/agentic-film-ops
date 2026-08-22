import { spawnSync } from "node:child_process";
import { resolve } from "node:path";

const nextBin = resolve("node_modules", ".bin", process.platform === "win32" ? "next.cmd" : "next");
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
  const result = spawnSync(nextBin, ["build"], { env: { ...baseEnv, ...testCase.env }, encoding: "utf8" });
  const output = `${result.stdout ?? ""}\n${result.stderr ?? ""}`;
  const passed = result.status === 0;
  if (passed !== testCase.succeeds || (testCase.error && !output.includes(testCase.error))) {
    process.stderr.write(`Build config case failed: ${testCase.name}\n${output}`);
    process.exit(1);
  }
  process.stdout.write(`verified: ${testCase.name}\n`);
}
