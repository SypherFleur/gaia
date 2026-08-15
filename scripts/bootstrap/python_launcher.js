#!/usr/bin/env node
// Resolves a working Python interpreter across platforms so npm scripts are not
// pinned to the Windows-only `py` launcher. Override with GAIA_PYTHON.
const { spawnSync } = require("node:child_process");

function candidates() {
  if (process.env.GAIA_PYTHON) {
    return [process.env.GAIA_PYTHON.split(" ")];
  }
  const preferred = [["python3"], ["python"]];
  return process.platform === "win32" ? [["py", "-3.13"], ["py", "-3"], ...preferred] : preferred;
}

function works(command) {
  const probe = spawnSync(command[0], [...command.slice(1), "--version"], { stdio: "ignore" });
  return probe.status === 0;
}

const interpreter = candidates().find(works);
if (!interpreter) {
  console.error("No Python interpreter found. Install Python 3.12+ or set GAIA_PYTHON.");
  process.exit(1);
}

const result = spawnSync(interpreter[0], [...interpreter.slice(1), ...process.argv.slice(2)], { stdio: "inherit" });
process.exit(result.status === null ? 1 : result.status);
