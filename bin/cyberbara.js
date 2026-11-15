#!/usr/bin/env node
"use strict";

const path = require("node:path");
const { spawn } = require("node:child_process");

const packageRoot = path.resolve(__dirname, "..");
const pythonPath = path.join(packageRoot, "src");
const script = [
  "from cyberbara_cli.cli import main",
  "main()"
].join("; ");

const child = spawn("python3", ["-c", script, ...process.argv.slice(2)], {
  stdio: "inherit",
  env: {
    ...process.env,
    PYTHONPATH: pythonPath + (process.env.PYTHONPATH ? path.delimiter + process.env.PYTHONPATH : "")
  }
});

child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }
  process.exit(code ?? 1);
});

child.on("error", (error) => {
  console.error("Failed to start python3 for cyberbara-cli:", error.message);
  process.exit(1);
});
