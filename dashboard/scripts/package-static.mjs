import { cpSync, mkdirSync, rmSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { execFileSync } from "node:child_process";

const here = dirname(fileURLToPath(import.meta.url));
const dashboardRoot = resolve(here, "..");
const output = resolve(dashboardRoot, "out");
const target = resolve(dashboardRoot, "..", "proxy", "dashboard_static");

execFileSync("npm", ["run", "build"], { cwd: dashboardRoot, stdio: "inherit" });
rmSync(target, { recursive: true, force: true });
mkdirSync(target, { recursive: true });
cpSync(output, target, { recursive: true });
console.log(`Bundled dashboard into ${target}`);
