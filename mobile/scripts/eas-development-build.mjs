import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const [platform, ...easArgs] = process.argv.slice(2);
const supportedPlatforms = new Set(["android", "ios"]);

if (!supportedPlatforms.has(platform)) {
  console.error(
    "Usage: node ./scripts/eas-development-build.mjs <android|ios> [EAS options]",
  );
  process.exit(1);
}

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const npmCliPath = process.env.npm_execpath;

if (!npmCliPath) {
  console.error("Run this command through one of the npm build scripts.");
  process.exit(1);
}

const npxCliPath = resolve(dirname(npmCliPath), "npx-cli.js");

const result = spawnSync(
  process.execPath,
  [
    npxCliPath,
    "eas-cli@latest",
    "build",
    "--platform",
    platform,
    "--profile",
    "development",
    ...easArgs,
  ],
  {
    cwd: projectRoot,
    env: {
      ...process.env,
      EAS_NO_VCS: "1",
      EAS_PROJECT_ROOT: projectRoot,
    },
    shell: false,
    stdio: "inherit",
  },
);

if (result.error) {
  console.error(`Unable to start EAS Build: ${result.error.message}`);
  process.exit(1);
}

process.exit(result.status ?? 1);
